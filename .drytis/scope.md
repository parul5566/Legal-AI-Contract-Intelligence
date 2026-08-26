# Scope

## In scope (this build)
1. Auth: register/login/me, JWT, roles admin/analyst/viewer
2. Documents: upload PDF/DOCX/TXT (≤10MB), parse, sections, metadata, delete, list, search
3. Analysis pipeline (async worker): clause extraction (17 categories), risk findings
   (13 categories, Low/Medium/High/Critical), AI summary (9 sections + health score)
4. Comparison: 2 documents, added/removed/modified, similarity, materiality flag, rationale
5. Review: accept/reject finding, correct clause category, comment, flag
6. Dashboard: totals, high-risk counts, severity distribution, recent docs
7. Audit log: auth events, uploads, analysis, reviews, comparisons, deletes (admin view)
8. Export: self-contained HTML report per document
9. SPA UI: login/register, dashboard, documents, document viewer (tabs: Document |
   Clauses | Risks | Summary | Review | Export), comparison screen, audit screen (admin)
10. Sample contracts seeded (MSA vs revised MSA + NDA) for demo/eval

## Out of scope (future)
- OCR of scanned images, e-signature, redlining editor, multi-tenant orgs,
  precedent search, obligation tracking, automated alerts, billing

## Phases
1. Scaffold + auth + schema + upload/parse
2. Clause engine + viewer UI
3. Risk engine + dashboard
4. Comparison engine + UI
5. Summarization + review + export
6. Tests + eval + polish
