import io

SAMPLE = (
    b"MASTER SERVICES AGREEMENT\n\n"
    b"This agreement is between Acme Corp and Beta LLC.\n\n"
    b"1. PAYMENT TERMS\nCustomer shall pay invoices net 90 days.\n\n"
    b"2. TERMINATION\nEither party may terminate at any time without cause immediately.\n\n"
    b"3. CONFIDENTIALITY\nEach party protects Confidential Information.\n"
)


def _upload(c, name="doc.txt", content=SAMPLE, mime="text/plain"):
    return c.post(
        "/api/documents",
        files={"file": (name, io.BytesIO(content), mime)},
    )


def test_upload_and_get(auth_client):
    r = _upload(auth_client)
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["status"] == "pending"
    r = auth_client.get(f"/api/documents/{doc['id']}")
    assert r.status_code == 200


def test_upload_rejects_wrong_type(auth_client):
    r = auth_client.post(
        "/api/documents",
        files={"file": ("v.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
    )
    assert r.status_code == 415


def test_upload_rejects_oversize(auth_client):
    big = b"x" * (10 * 1024 * 1024 + 100)
    r = _upload(auth_client, content=big)
    assert r.status_code == 413


def test_upload_rejects_empty(auth_client):
    r = _upload(auth_client, content=b"   ")
    assert r.status_code == 422


def test_viewer_cannot_upload(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "v@x.com", "name": "Viewer", "password": "Passw0rd!xx",
              "role": "viewer"},
    )
    token = r.json()["access_token"]
    r = client.post(
        "/api/documents",
        files={"file": ("a.txt", io.BytesIO(b"data"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_document_isolation(client, auth_client):
    _upload(auth_client)
    r = client.post(
        "/api/auth/register",
        json={"email": "other@x.com", "name": "Other", "password": "Passw0rd!xx"},
    )
    token = r.json()["access_token"]
    docs = auth_client.get("/api/documents").json()["items"]
    r = client.get(
        f"/api/documents/{docs[0]['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 404


def test_list_and_search(auth_client):
    _upload(auth_client, name="alpha.txt")
    _upload(auth_client, name="beta.txt")
    r = auth_client.get("/api/documents")
    assert r.json()["total"] == 2
    r = auth_client.get("/api/documents", params={"q": "alpha"})
    assert r.json()["total"] == 1


def test_delete(auth_client):
    doc = _upload(auth_client).json()
    r = auth_client.delete(f"/api/documents/{doc['id']}")
    assert r.status_code == 204
    r = auth_client.get(f"/api/documents/{doc['id']}")
    assert r.status_code == 404


def test_analyze_requires_ready_or_queues(auth_client, db_session):
    doc = _upload(auth_client).json()
    r = auth_client.post(f"/api/documents/{doc['id']}/analyze")
    assert r.status_code == 200
    assert r.json()["queued"] is True
    # double queue → same job returned, no duplicate
    r2 = auth_client.post(f"/api/documents/{doc['id']}/analyze")
    assert r2.json()["job_id"] == r.json()["job_id"]


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
