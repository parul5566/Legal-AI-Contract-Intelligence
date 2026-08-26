# Legal AI Contract Intelligence — Blueprint

## Overview
AI-powered legal document analysis & contract intelligence platform.
Upload contracts (PDF/DOCX/TXT) → parse → extract clauses (17 categories) →
identify risks (13 categories × 4 severities) → compare two contracts →
business-friendly AI summary → human review (accept/reject/comment) → export.

Decision-support tool; never autonomous legal advice (banner in UI).

## Tech stack
- Backend: Python 3.13, FastAPI, Pydantic, SQLAlchemy 2 (sync, pooled), MySQL/MariaDB, Alembic
- Auth: JWT (python-jose), bcrypt (passlib), roles: admin/analyst/viewer
- Parsing: pdfminer.six (PDF), python-docx (DOCX), plain text (TXT)
- AI: managed OpenAI-compatible gateway (LLM_API_KEY/LLM_BASE_URL/LLM_MODEL), JSON-schema outputs,
  graceful fallback to deterministic heuristics; TF-IDF cosine similarity (scikit-learn) for clause matching
- Frontend: React 18 + Vite SPA, served by `npx serve -s dist` on :3000
- Serving: Caddy reverse_proxy → :8000 API; SPA bundled INTO the FastAPI app
  (FastAPI serves static dist + client-side fallback route) so ONE port serves everything.

## Architecture
- `/workspace/backend` — FastAPI app (`app/`), alembic, tests, venv
- `/workspace/frontend` — React source; `npm run build` outputs to `backend/app/static/dist`
- `/workspace/storage/uploads` — uploaded originals (outside web root)
- background services: `backend` (uvicorn :8000), `worker` (analysis queue consumer)

## Data flow
Upload → documents row (status=pending) → worker picks job → extract text →
segment sections → heuristic clause candidates → LLM refine/classify → persist clauses →
rule engine + LLM risk pass → persist risks → LLM summary → status=ready.
Comparison: pairwise clause matching via TF-IDF cosine + category → changes.

## Key invariants
- All env via backend env_keys (file `/workspace/backend/.env`), never hardcoded
- Schema changes ONLY via Alembic migrations
- Analysis is async (jobs table), API stays non-blocking
- Every LLM finding carries clause_id + source span for traceability
- User sees AI disclaimer; findings are proposals until reviewed
