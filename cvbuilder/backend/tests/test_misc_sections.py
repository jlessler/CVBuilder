"""Tests for CVItem CRUD (formerly MiscSection)."""


def test_create_and_list_cvitem(client):
    resp = client.post("/api/cv", json={
        "section": "peerrev",
        "data": {"value": "Nature Reviews"},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["section"] == "peerrev"
    assert body["data"]["value"] == "Nature Reviews"

    items = client.get("/api/cv/peerrev").json()
    assert len(items) == 1


def test_update_cvitem(client):
    created = client.post("/api/cv", json={
        "section": "peerrev",
        "data": {"journal": "Nature"},
    }).json()
    resp = client.put(f"/api/cv/{created['id']}", json={
        "section": "peerrev",
        "data": {"journal": "Science"},
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["journal"] == "Science"


def test_delete_cvitem(client):
    created = client.post("/api/cv", json={
        "section": "otherservice",
        "data": {"value": "Temp"},
    }).json()
    resp = client.delete(f"/api/cv/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_editorial_sections(client):
    """Editorial items are stored as individual CVItems queryable by section."""
    client.post("/api/cv", json={
        "section": "editor", "data": {"journal": "Lancet"},
    })
    client.post("/api/cv", json={
        "section": "assocedit", "data": {"journal": "BMJ"},
    })
    client.post("/api/cv", json={
        "section": "otheredit", "data": {"journal": "NEJM"},
    })
    # Also add a non-editorial CVItem to confirm it's excluded
    client.post("/api/cv", json={
        "section": "peerrev", "data": {"value": "Noise"},
    })

    editors = client.get("/api/cv/editor").json()
    assert len(editors) == 1
    assert editors[0]["data"]["journal"] == "Lancet"

    assoc = client.get("/api/cv/assocedit").json()
    assert len(assoc) == 1
    assert assoc[0]["data"]["journal"] == "BMJ"

    other = client.get("/api/cv/otheredit").json()
    assert len(other) == 1
    assert other[0]["data"]["journal"] == "NEJM"


def test_list_cvitem_by_section(client):
    client.post("/api/cv", json={"section": "policycons", "data": {"org": "WHO"}})
    client.post("/api/cv", json={"section": "policypres", "data": {"title": "Talk"}})
    items = client.get("/api/cv/policycons").json()
    assert len(items) == 1
    assert items[0]["data"]["org"] == "WHO"
