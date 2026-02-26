"""Tests for MiscSection CRUD and editorial aggregation."""


def test_create_and_list_misc(client):
    resp = client.post("/api/misc", json={
        "section": "software",
        "data": {"name": "EpiTools", "url": "https://example.com"},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["section"] == "software"
    assert body["data"]["name"] == "EpiTools"

    items = client.get("/api/misc/software").json()
    assert len(items) == 1


def test_update_misc(client):
    created = client.post("/api/misc", json={
        "section": "peerrev",
        "data": {"journal": "Nature"},
    }).json()
    resp = client.put(f"/api/misc/{created['id']}", json={
        "section": "peerrev",
        "data": {"journal": "Science"},
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["journal"] == "Science"


def test_delete_misc(client):
    created = client.post("/api/misc", json={
        "section": "software",
        "data": {"name": "Temp"},
    }).json()
    resp = client.delete(f"/api/misc/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_editorial_aggregation(client):
    """GET /api/misc/editorial returns editor + assocedit + otheredit combined."""
    client.post("/api/misc", json={
        "section": "editor", "data": {"journal": "Lancet"},
    })
    client.post("/api/misc", json={
        "section": "assocedit", "data": {"journal": "BMJ"},
    })
    client.post("/api/misc", json={
        "section": "otheredit", "data": {"journal": "NEJM"},
    })
    # Also add a non-editorial misc to confirm it's excluded
    client.post("/api/misc", json={
        "section": "software", "data": {"name": "Noise"},
    })

    items = client.get("/api/misc/editorial").json()
    assert len(items) == 3
    sections = {i["section"] for i in items}
    assert sections == {"editor", "assocedit", "otheredit"}


def test_list_misc_by_section(client):
    client.post("/api/misc", json={"section": "policycons", "data": {"org": "WHO"}})
    client.post("/api/misc", json={"section": "policypres", "data": {"title": "Talk"}})
    items = client.get("/api/misc/policycons").json()
    assert len(items) == 1
    assert items[0]["data"]["org"] == "WHO"
