"""Tests for YAML export and import endpoints."""
import yaml


def test_export_yaml_empty_db(client):
    resp = client.get("/api/export/yaml")
    assert resp.status_code == 200
    assert "yaml" in resp.headers["content-type"]
    data = yaml.safe_load(resp.content)
    assert "cv" in data
    assert "refs" in data


def test_export_yaml_with_data(client, sample_profile, sample_publication):
    resp = client.get("/api/export/yaml")
    assert resp.status_code == 200
    data = yaml.safe_load(resp.content)
    assert data["cv"]["name"] == "Jane Doe"
    assert len(data["refs"]["papers"]) >= 1


# ── YAML import ─────────────────────────────────────────────────────────

def test_import_yaml_no_files(client):
    resp = client.post("/api/export/yaml/import")
    assert resp.status_code == 400
    assert "No files" in resp.json()["detail"]


def test_import_yaml_cv_file(client):
    cv_yaml = yaml.dump({
        "name": "Imported User",
        "email": "imported@test.com",
        "education": [
            {"degree": "PhD", "year": 2020, "subject": "Epi", "school": "UNC"},
        ],
    })
    resp = client.post(
        "/api/export/yaml/import",
        files={"cv_file": ("CV.yml", cv_yaml.encode(), "application/x-yaml")},
    )
    assert resp.status_code == 200
    assert "CV.yml imported" in resp.json()["imported"]

    profile = client.get("/api/profile").json()
    assert profile["name"] == "Imported User"


def test_import_yaml_refs_file(client):
    refs_yaml = yaml.dump({
        "myname": "Test User",
        "papers": [
            {
                "title": "Imported Paper",
                "year": "2024",
                "journal": "Science",
                "authors": ["Author A", "Author B"],
            },
        ],
    })
    resp = client.post(
        "/api/export/yaml/import",
        files={"refs_file": ("refs.yml", refs_yaml.encode(), "application/x-yaml")},
    )
    assert resp.status_code == 200
    assert "refs.yml imported" in resp.json()["imported"]

    works = client.get("/api/works?type=papers").json()
    assert any(w["title"] == "Imported Paper" for w in works)
