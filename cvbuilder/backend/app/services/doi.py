"""DOI lookup service using the Crossref REST API."""
from __future__ import annotations

import httpx


def _scalar(value, default=""):
    """Return first element if list, otherwise the value itself."""
    if isinstance(value, list):
        return value[0] if value else default
    return value if value is not None else default


def _year_from_date_parts(ref: dict) -> str | None:
    """Extract the year from published-print or published-online date-parts."""
    for key in ("published-print", "published-online", "issued"):
        parts = ref.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            return str(parts[0][0])
    return None


def lookup_doi(doi: str) -> dict:
    """
    Fetch metadata for a DOI via the Crossref REST API.

    Returns a dict with keys:
        title, year, journal, volume, issue, pages, authors (list of str), doi
    Raises ValueError on not-found, RuntimeError on other errors.
    """
    url = f"https://api.crossref.org/works/{doi.strip()}"
    try:
        response = httpx.get(url, timeout=15, headers={"User-Agent": "CVBuilder/1.0"})
    except httpx.RequestError as e:
        raise RuntimeError(f"Network error contacting Crossref: {e}")

    if response.status_code == 404:
        raise ValueError(f"DOI not found: {doi}")
    if response.status_code != 200:
        raise RuntimeError(f"Crossref returned status {response.status_code}")

    ref = response.json().get("message", {})

    authors = [
        f"{a.get('family', '')} {a.get('given', '')}".strip()
        for a in ref.get("author", [])
        if a.get("family")
    ]

    return {
        "title": _scalar(ref.get("title")),
        "year": _year_from_date_parts(ref),
        "journal": _scalar(ref.get("container-title")),
        "volume": _scalar(ref.get("volume")),
        "issue": _scalar(ref.get("issue")),
        "pages": _scalar(ref.get("page")),
        "authors": authors,
        "doi": doi.strip(),
    }
