"""Tests that user A cannot access user B's data."""
from app import models


def _make_work(db_session, user):
    """Insert a Work directly via DB for the given user."""
    w = models.Work(user_id=user.id, work_type="papers", title="User's Paper", year=2024)
    db_session.add(w)
    db_session.flush()
    return w


def _make_cvitem(db_session, user):
    """Insert a CVItem directly via DB for the given user."""
    item = models.CVItem(user_id=user.id, section="education", data={"degree": "PhD", "year": 2020})
    db_session.add(item)
    db_session.flush()
    return item


def _make_template(db_session, user):
    """Insert a CVTemplate directly via DB for the given user."""
    tmpl = models.CVTemplate(user_id=user.id, name="Private Template", style={})
    db_session.add(tmpl)
    db_session.flush()
    return tmpl


# ── Works isolation ─────────────────────────────────────────────────────

class TestWorksIsolation:
    def test_cannot_get_other_users_work(self, db_session, test_user, client_b):
        w = _make_work(db_session, test_user)
        assert client_b.get(f"/api/works/{w.id}").status_code == 404

    def test_list_excludes_other_users_works(self, db_session, test_user, client_b):
        _make_work(db_session, test_user)
        items = client_b.get("/api/works").json()
        assert len(items) == 0

    def test_cannot_update_other_users_work(self, db_session, test_user, client_b):
        w = _make_work(db_session, test_user)
        resp = client_b.put(f"/api/works/{w.id}", json={
            "work_type": "papers", "title": "Hijacked",
        })
        assert resp.status_code == 404

    def test_cannot_delete_other_users_work(self, db_session, test_user, client_b):
        w = _make_work(db_session, test_user)
        assert client_b.delete(f"/api/works/{w.id}").status_code == 404


# ── CVItem isolation ────────────────────────────────────────────────────

class TestCVItemIsolation:
    def test_list_excludes_other_users_items(self, db_session, test_user, client_b):
        _make_cvitem(db_session, test_user)
        items = client_b.get("/api/cv/education").json()
        assert len(items) == 0

    def test_cannot_update_other_users_item(self, db_session, test_user, client_b):
        item = _make_cvitem(db_session, test_user)
        resp = client_b.put(f"/api/cv/{item.id}", json={"data": {"degree": "Stolen"}})
        assert resp.status_code == 404

    def test_cannot_delete_other_users_item(self, db_session, test_user, client_b):
        item = _make_cvitem(db_session, test_user)
        assert client_b.delete(f"/api/cv/{item.id}").status_code == 404


# ── Template isolation ──────────────────────────────────────────────────

class TestTemplateIsolation:
    def test_list_excludes_other_users_templates(self, db_session, test_user, client_b):
        _make_template(db_session, test_user)
        templates = client_b.get("/api/templates").json()
        ids = [t["id"] for t in templates]
        tmpl = db_session.query(models.CVTemplate).filter_by(user_id=test_user.id).first()
        assert tmpl.id not in ids

    def test_cannot_get_other_users_template(self, db_session, test_user, client_b):
        tmpl = _make_template(db_session, test_user)
        assert client_b.get(f"/api/templates/{tmpl.id}").status_code == 404

    def test_cannot_delete_other_users_template(self, db_session, test_user, client_b):
        tmpl = _make_template(db_session, test_user)
        assert client_b.delete(f"/api/templates/{tmpl.id}").status_code == 404


# ── Profile isolation ───────────────────────────────────────────────────

class TestProfileIsolation:
    def test_cannot_see_other_users_profile(self, db_session, test_user, client_b):
        # Create a profile for test_user directly
        db_session.add(models.Profile(user_id=test_user.id, name="Secret Name"))
        db_session.flush()
        resp = client_b.get("/api/profile")
        assert resp.status_code == 404
