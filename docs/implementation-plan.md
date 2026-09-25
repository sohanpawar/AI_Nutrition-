# Implementation Plan — AI Nutrition Assistant Prototype

Phase-wise plan for Milestone 1, derived from [`problemStatement.md`](./problemStatement.md) and [`architecture.md`](./architecture.md).

**Stack locked for this plan:** Next.js (Vercel) + FastAPI (Railway) + Postgres + OpenAI or Anthropic structured outputs.

**Guiding rules (do not violate in any phase):**

- Model calls only on the backend
- Response schema is stable; `claims[].source` stays `null`
- Scope limits live in code **and** the prompt
- Fail closed on schema parse errors
- Record failures; do not hardcode fixes for eval questions
- Sources panel exists now, empty until Milestone 2

---

## Phase Overview

| Phase | Name | Outcome |
| --- | --- | --- |
| 0 | Foundations | Repo, docs, env contracts, shared schema types |
| 1 | Contract & stub API | Typed schema + chat stub that returns valid structured JSON |
| 2 | Chat UI shell | Message list, input, empty Sources panel wired to stub |
| 3 | Persistence | Conversations/messages in Postgres |
| 4 | LLM integration | Real structured completions, validation, `source` nulling |
| 5 | Scope & prompt | Code guards + system prompt v1 + refusal tests |
| 6 | Eval harness | Fixed 10 questions + scope probes + prompt changelog process |
| 7 | Deploy | GitHub + Vercel + Railway public URL |
| 8 | Failure log & submit | Consistency tests, failure log, README |

Phases 1–5 are mostly sequential. Phase 6 can start as soon as Phase 5 lands. Phase 7 can begin in parallel once Phase 4 works locally. Phase 8 depends on a live (or stable local) pipeline.

---

## Phase 0 — Foundations

**Goal:** Scaffold the monorepo and freeze contracts before features.

### Tasks

- [x] Create repo layout per architecture (`apps/web`, `services/api`, `docs/`)
- [x] Add `.env.example` with `LLM_PROVIDER`, API keys, `MODEL_NAME`, `DATABASE_URL`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`
- [x] Initialize Next.js (App Router, TypeScript) in `apps/web`
- [x] Initialize FastAPI project in `services/api` with `requirements.txt` / `pyproject.toml`
- [x] Add `GET /health` returning `{ "status": "ok" }`
- [x] Document local run commands in a scratch `README` stub
- [x] Keep `docs/problemStatement.md` and `docs/architecture.md` as source of truth

### Deliverables

- Runnable empty web app and API health endpoint
- Env contract checked in (no secrets)

### Exit criteria

- [x] `uvicorn` serves `/health`
- [x] `next dev` loads a blank page
- [x] No provider keys in the repo

---

## Phase 1 — Response Contract & Stub API

**Goal:** Lock the Milestone 1/2 response schema and exercise it without an LLM.

### Tasks

- [x] Define Pydantic models: `Claim`, `AssistantResponse` (`answer`, `claims[]`, `declined`, `decline_reason`)
- [x] Mirror types in `apps/web/lib/types.ts`
- [x] Implement `POST /api/chat` stub:
  - Accept `{ conversation_id: string | null, message: string }`
  - Return canned valid `AssistantResponse` with `claims[].source = null`
  - Include `conversation_id` / `message_id` in the response DTO
- [x] Validate outbound payload with Pydantic before respond
- [x] Add unit tests that reject malformed claim objects and accept `source: null`
- [x] Define error shapes for 400 (empty message) and document 502 (future schema failure)

### Deliverables

- Shared schema (Python + TypeScript)
- Stub chat endpoint returning contract-compliant JSON

### Exit criteria

- [x] `curl`/`httpie` against stub returns parseable body matching architecture §8
- [x] Schema tests pass without calling an LLM

---

## Phase 2 — Chat Frontend Shell

**Goal:** Ship the three UI regions the brief requires, backed by the stub.

### Tasks

- [x] Build layout: message list | input | Sources panel (side-by-side on desktop; stacked on mobile)
- [x] `MessageList` / `MessageBubble` for user + assistant turns
- [x] `ChatInput` with send + disabled-while-sending
- [x] `SourcesPanel` always visible; empty state copy (e.g. “Sources will appear here when citations are available”)
- [x] Wire Sources panel to selected/latest assistant message’s `claims[].source` (all null → stays empty)
- [x] Client `POST` to stub API; render `answer` (optionally list claim texts under the bubble)
- [x] Track `conversationId` in React state + `localStorage`
- [x] Basic error UI for failed requests
- [x] CORS on FastAPI for local Next origin (`http://localhost:3000`)

### Deliverables

- Usable chat UI against stub
- Empty Sources panel ready for Milestone 2 data

### Exit criteria

- [x] User can send a message and see a structured stub reply
- [x] Sources panel renders empty for every Milestone 1 response
- [x] Layout matches “message list + input + sources panel”

