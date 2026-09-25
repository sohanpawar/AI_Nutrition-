# Architecture — AI Nutrition Assistant Prototype

## 1. Purpose

This document defines how to build the Milestone 1 prototype described in [`problemStatement.md`](./problemStatement.md).

Milestone 1 goals:

- Chat UI with an empty Sources panel (ready for Milestone 2 citations)
- Backend-owned model calls with structured output
- Response contract with `claims[].source = null`
- Scope limits enforced in **code and** the system prompt
- Conversation persistence
- Failure log for unsupported / inconsistent claims (recorded, not patched)
- Public deployment

Milestone 2 will add retrieval under the same interfaces. Architecture choices below treat the response schema, API shapes, and Sources panel as stable contracts.

---

## 2. Recommended Stack

| Layer | Choice | Rationale |
| --- | --- | --- |
| Frontend | **Next.js (App Router) + TypeScript** | Single app for UI + optional edge helpers; deploys cleanly to Vercel |
| Backend | **FastAPI (Python)** | Clear place for model calls, schema validation, scope checks, and future RAG |
| Model | **OpenAI** (`gpt-4o` / `gpt-4o-mini`) **or Anthropic** (`claude-sonnet`) with **structured outputs** | Required; avoids fragile prose parsing |
| Validation | **Pydantic** (backend) + shared TypeScript types (frontend) | Fail closed when output does not match schema |
| Storage | **Postgres** (Supabase or Railway Postgres) | Conversation history; SQLite acceptable for local-only |
| Frontend host | **Vercel** | Static/SSR Next.js |
| Backend host | **Railway** | FastAPI + env secrets for API keys |
| Scaffolding | Cursor | As allowed |

**Why split frontend/backend?**

- Model API keys stay off the client (hard rule).
- Scope checks, schema parse failures, and later retrieval live in one service.
- Milestone 2 can add a retrieval pipeline without rewriting the Next.js UI or the chat contract.

**Acceptable alternative:** Next.js full-stack (Route Handlers) on Vercel only. Prefer FastAPI if you want a cleaner RAG insertion point in Milestone 2.

---

## 3. High-Level System Diagram

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Browser)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Message List │  │ Input Box    │  │ Sources Panel (empty) │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────▲───────────┘  │
│         │                 │                      │              │
│         └────────┬────────┘                      │              │
│                  │ POST /api/chat                │              │
│                  │ GET  /api/conversations/:id   │ sources[]    │
└──────────────────┼───────────────────────────────┼──────────────┘
                   │                               │
                   ▼                               │
┌──────────────────────────────────────────────────┼──────────────┐
│                     FastAPI Backend              │              │
│  ┌─────────────────┐  ┌──────────────────────┐   │              │
│  │ Scope Guard     │─▶│ Chat Orchestrator    │───┘              │
│  │ (code, not just │  │ - load history       │                  │
│  │  prompt)        │  │ - call LLM           │                  │
│  └─────────────────┘  │ - validate schema    │                  │
│                       │ - force source=null  │                  │
│                       │ - persist messages   │                  │
│                       └──────────┬───────────┘                  │
│                                  │                              │
│         ┌────────────────────────┼────────────────────┐         │
│         ▼                        ▼                    ▼         │
│  ┌─────────────┐      ┌──────────────────┐   ┌──────────────┐  │
│  │ System      │      │ LLM Provider     │   │ Postgres     │  │
│  │ Prompt      │      │ (OpenAI /        │   │ conversations│  │
│  │ Store       │      │  Anthropic       │   │ messages     │  │
│  │             │      │  structured out) │   │              │  │
│  └─────────────┘      └──────────────────┘   └──────────────┘  │
│                                                                 │
│  [Milestone 2 insertion] Retrieval / RAG ──▶ fill claim.source │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Design Principles

