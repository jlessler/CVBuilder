"""Tests for CVItem generic CRUD endpoints."""


def test_create_cv_item(client):
    resp = client.post("/api/cv", json={
        "section": "education",
        "data": {"degree": "PhD", "year": 2020, "subject": "Physics", "school": "MIT"},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["section"] == "education"
    assert body["data"]["degree"] == "PhD"
    assert body["sort_date"] == 2020


def test_list_cv_items_by_section(client):
    client.post("/api/cv", json={
        "section": "education",
        "data": {"degree": "PhD", "year": 2020, "school": "MIT"},
    })
    client.post("/api/cv", json={
        "section": "education",
        "data": {"degree": "BS", "year": 2015, "school": "Stanford"},
    })
    client.post("/api/cv", json={
        "section": "experience",
        "data": {"title": "Professor", "years_start": "2021"},
    })

    edu = client.get("/api/cv/education").json()
    assert len(edu) == 2
    assert all(e["section"] == "education" for e in edu)

    exp = client.get("/api/cv/experience").json()
    assert len(exp) == 1


def test_update_cv_item(client):
    created = client.post("/api/cv", json={
        "section": "awards",
        "data": {"name": "Best Paper", "year": "2023"},
    }).json()

    resp = client.put(f"/api/cv/{created['id']}", json={
        "data": {"name": "Best Paper Award", "year": "2024"},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Best Paper Award"
    assert body["sort_date"] == 2024


def test_update_cv_item_404(client):
    resp = client.put("/api/cv/9999", json={"data": {"name": "Ghost"}})
    assert resp.status_code == 404


def test_delete_cv_item(client):
    created = client.post("/api/cv", json={
        "section": "memberships",
        "data": {"org": "IEEE", "years": "2020-present"},
    }).json()

    resp = client.delete(f"/api/cv/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    items = client.get("/api/cv/memberships").json()
    assert len(items) == 0


def test_delete_cv_item_404(client):
    assert client.delete("/api/cv/9999").status_code == 404


def test_sort_date_computed_for_experience(client):
    resp = client.post("/api/cv", json={
        "section": "experience",
        "data": {"title": "Postdoc", "years_start": "2018", "years_end": "2021"},
    })
    assert resp.json()["sort_date"] == 2018


def test_sort_date_computed_for_grants(client):
    resp = client.post("/api/cv", json={
        "section": "grants",
        "data": {"title": "R01", "years_start": "2022", "agency": "NIH"},
    })
    assert resp.json()["sort_date"] == 2022


def test_sort_date_null_for_unknown_section(client):
    resp = client.post("/api/cv", json={
        "section": "editorial",
        "data": {"journal": "Nature", "role": "Editor"},
    })
    assert resp.json()["sort_date"] is None


def test_sort_date_misc_fallback(client):
    """Misc sections with a 'date' field should still get sort_date via fallback."""
    resp = client.post("/api/cv", json={
        "section": "chairedsessions",
        "data": {"title": "Session A", "date": "June 2019", "meeting": "ASTMH"},
    })
    assert resp.json()["sort_date"] == 2019


def test_getattr_delegation(db_session):
    """CVItem.__getattr__ delegates to data dict."""
    from app.models import CVItem
    item = CVItem(section="education", data={"degree": "PhD", "year": 2020})
    assert item.degree == "PhD"
    assert item.year == 2020
    assert item.nonexistent is None


def test_sort_order_preserved(client):
    client.post("/api/cv", json={
        "section": "education",
        "data": {"degree": "PhD"}, "sort_order": 2,
    })
    client.post("/api/cv", json={
        "section": "education",
        "data": {"degree": "BS"}, "sort_order": 1,
    })
    items = client.get("/api/cv/education").json()
    assert items[0]["data"]["degree"] == "BS"
    assert items[1]["data"]["degree"] == "PhD"
