"""Integration: pipeline → clauses/risks/summary/comparison/review/export/stats."""
import io

import pytest



from app.engine.pipeline import analyze_document
from app.models import AnalysisJob, Document

MSA_TEXT = """MASTER SERVICES AGREEMENT

This Agreement is entered into between Acme Corp ("Supplier") and Beta LLC ("Customer").

1. PAYMENT TERMS
Customer shall pay invoices within sixty (60) days. Supplier may charge such other amounts as may be agreed.

2. TERM AND TERMINATION
Initial term of two years. Either party may terminate at any time without cause immediately upon written notice.

3. CONFIDENTIALITY
Each party shall protect the other's Confidential Information.

4. INDEMNIFICATION
Customer shall defend and indemnify Supplier against all claims.

5. LIMITATION OF LIABILITY
Supplier's liability shall be unlimited. Supplier is liable for consequential damages.

6. GOVERNING LAW
Governed by the laws of the State of Delaware.

7. DISPUTE RESOLUTION
Disputes resolved by binding arbitration.
""".encode()


def _upload_ready(auth_client, db_session, upload_dir, name="msa.txt", content=MSA_TEXT):
    r = auth_client.post(
        "/api/documents",
        files={"file": (name, io.BytesIO(content), "text/plain")},
    )
    assert r.status_code == 201, r.text
    doc = db_session.get(Document, r.json()["id"])
    analyze_document(db_session, doc, upload_dir)
    for j in (
        db_session.query(AnalysisJob).filter(AnalysisJob.document_id == doc.id).all()
    ):
        j.status = "done"
    db_session.commit()
    return doc


def test_full_analysis(auth_client, db_session, upload_dir):
    doc = _upload_ready(auth_client, db_session, upload_dir)
    assert doc.status == "ready"
    assert len(doc.clauses) >= 5
    assert len(doc.risks) >= 3
    assert doc.summary is not None
    assert doc.summary.model == "deterministic"
    assert 0 <= doc.summary.health_score <= 100

    cats = {c.category for c in doc.clauses}
    assert "payment_terms" in cats
    assert "liability" in cats

    sev = {r.severity for r in doc.risks}
    assert "critical" in sev  # unlimited liability


