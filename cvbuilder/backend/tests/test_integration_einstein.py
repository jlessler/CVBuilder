"""Integration test: import Einstein sample YAML, verify DB state, exercise UNC CV preview.

This test imports the sample Einstein CV and publications YAML fixtures,
then verifies the data round-trips correctly through the API and can
render a UNC-format CV preview.
"""
from pathlib import Path
from unittest.mock import patch

import yaml

from app.services.yaml_import import import_cv_yaml, import_refs_yaml

FIXTURES = Path(__file__).parent / "fixtures"


# ── YAML import populates all expected sections ─────────────────────────

class TestImportCV:
    """Import einstein_cv.yml via the service and verify via API."""

    def _import(self, db_session):
        import_cv_yaml(str(FIXTURES / "einstein_cv.yml"), db_session)

    # -- Profile ----------------------------------------------------------

    def test_profile(self, client, db_session):
        self._import(db_session)
        p = client.get("/api/profile").json()
        assert p["name"] == "Albert Einstein"
        assert p["email"] == "einstein@ias.edu"
        assert any("Institute for Advanced Study" in a["text"] for a in p["addresses"])
        assert any("Mercer Street" in a["text"] for a in p["addresses"])
        work = [a for a in p["addresses"] if a["type"] == "work"]
        home = [a for a in p["addresses"] if a["type"] == "home"]
        assert len(work) == 3
        assert len(home) == 2

    # -- Education --------------------------------------------------------

    def test_education(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/education").json()
        assert len(items) == 2
        degrees = {i["data"]["degree"] for i in items}
        assert degrees == {"PhD", "Diploma"}
        phd = next(i for i in items if i["data"]["degree"] == "PhD")
        assert phd["data"]["year"] == 1905
        assert phd["data"]["school"] == "University of Zurich"

    # -- Experience -------------------------------------------------------

    def test_experience(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/experience").json()
        assert len(items) == 6
        ias = next(i for i in items if "Institute for Advanced Study" in i["data"]["employer"])
        assert ias["data"]["years_start"] == "1933"
        assert ias["data"]["years_end"] == "1955"
        patent_office = next(i for i in items if "Patent Office" in i["data"]["employer"])
        assert patent_office["data"]["title"] == "Technical Expert, Class III"

    # -- Awards -----------------------------------------------------------

    def test_awards(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/awards").json()
        assert len(items) == 5
        names = {i["data"]["name"] for i in items}
        assert "Nobel Prize in Physics" in names
        assert "Copley Medal" in names
        nobel = next(i for i in items if "Nobel" in i["data"]["name"])
        assert nobel["data"]["org"] == "Royal Swedish Academy of Sciences"

    # -- Memberships ------------------------------------------------------

    def test_memberships(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/memberships").json()
        assert len(items) == 4
        orgs = {i["data"]["org"] for i in items}
        assert "Royal Society (Foreign Member)" in orgs

    # -- Panels (advisory + grant review) ---------------------------------

    def test_panels(self, client, db_session):
        self._import(db_session)
        advisory = client.get("/api/cv/panels_advisory").json()
        grant_rev = client.get("/api/cv/panels_grantreview").json()
        assert len(advisory) == 2
        assert len(grant_rev) == 1
        assert any("Emergency Committee" in p["data"]["panel"] for p in advisory)

    # -- Patents ----------------------------------------------------------

    def test_patents(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/works?type=patents").json()
        assert len(items) == 1
        p = items[0]
        assert "Einstein-Szilard" in p["title"] or "Refrigerator" in p["title"]
        assert p["data"]["identifier"] == "US1781541"
        assert len(p["authors"]) == 2
        author_names = [a["author_name"] for a in p["authors"]]
        assert "Einstein A" in author_names
        assert "Szilard L" in author_names

    # -- Symposia ---------------------------------------------------------

    def test_symposia(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/symposia").json()
        assert len(items) == 2
        assert any("Solvay" in i["data"]["meeting"] for i in items)

    # -- Teaching ---------------------------------------------------------

    def test_classes(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/classes").json()
        assert len(items) == 3
        stat_mech = next(i for i in items if "Statistical" in (i["data"].get("class_name") or ""))
        assert stat_mech["data"]["year"] == 1936
        assert stat_mech["data"]["school"] == "Institute for Advanced Study"

    # -- Grants -----------------------------------------------------------

    def test_grants(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/grants").json()
        assert len(items) == 3  # 1 active + 2 completed
        statuses = {i["data"]["status"] for i in items}
        assert statuses == {"active", "completed"}
        uft = next(i for i in items if "Unified" in (i["data"].get("title") or "") and i["data"]["status"] == "completed")
        assert uft["data"]["agency"] == "Institute for Advanced Study"
        assert uft["data"]["years_start"] == "1933"
        active = [i for i in items if i["data"]["status"] == "active"]
        assert len(active) == 1
        assert "Rockefeller" in active[0]["data"]["agency"]

    # -- Trainees ---------------------------------------------------------

    def test_trainees(self, client, db_session):
        self._import(db_session)
        advisees = client.get("/api/cv/trainees_advisees").json()
        postdocs = client.get("/api/cv/trainees_postdocs").json()
        assert len(advisees) == 2
        assert len(postdocs) == 3
        rosen = next(t for t in advisees if "Rosen" in t["data"]["name"])
        assert "EPR" in rosen["data"]["thesis"]
        infeld = next(t for t in postdocs if "Infeld" in t["data"]["name"])
        assert "Warsaw" in infeld["data"]["current_position"]

    # -- Seminars ---------------------------------------------------------

    def test_seminars(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/works?type=seminars").json()
        assert len(items) == 3
        assert any("Electrodynamics" in (i["title"] or "") for i in items)

    # -- Committees -------------------------------------------------------

    def test_committees(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/committees").json()
        assert len(items) == 2
        assert any("League of Nations" in (i["data"].get("org") or "") for i in items)

    # -- Misc sections ----------------------------------------------------

    def test_editorial(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/editor").json()
        assert len(items) == 1
        assert items[0]["data"]["journal"] == "Annalen der Physik"

    def test_assocedit(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/assocedit").json()
        assert len(items) == 2
        assert any("Zeitschrift" in i["data"]["journal"] for i in items)

    def test_otheredit(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/otheredit").json()
        assert len(items) == 2
        assert any("Physical Review" in i["data"]["journal"] for i in items)

    def test_peerrev(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/peerrev").json()
        assert len(items) == 3

    def test_software(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/works?type=software").json()
        assert len(items) == 2
        titles = [i["title"] for i in items]
        assert "Unified Field Equation Solver" in titles

    def test_otherservice(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/otherservice").json()
        assert len(items) == 2
        assert any("colloquium" in i["data"]["description"] for i in items)

    def test_policypres(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/policypres").json()
        assert len(items) == 2
        assert any("Atomic energy" in i["data"]["title"] for i in items)

    def test_policycons(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/policycons").json()
        assert len(items) == 2
        assert any("Manhattan" in i["data"]["title"] for i in items)

    def test_otherpractice(self, client, db_session):
        """policyother in YAML maps to otherpractice in the DB."""
        self._import(db_session)
        items = client.get("/api/cv/otherpractice").json()
        assert len(items) == 2
        assert any("Russell-Einstein" in i["data"]["title"] for i in items)

    def test_departmental_orals(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/departmentalOrals").json()
        assert len(items) == 2
        names = [i["data"]["name"] for i in items]
        assert "Valentine Bargmann" in names

    def test_final_defense(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/finaldefense").json()
        assert len(items) == 3
        assert any(i["data"].get("ischair") for i in items)

    def test_schoolwide_orals(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/schoolwideOrals").json()
        assert len(items) == 2
        assert any("Wheeler" in i["data"]["name"] for i in items)

    def test_dissertation(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/works?type=dissertation").json()
        assert len(items) == 1
        d = items[0]
        assert "Molecular Dimensions" in d["title"]
        assert d["year"] == 1905

    def test_chaired_sessions(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/chairedsessions").json()
        assert len(items) == 1
        assert "Quantum" in items[0]["data"]["title"]

    # -- Press / Media ----------------------------------------------------

    def test_press(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/press").json()
        assert len(items) == 3  # 2 outlets for eclipse + 1 for Roosevelt letter
        outlets = {i["data"]["outlet"] for i in items}
        assert "The New York Times" in outlets

    # -- Consulting -------------------------------------------------------

    def test_consulting(self, client, db_session):
        self._import(db_session)
        items = client.get("/api/cv/consulting").json()
        assert len(items) == 1
        assert "Scientific Advisor" in items[0]["data"]["title"]


# ── YAML import for publications ────────────────────────────────────────

class TestImportRefs:
    """Import einstein_refs.yml and verify works via API."""

    def _import(self, db_session):
        import_refs_yaml(str(FIXTURES / "einstein_refs.yml"), db_session)

    def test_paper_count(self, client, db_session):
        self._import(db_session)
        papers = client.get("/api/works?type=papers").json()
        assert len(papers) == 10

    def test_chapters(self, client, db_session):
        self._import(db_session)
        chapters = client.get("/api/works?type=chapters").json()
        assert len(chapters) == 2
        assert any("Meaning of Relativity" in c["title"] for c in chapters)

    def test_letters(self, client, db_session):
        self._import(db_session)
        letters = client.get("/api/works?type=letters").json()
        assert len(letters) == 2

    def test_scimeetings(self, client, db_session):
        self._import(db_session)
        meetings = client.get("/api/works?type=scimeetings").json()
        assert len(meetings) == 3

    def test_select_flag(self, client, db_session):
        self._import(db_session)
        # select_flag is in data JSON, not a top-level filter on works endpoint
        all_works = client.get("/api/works?type=papers").json()
        selected = [w for w in all_works if (w.get("data") or {}).get("select_flag")]
        # Also check chapters/letters/etc
        for wt in ["chapters", "letters", "scimeetings"]:
            works = client.get(f"/api/works?type={wt}").json()
            selected.extend(w for w in works if (w.get("data") or {}).get("select_flag"))
        assert len(selected) == 6
        titles = {p["title"] for p in selected}
        assert any("Quantum-Mechanical" in t for t in titles)

    def test_authors_preserved(self, client, db_session):
        self._import(db_session)
        pubs = client.get("/api/works?type=papers").json()
        epr = next(p for p in pubs if "Quantum-Mechanical" in p["title"])
        names = [a["author_name"] for a in epr["authors"]]
        assert names == ["Einstein A", "Podolsky B", "Rosen N"]

    def test_doi_preserved(self, client, db_session):
        self._import(db_session)
        pubs = client.get("/api/works?type=papers").json()
        epr = next(p for p in pubs if "Quantum-Mechanical" in p["title"])
        assert epr["doi"] == "10.1103/PhysRev.47.777"

    def test_corr_flag(self, client, db_session):
        self._import(db_session)
        pubs = client.get("/api/works?type=papers").json()
        sr = next(p for p in pubs if "Elektrodynamik" in p["title"])
        # corr is now per-author: first author should have corresponding=True
        assert any(a["corresponding"] for a in sr["authors"])

    def test_keyword_search(self, client, db_session):
        self._import(db_session)
        results = client.get("/api/works?keyword=relativity").json()
        assert len(results) >= 1


# ── Full round-trip: import → export YAML → compare ────────────────────

class TestRoundTrip:
    """Import both files, export YAML, verify key data survives."""

    def _import_both(self, db_session):
        import_cv_yaml(str(FIXTURES / "einstein_cv.yml"), db_session)
        import_refs_yaml(str(FIXTURES / "einstein_refs.yml"), db_session)

    def test_export_contains_profile(self, client, db_session):
        self._import_both(db_session)
        resp = client.get("/api/export/yaml")
        assert resp.status_code == 200
        data = yaml.safe_load(resp.content)
        assert data["cv"]["name"] == "Albert Einstein"
        assert data["cv"]["email"] == "einstein@ias.edu"

    def test_export_contains_publications(self, client, db_session):
        self._import_both(db_session)
        data = yaml.safe_load(client.get("/api/export/yaml").content)
        assert len(data["refs"]["papers"]) == 10
        assert len(data["refs"]["chapters"]) == 2
        # EPR paper authors round-trip
        epr = next(p for p in data["refs"]["papers"]
                   if "Quantum-Mechanical" in p["title"])
        assert epr["authors"] == ["Einstein A", "Podolsky B", "Rosen N"]
        assert epr["doi"] == "10.1103/PhysRev.47.777"

    def test_export_contains_education(self, client, db_session):
        self._import_both(db_session)
        data = yaml.safe_load(client.get("/api/export/yaml").content)
        edu = data["cv"]["education"]
        assert len(edu) == 2
        assert any(e["degree"] == "PhD" for e in edu)

    def test_dashboard_after_import(self, client, db_session):
        self._import_both(db_session)
        d = client.get("/api/dashboard").json()
        assert d["profile_complete"] is True
        so = d["scholarly_output"]
        assert so["total_works"] == 17  # 10 + 2 + 2 + 3
        assert so["counts_by_type"]["papers"] == 10
        tm = d["teaching_mentorship"]
        assert tm["trainees_total"] == 5  # 2 advisees + 3 postdocs
        f = d["funding"]
        assert f["grants_total"] == 3


# ── UNC CV template preview with imported data ──────────────────────────

class TestUNCPreview:
    """Create a UNC-style template, import Einstein data, render preview."""

    UNC_SECTIONS = [
        "education", "experience", "awards", "memberships",
        "dissertation",
        "publications_papers", "patents",
        "publications_editorials",
        "publications_chapters", "publications_preprints",
        "publications_letters", "publications_scimeetings",
        "classes", "trainees_advisees", "trainees_postdocs",
        "grants",
        "panels_advisory", "panels_grantreview", "symposia",
        "chairedsessions",
        "consulting", "press",
        "otherpractice",
        "editorial", "peerrev", "software",
        "policypres", "policycons", "otherservice",
        "seminars", "committees",
        "departmentalOrals", "finaldefense", "schoolwideOrals",
    ]

    def _setup(self, client, db_session):
        from app.services.pdf import THEME_PRESETS
        import_cv_yaml(str(FIXTURES / "einstein_cv.yml"), db_session)
        import_refs_yaml(str(FIXTURES / "einstein_refs.yml"), db_session)
        resp = client.post("/api/templates", json={
            "name": "Einstein UNC CV",
            "description": "UNC format for Einstein",
            "style": THEME_PRESETS["unc"],
            "sort_direction": "desc",
            "sections": [
                {"section_key": k, "enabled": True, "section_order": i}
                for i, k in enumerate(self.UNC_SECTIONS)
            ],
        })
        assert resp.status_code == 200
        return resp.json()

    def test_preview_renders(self, client, db_session):
        tmpl = self._setup(client, db_session)
        resp = client.get(f"/api/templates/{tmpl['id']}/preview")
        assert resp.status_code == 200
        html = resp.text
        assert "Albert Einstein" in html

    def test_preview_contains_education(self, client, db_session):
        tmpl = self._setup(client, db_session)
        html = client.get(f"/api/templates/{tmpl['id']}/preview").text
        assert "University of Zurich" in html

    def test_preview_contains_publications(self, client, db_session):
        tmpl = self._setup(client, db_session)
        html = client.get(f"/api/templates/{tmpl['id']}/preview").text
        assert "Quantum-Mechanical" in html or "Physical Review" in html

    def test_preview_contains_awards(self, client, db_session):
        tmpl = self._setup(client, db_session)
        html = client.get(f"/api/templates/{tmpl['id']}/preview").text
        assert "Nobel Prize" in html

    def test_pdf_export(self, client, db_session):
        tmpl = self._setup(client, db_session)
        with patch("app.services.pdf.html_to_pdf", return_value=b"%PDF-einstein"):
            resp = client.post(f"/api/templates/{tmpl['id']}/export/pdf")
        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF")