---

## Phase 3 — Conversation Persistence

**Goal:** Store threads so history survives refresh and multi-turn context works.

### Tasks

- [x] Provision local Postgres (Docker) or SQLite for local-only if preferred; prefer Postgres to match prod
- [x] SQLAlchemy (or equivalent) models: `conversations`, `messages` per architecture §11
- [x] Repository helpers: create conversation, append messages, load history by id
- [x] Update `POST /api/chat` to create conversation when `conversation_id` is null
- [x] Persist user message + assistant payload (`content`, `claims` JSONB, `declined`, `decline_reason`)
- [x] Implement `GET /api/conversations/{id}` for UI reload
- [x] On unknown `conversation_id`, return 404 (or documented create-new behavior)
- [x] Bound message length (e.g. 2–4k chars) at the API layer

### Deliverables

- Durable conversation storage
- History reload endpoint

### Exit criteria

- [x] Refresh restores prior turns for a stored `conversation_id`
- [x] Multi-turn history is available to the upcoming LLM step

---

## Phase 4 — LLM Structured Outputs

**Goal:** Replace the stub with a real server-side model call; fail closed on bad output.

### Tasks

- [x] Implement `llm.py`: provider client, timeout, one transient retry
- [x] Call OpenAI or Anthropic **structured output** mode bound to `AssistantResponse`
- [x] Chat orchestrator pipeline steps 4–7 and 9–10 from architecture §7.1 (scope comes in Phase 5)
- [x] Build messages: system placeholder + DB history + new user message
- [x] Pydantic-validate model output; on failure → log raw payload, return 502, **do not** ship prose
- [x] Normalize: force every `claim.source = null` in code
- [x] Keep API keys in server env only
- [x] Optional: light rate limit on `/api/chat`
- [x] Integration test (mocked LLM) for happy path + schema failure path
- [x] Leave Milestone 2 stub comments where retrieval will plug in

### Deliverables

- Live nutrition Q&A through the real pipeline
- Schema enforcement and `source` null invariant

### Exit criteria

- [x] In-scope food/nutrition question returns validated structured JSON
- [x] Invalid model mock → 502, no unparsed answer in DB/UI
- [x] Browser network tab shows no provider API key traffic

---

## Phase 5 — Scope Limits & System Prompt

**Goal:** Decline calorie/weight targets and medical advice in code and prompt; survive rephrases.

### Tasks

#### System prompt

- [x] Write prompt v1 covering: role, how it answers, length limits, what it won’t touch, uncertainty handling
- [x] Store as versioned artifact (`prompts/v1` + load in `prompts.py`)
- [x] Start `docs/prompt-changelog.md` with v1 rationale

#### ScopeGuard (code)

- [x] `pre_check(user_message)` — block calorie/weight targets and medical advice; skip LLM on block
- [x] `post_check(assistant_payload)` — scan answer + claims; replace with refusal if leaked
- [x] Return same response schema with `declined: true`, empty `claims`, professional redirect copy
- [x] Wire pre/post into orchestrator (architecture §7.1 steps 3 and 8)

#### Tests (required by brief)

- [x] Direct: daily calorie target → decline
- [x] Direct: condition-specific diet → decline
- [x] Rephrased variants of both
- [x] Sideways / indirect phrasing
- [x] Same asks after unrelated in-scope turns in one conversation
- [x] Confirm in-scope questions still answer

### Deliverables

- Dual-layer scope enforcement
- Prompt v1 + changelog entry
- Automated refusal tests

### Exit criteria

- [x] All refusal probes decline every time
- [x] Prompt alone is not the only control — code paths proven by tests

---

## Phase 6 — Eval Set & Prompt Discipline

**Goal:** Freeze the 10 questions and the process for safe prompt iteration.

### Tasks

- [x] Author `docs/eval-questions.json`:
  - **10 questions** across: nutrient requirements, food safety/storage, cooking methods, no-clear-answer
  - Separate **scope probes** for refusal regression
- [x] Add a small script or checklist to run the fixed set after every prompt change
- [x] Rule: never hardcode answers for eval questions in app code
- [x] Document “re-run all after every prompt edit” in `prompt-changelog.md`

### Deliverables

- Fixed eval artifact used for failure log and future Milestone 2 comparison
- Prompt change process in writing

### Exit criteria

- [x] 10 questions + scope probes checked in
- [x] Team can re-run the set without inventing new questions each time

---

## Phase 7 — Deploy (GitHub, Vercel, Railway)

**Goal:** Public working prototype URL.

### Tasks

