# Task: Build complete platform (all phases)

## Goal
Legal document analysis & contract intelligence platform per .drytis/spec.md —
auth, upload/parse, clause extraction, risk findings, comparison, summary, review,
dashboard, audit, export, React UI — fully working and verified.

## Files
- backend/app/** (config, db, models, schemas, security, deps, audit, llm, worker, engine/*, routers/*)
- backend/alembic/** (initial migration = full schema)
- backend/app/seed.py, backend/requirements.txt, backend/tests/**
- frontend/** (React SPA), built into backend/app/static/dist

## Acceptance criteria
- [ ] POST /api/auth/register + /auth/login issue JWT; GET /auth/me returns user+role
- [ ] Upload PDF/DOCX/TXT ≤10MB rejected above size or wrong type (415/413)
- [ ] Uploaded doc transitions pending→parsing→analyzing→ready via worker
- [ ] Clauses extracted with category from 17-category taxonomy, page + char span + confidence
- [ ] Risks have severity low|medium|high|critical, explanation, suggestion, clause link or
      missing-clause evidence; risk counts appear on dashboard
- [ ] Missing clauses (no liability/confidentiality/termination...) produce findings
- [ ] POST /api/comparisons returns changes: added, removed, modified w/ similarity + materiality
- [ ] GET summary returns executive + obligations + dates + payments + risks + termination +
      restrictions + compliance + health_score 0-100; works even when LLM down (fallback)
- [ ] Review endpoints flip clause/risk review_status and append review_actions + audit rows
- [ ] Export returns self-contained HTML with clauses/risks/summary
- [ ] Dashboard stats: totals, analyzed, high-risk docs, severity histogram, recent
- [ ] Audit log rows for login, upload, analyze, review, compare, delete; admin-only endpoint
- [ ] RBAC: viewer cannot upload/analyze/review; non-owner non-admin gets 404 on doc access
- [ ] React SPA loads at /, login works, all tabs render with seeded analyzed docs
- [ ] Unit tests: segmenter, clause heuristics, risk rules, comparator, auth (≥20 tests, green)
- [ ] Integration: full flow via TestClient (register→login→upload→(mock analysis)→clauses→risks→
      compare→summary→review→export→stats) green
- [ ] procmgr services backend+worker running; curl /api/health → {"status":"ok"}
- [ ] No secrets/URLs hardcoded in source (env only)

## Tests
- tests/test_segmenter.py, test_clauses.py, test_risks.py, test_compare.py, test_auth.py,
  test_documents_api.py, test_review_export.py — run: pytest -q (LLM mocked/off)

## Edge cases
- empty/whitespace file, >10MB file, duplicate filename, LLM timeout/500 (fallback),
  unauthenticated access, expired token, delete doc with existing clauses/risks (cascade)
