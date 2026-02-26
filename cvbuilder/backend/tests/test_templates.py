"""Tests for CV Template CRUD, preview, and PDF export."""
from unittest.mock import patch


def test_list_templates_empty(client):
    items = client.get("/api/templates").json()
    assert isinstance(items, list)


def test_create_template(client, sample_template):
    assert sample_template["name"] == "Test Template"
    assert len(sample_template["sections"]) == 2


def test_get_template_by_id(client, sample_template):
    tid = sample_template["id"]
    resp = client.get(f"/api/templates/{tid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Template"


def test_get_template_404(client):
    assert client.get("/api/templates/9999").status_code == 404


def test_update_template_replaces_sections(client, sample_template):
    tid = sample_template["id"]
    resp = client.put(f"/api/templates/{tid}", json={
        "name": "Updated",
        "description": "Updated desc",
        "theme_css": "minimal",
        "sort_direction": "asc",
        "sections": [
            {"section_key": "grants", "enabled": True, "section_order": 0},
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Updated"
    assert len(body["sections"]) == 1
    assert body["sections"][0]["section_key"] == "grants"


def test_delete_template(client, sample_template):
    tid = sample_template["id"]
    resp = client.delete(f"/api/templates/{tid}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert client.get(f"/api/templates/{tid}").status_code == 404


def test_delete_template_404(client):
    assert client.delete("/api/templates/9999").status_code == 404


def test_preview_returns_html(client, sample_profile, sample_template):
    tid = sample_template["id"]
    resp = client.get(f"/api/templates/{tid}/preview")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert sample_profile["name"] in resp.text


def test_pdf_export_mocked(client, sample_profile, sample_template):
    tid = sample_template["id"]
    with patch("app.services.pdf.html_to_pdf", return_value=b"%PDF-fake"):
        resp = client.post(f"/api/templates/{tid}/export/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
