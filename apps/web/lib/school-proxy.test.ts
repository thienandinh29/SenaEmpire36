import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "@/app/api/school/[...path]/route";

const classId = "11111111-1111-4111-8111-111111111111";
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });
function configure() {
  vi.stubEnv("NODETRAIL_DATA_MODE", "api");
  vi.stubEnv("NODETRAIL_API_URL", "http://127.0.0.1:8019");
  vi.stubEnv("NODETRAIL_API_KEY", "server-only-key");
  vi.stubEnv("NODETRAIL_API_KEY_HEADER", "X-API-Key");
}
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});
describe("school proxy", () => {
  it("forwards only the learner credential and class-scoped teacher key", async () => {
    configure();
    const mock = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", mock);
    const key = "k".repeat(43);
    const learner = "l".repeat(43);
    const response = await GET(
      new NextRequest(`http://localhost:3019/api/school/classes/${classId}`, {
        headers: {
          cookie: `other=private; nodetrail_learner=${learner}`,
          "X-Class-Key": key,
        },
      }),
      context(["classes", classId]),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("referrer-policy")).toBe("no-referrer");
    const headers = mock.mock.calls[0][1].headers as Headers;
    expect(headers.get("cookie")).toBe(`nodetrail_learner=${learner}`);
    expect(headers.get("x-class-key")).toBe(key);
    expect(headers.get("x-api-key")).toBe("server-only-key");
    expect(await response.text()).not.toContain("server-only-key");
    await GET(
      new NextRequest("http://localhost:3019/api/school/curricula", {
        headers: { "X-Class-Key": key },
      }),
      context(["curricula"]),
    );
    expect(
      (mock.mock.calls[1][1].headers as Headers).get("x-class-key"),
    ).toBeNull();
  });
  it("rejects cross-origin writes and unsupported paths before contacting the API", async () => {
    configure();
    const mock = vi.fn();
    vi.stubGlobal("fetch", mock);
    expect(
      (
        await POST(
          new NextRequest("http://localhost:3019/api/school/classes", {
            method: "POST",
            headers: { origin: "https://other.example" },
            body: "{}",
          }),
          context(["classes"]),
        )
      ).status,
    ).toBe(403);
    expect(
      (
        await GET(
          new NextRequest("http://localhost:3019/api/school/anything"),
          context(["..", "classes"]),
        )
      ).status,
    ).toBe(404);
    expect(mock).not.toHaveBeenCalled();
  });
  it("bounds JSON bodies and never follows upstream redirects", async () => {
    configure();
    const mock = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", mock);
    const request = (body: string) =>
      new NextRequest("http://localhost:3019/api/school/curricula", {
        method: "POST",
        headers: {
          origin: "http://localhost:3019",
          "content-type": "application/json",
        },
        body,
      });
    expect(
      (await POST(request("x".repeat(33000)), context(["curricula"]))).status,
    ).toBe(413);
    expect(mock).not.toHaveBeenCalled();
    await POST(request("{}"), context(["curricula"]));
    expect(mock.mock.calls[0][1].redirect).toBe("error");
  });
});
