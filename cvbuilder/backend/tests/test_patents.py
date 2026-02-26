"""Tests for Patent CRUD with nested authors."""


def test_create_patent_with_authors(client):
    resp = client.post("/api/patents", json={
        "name": "Cool Invention",
        "number": "US123",
        "status": "granted",
        "authors": [
            {"author_name": "Doe J", "author_order": 0},
            {"author_name": "Smith A", "author_order": 1},
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Cool Invention"
    assert len(body["authors"]) == 2
    assert body["authors"][0]["author_name"] == "Doe J"


def test_update_replaces_authors(client):
    created = client.post("/api/patents", json={
        "name": "Widget",
        "authors": [{"author_name": "Alice", "author_order": 0}],
    }).json()
    resp = client.put(f"/api/patents/{created['id']}", json={
        "name": "Widget v2",
        "authors": [
            {"author_name": "Bob", "author_order": 0},
            {"author_name": "Carol", "author_order": 1},
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Widget v2"
    names = [a["author_name"] for a in body["authors"]]
    assert "Alice" not in names
    assert "Bob" in names


def test_delete_patent(client):
    created = client.post("/api/patents", json={
        "name": "Temp Patent",
        "authors": [{"author_name": "X", "author_order": 0}],
    }).json()
    resp = client.delete(f"/api/patents/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_update_patent_404(client):
    resp = client.put("/api/patents/9999", json={
        "name": "Ghost", "authors": [],
    })
    assert resp.status_code == 404


def test_delete_patent_404(client):
    assert client.delete("/api/patents/9999").status_code == 404
