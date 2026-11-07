import { NextRequest } from "next/server";
import { isSameOrigin } from "@/lib/same-origin";

const id = "[0-9a-f-]{36}";
const allowed = new RegExp(
  `^(session|library|curricula(?:/outline|/${id}(?:/lessons/${id}/(?:start|material|link))?)?|classes(?:/join|/${id})?)$`,
);
const token = /^[A-Za-z0-9_-]{43}$/;

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const segments = (await context.params).path;
  if (segments.some((part) => !/^[a-z0-9-]+$/.test(part)))
    return new Response(null, { status: 404 });
  const path = segments.join("/");
  if (!allowed.test(path)) return new Response(null, { status: 404 });
  if (request.method === "POST" && !isSameOrigin(request))
    return new Response(null, { status: 403 });
  const key = process.env.NODETRAIL_API_KEY;
  const header = process.env.NODETRAIL_API_KEY_HEADER;
  const origin = process.env.NODETRAIL_API_URL;
  if (
    process.env.NODETRAIL_DATA_MODE !== "api" ||
    !key ||
    !origin ||
    !header ||
    !/^[A-Za-z0-9-]+$/.test(header) ||
    ["cookie", "host", "content-type", "origin"].includes(header.toLowerCase())
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
      `${base.pathname.replace(/\/$/, "")}/school/${path}`,
      base.origin,
    );
    const headers = new Headers({ [header]: key });
    const learner = request.cookies.get("nodetrail_learner")?.value;
    if (learner && token.test(learner))
      headers.set("cookie", `nodetrail_learner=${learner}`);
    const teacher = request.headers.get("x-class-key");
    if (
      teacher &&
      token.test(teacher) &&
      new RegExp(`^classes/${id}$`).test(path)
    )
      headers.set("x-class-key", teacher);
    let body: Uint8Array | undefined;
    if (request.method === "POST") {
      if (!request.headers.get("content-type")?.startsWith("application/json"))
        return new Response(null, { status: 415 });
      headers.set("content-type", "application/json");
      const reader = request.body?.getReader();
      const chunks: Uint8Array[] = [];
      let size = 0;
      if (reader)
        while (true) {
          const chunk = await reader.read();
          if (chunk.done) break;
          size += chunk.value.byteLength;
          if (size > 32 * 1024) {
            await reader.cancel();
            return new Response(null, { status: 413 });
          }
          chunks.push(chunk.value);
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
      redirect: "error",
      cache: "no-store",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(25000)]),
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
      },
    });
  } catch {
    return new Response(null, { status: 502 });
  }
}
export { proxy as GET, proxy as POST };
