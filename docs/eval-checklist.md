# Eval checklist (after every prompt change)

Use this checklist whenever you edit the system prompt. Do **not** invent new questions — use the frozen set in [`eval-questions.json`](./eval-questions.json).

## Rules

1. Never hardcode answers for eval questions in application code.
2. Re-run the **full** fixed set after every prompt edit.
3. Record failures in `failure-log.md`; do not patch hallucinations for a prettier log.
4. Keep `core10` wording identical through Milestone 2.

## Steps

- [ ] Bump / note prompt version in [`prompt-changelog.md`](./prompt-changelog.md) (what changed and why)
- [ ] Ensure API is running (`uvicorn` local or deployed URL)
- [ ] Run scope suite (hard gate):

```bash
python scripts/run_eval.py --suite scope --api-url http://localhost:8000
```

- [ ] Run core 10 (contract check; annotate failures manually for submission):

```bash
python scripts/run_eval.py --suite core10 --api-url http://localhost:8000 \
  --out docs/eval-runs/$(date +%Y%m%d)-core10.json
```

- [ ] Optional consistency (numeric drift):

```bash
python scripts/run_eval.py --suite consistency --api-url http://localhost:8000
```

- [ ] Or run everything:

```bash
python scripts/run_eval.py --suite all --api-url http://localhost:8000 \
  --out docs/eval-runs/$(date +%Y%m%d)-all.json
```

- [ ] Update [`prompt-changelog.md`](./prompt-changelog.md) with eval outcome (pass/fail counts + notable regressions)
- [ ] If a refusal probe fails: fix **ScopeGuard** and/or prompt — do not special-case the question text in code

## Suites

| Suite | Purpose | Gate |
| --- | --- | --- |
| `scope` | Refusal regression + in-scope controls | Fail CI/local if any probe fails |
| `core10` | Fixed 10 for failure log / Milestone 2 compare | Contract only (`answer` present, sources null) |
| `consistency` | Same question × 3 | Manual number comparison |

See also [`eval.md`](./eval.md) for taxonomy and failure-log template.
