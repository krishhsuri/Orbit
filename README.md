# Orbit

**Agentic job application tracker** — extracts actions from Gmail, decides follow-ups with a bounded tool-calling agent, sends with policy guardrails, and measures outcomes.

## What it does

1. **Agent A** — extracts deadlines, OAs, and interview requests from recruiter emails
2. **Agent B** — tool-calling orchestrator decides whether/when to follow up and drafts email
3. **Policy engine** — vetoes unsafe sends (caps, quiet hours, terminal status)
4. **ARQ queue** — durable sends with 60s undo window and idempotency
5. **Outcome loop** — detects thread replies, classifies them, feeds back into priors

## Tech stack

| Layer | Stack |
|-------|-------|
| Frontend | Next.js **16.1.4**, React 19, TypeScript, Zustand, TanStack Query, CSS Modules |
| Backend | FastAPI, PostgreSQL (async SQLAlchemy), Redis, ARQ |
| AI | Groq (`gpt-oss-20b` fast with 2 fallbacks, `qwen3.8-27b` reasoning), native tool calling with JSON fallback |
| Integrations | Gmail (read + send), Google Calendar |

## Quick start

### Docker (recommended)

```bash
cp backend/.env.example backend/.env   # set GROQ_API_KEY (+ Google OAuth if needed)
cp frontend/.env.local.example frontend/.env.local
docker compose up --build
# Frontend: http://localhost:3000
# API:      http://localhost:8000/docs
```

Compose loads `backend/.env` for API and worker (Groq / Google). Without that file the API boots but the AI is inert.

### One command (local dev with hot reload)

```bash
npm install          # once, from repo root
npm run all          # postgres + redis (docker), backend, worker, frontend
```

- **App:** http://localhost:3000  
- **API:** http://localhost:8000/docs  
- Uses Docker for Postgres/Redis only (ports **5433** / **6380**); Python + Next run locally with your `backend/.env` (Groq key, etc.)

```bash
npm run all:docker   # everything in Docker (slower rebuild loop)
npm run stop         # stop postgres + redis containers
```

### Manual

```bash
# Infrastructure
docker compose up postgres redis -d

# Backend
cd backend
cp .env.example .env   # set GROQ_API_KEY, GOOGLE creds
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# ARQ worker (separate terminal)
arq app.worker.settings.WorkerSettings

# Frontend
cd frontend
npm install
npm run dev
```

### Demo seed (date-relative, never expires)

```bash
cd backend
python scripts/seed_demo.py --user-email your@email.com
```

## Agent safety defaults

```env
AGENT_SEND_ENABLED=false          # must opt in for real sends
AGENT_SEND_TEST_INBOX=test@gmail.com  # redirect all sends in dev
AGENT_KILL_SWITCH_GLOBAL=false
```

## Evaluation

See [EVALUATION.md](EVALUATION.md) for committed extraction metrics, failure taxonomy, and ablation results.

```bash
python evals/eval_extraction.py --corpus evals/data/corpus.json --offline
python evals/eval_decision.py --offline
python evals/adversarial/run.py
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for component justifications, deleted-code rationale, and the agent design story.

## Demo script

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for a rehearsed 5-minute walkthrough.

## Tests

```bash
cd backend && pytest tests/ -q
```

77 tests covering the LLM client, policy engine, tool registry, orchestrator loop (fake LLM), rules baseline, outreach classifiers, and metrics.
