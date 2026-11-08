import { describe, expect, it, vi, afterEach } from "vitest";
import { shuffleAnswers } from "./answer-order";
import { createLearningClient } from "./data-client";
import { getWebConfig } from "./config";

afterEach(() => vi.restoreAllMocks());
const item = {
  id: "question",
  kind: "mcq" as const,
  prompt_vi: "?",
  options: ["correct", "wrong-1", "wrong-2", "wrong-3"].map((label) => ({
    label,
  })),
};

describe("choice presentation", () => {
  it("moves the correct choice away from A without changing source options", () => {
    const shuffled = shuffleAnswers(item, () => 0);
    expect(shuffled.item.options[0].label).not.toBe("correct");
    expect(item.options[0].label).toBe("correct");
    expect(new Set(shuffled.order).size).toBe(4);
  });
  it("maps displayed selections back to canonical indices before grading", async () => {
    vi.spyOn(Math, "random").mockReturnValue(0);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ item, reason_vi: "Review", concept_slug: "a" }),
        ),
      )
      .mockResolvedValueOnce(new Response("{}", { status: 503 }));
    vi.stubGlobal("fetch", fetchMock);
    const client = createLearningClient(getWebConfig());
    const next = await client.nextItem("learner", "subject");
    const displayed = next!.item.options.findIndex(
      (option) => option.label === "correct",
    );
    expect(displayed).not.toBe(0);
    await expect(
      client.attempt("learner", next!.item, "a", displayed, 0),
    ).rejects.toBeDefined();
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).answer).toBe(0);
    vi.unstubAllGlobals();
  });
});
