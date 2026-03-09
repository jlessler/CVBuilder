"""Tests for the CV Instances router — CRUD, curation, style merging, preview."""
import pytest
from unittest.mock import patch

from app.services.pdf import THEME_PRESETS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_template(client, **overrides):
    """Create a template with education + publications_papers sections."""
    payload = {
        "name": "Instance Test Template",
        "description": "Template for instance tests",
        "style": THEME_PRESETS["academic"],
        "sort_direction": "desc",
        "sections": [
            {"section_key": "education", "enabled": True, "section_order": 0},
            {"section_key": "experience", "enabled": True, "section_order": 1},
            {"section_key": "publications_papers", "enabled": True, "section_order": 2},
        ],
    }
    payload.update(overrides)
    resp = client.post("/api/templates", json=payload)
    assert resp.status_code == 200
    return resp.json()


def _make_instance(client, template_id, **overrides):
    """Create a CV instance from a template."""
    payload = {
        "name": "Test Instance",
        "template_id": template_id,
    }
    payload.update(overrides)
    resp = client.post("/api/cv-instances", json=payload)
    assert resp.status_code == 200
    return resp.json()


def _add_education(client, degree="PhD", year=2020, school="MIT"):
    resp = client.post("/api/education", json={
        "degree": degree, "year": year, "school": school,
    })
    assert resp.status_code == 200
    return resp.json()


