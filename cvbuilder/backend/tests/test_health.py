"""Tests for /api/health and /api/dashboard endpoints."""


def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_dashboard_empty_db(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    d = resp.json()
    assert d["total_publications"] == 0
    assert d["papers"] == 0
    assert d["trainees"] == 0
    assert d["grants"] == 0
    assert d["profile_complete"] is False
    assert d["trainee_breakdown"] == []
    assert d["active_grant_breakdown"] == []


def test_dashboard_with_data(client, sample_profile, sample_publication):
    # Add a trainee
    client.post("/api/trainees", json={
        "name": "Student One", "trainee_type": "advisee",
        "years_start": "2020",
    })
    # Add an active grant
    client.post("/api/grants", json={
        "title": "Big Grant", "status": "active", "role": "PI",
        "years_start": "2023",
    })

    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    d = resp.json()
    assert d["total_publications"] == 1
    assert d["papers"] == 1
    assert d["trainees"] == 1
    assert d["grants"] == 1
    assert d["active_grants"] == 1
    assert d["profile_complete"] is True
