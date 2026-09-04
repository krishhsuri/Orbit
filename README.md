# Orbit

**Agentic job-application tracker** — syncs Gmail, extracts deadlines and asks, decides follow-ups with a bounded tool-calling agent, sends under policy guardrails, and closes the loop by classifying replies.

> The LLM decides. The policy engine constrains. Outcomes feed the next run.

---

## Why Orbit

Most trackers are passive databases. You still decide when to follow up, dig deadlines out of threads, and never learn what worked. Orbit closes that loop:

| Without Orbit | With Orbit |
|---|---|
| Statuses go stale when recruiters ghost you | Ghost / reply outcomes update priors |
| Deadlines hide in email | Agent A extracts OAs, interviews, docs, responses |
| Follow-up timing is guesswork | Agent B tools + policy decide whether / when |
| Drafts never get measured | Durable sends → reply classification → analytics |

---

## What it does

### 1. Track applications end-to-end

- **Dashboard** — pipeline overview and signals that need attention
- **Applications** — status, notes, tags, thread context
- **Kanban** — drag-and-drop board across stages
- **Emails** — Gmail sync, matching to applications
- **Leads** — recruiter / company leads
- **Settings** — Google OAuth, agent send controls, kill switch

### 2. Agent A — action extraction

Reads recruiter email and surfaces structured actions:

- Online assessments / coding tests
- Interview scheduling
- Document uploads
- General response required

Uses a cost-aware cascade (quick filters → NLP → regex → LLM) so most mail never burns a reasoning call.

### 3. Agent B — bounded follow-up agent

A ReAct-style orchestrator (max iterations, tool-call cap, token budget, timeout, circuit breaker) with **11 tools**, including:

`get_application_state` · `get_thread_history` · `get_pending_actions` · `get_outreach_history` · `get_reply_priors` · `get_policy_budget` · `draft_followup` · `schedule_send` · `create_calendar_event` · `escalate_to_human` · `mark_no_action`

Every run is audited: tool trace, cost, latency, decision, and policy vetoes (`/agents` → Trace).

### 4. Policy + durable send

- Pre-flight eligibility and post-insert **veto** (fail closed)
- Caps, quiet hours, terminal statuses, risk tiers
- ARQ queue with **idempotency**, **60s undo**, approval for high-risk sends
- Global + per-user **kill switch**
- Calendar events when a deadline needs a hard hold

Sends are off by default (`AGENT_SEND_ENABLED=false`); optional `AGENT_SEND_TEST_INBOX` redirects outbound mail in dev.

### 5. Outcome loop

After a send, Orbit watches the thread, classifies replies, stores outcomes, and feeds reply priors back into Agent B — so soft rejects, future timelines, and recovered ghosts change future decisions.

### 6. Honest evaluation

Committed harnesses (not vibes):

| Harness | What it proves |
|---|---|
| `evals/eval_extraction.py` | Agent A precision / recall / F1 (stale vs date-relative corpus) |
| `evals/eval_decision.py` | Agent vs rules-only ablation; degraded runs excluded |
| `evals/adversarial/` | Injection, disguised rejection, fabricated deadlines |

Numbers and failure taxonomy live in [EVALUATION.md](EVALUATION.md). Design rationale and deletions: [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Product map

```
Gmail sync → Agent A (extract) → events
                 ↓
           Agent B (tools + ReAct)
                 ↓
      policy veto → outreach_actions → ARQ → Gmail / Calendar
                 ↓
           outcome observer → priors → next Agent B run
```

**UI surfaces that make the agent inspectable**

| Route | Purpose |
|---|---|
| `/agents` | Action inbox, follow-up queue, agent trace, send queue |
| `/analytics` | Reply rate, vetoes, degraded rate, cost per app |
| `/emails` | Synced mail + matching |
| `/applications`, `/kanban` | Human pipeline control |

---

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Zustand, TanStack Query, Tailwind / CSS Modules |
| Backend | FastAPI, async SQLAlchemy, PostgreSQL, Alembic |
| Jobs | Redis + ARQ (sends, 6h follow-up scan, cleanup, stale-queue reap) |
| AI | Groq — fast tier (`gpt-oss-20b` + fallbacks) and reasoning (`qwen3.8-27b`); native tool calling with JSON fallback |
| Integrations | Gmail (read + send), Google Calendar |
| Deploy | Docker Compose locally; `render.yaml` for API (worker must be wired separately for sends) |

---

## Quick start

### Prerequisites

- Docker Desktop
- Node.js 18+
- Python 3.12+
- `GROQ_API_KEY` (and Google OAuth creds if you want live Gmail)

### One command (local hot reload)

```bash
cp backend/.env.example backend/.env          # set GROQ_API_KEY (+ Google if needed)
cp frontend/.env.local.example frontend/.env.local
cd backend && pip install -r requirements.txt && python -m spacy download en_core_web_sm && cd ..
npm install                                   # once, from repo root
npm run all                                   # postgres + redis + migrate + API + worker + frontend
```

| Service | URL |
|---|---|
| App | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| Postgres (host) | `localhost:5433` |
| Redis (host) | `localhost:6380` |

```bash
npm run all:docker   # full stack in Compose
npm run stop         # stop postgres + redis only
```

### Full Docker

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
docker compose up --build
```

Compose loads `backend/.env` for API and worker. Without a Groq key the API boots but agents stay inert.

### Demo seed (date-relative — does not expire)

```bash
cd backend
python scripts/seed_demo.py --user-email your@email.com
```

Step-by-step terminals: [STARTUP.md](STARTUP.md). Five-minute walkthrough: [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

---

## Agent safety defaults

```env
AGENT_SEND_ENABLED=false           # must opt in for real sends
AGENT_SEND_TEST_INBOX=you@gmail.com  # redirect all sends in dev
AGENT_UNDO_WINDOW_SECONDS=60
AGENT_KILL_SWITCH_GLOBAL=false
```

Manual **Scan now** in the UI runs inline for the current user (demo-friendly). The ARQ cron scans all users every 6 hours and skips apps already evaluated in that window.

---

## Evaluation & tests

```bash
# Extraction (offline corpus)
python evals/eval_extraction.py --corpus evals/data/corpus.json --offline

# Decision ablation vs rules baseline
python evals/eval_decision.py --offline

# Adversarial gate suite
python evals/adversarial/run.py

# Unit / integration
cd backend && pytest tests/ -q
```

77 tests cover the LLM client, policy engine, tool registry, orchestrator (fake LLM), rules baseline, outreach classifiers, and metrics.

Headline results (see [EVALUATION.md](EVALUATION.md) for full tables):

- Fresh extraction micro-F1 ≈ **0.71** (stale dated corpus collapses recall — measured, not hand-waved)
- Decision ablation: agent action accuracy **0.935** vs rules baseline **0.360** on a labelled set designed to include rule failures; degraded runs excluded

---

## Repo layout

```
backend/     FastAPI, agents, ML cascade, ARQ worker, Alembic
frontend/    Next.js app (dashboard → agents → analytics)
evals/       Extraction, decision ablation, adversarial suites
ARCHITECTURE.md   Why each component exists (and what we deleted)
EVALUATION.md     Committed metrics + failure taxonomy
DEMO_SCRIPT.md    Rehearsed demo path
STARTUP.md        Multi-terminal startup
```

---

## License / status

Private project. Agentic follow-up stack (tools, policy, durable sends, outcomes, evals) is the current baseline — see the latest `Ship agentic follow-up stack…` commit for the full wiring.
