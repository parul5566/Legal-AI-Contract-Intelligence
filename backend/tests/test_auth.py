def test_register_login_me(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "u1@x.com", "name": "User One", "password": "Passw0rd!xx"},
    )
    assert r.status_code == 201
    token = r.json()["access_token"]

    r = client.post(
        "/api/auth/login", json={"email": "u1@x.com", "password": "Passw0rd!xx"}
    )
    assert r.status_code == 200
    assert r.json()["access_token"]

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "u1@x.com"

    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_login_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={"email": "u2@x.com", "name": "User Two", "password": "Passw0rd!xx"},
    )
    r = client.post("/api/auth/login", json={"email": "u2@x.com", "password": "wrong!!!1"})
    assert r.status_code == 401


def test_duplicate_register(client):
    client.post(
        "/api/auth/register",
        json={"email": "dup@x.com", "name": "Dup", "password": "Passw0rd!xx"},
    )
    r = client.post(
        "/api/auth/register",
        json={"email": "dup@x.com", "name": "Dup", "password": "Passw0rd!xx"},
    )
    assert r.status_code == 409


def test_admin_role_not_self_assignable(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "esc@x.com", "name": "Esc", "password": "Passw0rd!xx",
            "role": "admin",
        },
    )
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "analyst"  # downgraded


def test_invalid_token_rejected(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401
