"""Tests for /api/auth endpoints: register, login, me."""
import app.auth as auth_module


def _clear_rate_limit():
    auth_module._rate_limit.clear()


# ── Register ────────────────────────────────────────────────────────────

def test_register_success(unauth_client):
    _clear_rate_limit()
    resp = unauth_client.post("/api/auth/register", json={
        "email": "newuser@test.com",
        "password": "secret123",
        "full_name": "New User",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "newuser@test.com"
    assert body["full_name"] == "New User"
    assert body["is_active"] is True
    assert "id" in body


def test_register_duplicate_email(unauth_client, test_user):
    _clear_rate_limit()
    resp = unauth_client.post("/api/auth/register", json={
        "email": "test@test.com",
        "password": "anything",
    })
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


# ── Login ───────────────────────────────────────────────────────────────

def test_login_success(unauth_client, test_user):
    _clear_rate_limit()
    resp = unauth_client.post("/api/auth/login", data={
        "username": "test@test.com",
        "password": "testpass",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(unauth_client, test_user):
    _clear_rate_limit()
    resp = unauth_client.post("/api/auth/login", data={
        "username": "test@test.com",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(unauth_client):
    _clear_rate_limit()
    resp = unauth_client.post("/api/auth/login", data={
        "username": "nobody@test.com",
        "password": "anything",
    })
    assert resp.status_code == 401


def test_login_inactive_user(unauth_client, db_session):
    from app.models import User
    _clear_rate_limit()
    user = User(
        email="inactive@test.com",
        hashed_password=auth_module.get_password_hash("secret"),
        full_name="Inactive",
        is_active=False,
    )
    db_session.add(user)
    db_session.flush()
    resp = unauth_client.post("/api/auth/login", data={
        "username": "inactive@test.com",
        "password": "secret",
    })
    assert resp.status_code == 403
    assert "inactive" in resp.json()["detail"].lower()


# ── Me ──────────────────────────────────────────────────────────────────

def test_me_with_token(unauth_client, test_user):
    _clear_rate_limit()
    login = unauth_client.post("/api/auth/login", data={
        "username": "test@test.com",
        "password": "testpass",
    })
    token = login.json()["access_token"]
    resp = unauth_client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@test.com"


def test_me_no_token(unauth_client):
    resp = unauth_client.get("/api/auth/me")
    assert resp.status_code == 401


# ── Rate limiting ───────────────────────────────────────────────────────

def test_rate_limit_triggers(unauth_client, monkeypatch):
    _clear_rate_limit()
    monkeypatch.setattr(auth_module, "RATE_LIMIT_MAX", 2)
    # First 2 should succeed (even if credentials are wrong)
    for _ in range(2):
        unauth_client.post("/api/auth/login", data={
            "username": "nobody@test.com", "password": "x",
        })
    # Third should be rate-limited
    resp = unauth_client.post("/api/auth/login", data={
        "username": "nobody@test.com", "password": "x",
    })
    assert resp.status_code == 429
    assert "Too many" in resp.json()["detail"]
