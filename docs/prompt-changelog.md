# Prompt changelog

Track system-prompt versions, why they changed, and eval outcomes.

## Process (required)

1. Edit the versioned prompt under `services/api/app/core/prompts/`.
2. Add a changelog entry **before** merging the change.
3. Re-run the **full frozen set** in [`eval-questions.json`](./eval-questions.json) using [`eval-checklist.md`](./eval-checklist.md) / `scripts/run_eval.py`.
4. Record pass/fail counts and notable regressions here.
5. **Never** hardcode answers for eval questions in application code.

## v1 — 2026-09-25

**Why:** Phase 5 baseline. Replace the Phase 4 placeholder with a full prompt covering role, answer style, length, out-of-scope boundaries, and uncertainty.

**Contents:**
- Role: food / nutrition / food-safety assistant (non-clinical)
- Answer style: concise, claim-structured, `source` always null
- Length: ~2–4 short paragraphs
- Won’t touch: calorie/weight targets, medical advice — decline with redirect
- Uncertainty: prefer honesty over fabricated certainty

**Code pairing:** `ScopeGuard` pre/post checks enforce the same boundaries in code (prompt alone is not trusted).

**Eval:** Frozen set added in Phase 6 (`docs/eval-questions.json`). After any prompt edit, re-run:

```bash
python scripts/run_eval.py --suite all --api-url http://localhost:8000
```