1. **Contract first** — Response JSON shape does not change in Milestone 2; only `source` values do.
2. **Fail closed** — Invalid model output → HTTP 502/422 with a clear error; do not invent a fallback prose answer.
3. **Defense in depth for scope** — Prompt declines out-of-scope topics; code blocks them before and after the model call.
4. **Sources panel is real UI** — Render the panel now with empty state; wire it to `claims[].source` so Milestone 2 is a data fill, not a UI rewrite.
5. **Observe, don't patch** — Failure log captures hallucinations and inconsistencies; do not hardcode special-case answers for the 10 eval questions.
6. **Server-only model access** — Browser never holds provider API keys.

---

## 5. Repository Layout

```text
ai-nutrition/
├── docs/
│   ├── problemStatement.md
│   ├── architecture.md          ← this file
│   ├── failure-log.md           ← Milestone 1 eval results
│   ├── eval-questions.json      ← fixed set of 10 questions
│   └── prompt-changelog.md      ← prompt versions + why
├── apps/
│   └── web/                     ← Next.js
│       ├── app/
│       │   ├── page.tsx         ← chat shell
│       │   ├── layout.tsx
│       │   └── api/             ← optional BFF proxy to FastAPI
│       ├── components/
│       │   ├── MessageList.tsx
│       │   ├── ChatInput.tsx
│       │   ├── SourcesPanel.tsx
│       │   └── MessageBubble.tsx
│       ├── lib/
│       │   ├── api.ts
│       │   └── types.ts         ← mirrors backend schema
│       └── package.json
├── services/
│   └── api/                     ← FastAPI
│       ├── app/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── api/
│       │   │   └── routes/
│       │   │       ├── chat.py
│       │   │       └── health.py
│       │   ├── core/
│       │   │   ├── scope_guard.py
│       │   │   ├── prompts.py
│       │   │   └── llm.py
│       │   ├── schemas/
│       │   │   ├── chat.py
│       │   │   └── response.py
│       │   ├── db/
│       │   │   ├── models.py
│       │   │   ├── session.py
│       │   │   └── repository.py
│       │   └── services/
│       │       └── chat_service.py
│       ├── tests/
│       │   ├── test_scope_guard.py
│       │   ├── test_schema.py
│       │   └── test_chat_flow.py
│       ├── requirements.txt
│       └── Dockerfile
├── README.md
└── .env.example
```

---

## 6. Frontend Architecture

### 6.1 Layout

Single chat view, three regions:

| Region | Behavior (Milestone 1) |
| --- | --- |
| **Message list** | User + assistant turns; show answer text; optionally list claim texts under the answer |
| **Input** | Text field + send; disable while request in flight |
| **Sources panel** | Always visible beside the conversation; **empty** this week (copy: “Sources will appear here when citations are available”) |

When an assistant message is selected (or for the latest reply), the Sources panel reads `claims[].source`. In Milestone 1 every source is `null` → panel stays empty. In Milestone 2 non-null sources render as citations.

### 6.2 Client state

Minimal state is enough:

```ts
type ChatState = {
  conversationId: string | null;
  messages: UiMessage[];
  selectedMessageId: string | null; // drives Sources panel
  status: "idle" | "sending" | "error";
  error: string | null;
};
```

- Persist `conversationId` in `localStorage` so refresh continues the thread.
- Do not stream required for Milestone 1; one request → one structured response is fine.
- Types in `lib/types.ts` must match the backend response schema exactly.

### 6.3 UI → API

Prefer calling FastAPI directly from the browser (CORS allowlisted) **or** a thin Next.js BFF at `/api/chat` that forwards to Railway. BFF helps hide backend URL and attach server-side config later; either is fine if keys never touch the client.

---

## 7. Backend Architecture

### 7.1 Chat orchestrator pipeline

Every user message flows through a fixed pipeline:

