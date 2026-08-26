# Architecture

```
Caddy (preview :443) ──▶ :8000 uvicorn (FastAPI, 2 workers)
                           ├── /api/*  → routers (auth, documents, analysis,
                           │             review, comparisons, stats, audit)
                           ├── /uploads/* → static from /workspace/storage/uploads
                           └── /*      → SPA static (frontend build) + fallback index.html
worker service ──▶ app.worker loop: analysis_jobs → engine pipeline → DB
```

## Directory
```
backend/app/
  main.py            FastAPI app, static mount, exception handlers
  config.py          pydantic-settings, reads /workspace/backend/.env
  db.py              engine, SessionLocal, Base
  models.py          SQLAlchemy models (all tables)
  schemas.py         Pydantic request/response schemas
  deps.py            get_db, get_current_user, require_roles
  security.py        bcrypt hash/verify, JWT encode/decode
  audit.py           audit() helper
  llm.py             OpenAI-compatible client w/ retry + JSON coercion + fallback
  worker.py          queue consumer loop
  engine/__init__.py
  engine/parser.py       PDF/DOCX/TXT → pages, full text, headings
  engine/segmenter.py    text → sections (heading + body + spans)
  engine/taxonomy.py     clause categories + risk categories constants
  engine/clauses.py      heuristic candidate detection + LLM refinement
  engine/risks.py        rule-based risk rules + LLM risk pass + missing-clause detection
  engine/compare.py      TF-IDF cosine matching → added/removed/modified
  engine/summarizer.py   LLM summary with 9 sections + health score
  engine/pipeline.py     orchestrates document analysis end-to-end
  routers/*.py
backend/tests/        pytest unit + integration (API via TestClient)
frontend/src/         React SPA (vite build → backend/app/static/dist)
```

## Status pipeline
document.status: pending → parsing → analyzing → ready | failed
job.status: queued → running → done | failed

## Traceability
clauses carry char_start/char_end/page/section_id; risks carry clause_id (nullable for
missing-clause findings); summaries reference clause categories. UI highlights spans.

## Failure handling
- LLM unavailable → heuristic-only clause extraction, rule-only risks, template summary
  (summary.source=deterministic). Analysis still completes, degraded flag shown.
- parse failure → status=failed + error message surfaced in UI
