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
    assert d["profile_complete"] is False
    so = d["scholarly_output"]
    assert so["total_works"] == 0
    assert so["counts_by_type"] == {}
    assert so["works_by_year"] == []
    tm = d["teaching_mentorship"]
    assert tm["trainees_total"] == 0
    assert tm["trainee_breakdown"] == []
    f = d["funding"]
    assert f["grants_total"] == 0
    assert f["grants_active"] == 0
    s = d["service"]
    assert s["service_breakdown"] == []


def test_dashboard_with_data(client, sample_profile, sample_publication):
    # Add a trainee
    client.post("/api/cv", json={
        "section": "trainees_advisees",
        "data": {"name": "Student One", "trainee_type": "advisee", "years_start": "2020"},
    })
    # Add an active grant
    client.post("/api/cv", json={
        "section": "grants",
        "data": {"title": "Big Grant", "status": "active", "role": "PI", "years_start": "2023"},
    })
    # Add a committee
    client.post("/api/cv", json={
        "section": "committees",
        "data": {"committee": "Faculty Senate", "org": "University"},
    })

    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    d = resp.json()
    assert d["profile_complete"] is True

    so = d["scholarly_output"]
    assert so["total_works"] == 1
    assert so["counts_by_type"]["papers"] == 1

    tm = d["teaching_mentorship"]
    assert tm["trainees_total"] == 1
    assert tm["current_trainees"] == 1  # no years_end = current

    f = d["funding"]
    assert f["grants_total"] == 1
    assert f["grants_active"] == 1
    assert len(f["active_grants_detail"]) == 1
    assert f["active_grants_detail"][0]["role"] == "PI"

    s = d["service"]
    assert s["committees"] == 1
    assert any(b["label"] == "Committees" and b["count"] == 1 for b in s["service_breakdown"])
