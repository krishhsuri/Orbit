# 🚀 Orbit — Startup Guide

All commands to get the full stack running. Open **4 separate terminals**.

---

## Prerequisites

- **Docker Desktop** must be running
- **Node.js** installed (v18+ recommended)
- **Python 3.10+** with a virtual environment set up for the backend

---

## Terminal 1 — Docker (PostgreSQL + Redis)

```bash
cd d:\Orbit
docker-compose up
```

> Wait until you see both `orbit_postgres` and `orbit_redis` are healthy before starting the backend.

To run in detached (background) mode instead:

```bash
docker-compose up -d
```

---

## Terminal 2 — Backend (FastAPI)

```bash
cd d:\Orbit\backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

> If your virtual environment is named differently, adjust the activate path.

---

## Terminal 3 — Celery Worker (Background Tasks)

```bash
cd d:\Orbit\backend
.\venv\Scripts\activate
celery -A app.celery_app:celery_app worker --loglevel=info --pool=solo
```

> `--pool=solo` is required on Windows. On Linux/Mac you can omit it.

---

## Terminal 4 — Frontend (Next.js)

```bash
cd d:\Orbit\frontend
npm run dev
```

> App will be available at **http://localhost:3000**

---

## Quick Reference

| Service    | URL / Port                | Health Check                |
|------------|---------------------------|-----------------------------|
| Frontend   | http://localhost:3000      | Open in browser             |
| Backend    | http://localhost:8000      | http://localhost:8000/docs   |
| PostgreSQL | localhost:5432             | `docker ps`                 |
| Redis      | localhost:6379             | `docker ps`                 |

---

## Shutting Down

```bash
# Stop Docker services
cd d:\Orbit
docker-compose down

# Stop backend/celery/frontend — just Ctrl+C in each terminal
```

To also wipe the database volumes:

```bash
docker-compose down -v
```
