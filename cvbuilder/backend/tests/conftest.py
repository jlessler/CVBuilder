"""Shared fixtures for the CVBuilder backend test suite."""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.auth import get_current_user, get_optional_current_user
from app.main import app
from app.models import User
from app.auth import get_password_hash


# ── In-memory SQLite engine (shared across the session) ──────────────────

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture(scope="session")
def _disable_startup():
    """Prevent the real startup event from running against production DB."""
    app.router.on_startup.clear()


# ── Per-test database session with rollback isolation ────────────────────

@pytest.fixture()
def db_session(engine, _disable_startup):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    # Ensure nested transactions work (BEGIN inside a transaction)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def test_user(db_session):
    """Create a test user in the DB and return it."""
    user = db_session.query(User).filter_by(email="test@test.com").first()
    if not user:
        user = User(
            email="test@test.com",
            hashed_password=get_password_hash("testpass"),
            full_name="Test User",
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()
    return user


@pytest.fixture()
def client(db_session, test_user):
    """TestClient that uses the per-test DB session and authenticated user."""

    def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_optional_current_user] = _override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Factory helpers ──────────────────────────────────────────────────────

@pytest.fixture()
def unauth_client(db_session, test_user):
    """TestClient with DB override but NO auth override — for testing real auth flow."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    # Do NOT override get_current_user — let real JWT auth run
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def user_b(db_session):
    """Second test user for isolation tests."""
    user = User(
        email="userb@test.com",
        hashed_password=get_password_hash("testpass"),
        full_name="User B",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def client_b(db_session, user_b):
    """TestClient authenticated as user_b."""

    def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return user_b

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_optional_current_user] = _override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_profile(client):
    """Create a minimal profile and return the response JSON."""
    resp = client.put("/api/profile", json={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "addresses": [
            {"type": "work", "line_order": 0, "text": "123 Lab St"},
        ],
    })
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture()
def sample_publication(client):
    """Create a minimal publication (as a Work) and return the response JSON."""
    resp = client.post("/api/works", json={
        "work_type": "papers",
        "title": "A Great Paper",
        "year": 2024,
        "data": {"journal": "Nature"},
        "authors": [
            {"author_name": "Doe J", "author_order": 0},
            {"author_name": "Smith A", "author_order": 1},
        ],
    })
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture()
def sample_template(client):
    """Create a minimal template and return the response JSON."""
    resp = client.post("/api/templates", json={
        "name": "Test Template",
        "description": "For testing",
        "style": {
            "primary_color": "#1a3a5c", "accent_color": "#2e6da4",
            "font_body": '"Times New Roman", Times, serif',
            "font_heading": "Arial, Helvetica, sans-serif",
            "body_font_size": "11pt", "name_font_size": "20pt",
            "header_alignment": "center", "section_decoration": "bottom-border",
            "heading_transform": "uppercase",
        },
        "sort_direction": "desc",
        "sections": [
            {"section_key": "education", "enabled": True, "section_order": 0},
            {"section_key": "experience", "enabled": True, "section_order": 1},
        ],
    })
    assert resp.status_code == 200
    return resp.json()
