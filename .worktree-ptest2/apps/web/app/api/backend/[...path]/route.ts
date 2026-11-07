import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const allowed =
  /^(learners|topics|topics\/[^/]+|graph|placement\/next|attempts|tutor\/hint|uploads|reviews\/due)$/;

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const segments = (await context.params).path;
  if (
    segments.some(
      (segment) => [".", ".."].includes(segment) || /[%/\\?#]/.test(segment),
    )
  )
    return new Response(null, { status: 404 });
  const path = segments.join("/");
  if (!allowed.test(path)) return new Response(null, { status: 404 });
  if (
    request.method === "POST" &&
    request.headers.get("origin") !== request.nextUrl.origin
  )
    return new Response(null, { status: 403 });
  const origin = process.env.NODETRAIL_API_URL;
  const key = process.env.NODETRAIL_API_KEY;
  const keyHeader = process.env.NODETRAIL_API_KEY_HEADER;
  if (
    process.env.NODETRAIL_DATA_MODE !== "api" ||
    !origin ||
    !key ||
    !keyHeader ||
    !/^[A-Za-z0-9-]+$/.test(keyHeader) ||
    ["host", "content-type", "content-length", "cookie", "origin"].includes(
      keyHeader.toLowerCase(),
    )
  )
    return new Response(null, { status: 503 });
  try {
    const base = new URL(origin);
    if (
      !["http:", "https:"].includes(base.protocol) ||
      base.username ||
      base.password ||
      base.search ||
      base.hash
    )
      return new Response(null, { status: 503 });
    const target = new URL(
      `${base.pathname.replace(/\/$/, "")}/${path}`,
      base.origin,
    );
    for (const name of ["learner_id", "subject"]) {
      const value = request.nextUrl.searchParams.get(name);
      if (value) target.searchParams.set(name, value);
    }
    const headers = new Headers({ [keyHeader]: key });
    const contentType = request.headers.get("content-type");
    if (contentType) headers.set("content-type", contentType);
    const signals = AbortSignal.any([
      request.signal,
      AbortSignal.timeout(25000),
    ]);
    let body: Uint8Array | undefined;
    if (request.method === "POST") {
      const limit =
        path === "uploads"
          ? Number(process.env.NODETRAIL_MAX_UPLOAD_BYTES) + 64 * 1024
          : 64 * 1024;
      if (
        !Number.isSafeInteger(limit) ||
        (limit <= 64 * 1024 && path === "uploads")
      )
        return new Response(null, { status: 503 });
      const reader = request.body?.getReader();
      const chunks: Uint8Array[] = [];
      let size = 0;
      if (reader) {
        while (true) {
          const next = await reader.read();
          if (next.done) break;
          size += next.value.byteLength;
          if (size > limit) {
            await reader.cancel();
            return new Response(null, { status: 413 });
          }
          chunks.push(next.value);
        }
      }
      body = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) {
        body.set(chunk, offset);
        offset += chunk.byteLength;
      }
    }
    const response = await fetch(target, {
      method: request.method,
      headers,
      body: body as BodyInit | undefined,
      cache: "no-store",
      signal: signals,
      redirect: "error",
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return new Response(null, { status: 502 });
  }
}
export { proxy as GET, proxy as POST };
