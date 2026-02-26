"""CRUD tests for representative CV sections (Education, Grants, Panels, Trainees)."""


# ── Education (full CRUD cycle) ─────────────────────────────────────────

class TestEducation:
    def test_list_empty(self, client):
        assert client.get("/api/education").json() == []

    def test_create(self, client):
        resp = client.post("/api/education", json={
            "degree": "PhD", "year": 2020, "subject": "Epi", "school": "UNC",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["degree"] == "PhD"
        assert body["year"] == 2020
        assert "id" in body

    def test_update(self, client):
        created = client.post("/api/education", json={
            "degree": "MPH", "year": 2015, "school": "Hopkins",
        }).json()
        resp = client.put(f"/api/education/{created['id']}", json={
            "degree": "DrPH", "year": 2015, "school": "Hopkins",
        })
        assert resp.status_code == 200
        assert resp.json()["degree"] == "DrPH"

    def test_delete(self, client):
        created = client.post("/api/education", json={
            "degree": "BS", "year": 2010, "school": "MIT",
        }).json()
        resp = client.delete(f"/api/education/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Verify gone
        items = client.get("/api/education").json()
        assert all(i["id"] != created["id"] for i in items)

    def test_update_404(self, client):
        resp = client.put("/api/education/9999", json={
            "degree": "PhD", "year": 2020,
        })
        assert resp.status_code == 404

    def test_delete_404(self, client):
        assert client.delete("/api/education/9999").status_code == 404

    def test_sorted_by_year_desc(self, client):
        client.post("/api/education", json={"degree": "BS", "year": 2010})
        client.post("/api/education", json={"degree": "PhD", "year": 2020})
        client.post("/api/education", json={"degree": "MPH", "year": 2015})
        items = client.get("/api/education").json()
        years = [i["year"] for i in items]
        assert years == sorted(years, reverse=True)


# ── Grants (sorted listing, many fields) ────────────────────────────────

class TestGrants:
    def test_create_and_list(self, client):
        client.post("/api/grants", json={
            "title": "Grant A", "agency": "NIH", "years_start": "2018",
            "role": "PI", "status": "active",
        })
        client.post("/api/grants", json={
            "title": "Grant B", "agency": "CDC", "years_start": "2022",
            "role": "Co-I", "status": "completed",
        })
        items = client.get("/api/grants").json()
        assert len(items) == 2
        # Default sort is desc by years_start
        assert items[0]["years_start"] >= items[1]["years_start"]


# ── Panels (query param filtering by panel_type) ────────────────────────

class TestPanels:
    def test_filter_by_panel_type(self, client):
        client.post("/api/panels", json={
            "panel": "DSMB", "type": "advisory", "date": "2023",
        })
        client.post("/api/panels", json={
            "panel": "NIH Study", "type": "grant_review", "date": "2024",
        })
        adv = client.get("/api/panels?panel_type=advisory").json()
        gr = client.get("/api/panels?panel_type=grant_review").json()
        assert len(adv) == 1
        assert adv[0]["panel"] == "DSMB"
        assert len(gr) == 1
        assert gr[0]["panel"] == "NIH Study"

    def test_no_filter_returns_all(self, client):
        client.post("/api/panels", json={"panel": "A", "type": "advisory"})
        client.post("/api/panels", json={"panel": "B", "type": "grant_review"})
        assert len(client.get("/api/panels").json()) == 2


# ── Trainees (query param filtering by trainee_type) ────────────────────

class TestTrainees:
    def test_filter_by_trainee_type(self, client):
        client.post("/api/trainees", json={
            "name": "Student", "trainee_type": "advisee",
        })
        client.post("/api/trainees", json={
            "name": "Postdoc", "trainee_type": "postdoc",
        })
        adv = client.get("/api/trainees?trainee_type=advisee").json()
        pd = client.get("/api/trainees?trainee_type=postdoc").json()
        assert len(adv) == 1 and adv[0]["name"] == "Student"
        assert len(pd) == 1 and pd[0]["name"] == "Postdoc"