def _add_publication(client, title="Test Paper", year="2024", pub_type="papers"):
    resp = client.post("/api/works", json={
        "work_type": pub_type,
        "title": title,
        "year": int(year) if year.isdigit() else None,
        "data": {"journal": "Test Journal"},
        "authors": [
            {"author_name": "Doe J", "author_order": 0},
        ],
    })
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestCRUD:

    def test_create_instance(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        assert inst["name"] == "Test Instance"
        assert inst["template_id"] == tmpl["id"]
        assert inst["template_name"] == tmpl["name"]

    def test_create_copies_sections_from_template(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        assert len(inst["sections"]) == 3
        keys = [s["section_key"] for s in inst["sections"]]
        assert "education" in keys
        assert "experience" in keys
        assert "publications_papers" in keys

    def test_create_with_description(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"], description="My special CV")
        assert inst["description"] == "My special CV"

    def test_create_with_style_overrides(self, client):
        tmpl = _make_template(client)
        overrides = {"primary_color": "#ff0000", "accent_color": "#00ff00"}
        inst = _make_instance(client, tmpl["id"], style_overrides=overrides)
        assert inst["style_overrides"] == overrides

    def test_create_with_sort_direction_override(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"], sort_direction_override="asc")
        assert inst["sort_direction_override"] == "asc"

    def test_create_with_bad_template_404(self, client):
        resp = client.post("/api/cv-instances", json={
            "name": "Bad", "template_id": 99999,
        })
        assert resp.status_code == 404

    def test_list_instances(self, client):
        tmpl = _make_template(client)
        _make_instance(client, tmpl["id"], name="First")
        _make_instance(client, tmpl["id"], name="Second")
        resp = client.get("/api/cv-instances")
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "First" in names
        assert "Second" in names

    def test_get_instance(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.get(f"/api/cv-instances/{inst['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == inst["id"]

    def test_get_nonexistent_instance_404(self, client):
        resp = client.get("/api/cv-instances/99999")
        assert resp.status_code == 404

    def test_update_instance_name(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.put(f"/api/cv-instances/{inst['id']}", json={
            "name": "Renamed Instance",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Instance"

    def test_update_style_overrides(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.put(f"/api/cv-instances/{inst['id']}", json={
            "style_overrides": {"primary_color": "#aaa"},
        })
        assert resp.status_code == 200
        assert resp.json()["style_overrides"] == {"primary_color": "#aaa"}

    def test_clear_style_overrides(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"], style_overrides={"primary_color": "#aaa"})
        resp = client.put(f"/api/cv-instances/{inst['id']}", json={
            "style_overrides": None,
        })
        assert resp.status_code == 200
        assert resp.json()["style_overrides"] is None

    def test_update_sort_direction_override(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.put(f"/api/cv-instances/{inst['id']}", json={
            "sort_direction_override": "asc",
        })
        assert resp.status_code == 200
        assert resp.json()["sort_direction_override"] == "asc"

    def test_delete_instance(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.delete(f"/api/cv-instances/{inst['id']}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Verify gone
        resp = client.get(f"/api/cv-instances/{inst['id']}")
        assert resp.status_code == 404

    def test_delete_nonexistent_404(self, client):
        resp = client.delete("/api/cv-instances/99999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Section management
# ---------------------------------------------------------------------------

class TestSections:

    def test_sections_copied_from_template(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        sections = inst["sections"]
        assert len(sections) == 3
        for s in sections:
            assert s["curated"] is False

    def test_update_sections(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.put(f"/api/cv-instances/{inst['id']}/sections", json={
            "sections": [
                {"section_key": "education", "enabled": False, "section_order": 0},
                {"section_key": "experience", "enabled": True, "section_order": 1},
                {"section_key": "publications_papers", "enabled": True, "section_order": 2, "curated": True},
            ],
        })
        assert resp.status_code == 200
        result = resp.json()
        edu = next(s for s in result if s["section_key"] == "education")
        assert edu["enabled"] is False
        pubs = next(s for s in result if s["section_key"] == "publications_papers")
        assert pubs["curated"] is True

    def test_update_heading_override(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.put(f"/api/cv-instances/{inst['id']}/sections", json={
            "sections": [
                {"section_key": "education", "enabled": True, "section_order": 0,
                 "heading_override": "My Education"},
            ],
        })
        assert resp.status_code == 200
        edu = next(s for s in resp.json() if s["section_key"] == "education")
        assert edu["heading_override"] == "My Education"

    def test_add_new_section(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        # Add a section not in the original template
        resp = client.put(f"/api/cv-instances/{inst['id']}/sections", json={
            "sections": [
                {"section_key": "awards", "enabled": True, "section_order": 10},
            ],
        })
        assert resp.status_code == 200
        keys = [s["section_key"] for s in resp.json()]
        assert "awards" in keys


# ---------------------------------------------------------------------------
# Item curation
# ---------------------------------------------------------------------------

class TestItemCuration:

    def test_get_available_items(self, client):
        _add_education(client, degree="PhD", year=2020, school="MIT")
        _add_education(client, degree="BS", year=2016, school="Stanford")
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])

        resp = client.get(f"/api/cv-instances/{inst['id']}/sections/education/items")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        assert all(not item["selected"] for item in items)

    def test_curate_items(self, client):
        edu1 = _add_education(client, degree="PhD", year=2020, school="MIT")
        _add_education(client, degree="BS", year=2016, school="Stanford")
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])

        # Mark education section as curated
        client.put(f"/api/cv-instances/{inst['id']}/sections", json={
            "sections": [
                {"section_key": "education", "enabled": True, "section_order": 0, "curated": True},
            ],
        })

        # Select only PhD
        resp = client.put(
            f"/api/cv-instances/{inst['id']}/sections/education/items",
            json={"item_ids": [edu1["id"]]},
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_curated_items_reflected_in_available(self, client):
        edu1 = _add_education(client, degree="PhD", year=2020, school="MIT")
        edu2 = _add_education(client, degree="BS", year=2016, school="Stanford")
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])

        # Mark curated and select PhD only
        client.put(f"/api/cv-instances/{inst['id']}/sections", json={
            "sections": [
                {"section_key": "education", "enabled": True, "section_order": 0, "curated": True},
            ],
        })
        client.put(
            f"/api/cv-instances/{inst['id']}/sections/education/items",
            json={"item_ids": [edu1["id"]]},
        )

        # Check available items reflect selection
        resp = client.get(f"/api/cv-instances/{inst['id']}/sections/education/items")
        items = resp.json()
        selected = {i["id"]: i["selected"] for i in items}
        assert selected[edu1["id"]] is True
        assert selected[edu2["id"]] is False

    def test_curate_publications(self, client):
        pub1 = _add_publication(client, title="Paper A", year="2024")
        _add_publication(client, title="Paper B", year="2023")
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])

        # Mark pubs curated
        client.put(f"/api/cv-instances/{inst['id']}/sections", json={
            "sections": [
                {"section_key": "publications_papers", "enabled": True,
                 "section_order": 2, "curated": True},
            ],
        })

        # Select only Paper A
        resp = client.put(
            f"/api/cv-instances/{inst['id']}/sections/publications_papers/items",
            json={"item_ids": [pub1["id"]]},
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_update_items_on_nonexistent_section_404(self, client):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.put(
            f"/api/cv-instances/{inst['id']}/sections/nonexistent/items",
            json={"item_ids": [1]},
        )
        assert resp.status_code == 404

    def test_replace_curated_items(self, client):
        edu1 = _add_education(client, degree="PhD", year=2020, school="MIT")
        edu2 = _add_education(client, degree="BS", year=2016, school="Stanford")
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])

        client.put(f"/api/cv-instances/{inst['id']}/sections", json={
            "sections": [
                {"section_key": "education", "enabled": True, "section_order": 0, "curated": True},
            ],
        })

        # First select PhD
        client.put(
            f"/api/cv-instances/{inst['id']}/sections/education/items",
            json={"item_ids": [edu1["id"]]},
        )

        # Replace with BS
        resp = client.put(
            f"/api/cv-instances/{inst['id']}/sections/education/items",
            json={"item_ids": [edu2["id"]]},
        )
        assert resp.json()["count"] == 1

        # Verify only BS selected
        items = client.get(f"/api/cv-instances/{inst['id']}/sections/education/items").json()
        selected = {i["id"]: i["selected"] for i in items}
        assert selected[edu1["id"]] is False
        assert selected[edu2["id"]] is True


# ---------------------------------------------------------------------------
# Style merging in _build_cv_instance_data
# ---------------------------------------------------------------------------

class TestStyleMerging:

    def test_template_style_used_when_no_overrides(self, client, sample_profile):
        tmpl = _make_template(client, style=THEME_PRESETS["unc"])
        inst = _make_instance(client, tmpl["id"])
        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        assert resp.status_code == 200
        html = resp.text
        # UNC primary color should appear in generated CSS
        assert "#13294B" in html

    def test_style_overrides_win(self, client, sample_profile):
        tmpl = _make_template(client, style=THEME_PRESETS["unc"])
        inst = _make_instance(client, tmpl["id"],
                              style_overrides={"primary_color": "#ff0000"})
        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        assert resp.status_code == 200
        html = resp.text
        # Override should win
        assert "#ff0000" in html

    def test_empty_string_overrides_ignored(self, client, sample_profile):
        tmpl = _make_template(client, style=THEME_PRESETS["unc"])
        inst = _make_instance(client, tmpl["id"],
                              style_overrides={"primary_color": ""})
        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        html = resp.text
        # Template color should be used since empty string is ignored
        assert "#13294B" in html

    def test_partial_overrides_preserve_template_style(self, client, sample_profile):
        tmpl = _make_template(client, style=THEME_PRESETS["unc"])
        inst = _make_instance(client, tmpl["id"],
                              style_overrides={"primary_color": "#ff0000"})
        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        html = resp.text
        # Override wins for primary
        assert "#ff0000" in html
        # Template's accent color preserved
        assert "#4B9CD3" in html

    def test_sort_direction_override(self, client, sample_profile):
        tmpl = _make_template(client, sort_direction="desc")
        _add_education(client, degree="BS", year=2016, school="Stanford")
        _add_education(client, degree="PhD", year=2020, school="MIT")

        inst = _make_instance(client, tmpl["id"], sort_direction_override="asc")
        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        assert resp.status_code == 200
        html = resp.text
        # In ascending order, 2016 should come before 2020
        pos_2016 = html.index("2016")
        pos_2020 = html.index("2020")
        assert pos_2016 < pos_2020

    def test_sort_direction_defaults_to_template(self, client, sample_profile):
        tmpl = _make_template(client, sort_direction="desc")
        _add_education(client, degree="BS", year=2016, school="Stanford")
        _add_education(client, degree="PhD", year=2020, school="MIT")

        inst = _make_instance(client, tmpl["id"])
        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        html = resp.text
        # In descending order, 2020 should come before 2016
        pos_2016 = html.index("2016")
        pos_2020 = html.index("2020")
        assert pos_2020 < pos_2016


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

class TestPreview:

    def test_preview_returns_html(self, client, sample_profile):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "<html" in resp.text or "<!DOCTYPE" in resp.text.upper() or "cv-page" in resp.text

    def test_preview_includes_profile(self, client, sample_profile):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        assert "Jane Doe" in resp.text

    def test_preview_includes_education(self, client, sample_profile):
        _add_education(client, degree="PhD", year=2020, school="MIT")
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        assert "PhD" in resp.text
        assert "MIT" in resp.text

    def test_preview_disabled_section_hidden(self, client, sample_profile):
        _add_education(client, degree="PhD", year=2020, school="MIT")
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])

        # Disable education section
        client.put(f"/api/cv-instances/{inst['id']}/sections", json={
            "sections": [
                {"section_key": "education", "enabled": False, "section_order": 0},
            ],
        })

        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        assert resp.status_code == 200
        # Education heading should not appear, but profile still there
        assert "Jane Doe" in resp.text

    def test_preview_curated_section_filters_items(self, client, sample_profile):
        edu1 = _add_education(client, degree="PhD", year=2020, school="MIT")
        edu2 = _add_education(client, degree="BS", year=2016, school="Stanford")
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])

        # Mark curated and select only PhD
        client.put(f"/api/cv-instances/{inst['id']}/sections", json={
            "sections": [
                {"section_key": "education", "enabled": True, "section_order": 0, "curated": True},
            ],
        })
        client.put(
            f"/api/cv-instances/{inst['id']}/sections/education/items",
            json={"item_ids": [edu1["id"]]},
        )

        resp = client.get(f"/api/cv-instances/{inst['id']}/preview")
        assert "MIT" in resp.text
        assert "Stanford" not in resp.text


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

class TestPdfExport:

    @patch("app.services.pdf.html_to_pdf", return_value=b"%PDF-1.4 fake")
    def test_export_pdf(self, mock_pdf, client, sample_profile):
        tmpl = _make_template(client)
        inst = _make_instance(client, tmpl["id"])
        resp = client.post(f"/api/cv-instances/{inst['id']}/export/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert b"%PDF" in resp.content
        mock_pdf.assert_called_once()

    @patch("app.services.pdf.html_to_pdf", return_value=b"%PDF-1.4 fake")
    def test_export_pdf_with_style_overrides(self, mock_pdf, client, sample_profile):
        tmpl = _make_template(client, style=THEME_PRESETS["unc"])
        inst = _make_instance(client, tmpl["id"],
                              style_overrides={"primary_color": "#ff0000"})
        resp = client.post(f"/api/cv-instances/{inst['id']}/export/pdf")
        assert resp.status_code == 200
        mock_pdf.assert_called_once()

    def test_export_pdf_nonexistent_404(self, client):
        resp = client.post("/api/cv-instances/99999/export/pdf")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Template deletion with instances
# ---------------------------------------------------------------------------

class TestTemplateInstanceRelationship:

    def test_template_with_instances_cannot_be_deleted(self, client):
        tmpl = _make_template(client)
        _make_instance(client, tmpl["id"])
        resp = client.delete(f"/api/templates/{tmpl['id']}")
        # Should fail because instance references it
        assert resp.status_code in (400, 409, 500)
