"""CRUD tests for representative CV sections (Education, Grants, Panels, Trainees)."""


# ── Education (full CRUD cycle) ─────────────────────────────────────────

class TestEducation:
    def test_list_empty(self, client):
        assert client.get("/api/cv/education").json() == []

    def test_create(self, client):
        resp = client.post("/api/cv", json={
            "section": "education",
            "data": {"degree": "PhD", "year": 2020, "subject": "Epi", "school": "UNC"},
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["degree"] == "PhD"
        assert body["data"]["year"] == 2020
        assert "id" in body
        assert body["section"] == "education"

    def test_update(self, client):
        created = client.post("/api/cv", json={
            "section": "education",
            "data": {"degree": "MPH", "year": 2015, "school": "Hopkins"},
        }).json()
        resp = client.put(f"/api/cv/{created['id']}", json={
            "data": {"degree": "DrPH", "year": 2015, "school": "Hopkins"},
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["degree"] == "DrPH"

    def test_delete(self, client):
        created = client.post("/api/cv", json={
            "section": "education",
            "data": {"degree": "BS", "year": 2010, "school": "MIT"},
        }).json()
        resp = client.delete(f"/api/cv/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Verify gone
        items = client.get("/api/cv/education").json()
        assert all(i["id"] != created["id"] for i in items)

    def test_update_404(self, client):
        resp = client.put("/api/cv/9999", json={
            "data": {"degree": "PhD", "year": 2020},
        })
        assert resp.status_code == 404

    def test_delete_404(self, client):
        assert client.delete("/api/cv/9999").status_code == 404

    def test_sorted_by_year_desc(self, client):
        client.post("/api/cv", json={"section": "education", "data": {"degree": "BS", "year": 2010}})
        client.post("/api/cv", json={"section": "education", "data": {"degree": "PhD", "year": 2020}})
        client.post("/api/cv", json={"section": "education", "data": {"degree": "MPH", "year": 2015}})
        items = client.get("/api/cv/education").json()
        years = [i["data"]["year"] for i in items]
        assert years == sorted(years, reverse=True)


# ── Grants (sorted listing, many fields) ────────────────────────────────

class TestGrants:
    def test_create_and_list(self, client):
        client.post("/api/cv", json={
            "section": "grants",
            "data": {"title": "Grant A", "agency": "NIH", "years_start": "2018",
                     "role": "PI", "status": "active"},
        })
        client.post("/api/cv", json={
            "section": "grants",
            "data": {"title": "Grant B", "agency": "CDC", "years_start": "2022",
                     "role": "Co-I", "status": "completed"},
        })
        items = client.get("/api/cv/grants").json()
        assert len(items) == 2
        # Default sort is desc by years_start
        assert items[0]["data"]["years_start"] >= items[1]["data"]["years_start"]


# ── Panels (separate sections per panel_type) ───────────────────────────

class TestPanels:
    def test_filter_by_panel_type(self, client):
        client.post("/api/cv", json={
            "section": "panels_advisory",
            "data": {"panel": "DSMB", "type": "advisory", "date": "2023"},
        })
        client.post("/api/cv", json={
            "section": "panels_grant_review",
            "data": {"panel": "NIH Study", "type": "grant_review", "date": "2024"},
        })
        adv = client.get("/api/cv/panels_advisory").json()
        gr = client.get("/api/cv/panels_grant_review").json()
        assert len(adv) == 1
        assert adv[0]["data"]["panel"] == "DSMB"
        assert len(gr) == 1
        assert gr[0]["data"]["panel"] == "NIH Study"

    def test_no_filter_returns_all(self, client):
        client.post("/api/cv", json={
            "section": "panels_advisory",
            "data": {"panel": "A", "type": "advisory"},
        })
        client.post("/api/cv", json={
            "section": "panels_grant_review",
            "data": {"panel": "B", "type": "grant_review"},
        })
        adv = client.get("/api/cv/panels_advisory").json()
        gr = client.get("/api/cv/panels_grant_review").json()
        assert len(adv) == 1
        assert len(gr) == 1


# ── Trainees (separate sections per trainee_type) ────────────────────────

class TestTrainees:
    def test_filter_by_trainee_type(self, client):
        client.post("/api/cv", json={
            "section": "trainees_advisees",
            "data": {"name": "Student", "trainee_type": "advisee"},
        })
        client.post("/api/cv", json={
            "section": "trainees_postdocs",
            "data": {"name": "Postdoc", "trainee_type": "postdoc"},
        })
        adv = client.get("/api/cv/trainees_advisees").json()
        pd = client.get("/api/cv/trainees_postdocs").json()
        assert len(adv) == 1 and adv[0]["data"]["name"] == "Student"
        assert len(pd) == 1 and pd[0]["data"]["name"] == "Postdoc"