def test_api_results_endpoints(auth_client, db_session, upload_dir):
    doc = _upload_ready(auth_client, db_session, upload_dir)
    r = auth_client.get(f"/api/documents/{doc.id}/clauses")
    assert r.status_code == 200 and len(r.json()) >= 5
    r = auth_client.get(f"/api/documents/{doc.id}/clauses", params={"category": "payment_terms"})
    assert all(c["category"] == "payment_terms" for c in r.json())

    r = auth_client.get(f"/api/documents/{doc.id}/risks")
    assert r.status_code == 200 and len(r.json()) >= 3
    # severity ordering: critical first
    sevs = [x["severity"] for x in r.json()]
    assert sevs.index("critical") < sevs.index("medium")

    r = auth_client.get(f"/api/documents/{doc.id}/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["executive"]
    assert isinstance(body["key_obligations"], list)

    r = auth_client.get(f"/api/documents/{doc.id}/sections")
    assert r.status_code == 200 and len(r.json()) >= 3


def test_comparison_flow(auth_client, db_session, upload_dir):
    doc_a = _upload_ready(auth_client, db_session, upload_dir, name="a.txt")
    revised = MSA_TEXT.replace(b"sixty (60) days", b"thirty (30) days")
    doc_b = _upload_ready(auth_client, db_session, upload_dir, name="b.txt", content=revised)

    r = auth_client.post(
        "/api/comparisons", json={"doc_a_id": doc_a.id, "doc_b_id": doc_b.id}
    )
    assert r.status_code == 201, r.text
    cmp_id = r.json()["id"]

    from app.engine.pipeline import analyze_comparison
    from app.models import Comparison

    cmp_ = db_session.get(Comparison, cmp_id)
    analyze_comparison(db_session, cmp_)
    assert cmp_.status == "ready"
    assert len(cmp_.changes) >= 1
    kinds = {c.kind for c in cmp_.changes}
    assert "modified" in kinds
    assert any(c.material for c in cmp_.changes)

    r = auth_client.get(f"/api/comparisons/{cmp_id}")
    assert r.status_code == 200
    assert len(r.json()["changes"]) >= 1


def test_comparison_requires_ready(auth_client, db_session, upload_dir):
    r = auth_client.post(
        "/api/documents",
        files={"file": ("x.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    doc_id = r.json()["id"]
    r = auth_client.post(
        "/api/comparisons", json={"doc_a_id": doc_id, "doc_b_id": doc_id}
    )
    assert r.status_code == 422  # self-comparison
    doc2 = _upload_ready(auth_client, db_session, upload_dir)
    r = auth_client.post(
        "/api/comparisons", json={"doc_a_id": doc_id, "doc_b_id": doc2.id}
    )
    assert r.status_code == 409  # not ready


def test_review_actions(auth_client, db_session, upload_dir):
    doc = _upload_ready(auth_client, db_session, upload_dir)
    clause = doc.clauses[0]
    risk = doc.risks[0]

    r = auth_client.post(
        f"/api/clauses/{clause.id}/review", json={"action": "accept"}
    )
    assert r.status_code == 200 and r.json()["review_status"] == "accepted"

    r = auth_client.post(
        f"/api/clauses/{clause.id}/review",
        json={"action": "correct", "note": "wrong category", "category": "warranty"},
    )
    assert r.status_code == 200
    assert r.json()["category"] == "warranty"
    assert r.json()["review_status"] == "corrected"

    r = auth_client.post(
        f"/api/risks/{risk.id}/review",
        json={"action": "reject", "note": "not applicable"},
    )
    assert r.status_code == 200 and r.json()["review_status"] == "rejected"

    r = auth_client.post(
        f"/api/risks/{risk.id}/review", json={"action": "bogus"}
    )
    assert r.status_code == 422

    r = auth_client.get(f"/api/documents/{doc.id}/review-log")
    assert r.status_code == 200 and len(r.json()) == 3


def test_export(auth_client, db_session, upload_dir):
    doc = _upload_ready(auth_client, db_session, upload_dir)
    r = auth_client.get(f"/api/documents/{doc.id}/export")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Risk Findings" in r.text
    assert "Unlimited" in r.text or "unlimited" in r.text


def test_dashboard_stats(auth_client, db_session, upload_dir):
    _upload_ready(auth_client, db_session, upload_dir)
    r = auth_client.get("/api/stats/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert body["total_documents"] >= 1
    assert body["ready_documents"] >= 1
    assert body["high_risk_documents"] >= 1
    assert "critical" in body["severity_histogram"]
    assert len(body["recent_documents"]) >= 1


def test_audit_admin_only(auth_client, client, db_session, upload_dir):
    _upload_ready(auth_client, db_session, upload_dir)
    r = auth_client.get("/api/audit")
    assert r.status_code == 403  # analyst is not admin

    from app.models import User
    from app.security import hash_password

    db_session.add(
        User(
            email="root@x.com", name="Root",
            password_hash=hash_password("Passw0rd!xx"), role="admin",
        )
    )
    db_session.commit()
    r = client.post(
        "/api/auth/login", json={"email": "root@x.com", "password": "Passw0rd!xx"}
    )
    admin_token = r.json()["access_token"]
    r = client.get("/api/audit", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    events = {i["event"] for i in r.json()["items"]}
    assert "upload" in events


def test_summary_regenerate(auth_client, db_session, upload_dir):
    doc = _upload_ready(auth_client, db_session, upload_dir)
    r = auth_client.post(f"/api/documents/{doc.id}/summary/regenerate")
    assert r.status_code == 200
    assert r.json()["executive"]
