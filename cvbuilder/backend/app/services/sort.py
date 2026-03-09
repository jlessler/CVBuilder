import re
from typing import Any


def _parse_year(v: Any) -> int:
    """Extract the first 4-digit year from a string/int, or return 0."""
    if v is None:
        return 0
    m = re.search(r'\d{4}', str(v))
    return int(m.group()) if m else 0


def _misc_date_key(e) -> int:
    """Extract a sortable year from a MiscSection's data JSON blob."""
    data = getattr(e, "data", None) or {}
    for field in ("date", "year", "years", "dates", "term"):
        val = data.get(field)
        if val:
            parsed = _parse_year(val)
            if parsed:
                return parsed
    return 0


# Maps SQLAlchemy model class name → callable that returns a sortable integer
SECTION_SORT_KEY = {
    "Education":   lambda e: e.year or 0,
    "Experience":  lambda e: _parse_year(e.years_start),
    "Consulting":  lambda e: _parse_year(e.years),
    "Membership":  lambda e: _parse_year(e.years),
    "Panel":       lambda e: _parse_year(e.date),
    "Symposium":   lambda e: _parse_year(e.date),
    "Class":       lambda e: e.year or 0,
    "Grant":       lambda e: _parse_year(e.years_start),
    "Award":       lambda e: _parse_year(e.year or e.date),
    "Press":       lambda e: _parse_year(e.date),
    "Trainee":     lambda e: _parse_year(e.years_start),
    "Committee":   lambda e: _parse_year(e.dates),
    "MiscSection": lambda e: _misc_date_key(e),
    "Work":        lambda w: (w.year or 0, w.month or 0, w.day or 0),
    "CVItem":      lambda e: e.sort_date or 0,
}


# Maps CVItem section → data field(s) used to compute sort_date
SORT_DATE_FIELD_MAP: dict[str, list[str]] = {
    "education":          ["year"],
    "experience":         ["years_start"],
    "consulting":         ["years"],
    "memberships":        ["years"],
    "panels_advisory":    ["date"],
    "panels_grantreview": ["date"],
    "symposia":           ["date"],
    "classes":            ["year"],
    "grants":             ["years_start"],
    "awards":             ["year", "date"],
    "press":              ["date"],
    "trainees_advisees":  ["years_start"],
    "trainees_postdocs":  ["years_start"],
    "committees":         ["dates"],
    "chairedsessions":    ["date"],
}


def compute_sort_date(section: str, data: dict) -> int | None:
    """Extract a sortable year integer from a CVItem's data dict."""
    fields = SORT_DATE_FIELD_MAP.get(section)
    if fields:
        for field in fields:
            val = data.get(field)
            if val:
                parsed = _parse_year(val)
                if parsed:
                    return parsed
        return None
    # Fallback: scan common date-like fields (for misc sections)
    return _misc_date_key_from_dict(data) or None


def _misc_date_key_from_dict(data: dict) -> int:
    """Extract a sortable year from a dict by scanning common date fields."""
    for field in ("date", "year", "years", "dates", "term"):
        val = data.get(field)
        if val:
            parsed = _parse_year(val)
            if parsed:
                return parsed
    return 0


def sort_items(items: list, model_class, reverse: bool = True) -> list:
    """Return items sorted by their primary date field (default: newest first)."""
    key_fn = SECTION_SORT_KEY.get(model_class.__name__, lambda e: e.id)
    return sorted(items, key=key_fn, reverse=reverse)
