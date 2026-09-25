import { NextResponse } from "next/server";

import { getBackendBaseUrl } from "@/lib/backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function proxy(request: Request): Promise<Response> {
  const backend = getBackendBaseUrl();
  if (!backend) {
    return NextResponse.json(
      {
        error: {
          code: "config_error",
          message:
            "Backend URL is not configured. Set BACKEND_API_URL (or API_URL) on Vercel to your Railway API origin, e.g. https://….up.railway.app",
        },
      },
      { status: 500 },
    );
  }

  const target = `${backend}/api/chat`;
  let body: string;
  try {
    body = await request.text();
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "invalid_request",
          message: "Could not read request body.",
        },
      },
      { status: 400 },
    );
  }

  try {
    const upstream = await fetch(target, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body,
      cache: "no-store",
    });

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("Content-Type") ?? "application/json",
      },
    });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Upstream request failed";
    return NextResponse.json(
      {
        error: {
          code: "upstream_unreachable",
          message: `Could not reach API at ${backend}: ${message}`,
        },
      },
      { status: 502 },
    );
  }
}

export async function POST(request: Request): Promise<Response> {
  return proxy(request);
}
