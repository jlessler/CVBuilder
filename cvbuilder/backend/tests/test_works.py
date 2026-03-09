"""Tests for Works CRUD, filters, nested authors, DOI lookup, and sync-add."""


# ── CRUD ─────────────────────────────────────────────────────────────────

def test_create_work_paper(client):
    resp = client.post("/api/works", json={
        "work_type": "papers",
        "title": "Test Paper",
        "year": 2023,
        "doi": "10.1234/test",
        "data": {"journal": "Science", "volume": "1", "pages": "1-10"},
        "authors": [
            {"author_name": "Doe J", "author_order": 0, "corresponding": True},
            {"author_name": "Smith A", "author_order": 1},
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Test Paper"
    assert body["work_type"] == "papers"
    assert body["year"] == 2023
    assert len(body["authors"]) == 2
    assert body["authors"][0]["corresponding"] is True
    assert body["data"]["journal"] == "Science"


def test_create_work_patent(client):
    resp = client.post("/api/works", json={
        "work_type": "patents",
        "title": "My Patent",
        "data": {"identifier": "US12345", "status": "granted"},
        "authors": [{"author_name": "Inventor A", "author_order": 0}],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["work_type"] == "patents"
    assert body["data"]["identifier"] == "US12345"


def test_create_work_seminar(client):
    resp = client.post("/api/works", json={
        "work_type": "seminars",
        "title": "Invited Talk",
        "year": 2024,
        "month": 3,
        "data": {"institution": "MIT", "conference": "EpiCon", "location": "Boston"},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["work_type"] == "seminars"
    assert body["month"] == 3
    assert body["data"]["institution"] == "MIT"


def test_create_work_software(client):
    resp = client.post("/api/works", json={
        "work_type": "software",
        "title": "EpiTools",
        "year": 2022,
        "data": {"publisher": "GitHub", "url": "https://github.com/test"},
        "authors": [
            {"author_name": "Dev A", "author_order": 0},
            {"author_name": "Dev B", "author_order": 1},
        ],
    })
    assert resp.status_code == 200
    assert resp.json()["work_type"] == "software"


def test_create_work_dissertation(client):
    resp = client.post("/api/works", json={
        "work_type": "dissertation",
        "title": "My Thesis",
        "year": 2010,
        "data": {"institution": "Harvard"},
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["institution"] == "Harvard"


def test_get_work_by_id(client):
    create = client.post("/api/works", json={
        "work_type": "papers", "title": "Fetch Me", "year": 2024,
        "authors": [],
    })
    wid = create.json()["id"]
    resp = client.get(f"/api/works/{wid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Fetch Me"


def test_get_work_404(client):
    assert client.get("/api/works/9999").status_code == 404


def test_update_work(client):
    create = client.post("/api/works", json={
        "work_type": "papers", "title": "Original", "year": 2023,
        "authors": [{"author_name": "A", "author_order": 0}],
    })
    wid = create.json()["id"]
    resp = client.put(f"/api/works/{wid}", json={
        "work_type": "papers", "title": "Updated Title", "year": 2024,
        "authors": [{"author_name": "New Author", "author_order": 0}],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Updated Title"
    assert len(body["authors"]) == 1
    assert body["authors"][0]["author_name"] == "New Author"


def test_update_work_404(client):
    resp = client.put("/api/works/9999", json={
        "work_type": "papers", "title": "Ghost",
    })
    assert resp.status_code == 404


def test_authors_preserved_when_null(client):
    """If authors is omitted in update, existing authors should remain."""
    create = client.post("/api/works", json={
        "work_type": "papers", "title": "Keep Authors", "year": 2023,
        "authors": [
            {"author_name": "A", "author_order": 0},
            {"author_name": "B", "author_order": 1},
        ],
    })
    wid = create.json()["id"]
    resp = client.put(f"/api/works/{wid}", json={
        "work_type": "papers", "title": "Same Authors", "year": 2024,
        # authors intentionally omitted
    })
    assert resp.status_code == 200
    assert len(resp.json()["authors"]) == 2


def test_delete_work(client):
    create = client.post("/api/works", json={
        "work_type": "papers", "title": "Delete Me", "year": 2023,
        "authors": [],
    })
    wid = create.json()["id"]
    resp = client.delete(f"/api/works/{wid}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert client.get(f"/api/works/{wid}").status_code == 404


def test_delete_work_404(client):
    assert client.delete("/api/works/9999").status_code == 404


# ── Author role flags ────────────────────────────────────────────────────

def test_author_role_flags(client):
    resp = client.post("/api/works", json={
        "work_type": "papers", "title": "Role Test", "year": 2024,
        "authors": [
            {"author_name": "First", "author_order": 0,
             "corresponding": True, "cofirst": True},
            {"author_name": "Middle", "author_order": 1, "student": True},
            {"author_name": "Last", "author_order": 2, "cosenior": True},
        ],
    })
    assert resp.status_code == 200
    authors = resp.json()["authors"]
    assert authors[0]["corresponding"] is True
    assert authors[0]["cofirst"] is True
    assert authors[1]["student"] is True
    assert authors[2]["cosenior"] is True


# ── Filters ──────────────────────────────────────────────────────────────

def _seed_works(client):
    client.post("/api/works", json={
        "work_type": "papers", "title": "Malaria Paper", "year": 2022,
        "data": {"journal": "Lancet"}, "authors": [],
    })
    client.post("/api/works", json={
        "work_type": "preprints", "title": "COVID Preprint", "year": 2023,
        "data": {"journal": "medRxiv"}, "authors": [],
    })
    client.post("/api/works", json={
        "work_type": "papers", "title": "Dengue Study", "year": 2022,
        "data": {"journal": "Nature", "select_flag": True}, "authors": [],
    })


def test_filter_by_type(client):
    _seed_works(client)
    items = client.get("/api/works?type=preprints").json()
    assert all(i["work_type"] == "preprints" for i in items)
    assert len(items) >= 1


def test_filter_by_year(client):
    _seed_works(client)
    items = client.get("/api/works?year=2022").json()
    assert all(i["year"] == 2022 for i in items)


def test_filter_by_keyword(client):
    _seed_works(client)
    items = client.get("/api/works?keyword=malaria").json()
    assert any("Malaria" in i["title"] for i in items)


def test_pagination(client):
    _seed_works(client)
    all_items = client.get("/api/works").json()
    page = client.get("/api/works?skip=0&limit=1").json()
    assert len(page) == 1
    assert len(all_items) >= len(page)


# ── DOI lookup (mocked) ─────────────────────────────────────────────────

def test_doi_lookup_mocked(client, monkeypatch):
    monkeypatch.setattr("app.routers.works.lookup_doi", lambda doi: {
        "title": "Mocked Title",
        "year": "2025",
        "journal": "Mock Journal",
        "authors": ["Author A"],
        "doi": doi,
    })
    resp = client.post("/api/works/doi-lookup", json={"doi": "10.1234/test"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Mocked Title"


def test_doi_lookup_not_found(client, monkeypatch):
    def _raise(doi):
        raise ValueError("DOI not found")
    monkeypatch.setattr("app.routers.works.lookup_doi", _raise)
    resp = client.post("/api/works/doi-lookup", json={"doi": "10.0000/bad"})
    assert resp.status_code == 404


# ── sync-add ─────────────────────────────────────────────────────────────

def test_sync_add(client):
    resp = client.post("/api/works/sync-add", json={
        "publications": [
            {
                "title": "Synced Work",
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
    assert body[0]["title"] == "Synced Work"
    assert body[0]["year"] == 2025
    assert len(body[0]["authors"]) == 2


def test_sync_add_non_numeric_year(client):
    resp = client.post("/api/works/sync-add", json={
        "publications": [
            {
                "title": "In Press Paper",
                "year": "in press",
                "journal": "Nature",
                "authors": [],
                "source": "pubmed",
                "pub_type": "papers",
            },
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["year"] is None
    assert body[0]["data"]["year_raw"] == "in press"
