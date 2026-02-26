"""Tests for YAML export endpoint."""
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
