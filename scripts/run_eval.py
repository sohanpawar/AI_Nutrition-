#!/usr/bin/env python3
"""Run the frozen Milestone 1 eval set against a live API.

Usage:
  python scripts/run_eval.py
  python scripts/run_eval.py --api-url http://localhost:8000 --suite all
  python scripts/run_eval.py --suite scope
  python scripts/run_eval.py --suite core10 --out docs/eval-runs/latest.json

Rules:
  - Never hardcode answers for these questions in app code.
  - Re-run after every prompt change.
  - This script records outcomes; it does not “fix” hallucinations.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "docs" / "eval-questions.json"


def load_questions() -> dict[str, Any]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def post_chat(api_url: str, message: str, conversation_id: str | None) -> dict[str, Any]:
    payload = {"conversation_id": conversation_id, "message": message}
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return {
                "http_status": resp.status,
                "body": json.loads(resp.read().decode("utf-8")),
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw": raw}
        return {"http_status": exc.code, "body": body}


def all_sources_null(claims: list[dict[str, Any]] | None) -> bool:
    if not claims:
        return True
    return all(c.get("source") is None for c in claims)


def evaluate_expect(body: dict[str, Any], expect: str) -> dict[str, Any]:
    declined = bool(body.get("declined"))
    if expect == "decline":
        ok = declined is True and body.get("claims") == []
        return {
            "ok": ok,
            "detail": "declined with empty claims" if ok else "expected decline",
        }
    # expect == "answer"
    ok = declined is False and bool(body.get("answer"))
    return {
        "ok": ok,
        "detail": "answered in scope" if ok else "expected non-declined answer",
    }


def run_item(
    api_url: str,
    item: dict[str, Any],
    *,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    result = post_chat(api_url, item["question"], conversation_id)
    body = result.get("body") or {}
    expect = item.get("expect")
    entry: dict[str, Any] = {
        "id": item["id"],
        "question": item["question"],
        "http_status": result["http_status"],
        "conversation_id": body.get("conversation_id"),
        "message_id": body.get("message_id"),
        "declined": body.get("declined"),
        "decline_reason": body.get("decline_reason"),
        "answer": body.get("answer"),
        "claims": body.get("claims"),
        "sources_all_null": all_sources_null(body.get("claims")),
    }
    if expect:
        entry["expect"] = expect
        check = evaluate_expect(body, expect) if result["http_status"] == 200 else {
            "ok": False,
            "detail": f"http {result['http_status']}",
        }
        entry["pass"] = check["ok"]
        entry["check_detail"] = check["detail"]
    else:
        # Core10: no correctness gate — only contract checks.
        entry["pass"] = (
            result["http_status"] == 200
            and bool(body.get("answer"))
            and all_sources_null(body.get("claims"))
        )
        entry["check_detail"] = (
            "contract ok (answer + null sources)"
            if entry["pass"]
            else "contract failed"
        )
    return entry


def run_core10(api_url: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    return [run_item(api_url, item) for item in data["core10"]]


def run_scope(api_url: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    conversation_ids: dict[str, str] = {}

    for item in data["scope_controls"]:
        results.append(run_item(api_url, item))

    for item in data["scope_probes"]:
        reuse_from = item.get("reuse_conversation_from")
        conversation_id = conversation_ids.get(reuse_from) if reuse_from else None
        entry = run_item(api_url, item, conversation_id=conversation_id)
        if entry.get("conversation_id"):
            conversation_ids[item["id"]] = entry["conversation_id"]
            # Mid-thread probes reuse the setup conversation.
            if item["id"] in {"S7a", "S7b"}:
                conversation_ids["S7a"] = entry["conversation_id"]
        results.append(entry)
    return results


def run_consistency(api_url: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {q["id"]: q for q in data["core10"]}
    results: list[dict[str, Any]] = []
    for item in data["consistency"]:
        question = by_id[item["id"]]
        runs = []
        for i in range(int(item.get("runs", 3))):
            entry = run_item(api_url, question)
            entry["run_index"] = i + 1
            runs.append(entry)
        results.append(
            {
                "id": item["id"],
                "question": question["question"],
                "runs": runs,
                "notes": item.get("notes"),
                "pass": all(r["pass"] for r in runs),
                "check_detail": "manual: compare numbers across runs in failure-log",
            }
        )
    return results


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    total = len(rows)
    passed = sum(1 for r in rows if r.get("pass"))
    return {"total": total, "passed": passed, "failed": total - passed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen AI Nutrition eval set")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument(
        "--suite",
        choices=["all", "core10", "scope", "consistency"],
        default="all",
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    data = load_questions()
    started = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "started_at": started,
        "api_url": args.api_url,
        "questions_version": data.get("version"),
        "suite": args.suite,
        "results": {},
        "summary": {},
    }

    print(f"Eval against {args.api_url} (suite={args.suite})")
    print(f"Questions: {QUESTIONS_PATH}")

    if args.suite in {"all", "scope"}:
        scope_rows = run_scope(args.api_url, data)
        report["results"]["scope"] = scope_rows
        report["summary"]["scope"] = summarize(scope_rows)
        print(f"SCOPE  {report['summary']['scope']}")

    if args.suite in {"all", "core10"}:
        core_rows = run_core10(args.api_url, data)
        report["results"]["core10"] = core_rows
        report["summary"]["core10"] = summarize(core_rows)
        print(f"CORE10 {report['summary']['core10']}")

    if args.suite in {"all", "consistency"}:
        consist_rows = run_consistency(args.api_url, data)
        report["results"]["consistency"] = consist_rows
        report["summary"]["consistency"] = summarize(consist_rows)
        print(f"CONSIST {report['summary']['consistency']}")

    # Print failures
    for suite_name, rows in report["results"].items():
        flat = rows
        if suite_name == "consistency":
            flat = [r for group in rows for r in group["runs"]]
        for row in flat:
            if not row.get("pass"):
                print(
                    f"FAIL [{suite_name}] {row.get('id')}: {row.get('check_detail')} "
                    f"(http={row.get('http_status')})"
                )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")

    # Scope suite is a hard gate; core10 is contract-only (not factual correctness).
    scope_summary = report["summary"].get("scope")
    if scope_summary and scope_summary["failed"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
