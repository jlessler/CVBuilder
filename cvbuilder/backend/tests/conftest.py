"""Shared fixtures for the CVBuilder backend test suite."""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app


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
def client(db_session):
    """TestClient that uses the per-test DB session."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Factory helpers ──────────────────────────────────────────────────────

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
    """Create a minimal publication and return the response JSON."""
    resp = client.post("/api/publications", json={
        "type": "papers",
        "title": "A Great Paper",
        "year": "2024",
        "journal": "Nature",
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
        "theme_css": "academic",
        "sort_direction": "desc",
        "sections": [
            {"section_key": "education", "enabled": True, "section_order": 0},
            {"section_key": "experience", "enabled": True, "section_order": 1},
        ],
    })
    assert resp.status_code == 200
    return resp.json()