```text
1. Validate request (conversation_id?, message text)
2. Load conversation history from DB (if conversation_id)
3. ScopeGuard.pre_check(user_message)
      ├─ BLOCKED → persist refusal turn → return structured refusal (claims=[])
      └─ OK → continue
4. Build messages: [system_prompt] + history + new user message
5. LLM.structured_completion(schema=AssistantResponse)
6. Validate with Pydantic; on failure → do not persist bad payload → return error
7. Normalize: force every claim.source = null (Milestone 1 invariant)
8. ScopeGuard.post_check(assistant_payload)
      ├─ BLOCKED → replace with refusal template
      └─ OK → keep
9. Persist user + assistant messages
10. Return response DTO to client
```

### 7.2 Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness for Railway |
| `POST` | `/api/chat` | Send message; create or continue conversation |
| `GET` | `/api/conversations/{id}` | Load history for UI refresh |
| `GET` | `/api/conversations/{id}/messages/{message_id}` | Optional: sources for a specific turn |

#### `POST /api/chat` request

```json
{
  "conversation_id": "uuid-or-null",
  "message": "How much protein does a vegetarian adult typically need?"
}
```

#### `POST /api/chat` success response

```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "role": "assistant",
  "answer": "…",
  "claims": [
    {
      "text": "…",
      "source": null
    }
  ],
  "declined": false,
  "decline_reason": null
}
```

Refusal shape (same schema — contract stays stable):

```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "role": "assistant",
  "answer": "I can't provide calorie targets or medical advice. Please consult a qualified professional.",
  "claims": [],
  "declined": true,
  "decline_reason": "medical_or_weight_target"
}
```

### 7.3 Error behavior

| Condition | HTTP | Behavior |
| --- | --- | --- |
| Empty message | 400 | Reject |
| Schema validation failure after LLM | 502 | Log raw output; return generic error; **do not** ship unparsed prose |
| Provider timeout / quota | 503 | Retry once optional; then fail |
| Unknown conversation_id | 404 | Reject or start new — pick one and document |

---

## 8. Response Schema (Stable Contract)

This is the Milestone 1 / Milestone 2 shared contract. Sources stay `null` until retrieval exists.

### 8.1 Pydantic (backend)

```python
from pydantic import BaseModel, Field
from typing import Literal

class Claim(BaseModel):
    text: str = Field(..., min_length=1)
    source: str | None = Field(
        default=None,
        description="Always null in Milestone 1; citation string/URL in Milestone 2",
    )

class AssistantResponse(BaseModel):
    answer: str = Field(..., min_length=1)
    claims: list[Claim] = Field(default_factory=list)
    declined: bool = False
    decline_reason: Literal[
        "calorie_or_weight_target",
        "medical_advice",
        "out_of_scope",
        None
    ] = None
```

### 8.2 LLM structured output

- Use the provider’s **structured output / JSON schema** mode with `AssistantResponse` as the schema.
- Instruct the model: extract atomic factual claims into `claims`; set `source` to `null` always (Milestone 1).
- After parse, **code** overwrites `source` to `null` so the model cannot violate the invariant.

### 8.3 Why `claims` exist before citations

The Sources panel and Milestone 2 retrieval both need claim-level units. Without them, Milestone 2 would have to re-segment prose. Building the list now is the “container the citations land in.”

---

## 9. Scope Limits (Code + Prompt)

### 9.1 Out of scope (must decline)

- Calorie or weight targets (e.g. “give me a 1500 kcal plan”, “what should I weigh”)
- Recommendations about what anyone should weigh
- Medical advice (conditions, diagnoses, treatment diets, “what should someone with X eat”)

In-scope examples: nutrient roles, general food safety/storage, cooking methods, general dietary pattern information **without** personalized targets or clinical advice.

### 9.2 `ScopeGuard` (code)

Implement as an explicit module, not only prompt text.

**Pre-check (user message):**

- Keyword / regex heuristics for calories, deficit, BMI targets, “what should I weigh”, disease names + “should I eat”, prescriptions, etc.
- Optional: lightweight classifier call — keep Milestone 1 simple; heuristics + tests are enough if thorough.
- On block: **skip LLM** (or still call with refusal-only prompt — prefer skip for cost/latency) and return refusal template.

**Post-check (assistant payload):**

