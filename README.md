# AI Nutrition Assistant

Milestone 1 prototype: a chatbot for food, nutrition, and food-safety questions with structured responses, code-enforced scope limits, and an empty Sources panel ready for Milestone 2 citations.

Source of truth for scope and design:

- [`docs/problemStatement.md`](docs/problemStatement.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/implementation-plan.md`](docs/implementation-plan.md)

## Stack

| Layer | Choice |
| --- | --- |
| Web | Next.js (App Router) + TypeScript — `apps/web` |
| API | FastAPI — `services/api` |
| Storage | Postgres (prod) / SQLite ok locally — Phase 3 |
| Model | OpenAI or Anthropic structured outputs — Phase 4 |
| Deploy | Vercel (web) + Railway (API) — Phase 7 |

## Phase status

| Phase | Status |
| --- | --- |
| 0 Foundations | Done |
| 1 Response contract & stub `/api/chat` | Done |
| 2 Chat UI shell | Done |
| 3 Conversation persistence | Done |
| 4 LLM structured outputs | Done |
| 5 Scope limits & system prompt | Done |
| 6 Eval set & prompt discipline | Done |
| 7 Deploy (GitHub, Vercel, Railway) | Ready — see [`docs/deploy.md`](docs/deploy.md) |
| 8 Failure log & submission | Next |

## Setup

```bash
# From repo root
cp .env.example .env
# Fill secrets in .env later (Phase 4+). Never commit .env.
```

### API

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Health: [http://localhost:8000/health](http://localhost:8000/health) → `{"status":"ok"}`
- Stub chat:

```bash
curl -s http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":null,"message":"How much protein do vegetarians need?"}'
```

```bash
# Schema / stub tests (no LLM)
cd services/api && pytest
```

### Web

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env` (or `apps/web/.env.local`) when the client starts calling the API (Phase 2).

## Repo layout

```text
apps/web/          Next.js frontend
services/api/      FastAPI backend
docs/              Problem statement, architecture, plan, eval
.env.example       Env contract (no secrets)
```

## API errors (Phase 1)

| HTTP | Code | When |
| --- | --- | --- |
| 400 | `empty_message` / `validation_error` / `message_too_long` | Blank, invalid, or oversized chat body |
| 404 | `conversation_not_found` | Unknown conversation id |
| 429 | `rate_limited` | Too many requests |
| 502 | `schema_validation_failed` | Invalid model structured output (never ship prose) |
| 503 | `provider_unavailable` | LLM timeout/quota/misconfig |

Envelope: `{ "error": { "code": "...", "message": "..." } }`

## Persistence (Phase 3)

- Default DB: SQLite (`DATABASE_URL=sqlite:///./local.db`)
- Optional Postgres: `docker compose up -d` then set `DATABASE_URL=postgresql+psycopg://nutrition:nutrition@localhost:5432/nutrition`
- `POST /api/chat` creates/continues conversations and stores turns
- `GET /api/conversations/{id}` reloads history (UI uses this on refresh)
- Unknown `conversation_id` → `404 conversation_not_found`
- Message max length: 4000 characters

## LLM (Phase 4)

- Providers: `LLM_PROVIDER=openai` | `anthropic` | `stub` (stub = local deterministic, no key)
- Structured outputs bound to `AssistantResponse`; invalid output → `502 schema_validation_failed` (no prose shipped)
- Every `claims[].source` forced to `null` in code
- Keys stay server-side only (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`)
- Light per-IP rate limit via `RATE_LIMIT_PER_MINUTE`

## Scope limits (Phase 5)

- System prompt `v1` at `services/api/app/core/prompts/v1.md` (changelog: `docs/prompt-changelog.md`)
- `ScopeGuard` pre-check skips the LLM on calorie/weight targets and medical advice
- Post-check replaces leaked targets/medical advice with a refusal (`declined: true`, empty claims)
- Definitional questions (e.g. “What is a calorie?”) stay in scope

## Eval set (Phase 6)

- Frozen questions: [`docs/eval-questions.json`](docs/eval-questions.json) (10 core + scope probes/controls)
- Checklist: [`docs/eval-checklist.md`](docs/eval-checklist.md)
- Runner:

```bash
# API must be running
python scripts/run_eval.py --suite all --api-url http://localhost:8000 \
  --out docs/eval-runs/manual.json
```

- After every prompt edit: re-run the full set; never hardcode eval answers in app code

## Deploy (Phase 7)

Full runbook: [`docs/deploy.md`](docs/deploy.md)

| Target | Path / config |
| --- | --- |
| GitHub | Push this monorepo |
| Railway API | Root dir `services/api` — `Dockerfile` + `railway.toml`, health `/health` |
| Railway DB | Postgres plugin → `DATABASE_URL` |
| Vercel web | Root dir `apps/web` — set `NEXT_PUBLIC_API_URL` to Railway URL |
| CORS | Railway `CORS_ORIGINS` = Vercel origin |

```bash
# After Railway + Vercel are live:
python scripts/smoke_prod.py \
  --api-url https://<railway-api>.up.railway.app \
  --web-origin https://<app>.vercel.app
```

## Next

Continue with **Phase 8** in `docs/implementation-plan.md` (failure log & submission).
