# Orbit Architecture

Orbit is a job-application tracker with a **bounded agentic follow-up loop** — not a multi-agent framework demo. Every component exists for a stated reason.

## System overview

```
Gmail sync → Agent A (action extraction) → events table
                    ↓
              Agent B (tool-calling orchestrator)
                    ↓
         policy engine (veto) → outreach_actions → ARQ → Gmail send
                    ↓
              outcome observer → outcomes table → reply priors
```

## Backend (`backend/`)

| Component | Purpose | Why it exists |
|-----------|---------|---------------|
| **FastAPI** | HTTP API | Async-native; matches Gmail/LLM I/O |
| **PostgreSQL** | Primary store | Applications, events, agent runs, outreach, outcomes |
| **Redis** | ARQ job broker | Durable deferred sends + cron — **not** an application cache |
| **ARQ worker** | Sends + cron | `execute_outreach_send`, follow-up scan, cleanup, stale-queue reap |
| **`app/llm/`** | Unified Groq client | Model tiers, tool calling, audit trail, typed errors |
| **`app/agents/`** | Follow-up agent | Tool registry + ReAct orchestrator + policy envelope |
| **`app/services/gmail_service.py`** | Gmail read/send | Core integration #1 |
| **`app/services/calendar_service.py`** | Calendar events | Core integration #2 (deadline → calendar) |
| **`app/ml/`** | Extraction pipeline | QuickFilter → NLP → regex → LLM waterfall for cost/latency |

### Why no application cache

At this scale (single-user / small cohorts) Postgres is the source of truth and Groq is the expensive hop. An app-level Redis cache would not change latency enough to justify invalidation bugs. Redis exists solely as the ARQ broker.

## Agent design (the defensibility story)

**The LLM decides; the policy engine constrains.**

- **Tools** (`app/agents/tools/`): 11 Pydantic-schema'd functions the model consults — not hardcoded if/else gates pretending to be AI.
- **Orchestrator**: max 6 iterations, 10 tool calls, token budget, wall-clock timeout, circuit breaker. Tool history follows OpenAI protocol (one assistant message with all `tool_calls`, then one tool message each).
- **Policy pre-flight**: `check_follow_up_eligibility` runs before the LLM loop and again inside `draft_followup` / `schedule_send` so a doomed follow-up does not burn a reasoning-tier draft.
- **Policy post-insert veto**: `schedule_send` still inserts then vetoes — fail-closed defense in depth.
- **Audit**: `agent_runs.tool_trace` JSONB — every decision reconstructable via `GET /agents/runs/{id}/trace`. Degraded runs (rules fallback) are labelled `status=degraded` and excluded from agent accuracy in evals.

## Scheduling

| Path | Scope | Notes |
|------|-------|-------|
| `POST /agents/scan-now` | Current user | Inline (demo UX); no 6h skip |
| ARQ `cron_scan_for_follow_ups` | All users | Every 6 hours; skips apps evaluated in last 6h |
| ARQ cleanup crons | Global | Purge rejected pending, enforce pending cap |
| ARQ `cron_reap_stale_outreach` | Global | Re-enqueue `pending_undo` past `undo_until` |

## What we deleted (and why)

| Removed | Reason |
|---------|--------|
| **Celery** | No durable-send requirement until Phase 3; ARQ is async-native |
| **`rapidfuzz`** | Unused dependency |
| **`search_vector` FTS** | Broken reference; replaced with `ilike` |
| **`test_notes.py`** | Vacuous tests (401 == 401) |
| **`demo_email` defaults in settings** | Insecure hardcoded credentials |
| **`output.json` in tree** | PII; untracked + ignored (history purge is a separate ops decision) |

## Frontend (`frontend/`)

| Stack | Version |
|-------|---------|
| Next.js | 16.1.4 (App Router) |
| React | 19 |
| State | Zustand + TanStack Query |
| Styling | CSS Modules |

**Signal screens**:
- **Agent Trace** (`/agents` → Trace tab) — tool calls, policy vetoes, final decision
- **Send Queue** — approval inbox, risk badges, undo, kill switch
- **Agent Outcomes** (Analytics) — reply rate, vetoes, degraded rate, cost/app

## Evaluations (`evals/`)

| Harness | Measures |
|---------|----------|
| `eval_extraction.py` | Agent A precision/recall/F1 on labelled corpus |
| `eval_decision.py` | Agent vs rules-only baseline ablation (fair-slice + divergence-slice; degraded excluded) |
| `evals/adversarial/` | Gate suite (injection, disguised rejections) — not the full orchestrator loop |

See [EVALUATION.md](EVALUATION.md) for committed numbers.

## Deploy notes

- **`render.yaml`**: API web service only. Redis + ARQ worker are required for outreach sends; they are not declared on Render today — local/docker-compose has the worker.
- **Python**: 3.12 (Dockerfile + CI + Render).
- **`frontend/Dockerfile`**: `npm run dev` for compose hot-reload; use `npm run build && npm start` for production images.

## Security defaults

- `AGENT_SEND_ENABLED=false` until explicitly enabled
- `AGENT_SEND_TEST_INBOX` redirects all sends in dev
- Global + per-user kill switch
- JWT secret validation when `DEBUG=false`

## One-command dev

```bash
cp backend/.env.example backend/.env   # set GROQ_API_KEY
docker compose up --build
```

Or infrastructure-only + local processes: `npm run all` (see [STARTUP.md](STARTUP.md)).
