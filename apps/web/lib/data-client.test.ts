import { afterEach, describe, expect, it, vi } from "vitest";
import { createLearningClient } from "./data-client";
import type { WebConfig } from "./config";
import {
  parseGraph,
  parseTrace,
  parseItem,
  parseHint,
  parseGraphReview,
} from "./decode";
import { getWebConfig } from "./config";
import { safeSourceUrl, validateFile } from "./safety";

const config: WebConfig = {
  mode: "api",
  uploadField: null,
  uploadMaxBytes: 10 * 1024 * 1024,
  answerEncoding: null,
  hintFirstLevel: null,
};
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("live data boundary", () => {
  const node = {
    slug: "cells",
    name_vi: "Tế bào",
    p_known: 0.2,
    mastered: false,
  };
  const review = {
    learner_id: "learner",
    subject: "biology",
    graph_revision: "a".repeat(64),
    confirmed: false,
    graph: {
      concepts: [
        {
          slug: "cells",
          name_vi: "Tế bào",
          description_vi: "Nguồn kiến thức",
          sources: ["https://example.com/cells"],
        },
      ],
      edges: [],
    },
  };
  it("always uses API mode, including when old configuration requests mock mode", () => {
    vi.stubEnv("NODETRAIL_DATA_MODE", "mock");
    expect(getWebConfig().mode).toBe("api");
  });
  it("loads the reviewed graph and server mastery without automatically confirming", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(review)))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ nodes: [node], edges: [] })),
      );
    vi.stubGlobal("fetch", fetchMock);
    const result = await createLearningClient(config).review(
      "learner",
      "biology",
    );
    expect(result.revision).toBe(review.graph_revision);
    expect(result.confirmed).toBe(false);
    expect(result.concepts[0].description_vi).toBe("Nguồn kiến thức");
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/backend/graph/review?subject=biology",
      "/api/backend/graph?learner_id=learner&subject=biology",
    ]);
    expect(
      fetchMock.mock.calls.every(([, init]) => init.method !== "POST"),
    ).toBe(true);
  });
  it("rejects a revision paired with another learner, subject or topology", () => {
    const graph = { nodes: [node], edges: [] };
    expect(() => parseGraphReview(review, graph, "other", "biology")).toThrow(
      "contract",
    );
    expect(() => parseGraphReview(review, graph, "learner", "other")).toThrow(
      "contract",
    );
    expect(() =>
      parseGraphReview(
        { ...review, graph_revision: "invalid" },
        graph,
        "learner",
        "biology",
      ),
    ).toThrow("contract");
    expect(() =>
      parseGraphReview(
        review,
        { nodes: [{ ...node, slug: "changed" }], edges: [] },
        "learner",
        "biology",
      ),
    ).toThrow("failed");
  });
  it("posts explicit confirmation and preserves stale-revision errors", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 409 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(
      createLearningClient(config).confirm("biology", review.graph_revision),
    ).rejects.toMatchObject({ status: 409 });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      subject: "biology",
      graph_revision: review.graph_revision,
    });
  });
  it("fetches the real next-item and does not invent one when unavailable", async () => {
    const item = {
      id: "verified-item",
      kind: "mcq",
      prompt_vi: "Câu hỏi đã kiểm chứng",
      options: [{ label: "A" }, { label: "B" }],
      answer: 1,
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ item, reason_vi: "Do bộ máy học tập chọn" }),
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 404 }));
    vi.stubGlobal("fetch", fetchMock);
    const client = createLearningClient(config);
    const next = await client.nextItem("learner", "biology");
    expect(next.item.id).toBe(item.id);
    expect(next.item).not.toHaveProperty("answer");
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/backend/next-item?learner_id=learner&subject=biology",
    );
    await expect(client.nextItem("learner", "biology")).rejects.toMatchObject({
      status: 404,
    });
  });
  it("accepts real tutor citations with optional sections and PDF pages", () => {
    expect(
      parseHint({
        hint_vi: "Gợi ý có nguồn",
        citations: [
          {
            title: "Giáo trình",
            section: null,
            url: "https://example.com/book.pdf",
            page: 8,
          },
        ],
      }).citations[0],
    ).toMatchObject({ page: 8 });
  });
  it("keeps an attempt key on network retry and rotates it only after success", async () => {
    const result = { correct: true, p_known: 0.6, mastered: false, traces: [] };
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("lost response"))
      .mockImplementation(() =>
        Promise.resolve(new Response(JSON.stringify(result))),
      );
    vi.stubGlobal("fetch", fetchMock);
    const client = createLearningClient({
      ...config,
      mode: "api",
      answerEncoding: "index0",
    });
    const item = {
      id: "i1",
      kind: "mcq" as const,
      prompt_vi: "?",
      options: [{ label: "a" }, { label: "b" }],
    };
    await expect(client.attempt("u1", item, "c", 0, 0)).rejects.toMatchObject({
      code: "network",
    });
    await client.attempt("u1", item, "c", 0, 0);
    await client.attempt("u1", item, "c", 1, 0);
    const bodies = fetchMock.mock.calls.map(([, init]) =>
      JSON.parse(init.body),
    );
    expect(bodies[0].client_attempt_id).toBe(bodies[1].client_attempt_id);
    expect(bodies[2].client_attempt_id).not.toBe(bodies[1].client_attempt_id);
  });
  it("sends an upload only after explicit demo consent", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ upload_id: "u1", pages: 1, text_ok: true }),
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const client = createLearningClient({
      ...config,
      mode: "api",
      uploadField: "file",
    });
    const file = new File(["public demo material"], "a.pdf");
    await expect(client.upload(file, false)).rejects.toMatchObject({
      code: "configuration",
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(await client.upload(file, true)).toEqual({
      upload_id: "u1",
      pages: 1,
      text_ok: true,
    });
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get("X-Demo-Upload-Consent")).toBe(
      "demo-v1",
    );
  });
  it("rejects malformed data and never substitutes a sample graph", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ nodes: [{ slug: "a" }], edges: [] })),
        ),
    );
    const client = createLearningClient({ ...config, mode: "api" });
    await expect(client.graph("learner", "subject")).rejects.toMatchObject({
      code: "contract",
    });
  });
  it("blocks unknown upload and answer conventions before making a network request", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const client = createLearningClient({ ...config, mode: "api" });
    await expect(
      client.upload(new File(["demo"], "a.pdf"), true),
    ).rejects.toMatchObject({ code: "configuration" });
    await expect(
      client.attempt(
        "learner",
        {
          id: "item",
          kind: "mcq",
          prompt_vi: "?",
          options: [{ label: "a" }, { label: "b" }],
        },
        "node",
        0,
        0,
      ),
    ).rejects.toMatchObject({ code: "configuration" });
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("rejects cycles, dangling edges and invalid probabilities", () => {
    const node = { slug: "a", name_vi: "A", p_known: 0.4, mastered: false };
    expect(() =>
      parseGraph({ nodes: [node], edges: [{ from: "a", to: "unknown" }] }),
    ).toThrow("contract");
    expect(() =>
      parseGraph({
        nodes: [node, { ...node, slug: "b" }],
        edges: [
          { from: "a", to: "b" },
          { from: "b", to: "a" },
        ],
      }),
    ).toThrow("contract");
    expect(() =>
      parseGraph({ nodes: [{ ...node, p_known: 1.2 }], edges: [] }),
    ).toThrow("contract");
    expect(parseGraph({ nodes: [], edges: [] })).toEqual({
      nodes: [],
      edges: [],
    });
  });
  it("retains trace evidence exactly and strips nonpublic item fields", () => {
    const value = {
      kind: "root_cause",
      concept_slug: "a",
      at: "2026-11-07T06:00:00Z",
      prior: 0.7,
      posterior: 0.3,
      evidence: { correct: false, slip: 0, guess: 0.25, item_id: "i" },
      rule: "r",
      rule_vi: "Dữ liệu thật",
      alternatives: [],
    };
    expect(parseTrace(value).evidence).toMatchObject(value.evidence);
    const item = parseItem({
      id: "i",
      kind: "mcq",
      prompt_vi: "?",
      answer: 1,
      options: [
        { label: "a", correct: true },
        { label: "b", correct: false },
      ],
    });
    expect(item).not.toHaveProperty("answer");
    expect(item.options[0]).not.toHaveProperty("correct");
  });
});

describe("source and upload validation", () => {
  it.each([
    "javascript:alert(1)",
    "data:text/html,hi",
    "file:///secret.pdf",
    "//other.example",
    "https://u:p@example.com",
    "not-a-url",
  ])("blocks unsafe source %s", (url) => expect(safeSourceUrl(url)).toBeNull());
  it("preserves section fragments and opens a PDF page only when provided", () => {
    expect(safeSourceUrl("https://example.com/book#section")).toBe(
      "https://example.com/book#section",
    );
    expect(safeSourceUrl("https://example.com/book.pdf?download=1", 5)).toBe(
      "https://example.com/book.pdf?download=1#page=5",
    );
  });
  it("distinguishes unsupported, empty, oversized and unconfigured uploads", () => {
    expect(validateFile({ name: "x.exe", size: 10 }, 100)).toBe("format");
    expect(validateFile({ name: "x.pdf", size: 0 }, 100)).toBe("size");
    expect(validateFile({ name: "x.pdf", size: 101 }, 100)).toBe("size");
    expect(validateFile({ name: "x.pdf", size: 10 }, null)).toBe(
      "unconfigured",
    );
    expect(validateFile({ name: "Đề cương.DOCX", size: 10 }, 100)).toBeNull();
  });
});
