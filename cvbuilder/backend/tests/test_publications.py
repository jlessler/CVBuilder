"""Tests for Publication CRUD, filters, nested authors, DOI lookup, and sync-add."""


# ── CRUD ─────────────────────────────────────────────────────────────────

def test_create_publication(client):
    resp = client.post("/api/publications", json={
        "type": "papers",
        "title": "Test Paper",
        "year": "2023",
        "journal": "Science",
        "authors": [{"author_name": "Doe J", "author_order": 0}],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Test Paper"
    assert len(body["authors"]) == 1


def test_get_publication_by_id(client):
    create = client.post("/api/publications", json={
        "type": "papers", "title": "Fetch Me", "year": "2024",
        "authors": [{"author_name": "Doe J", "author_order": 0}],
    })
    pid = create.json()["id"]
    resp = client.get(f"/api/publications/{pid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Fetch Me"


def test_get_publication_404(client):
    assert client.get("/api/publications/9999").status_code == 404


def test_update_publication(client):
    create = client.post("/api/publications", json={
        "type": "papers", "title": "Original", "year": "2023",
        "authors": [{"author_name": "Doe J", "author_order": 0}],
    })
    pid = create.json()["id"]
    resp = client.put(f"/api/publications/{pid}", json={
        "type": "papers",
        "title": "Updated Title",
        "year": "2024",
        "authors": [{"author_name": "New Author", "author_order": 0}],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Updated Title"
    assert len(body["authors"]) == 1
    assert body["authors"][0]["author_name"] == "New Author"


def test_update_publication_404(client):
    resp = client.put("/api/publications/9999", json={
        "type": "papers", "title": "Ghost",
    })
    assert resp.status_code == 404


def test_delete_publication(client):
    create = client.post("/api/publications", json={
        "type": "papers", "title": "Delete Me", "year": "2023",
        "authors": [],
    })
    pid = create.json()["id"]
    resp = client.delete(f"/api/publications/{pid}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_delete_publication_404(client):
    assert client.delete("/api/publications/9999").status_code == 404


# ── Author preservation when authors=null ────────────────────────────────

def test_authors_preserved_when_null(client):
    """If authors is omitted in update, existing authors should remain."""
    create = client.post("/api/publications", json={
        "type": "papers", "title": "Keep Authors", "year": "2023",
        "authors": [
            {"author_name": "A", "author_order": 0},
            {"author_name": "B", "author_order": 1},
        ],
    })
    pid = create.json()["id"]
    resp = client.put(f"/api/publications/{pid}", json={
        "type": "papers",
        "title": "Same Authors",
        "year": "2024",
        # authors intentionally omitted
    })
    assert resp.status_code == 200
    assert len(resp.json()["authors"]) == 2


# ── Filters ──────────────────────────────────────────────────────────────

def _seed_pubs(client):
    """Insert a few publications for filter tests."""
    client.post("/api/publications", json={
        "type": "papers", "title": "Malaria Paper", "year": "2022",
        "journal": "Lancet", "authors": [],
    })
    client.post("/api/publications", json={
        "type": "preprints", "title": "COVID Preprint", "year": "2023",
        "journal": "medRxiv", "authors": [],
    })
    client.post("/api/publications", json={
        "type": "papers", "title": "Dengue Study", "year": "2022",
        "journal": "Nature", "select_flag": True, "authors": [],
    })


def test_filter_by_type(client):
    _seed_pubs(client)
    items = client.get("/api/publications?type=preprints").json()
    assert all(i["type"] == "preprints" for i in items)
    assert len(items) >= 1


def test_filter_by_year(client):
    _seed_pubs(client)
    items = client.get("/api/publications?year=2022").json()
    assert all(i["year"] == "2022" for i in items)


def test_filter_by_keyword(client):
    _seed_pubs(client)
    items = client.get("/api/publications?keyword=malaria").json()
    assert any("Malaria" in i["title"] for i in items)


def test_filter_select_only(client):
    _seed_pubs(client)
    items = client.get("/api/publications?select_only=true").json()
    assert all(i["select_flag"] for i in items)
    assert len(items) >= 1


def test_pagination(client):
    _seed_pubs(client)
    all_items = client.get("/api/publications").json()
    page = client.get("/api/publications?skip=0&limit=1").json()
    assert len(page) == 1
    assert len(all_items) >= len(page)


# ── DOI lookup (mocked) ─────────────────────────────────────────────────

def test_doi_lookup_mocked(client, monkeypatch):
    monkeypatch.setattr("app.routers.publications.lookup_doi", lambda doi: {
        "title": "Mocked Title",
        "year": "2025",
        "journal": "Mock Journal",
        "authors": ["Author A"],
        "doi": doi,
    })
    resp = client.post("/api/publications/doi-lookup", json={"doi": "10.1234/test"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Mocked Title"


def test_doi_lookup_not_found(client, monkeypatch):
    def _raise(doi):
        raise ValueError("DOI not found")
    monkeypatch.setattr("app.routers.publications.lookup_doi", _raise)
    resp = client.post("/api/publications/doi-lookup", json={"doi": "10.0000/bad"})
    assert resp.status_code == 404


# ── sync-add ─────────────────────────────────────────────────────────────

def test_sync_add(client):
    resp = client.post("/api/publications/sync-add", json={
        "publications": [
            {
                "title": "Synced Paper",
                "year": "2025",
                "journal": "JAMA",
                "authors": ["First A", "Second B"],
                "source": "pubmed",
                "pub_type": "papers",
            },
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "Synced Paper"
    assert len(body[0]["authors"]) == 2