- Scan `answer` + `claims[].text` for calorie prescriptions, weight goals, condition-specific directives.
- If found: replace with refusal; set `declined=true`.

**Conversation-aware tests (required by brief):**

- Ask calorie target → decline
- Ask condition-specific diet → decline
- Rephrase both
- Ask sideways
- Re-ask after unrelated turns  
  All must decline. Cover these in automated tests against `ScopeGuard` and at least one integration test through `/api/chat`.

### 9.3 Prompt layer

System prompt must still state boundaries (what it won’t touch). Prompt alone is insufficient; code is authoritative.

---

## 10. System Prompt Architecture

### 10.1 Contents (required)

Versioned file, e.g. `services/api/app/core/prompts/v1.md` (or `.py` string constants):

1. **Role** — food, nutrition, and food-safety assistant
2. **How it answers** — clear, concise, structured into claims; no fake citations
3. **Length** — e.g. 2–4 short paragraphs max; prefer precision over padding
4. **Won’t touch** — calorie/weight targets, medical advice; decline and redirect to professionals
5. **Honesty** — if uncertain, say so; do not invent authorities or numbers you cannot support (still expect failures — that is what the log is for)

### 10.2 Prompt change process

- Keep a **fixed eval set** (`docs/eval-questions.json`) including the 10 failure-log questions + scope probes.
- After every prompt edit: re-run the full set.
- Log changes in `docs/prompt-changelog.md` (version, diff summary, why, eval outcome).
- Never “fix” one eval question by hardcoding its answer in code.

---

## 11. Data Model

### 11.1 Tables

**conversations**

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**messages**

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| conversation_id | UUID FK | |
| role | `user` \| `assistant` \| `system` | system usually not stored per turn |
| content | text | user text or assistant `answer` |
| claims | JSONB | assistant only; `{text, source}[]` |
| declined | bool | default false |
| decline_reason | text nullable | |
| raw_model_payload | JSONB nullable | for debugging schema failures (optional, strip in prod if sensitive) |
| created_at | timestamptz | |

### 11.2 Milestone 2 note

No schema change required for citations if `claims[].source` already exists. Optional later: `sources` table for normalized documents — not needed now.

---

## 12. LLM Integration

```text
llm.py responsibilities:
  - load API key from env
  - build provider client (OpenAI or Anthropic)
  - call with response_format / tool schema bound to AssistantResponse
  - return parsed dict → Pydantic validate
  - timeouts, one retry on transient errors
```

Config via env:

```bash
LLM_PROVIDER=openai          # or anthropic
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
MODEL_NAME=gpt-4o-mini
DATABASE_URL=postgres://...
CORS_ORIGINS=https://your-app.vercel.app
```

Temperature: moderate-low (e.g. `0.2–0.4`) to reduce wild variance for eval; still expect number drift — capture it in the failure log rather than over-constraining.

---

## 13. Failure Log Architecture

Failure logging is a **process + artifact**, not a runtime feature that “fixes” answers.

### 13.1 Eval set

`docs/eval-questions.json` — exactly 10 questions across:

1. Nutrient requirements  
2. Food safety and storage  
3. Cooking methods  
4. Questions with no clear answer  

Plus separate scope probes for refusal testing (can live in the same file under another key).

### 13.2 Run protocol

1. Deploy or run locally against the real pipeline.
2. Ask each of the 10 once; for consistency, pick 1–2 and ask **3 times**.
3. For each response, record in `docs/failure-log.md`:
   - Unsupported factual claims
   - Numbers that shift across runs
   - Cited sources that cannot be found (should be rare if `source` is always null — note any model that invents sources in prose inside `answer`)
   - Questions that should have been declined
   - Useless hedging
4. Group and count failure types.
5. Do **not** hardcode fixes for these questions.

Milestone 2 reuses the same 10 questions for before/after comparison.

---

## 14. Deployment Architecture

