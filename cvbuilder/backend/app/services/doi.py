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


def lookup_doi_raw(doi: str) -> dict:
    """
    Fetch the raw Crossref message dict for a DOI.

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

    return response.json().get("message", {})


def _parse_crossref_message(ref: dict, doi: str) -> dict:
    """Parse a raw Crossref message dict into our standard metadata dict."""
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


def lookup_doi(doi: str) -> dict:
    """
    Fetch metadata for a DOI via the Crossref REST API.

    Returns a dict with keys:
        title, year, journal, volume, issue, pages, authors (list of str), doi
    Raises ValueError on not-found, RuntimeError on other errors.
    """
    ref = lookup_doi_raw(doi)
    return _parse_crossref_message(ref, doi)


def search_doi_by_metadata(
    title: str,
    first_author: str | None = None,
    year: int | str | None = None,
    journal: str | None = None,
    volume: str | None = None,
    issue: str | None = None,
    pages: str | None = None,
) -> str | None:
    """
    Search Crossref for a DOI matching the given metadata.

    Returns a DOI string if a confident match is found, else None.
    Requires title similarity >= 0.80 plus >= 2 corroborating signals,
    or title similarity >= 0.95 standalone.
    """
    from app.services.fetch_pubs import _title_similarity

    # Build query — Crossref bibliographic search
    query_parts = [title]
    if first_author:
        query_parts.append(first_author)
    query = " ".join(query_parts)

    params = {"query.bibliographic": query, "rows": "5"}
    if year:
        params["filter"] = f"from-pub-date:{year},until-pub-date:{year}"

    try:
        response = httpx.get(
            "https://api.crossref.org/works",
            params=params,
            timeout=15,
            headers={"User-Agent": "CVBuilder/1.0"},
        )
        if response.status_code != 200:
            return None
    except httpx.RequestError:
        return None

    items = response.json().get("message", {}).get("items", [])
    if not items:
        return None

    str_year = str(year) if year else None

    for item in items:
        # Title similarity check
        cr_title = item.get("title", [""])[0] if isinstance(item.get("title"), list) else item.get("title", "")
        if not cr_title:
            continue
        sim = _title_similarity(title, cr_title)
        if sim < 0.80:
            continue

        # Count corroborating signals
        signals = 0

        # Year
        cr_year = _year_from_date_parts(item)
        if str_year and cr_year and str_year == cr_year:
            signals += 1

        # First author last name
        if first_author:
            cr_authors = item.get("author", [])
            if cr_authors:
                cr_family = cr_authors[0].get("family", "").lower()
                if cr_family and cr_family == first_author.lower():
                    signals += 1

        # Journal
        if journal:
            cr_journal = item.get("container-title", [""])[0] if isinstance(item.get("container-title"), list) else item.get("container-title", "")
            if cr_journal and cr_journal.lower().strip() == journal.lower().strip():
                signals += 1

        # Volume
        if volume:
            cr_vol = str(item.get("volume", "")).strip()
            if cr_vol and cr_vol == str(volume).strip():
                signals += 1

        # Issue
        if issue:
            cr_issue = str(item.get("issue", "")).strip()
            if cr_issue and cr_issue == str(issue).strip():
                signals += 1

        # Pages
        if pages:
            cr_pages = str(item.get("page", "")).strip()
            if cr_pages and cr_pages == str(pages).strip():
                signals += 1

        # Decision
        if sim >= 0.95:
            return item.get("DOI")
        if sim >= 0.80 and signals >= 2:
            return item.get("DOI")

    return None


def _strip_html(val: str) -> str:
    """Remove HTML tags from a string."""
    import re
    return re.sub(r"<[^>]+>", "", val)


def _normalize(val: str | None) -> str:
    """Lowercase, strip HTML tags, normalize unicode, and strip whitespace."""
    import unicodedata
    s = _strip_html((val or "")).strip()
    s = unicodedata.normalize("NFKC", s)
    return s.lower()


def _name_parts(name: str) -> list[str]:
    """Split a name into parts, stripping dots: 'K. E.' -> ['K', 'E'], 'D.A.' -> ['D', 'A']."""
    return [p for p in name.replace(".", " ").split() if p]


def _part_is_fuller(current_part: str, proposed_part: str) -> bool:
    """Check if a single name part is fuller: 'K' -> 'Kimberly' is True."""
    c = current_part.strip().rstrip(".")
    p = proposed_part.strip().rstrip(".")
    if not c or not p:
        return False
    if c.lower() == p.lower():
        return False
    # Current is an initial (1-2 chars) and proposed starts with same letter
    if len(c) <= 2 and p.lower().startswith(c[0].lower()) and len(p) > len(c):
        return True
    # Proposed is strictly longer and starts with current
    if len(p) > len(c) and p.lower().startswith(c.lower()):
        return True
    return False


def _strip_accents(s: str) -> str:
    """Remove diacritical marks: 'Martínez' -> 'Martinez'."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _has_better_accents(current: str, proposed: str) -> bool:
    """Check if proposed has proper accents that current is missing.
    'Martinez' vs 'Martínez' -> True.
    """
    if current == proposed:
        return False
    return _strip_accents(current).lower() == _strip_accents(proposed).lower() and current != proposed


