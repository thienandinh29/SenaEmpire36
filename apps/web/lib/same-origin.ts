import type { NextRequest } from "next/server";

export function isSameOrigin(request: NextRequest): boolean {
  // Next's URL may use its 0.0.0.0 bind address; Host is the browser-facing authority.
  const host = request.headers.get("host") ?? request.nextUrl.host;
  return (
    request.headers.get("origin") === `${request.nextUrl.protocol}//${host}`
  );
}