- [x] Push repo to GitHub — https://github.com/sohanpawar/ai-nutrition
- [x] Dockerfile / start command for FastAPI on Railway (`services/api/Dockerfile`, `railway.toml`)
- [x] Railway: Postgres + API service; set secrets (`DATABASE_URL`, LLM keys, `CORS_ORIGINS`) — documented in [`docs/deploy.md`](./deploy.md) *(needs `railway login` in dashboard/CLI)*
- [x] Healthcheck → `GET /health` (Railway `healthcheckPath` + Docker HEALTHCHECK)
- [x] Vercel: deploy `apps/web`; set `NEXT_PUBLIC_API_URL` to Railway URL — `apps/web/vercel.json` + deploy doc *(needs `vercel login`)*
- [x] Restrict CORS to the Vercel origin (`CORS_ORIGINS` env; prod instructions in deploy doc)
- [x] Smoke test script: in-scope, refusal, multi-turn, null sources (`scripts/smoke_prod.py`)
- [x] Confirm Sources panel still empty in production (checklist in deploy doc)

### Deliverables

- Live frontend URL *(pending Vercel login + project create — see [`docs/deploy.md`](./deploy.md))*
- Live backend + DB *(pending Railway login + project create — see [`docs/deploy.md`](./deploy.md))*
- GitHub remote: https://github.com/sohanpawar/ai-nutrition
- [`docs/deploy.md`](./deploy.md) runbook

### Exit criteria

- Anyone can open the public URL and chat
- Model keys never exposed to the client
- Prod behavior matches local for scope + schema

---

## Phase 8 — Failure Log, Consistency, Submission

**Goal:** Meet “Before You Submit” and submission checklist without patching hallucinations.

### Tasks

#### Consistency

- [ ] Ask the same in-scope question **3 times**; compare substance (especially numbers), not wording
- [ ] Record any number drift for the failure log

#### Failure log

- [ ] Run all 10 eval questions against the live (or final) build
- [ ] For each response, record in `docs/failure-log.md`:
  - Unsupported factual claims
  - Numbers that shift between runs
  - Sources cited that cannot be found (including invented authorities inside `answer` prose)
  - Questions that should have been declined
  - Useless hedging
- [ ] Group failures and count by type
- [ ] Do **not** hardcode fixes; leave baseline for Milestone 2 comparison

#### Scope retest on prod

- [ ] Calorie target, medical/condition diet, rephrase, sideways, after unrelated messages — all decline

#### README & handoff

- [ ] README covers: system prompt, response schema, prompt version history + why, how scope is enforced in code, tech stack
- [ ] Include GitHub link + live prototype URL
- [ ] Demo video (≤ 3 min) only if live URL unavailable: normal question, follow-up, refusal; Drive link viewable by anyone

### Deliverables

- `docs/failure-log.md` with grouped counts
- Submission-ready `README.md`
- Public URL (and optional demo video)

### Exit criteria

- Architecture §20 success checklist fully checked
- Problem statement submission requirements satisfied

---

## Dependency Graph

```text
Phase 0 Foundations
    └─▶ Phase 1 Contract & stub
            └─▶ Phase 2 Chat UI ──────────┐
            └─▶ Phase 3 Persistence ──────┤
                        └─▶ Phase 4 LLM ◀─┘
                                └─▶ Phase 5 Scope & prompt
                                        └─▶ Phase 6 Eval harness
                                └─▶ Phase 7 Deploy (can start once Phase 4 works)
                                        └─▶ Phase 8 Failure log & submit
                                              (needs Phase 5–7 + Phase 6 questions)
```

---

## Suggested Timeline (flexible)

| Phase | Rough effort |
| --- | --- |
| 0 Foundations | 0.5 day |
| 1 Contract & stub | 0.5 day |
| 2 Chat UI | 1 day |
| 3 Persistence | 0.5–1 day |
| 4 LLM | 1 day |
| 5 Scope & prompt | 1 day |
| 6 Eval harness | 0.5 day |
| 7 Deploy | 0.5–1 day |
| 8 Failure log & submit | 1 day |

Total: ~6–8 working days depending on deploy friction and eval thoroughness.

---

## Explicit Non-Goals During These Phases

Do not schedule or sneak in:

- Retrieval, embeddings, vector DB, real citations
- Populating Sources panel with fake sources
- Streaming token UI
- Auth / multi-user accounts
- Hardcoded special cases for the 10 eval questions

Those belong to Milestone 2 or are out of scope.

---

## Definition of Done (Milestone 1)

The project is done when all of the following are true:

1. Chat UI has message list, input, and empty Sources panel  
2. Backend owns model calls; structured responses validate; `source` is always `null`  
3. Scope limits enforced in code + prompt; refusal tests pass under rephrase / sideways / mid-thread  
4. Conversations persist  
5. App is live at a public URL (Vercel + Railway)  
6. Failure log for 10 questions is filled, grouped, and counted — not patched away  
7. README includes prompt, schema, prompt changelog, scope enforcement, and stack  

References: [`problemStatement.md`](./problemStatement.md), [`architecture.md`](./architecture.md).
