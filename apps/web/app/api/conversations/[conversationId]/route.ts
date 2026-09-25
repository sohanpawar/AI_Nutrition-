import { NextResponse } from "next/server";

import { getBackendBaseUrl } from "@/lib/backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ conversationId: string }>;
};

export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const backend = getBackendBaseUrl();
  if (!backend) {
    return NextResponse.json(
      {
        error: {
          code: "config_error",
          message:
            "Backend URL is not configured. Set BACKEND_API_URL (or API_URL) on Vercel to your Railway API origin.",
        },
      },
      { status: 500 },
    );
  }

  const { conversationId } = await context.params;
  const target = `${backend}/api/conversations/${encodeURIComponent(conversationId)}`;

  try {
    const upstream = await fetch(target, {
      method: "GET",
      headers: { Accept: "application/json" },
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
