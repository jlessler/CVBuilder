"""Tests for admin user management endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.auth import get_current_user, get_current_admin, get_password_hash
from app.models import User, Work, WorkAuthor, CVItem, Profile, Address


# ── Helpers ────────────────────────────────────────────────────────────

@pytest.fixture()
def admin_user(db_session):
    user = User(
        email="admin@test.com",
        hashed_password=get_password_hash("adminpass"),
        full_name="Admin User",
        is_active=True,
        is_admin=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def regular_user(db_session):
    user = User(
        email="regular@test.com",
        hashed_password=get_password_hash("pass"),
        full_name="Regular User",
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def admin_client(db_session, admin_user):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_current_admin] = lambda: admin_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def nonadmin_client(db_session, regular_user):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: regular_user
    # Don't override get_current_admin — let the real check run
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── List users ─────────────────────────────────────────────────────────

def test_list_users(admin_client, admin_user, regular_user):
    resp = admin_client.get("/api/admin/users")
    assert resp.status_code == 200
    users = resp.json()
    emails = [u["email"] for u in users]
    assert admin_user.email in emails
    assert regular_user.email in emails


def test_list_users_non_admin_403(nonadmin_client):
    resp = nonadmin_client.get("/api/admin/users")
    assert resp.status_code == 403


# ── Update user ────────────────────────────────────────────────────────

def test_deactivate_user(admin_client, regular_user):
    resp = admin_client.patch(
        f"/api/admin/users/{regular_user.id}",
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_activate_user(admin_client, db_session, regular_user):
    regular_user.is_active = False
    db_session.flush()
    resp = admin_client.patch(
        f"/api/admin/users/{regular_user.id}",
        json={"is_active": True},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


def test_promote_admin(admin_client, regular_user):
    resp = admin_client.patch(
        f"/api/admin/users/{regular_user.id}",
        json={"is_admin": True},
    )
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True


def test_demote_admin(admin_client, db_session, regular_user):
    regular_user.is_admin = True
    db_session.flush()
    resp = admin_client.patch(
        f"/api/admin/users/{regular_user.id}",
        json={"is_admin": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is False


def test_update_full_name(admin_client, regular_user):
    resp = admin_client.patch(
        f"/api/admin/users/{regular_user.id}",
        json={"full_name": "New Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "New Name"


def test_update_nonexistent_user_404(admin_client):
    resp = admin_client.patch("/api/admin/users/99999", json={"is_active": False})
    assert resp.status_code == 404


def test_update_non_admin_403(nonadmin_client, admin_user):
    resp = nonadmin_client.patch(
        f"/api/admin/users/{admin_user.id}",
        json={"is_active": False},
    )
    assert resp.status_code == 403


# ── Self-protection guards ─────────────────────────────────────────────

def test_cannot_deactivate_self(admin_client, admin_user):
    resp = admin_client.patch(
        f"/api/admin/users/{admin_user.id}",
        json={"is_active": False},
    )
    assert resp.status_code == 400
    assert "yourself" in resp.json()["detail"].lower()


def test_cannot_remove_own_admin(admin_client, admin_user):
    resp = admin_client.patch(
        f"/api/admin/users/{admin_user.id}",
        json={"is_admin": False},
    )
    assert resp.status_code == 400
    assert "yourself" in resp.json()["detail"].lower() or "own" in resp.json()["detail"].lower()


def test_cannot_delete_self(admin_client, admin_user):
    resp = admin_client.delete(f"/api/admin/users/{admin_user.id}")
    assert resp.status_code == 400


# ── Delete user ────────────────────────────────────────────────────────

def test_delete_user(admin_client, db_session, regular_user):
    # Create some data for the user to verify cascade
    work = Work(user_id=regular_user.id, work_type="papers", title="Test Paper", year=2024)
    db_session.add(work)
    db_session.flush()
    wa = WorkAuthor(work_id=work.id, author_name="Regular User", author_order=0)
    db_session.add(wa)
    item = CVItem(user_id=regular_user.id, section="education", data={"degree": "PhD"})
    db_session.add(item)
    profile = Profile(user_id=regular_user.id, name="Regular User")
    db_session.add(profile)
    db_session.flush()
    addr = Address(profile_id=profile.id, text="123 Main St")
    db_session.add(addr)
    db_session.flush()

    uid = regular_user.id
    wid = work.id
    pid = profile.id
    resp = admin_client.delete(f"/api/admin/users/{uid}")
    assert resp.status_code == 204

    # Verify cascaded deletion
    assert db_session.query(User).filter_by(id=uid).first() is None
    assert db_session.query(Work).filter_by(user_id=uid).count() == 0
    assert db_session.query(WorkAuthor).filter_by(work_id=wid).count() == 0
    assert db_session.query(CVItem).filter_by(user_id=uid).count() == 0
    assert db_session.query(Profile).filter_by(user_id=uid).count() == 0


def test_delete_nonexistent_user_404(admin_client):
    resp = admin_client.delete("/api/admin/users/99999")
    assert resp.status_code == 404


def test_delete_non_admin_403(nonadmin_client, admin_user):
    resp = nonadmin_client.delete(f"/api/admin/users/{admin_user.id}")
    assert resp.status_code == 403


# ── Reset password ────────────────────────────────────────────────────

def test_reset_password(admin_client, regular_user):
    resp = admin_client.post(
        f"/api/admin/users/{regular_user.id}/reset-password",
        json={"new_password": "resetpass123"},
    )
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Password reset"

    # Verify new password works via hash check
    from app.auth import verify_password
    assert verify_password("resetpass123", regular_user.hashed_password)


def test_reset_password_non_admin_403(nonadmin_client, admin_user):
    resp = nonadmin_client.post(
        f"/api/admin/users/{admin_user.id}/reset-password",
        json={"new_password": "newpass"},
    )
    assert resp.status_code == 403


def test_reset_password_nonexistent_user_404(admin_client):
    resp = admin_client.post(
        "/api/admin/users/99999/reset-password",
        json={"new_password": "newpass123"},
    )
    assert resp.status_code == 404


def test_reset_password_too_short(admin_client, regular_user):
    resp = admin_client.post(
        f"/api/admin/users/{regular_user.id}/reset-password",
        json={"new_password": "short"},
    )
    assert resp.status_code == 422
