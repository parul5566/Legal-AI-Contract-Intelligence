import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Base  # noqa: E402
from app import models  # noqa: F401,E402

TEST_DB_URL = "sqlite://"


@pytest.fixture()
def db_session():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def upload_dir(monkeypatch, tmp_path):
    """Shared upload dir — client fixture AND tests use this same directory."""
    from app.config import settings

    path = str(tmp_path)
    monkeypatch.setattr(settings, "upload_dir", path)
    return path


@pytest.fixture()
def client(db_session, monkeypatch, upload_dir):
    from fastapi.testclient import TestClient

    import app.deps as deps
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[deps.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def user_token(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "t1@example.com",
            "name": "Tester One",
            "password": "Passw0rd!xx",
            "role": "analyst",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


@pytest.fixture()
def auth_client(client, user_token):
    client.headers.update({"Authorization": f"Bearer {user_token}"})
    return client


@pytest.fixture()
def admin_token(client):
    # seed an admin directly (register downgrades admin → analyst)
    from app.security import hash_password

    from app.db import SessionLocal  # replaced? use override session via models
    r = client.post(
        "/api/auth/register",
        json={"email": "admin@example.com", "name": "Admin", "password": "Passw0rd!xx"},
    )
    uid = r.json()["user"]["id"]
    # promote via DB
    yield r.json()["access_token"], uid


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    """Keep tests deterministic — LLM never called."""
    from app import llm

    monkeypatch.setattr(llm, "available", lambda: False)