def _is_fuller_name(current: str, proposed: str) -> bool:
    """
    Check if proposed name is a fuller version of current name.
    Compares part by part: 'K. E.' vs 'Kimberly E.' -> True (K -> Kimberly).
    'D. A.' vs 'D.A.' -> False (same parts).
    Also detects accent improvements: 'Martinez' -> 'Martínez'.
    """
    c_parts = _name_parts(current)
    p_parts = _name_parts(proposed)
    if not c_parts or not p_parts:
        return False
    # Check accent improvements on any part
    for cp, pp in zip(c_parts, p_parts):
        if _has_better_accents(cp, pp):
            return True
    # Check if any part is fuller
    for cp, pp in zip(c_parts, p_parts):
        if _part_is_fuller(cp, pp):
            return True
    return False


def compute_work_diffs(work, raw_crossref: dict) -> dict:
    """
    Compare a Work ORM object against raw Crossref data.

    Returns dict with keys: field_diffs, author_diffs, proposed_authors,
    additional_authors.

    Top-level Work fields: title, year, doi.
    Data-blob fields: journal, volume, issue, pages.
    """
    parsed = _parse_crossref_message(raw_crossref, raw_crossref.get("DOI", ""))
    data = work.data or {}

    # --- Field diffs ---
    field_diffs = []
    # Top-level fields
    for field in ("title", "year", "doi"):
        current_val = getattr(work, field, None)
        proposed_val = _strip_html(str(parsed.get(field) or "")) or None
        if proposed_val and _normalize(proposed_val) != _normalize(str(current_val or "")):
            field_diffs.append({
                "field": field,
                "current": str(current_val) if current_val is not None else None,
                "proposed": proposed_val,
            })
    # Data-blob fields
    for field in ("journal", "volume", "issue", "pages"):
        current_val = data.get(field)
        proposed_val = _strip_html(str(parsed.get(field) or "")) or None
        if proposed_val and _normalize(proposed_val) != _normalize(str(current_val or "")):
            field_diffs.append({
                "field": field,
                "current": str(current_val) if current_val is not None else None,
                "proposed": proposed_val,
            })

    # --- Author diffs ---
    cr_authors = raw_crossref.get("author", [])
    work_authors = sorted(work.authors, key=lambda a: a.author_order)
    author_diffs = []
    proposed_authors = []
    additional_authors = []

    if len(work_authors) == 0 and cr_authors:
        # Work has no authors — propose entire Crossref list
        for i, a in enumerate(cr_authors):
            proposed_authors.append({
                "author_name": f"{a.get('family', '')} {a.get('given', '')}".strip(),
                "author_order": i,
                "given_name": a.get("given"),
                "family_name": a.get("family"),
                "suffix": a.get("suffix"),
            })
    else:
        # Compare matched authors by position
        for i, wa in enumerate(work_authors):
            if i >= len(cr_authors):
                break
            ca = cr_authors[i]
            cr_given = ca.get("given", "")
            cr_family = ca.get("family", "")

            # Use structured names if available, else parse display name
            w_given = wa.given_name or ""
            w_family = wa.family_name or ""
            if not w_family and wa.author_name:
                parts = wa.author_name.split()
                if len(parts) >= 2:
                    w_family = parts[0]
                    w_given = " ".join(parts[1:])
                elif parts:
                    w_family = parts[0]

            # Check if Crossref has a fuller name
            given_fuller = _is_fuller_name(w_given, cr_given)
            family_fuller = _is_fuller_name(w_family, cr_family)

            if given_fuller or family_fuller:
                new_given = cr_given if given_fuller else w_given
                new_family = cr_family if family_fuller else w_family
                proposed_name = f"{new_family} {new_given}".strip()
                author_diffs.append({
                    "author_order": wa.author_order,
                    "current_name": wa.author_name,
                    "proposed_name": proposed_name,
                })

        # Crossref has more authors than work
        if len(cr_authors) > len(work_authors) and len(work_authors) > 0:
            for i in range(len(work_authors), len(cr_authors)):
                a = cr_authors[i]
                additional_authors.append({
                    "author_name": f"{a.get('family', '')} {a.get('given', '')}".strip(),
                    "author_order": i,
                    "given_name": a.get("given"),
                    "family_name": a.get("family"),
                    "suffix": a.get("suffix"),
                })

    return {
        "field_diffs": field_diffs,
        "author_diffs": author_diffs,
        "proposed_authors": proposed_authors,
        "additional_authors": additional_authors,
    }
