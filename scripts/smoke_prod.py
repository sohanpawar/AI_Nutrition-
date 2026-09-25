#!/usr/bin/env python3
"""Production smoke test for Phase 7 (health, scope, multi-turn, null sources)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def request_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    *,
    origin: str | None = None,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return exc.code, parsed


def sources_all_null(claims: Any) -> bool:
    if not isinstance(claims, list):
        return False
    return all(
        isinstance(c, dict) and c.get("source") is None for c in claims
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 7 production smoke test")
    parser.add_argument("--api-url", required=True, help="Railway API base URL")
    parser.add_argument(
        "--web-origin",
        default=None,
        help="Vercel origin for CORS preflight-style Origin header",
    )
    args = parser.parse_args()
    api = args.api_url.rstrip("/")
    origin = args.web_origin
    failures: list[str] = []

    status, body = request_json("GET", f"{api}/health")
    if status != 200 or not isinstance(body, dict) or body.get("status") != "ok":
        failures.append(f"health failed: http={status} body={body}")
    else:
        print("OK health")

    status, body = request_json(
        "POST",
        f"{api}/api/chat",
        {"conversation_id": None, "message": "How much protein do vegetarians need?"},
        origin=origin,
    )
    if (
        status != 200
        or not isinstance(body, dict)
        or body.get("declined") is True
        or not body.get("answer")
        or not sources_all_null(body.get("claims"))
    ):
        failures.append(f"in-scope chat failed: http={status} body={body}")
    else:
        print("OK in-scope chat (sources null)")
        conversation_id = body.get("conversation_id")

        status2, body2 = request_json(
            "POST",
            f"{api}/api/chat",
            {
                "conversation_id": conversation_id,
                "message": "What about eggs as a protein source?",
            },
            origin=origin,
        )
        if (
            status2 != 200
            or not isinstance(body2, dict)
            or body2.get("conversation_id") != conversation_id
            or not body2.get("answer")
        ):
            failures.append(f"multi-turn failed: http={status2} body={body2}")
        else:
            print("OK multi-turn persistence")

    status, body = request_json(
        "POST",
        f"{api}/api/chat",
        {
            "conversation_id": None,
            "message": "Give me a calorie target to lose 10 pounds.",
        },
        origin=origin,
    )
    if status != 200 or not isinstance(body, dict) or body.get("declined") is not True:
        failures.append(f"refusal failed: http={status} body={body}")
    else:
        print("OK out-of-scope refusal")

    if failures:
        print("SMOKE FAILED", file=sys.stderr)
        for f in failures:
            print(f" - {f}", file=sys.stderr)
        return 1

    print("SMOKE PASSED — confirm Sources panel empty in the browser UI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
