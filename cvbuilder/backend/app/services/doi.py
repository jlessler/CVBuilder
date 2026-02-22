"""DOI lookup service using the Crossref API."""
from __future__ import annotations

from typing import Optional


def _safe_get(data: dict, key: str, default=""):
    """Safely extract a scalar value; if list, return first element."""
    if not isinstance(data, dict):
        return default
    value = data.get(key, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value if value is not None else default


def _safe_nested_list(data: dict, keys: list[str], default=None):
    """Walk nested keys and return the first element of the deepest list."""
    try:
        for key in keys:
            data = data[key]
        return data[0][0] if data and isinstance(data[0], list) else default
    except (KeyError, IndexError, TypeError):
        return default


def lookup_doi(doi: str) -> dict:
    """
    Fetch metadata for a DOI via Crossref.

    Returns a dict with keys:
        title, year, journal, volume, issue, pages, authors (list of str), doi
    Raises ValueError on not-found / API errors.
    """
    try:
        from crossref.restful import Works  # type: ignore
    except ImportError:
        raise RuntimeError("crossref-commons is not installed. Run: pip install crossref-commons")

    works = Works()
    ref = works.doi(doi)
    if not ref:
        raise ValueError(f"DOI not found: {doi}")

    year = (
        _safe_nested_list(ref, ["published-print", "date-parts"], None)
        or _safe_nested_list(ref, ["published-online", "date-parts"], None)
    )

    authors = [
        f"{a.get('family', '')} {a.get('given', '')}".strip()
        for a in ref.get("author", [])
    ]

    return {
        "title": _safe_get(ref, "title"),
        "year": str(year) if year else None,
        "journal": _safe_get(ref, "container-title"),
        "volume": _safe_get(ref, "volume"),
        "issue": _safe_get(ref, "issue"),
        "pages": _safe_get(ref, "page"),
        "authors": authors,
        "doi": doi,
    }
