"""Tests for Profile GET/PUT + address handling."""


def test_get_profile_empty(client):
    resp = client.get("/api/profile")
    assert resp.status_code == 404


def test_create_profile_via_put(client):
    resp = client.put("/api/profile", json={
        "name": "Alice",
        "email": "alice@example.com",
        "addresses": [
            {"type": "work", "line_order": 0, "text": "Work Address"},
            {"type": "home", "line_order": 0, "text": "Home Address"},
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Alice"
    assert len(body["addresses"]) == 2


def test_update_existing_profile(client, sample_profile):
    resp = client.put("/api/profile", json={
        "name": "Jane Updated",
        "email": "new@example.com",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Jane Updated"
    assert body["id"] == sample_profile["id"]


def test_address_replacement(client, sample_profile):
    """Passing addresses replaces all existing addresses."""
    resp = client.put("/api/profile", json={
        "name": "Jane Doe",
        "addresses": [
            {"type": "home", "line_order": 0, "text": "New Home"},
        ],
    })
    assert resp.status_code == 200
    addrs = resp.json()["addresses"]
    assert len(addrs) == 1
    assert addrs[0]["text"] == "New Home"


def test_omitting_addresses_preserves_them(client, sample_profile):
    """Omitting the addresses field entirely should not wipe them."""
    resp = client.put("/api/profile", json={"name": "Jane Doe"})
    assert resp.status_code == 200
    assert len(resp.json()["addresses"]) == len(sample_profile["addresses"])
