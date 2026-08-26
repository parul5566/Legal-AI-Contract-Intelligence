# Schema (MySQL — database name from env)

## users
id PK, email UNIQUE, name, password_hash, role ENUM(admin,analyst,viewer), created_at

## documents
id PK, owner_id FK users, filename, original_name, mime, size_bytes, status
ENUM(pending,parsing,analyzing,ready,failed), doc_type, title, parties (JSON),
effective_date, expiry_date, jurisdiction, page_count, char_count, error, created_at, analyzed_at

## document_sections
id PK, document_id FK, idx, heading, body, char_start, char_end, page

## clauses
id PK, document_id FK, category, title, text, char_start, char_end, page, section_id FK null,
confidence FLOAT, source ENUM(ai,heuristic,manual), review_status ENUM(pending,accepted,rejected,
corrected) default pending, created_at

## risk_findings
id PK, document_id FK, clause_id FK null, category, severity ENUM(low,medium,high,critical),
title, explanation, suggestion, evidence, confidence FLOAT, review_status, reviewer_id FK null,
review_note, created_at

## summaries
id PK, document_id FK UNIQUE, executive TEXT, key_obligations JSON, important_dates JSON,
payments JSON, major_risks JSON, termination TEXT, restrictions JSON, compliance JSON,
health_score INT, health_verdict TEXT, model TEXT, created_at

## comparisons
id PK, doc_a_id FK, doc_b_id FK, created_by FK, status ENUM(pending,processing,ready,failed),
summary TEXT, error, created_at

## comparison_changes
id PK, comparison_id FK, kind ENUM(added,removed,modified), category, clause_a_id FK null,
clause_b_id FK null, text_a TEXT, text_b TEXT, similarity FLOAT, material BOOL, rationale TEXT

## review_actions
id PK, document_id FK, actor_id FK, target_type ENUM(clause,risk,summary,comparison),
target_id INT, action ENUM(accept,reject,correct,comment,flag), detail TEXT, created_at

## audit_logs
id PK, user_id FK null, event, entity, entity_id, detail TEXT, ip, created_at

## analysis_jobs (worker queue)
id PK, document_id FK UNIQUE, comparison_id FK null, kind ENUM(document,comparison),
status ENUM(queued,running,done,failed), attempts INT, error TEXT, created_at, started_at, finished_at

## seeds (idempotent)
- users: admin@legalai.test / Admin@123 (admin), analyst@legalai.test / Analyst@123 (analyst),
  viewer@legalai.test / Viewer@123 (viewer)
- sample docs: msa_v1.txt, msa_v2.txt (revised), nda.txt parsed + fully analyzed on first worker run

## API endpoints (all under /api)
auth: POST /auth/register, POST /auth/login, GET /auth/me
documents: GET /documents, POST /documents (multipart), GET /documents/{id},
DELETE /documents/{id}, GET /documents/{id}/file, GET /documents/{id}/sections
analysis: POST /documents/{id}/analyze, GET /documents/{id}/status,
GET /documents/{id}/clauses, GET /documents/{id}/risks, GET /documents/{id}/summary
review: POST /clauses/{id}/review, POST /risks/{id}/review, GET /documents/{id}/review-log
comparisons: GET /comparisons, POST /comparisons, GET /comparisons/{id}
stats: GET /stats/dashboard
audit: GET /audit (admin)
misc: GET /health, GET /api/spec (OpenAPI)
