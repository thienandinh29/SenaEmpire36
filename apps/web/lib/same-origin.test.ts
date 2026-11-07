import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { isSameOrigin } from "./same-origin";

describe("browser-facing origin", () => {
  it("accepts the actual LAN host when Next uses its bind address", () => {
    const request = new NextRequest(
      "http://0.0.0.0:3019/api/backend/learners",
      {
        headers: {
          host: "192.168.1.20:3019",
          origin: "http://192.168.1.20:3019",
        },
      },
    );
    expect(isSameOrigin(request)).toBe(true);
  });
  it.each([
    "https://other.example",
    "null",
    "http://localhost:3020",
    "https://localhost:3019",
  ])("rejects mismatched origin %s", (origin) => {
    expect(
      isSameOrigin(
        new NextRequest("http://0.0.0.0:3019/api/school/classes", {
          headers: { host: "localhost:3019", origin },
        }),
      ),
    ).toBe(false);
  });
  it("rejects writes without an origin", () => {
    expect(
      isSameOrigin(new NextRequest("http://localhost:3019/api/school/classes")),
    ).toBe(false);
  });
});
