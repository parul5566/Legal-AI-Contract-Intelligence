# Infrastructure

## Env keys (backend file: /workspace/backend/.env)
APP_ENV, APP_DEBUG, DATABASE_HOST/PORT/NAME/USER/PASSWORD (tags), JWT_SECRET (secret),
JWT_EXPIRES_MIN, LLM_API_KEY (secret), LLM_BASE_URL, LLM_MODEL, UPLOAD_DIR,
ANALYSIS_CONCURRENCY, CORS_ORIGINS

## Background services (procmgr)
- backend: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 (venv)
- worker:  python -m app.worker (venv)

## Caddy
- root reverse_proxy → :8000 (single origin; SPA served by FastAPI from
  backend/app/static/dist, API under /api, uploaded files under /uploads/*)

## Setup script (runs on deploy)
1. python venv already present; pip install -r backend/requirements.txt
2. cd frontend && npm ci && npm run build → backend/app/static/dist (fallback: keep existing dist)
3. cd backend && alembic upgrade head
4. python -m app.seed (idempotent: users + sample docs + auto-queue analysis)

## Ports
8000 API+SPA (Caddy proxies here). No other public ports.

## Data dirs
/workspace/storage/uploads — originals, mode 600, served only via authenticated endpoint