```text
┌──────────────────┐         ┌──────────────────────┐
│  Vercel          │  HTTPS  │  Railway             │
│  Next.js web     │────────▶│  FastAPI + Postgres  │
│  (public URL)    │         │  LLM keys in secrets │
└──────────────────┘         └──────────────────────┘
```

| Concern | Approach |
| --- | --- |
| Frontend env | `NEXT_PUBLIC_API_URL` = Railway public URL |
| Backend secrets | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, `DATABASE_URL` |
| CORS | Allow Vercel origin only |
| Health | Railway healthcheck → `GET /health` |
| Migrations | Alembic or SQLAlchemy `create_all` for prototype |

README must include live URL, GitHub link, system prompt, schema, prompt changelog summary, scope enforcement description, and tech stack.

---

## 15. Milestone 2 Insertion Points (Do Not Build Yet)

Design so these slots exist without implementing them:

| Slot | Milestone 1 | Milestone 2 |
| --- | --- | --- |
| Sources panel UI | Empty state | Render `claims[].source` |
| `Claim.source` | Always `null` | Citation / doc id / URL |
| Chat pipeline | LLM only | Retrieve → augment prompt → fill sources |
| API / schema | Unchanged | Unchanged |
| Eval questions | Baseline failure counts | Same 10, compare deltas |

Suggested future hook in orchestrator (stub comment only):

```python
# Milestone 2: retrieved = retriever.search(user_message)
# Milestone 2: prompt = build_rag_prompt(system, retrieved, history)
# Milestone 2: attach sources onto claims after generation
```

---

## 16. Security & Safety

- API keys only on Railway (or server env); never `NEXT_PUBLIC_*` for secrets.
- Rate-limit `/api/chat` lightly to control cost (per IP).
- Do not log full PII; conversation content may be sensitive — restrict admin access to DB.
- Scope refusals are product safety, not security, but treat them as non-optional gates.
- Validate and bound message length (e.g. 2–4k chars).

---

## 17. Testing Strategy

| Layer | What |
| --- | --- |
| Unit | `ScopeGuard` — direct, rephrased, sideways, mid-conversation probes |
| Unit | Pydantic schema — reject missing claims field shape, accept `source: null` |
| Integration | `/api/chat` happy path returns parseable body with `source: null` |
| Integration | Out-of-scope returns `declined: true` without providing targets |
| Manual / scripted | 10 eval questions → failure log |
| Consistency | Same question × 3 → note number drift |

CI can run unit + schema tests without spending LLM budget; mark live LLM tests as optional/manual.

---

## 18. Build Sequence (Suggested)

1. Define shared schema (`AssistantResponse`) and empty Sources panel UI shell.
2. FastAPI health + chat stub returning canned structured JSON.
3. Wire Next.js chat UI to stub; verify layout (list, input, empty sources).
4. Add Postgres persistence.
5. Integrate LLM structured outputs + validation + `source` nulling.
6. Implement `ScopeGuard` pre/post + tests.
7. Write system prompt v1 + eval question file.
8. Deploy Vercel + Railway; set CORS and secrets.
9. Run consistency + 10-question failure log; fill `docs/failure-log.md` and `prompt-changelog.md`.
10. Polish README for submission.

---

## 19. Non-Goals (Milestone 1)

- Retrieval, embeddings, vector DB, or real citations
- Streaming tokens
- User auth / multi-user accounts
- Mobile native apps
- Hardcoded answers for eval questions
- Filling the Sources panel with fake sources

---

## 20. Success Criteria Checklist

- [ ] Chat UI: messages, input, Sources panel (empty)
- [ ] Model calls only on backend
- [ ] Structured responses validate against schema; parse failures do not leak prose
- [ ] Every `claim.source` is `null`
- [ ] Scope limits enforced in code and prompt; refusal tests pass under rephrase/sideways/context
- [ ] Conversations persisted
- [ ] Live public URL (Vercel + Railway as planned)
- [ ] Failure log completed for 10 questions; failures counted, not patched
- [ ] README covers prompt, schema, prompt versions, scope enforcement, stack
