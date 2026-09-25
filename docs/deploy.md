# Deployment (Phase 7)

GitHub → Railway (API + Postgres) → Vercel (Next.js). Model keys never go in the frontend.

## Prerequisites

- GitHub account (`gh` authenticated)
- [Railway](https://railway.app) account (`railway login`)
- [Vercel](https://vercel.com) account (`npx vercel login`)
- Optional LLM key if not using `LLM_PROVIDER=stub`

## 1. Push to GitHub

```bash
cd "AI Nutrition"
git init -b main          # if not already a repo
git add -A
git commit -m "Initial commit: Milestone 1 AI Nutrition Assistant"
gh repo create ai-nutrition --private --source=. --remote=origin --push
```

Or create an empty repo on github.com, then:

```bash
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

## 2. Railway — API + Postgres

1. New project → **Deploy from GitHub** → select this repo.
2. Set **Root Directory** to `services/api` (uses `Dockerfile` + `railway.toml`).
3. Add plugin: **PostgreSQL**.
4. Link Postgres so `DATABASE_URL` is injected (Railway does this when you reference the DB).
5. Set variables on the API service:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | From Postgres plugin (auto) |
| `CORS_ORIGINS` | Your Vercel origin, e.g. `https://your-app.vercel.app` (comma-separate if multiple) |
| `LLM_PROVIDER` | `stub` (or `openai` / `anthropic`) |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Only if not stub |
| `MODEL_NAME` | e.g. `gpt-4o-mini` |
| `RATE_LIMIT_PER_MINUTE` | `30` (optional) |

6. Healthcheck is `/health` (configured in `railway.toml`). Confirm:

```bash
curl -s https://<your-railway-api>.up.railway.app/health
# {"status":"ok"}
```

Postgres URLs from Railway (`postgresql://…`) are normalized to SQLAlchemy `postgresql+psycopg://` in code.

## 3. Vercel — Web

1. Import the same GitHub repo in Vercel.
2. Set **Root Directory** to `apps/web`.
3. Environment variable:

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Railway public API URL (no trailing slash), e.g. `https://….up.railway.app` |

4. Deploy. Note the production URL (`https://….vercel.app`).
5. Go back to Railway and set `CORS_ORIGINS` to that exact Vercel origin (scheme + host, no path). Redeploy API if needed.

## 4. Smoke test (prod)

```bash
python scripts/smoke_prod.py \
  --api-url https://<railway-api>.up.railway.app \
  --web-origin https://<app>.vercel.app
```

Checks:

- `GET /health` → ok
- In-scope chat → 200, `declined: false`, all `claims[].source` null
- Out-of-scope (calorie target) → `declined: true`
- Multi-turn: second message reuses `conversation_id` and persists

Also open the Vercel URL in a browser: Sources panel should stay empty (Milestone 1).

## Local Docker API (optional)

```bash
cd services/api
docker build -t nutrition-api .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=sqlite:////tmp/local.db \
  -e CORS_ORIGINS=http://localhost:3000 \
  -e LLM_PROVIDER=stub \
  nutrition-api
```

## Secrets reminder

- Never put `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in Vercel or `NEXT_PUBLIC_*` vars.
- Only `NEXT_PUBLIC_API_URL` is public by design.
