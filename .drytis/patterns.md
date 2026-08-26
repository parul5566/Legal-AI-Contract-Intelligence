# Patterns & Conventions

## Python backend
- Python 3.13, no async DB — sync SQLAlchemy sessions (FastAPI runs sync handlers in threadpool)
- Pydantic v2 schemas; response models on every route
- Snake_case everywhere; modules ≤ ~400 lines; functions single-purpose
- Errors: raise HTTPException with clear detail; global handler returns {"detail": ...}
- No business logic in routers — routers validate + delegate to services/engine
- Env ONLY via app.config.settings (pydantic-settings reads backend/.env). No literals.

## Auth
- Bearer JWT (sub=user_id, exp, role), get_current_user dependency
- Roles: admin > analyst > viewer. Mutations need analyst+; user mgmt/audit needs admin.
- Ownership: documents visible to owner or admin; others 404.

## DB
- Alembic migrations only; models define tables once; migration files committed
- Always index FKs; created_at/updated_at UTC datetimes via datetime.now(timezone.utc)
- JSON columns via sqlalchemy JSON type (lists/dicts)

## Engine
- Deterministic core (regex/keywords/TF-IDF) + optional LLM enhancement, LLM failures never crash pipeline
- All LLM calls return validated Pydantic objects (coerce + clamp)
- Confidence 0..1 stored on clauses/risks

## Frontend
- React function components + hooks; fetch wrapper with auth header + 401 redirect
- One CSS file, legal-tech palette (navy #1a2332, slate, amber accents for risk)
- No external UI libs; simple tables/cards/tabs
- Views: Login/Register, Dashboard, Documents, DocumentDetail (tabs), Compare, Audit (admin)

## Testing
- pytest; unit tests for segmenter/clauses/risks/compare (no LLM — fallback path);
  integration tests via TestClient with overridden DB (SQLite in-memory) + fake auth
- File names: test_<module>.py; one behavior per test

## Git
- feat/fix scope commits; conventional-ish messages; never commit .env, uploads, venv, node_modules
