# Orbit — Startup Guide

All commands to get the full stack running. Open **4 separate terminals**.

---

## Prerequisites

- **Docker Desktop** must be running
- **Node.js** installed (v18+ recommended)
- **Python 3.12+** with a virtual environment set up for the backend
- **Backend dependencies** installed:
  ```bash
  cd d:\Orbit\backend
  .\venv\Scripts\activate
  pip install -r requirements.txt
  python -m spacy download en_core_web_sm
  ```
- Copy `backend/.env.example` → `backend/.env` and set `GROQ_API_KEY` (+ Google OAuth if needed)

---

## Terminal 1 — Docker (PostgreSQL + Redis)

```bash
cd d:\Orbit
docker compose up postgres redis -d
```

> Wait until you see both `orbit_postgres` and `orbit_redis` are healthy before starting the backend.
> Host ports are **5433** (Postgres) and **6380** (Redis) to avoid clashes with other local stacks.

---

## Terminal 2 — Backend (FastAPI)

```bash
cd d:\Orbit\backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

> If your virtual environment is named differently, adjust the activate path.

---

## Terminal 3 — ARQ Worker (sends + cron)

```bash
cd d:\Orbit\backend
.\venv\Scripts\activate
arq app.worker.settings.WorkerSettings
```

> Runs `execute_outreach_send` and ARQ `cron_jobs`:
> - follow-up scan (all users, 6h skip) every 6 hours
> - purge old rejected pending apps / enforce pending cap (nightly)
> - reap stranded `pending_undo` rows every 5 minutes
>
> Manual "Scan now" in the UI stays inline (current user, no 6h skip) for demos.

---

## Terminal 4 — Frontend (Next.js)

```bash
cd d:\Orbit\frontend
cp .env.local.example .env.local   # once
npm install
npm run dev
```

> App will be available at **http://localhost:3000**

---

## One-command alternative

From the repo root (uses Docker for Postgres/Redis only; Python + Next run locally):

```bash
npm install
npm run all
```

---

## Quick Reference

| Service    | URL / Port                | Health Check                |
|------------|---------------------------|-----------------------------|
| Frontend   | http://localhost:3000      | Open in browser             |
| Backend    | http://localhost:8000      | http://localhost:8000/docs   |
| PostgreSQL | localhost:5433             | `docker ps`                 |
| Redis      | localhost:6380             | `docker ps`                 |

---

## Shutting Down

```bash
# Stop Docker services
cd d:\Orbit
docker compose down

# Stop backend / ARQ worker / frontend — Ctrl+C in each terminal
```

To also wipe the database volumes:

```bash
docker compose down -v
```

---

## Database Backups

Create a compressed backup of the PostgreSQL database:

```bash
cd d:\Orbit\backend
.\venv\Scripts\activate
python scripts/backup_db.py
```

> Backups are saved to `backend/backups/` as `.sql.gz` files. Only the last 7 are retained automatically.

> **Requires** `pg_dump` (PostgreSQL client tools) on your PATH. If using Docker, install [PostgreSQL client](https://www.postgresql.org/download/) or run pg_dump inside the container.
