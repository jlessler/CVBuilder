import re
from typing import Any


def _parse_year(v: Any) -> int:
    """Extract the first 4-digit year from a string/int, or return 0."""
    if v is None:
        return 0
    m = re.search(r'\d{4}', str(v))
    return int(m.group()) if m else 0


# Maps SQLAlchemy model class name → callable that returns a sortable integer
SECTION_SORT_KEY = {
    "Publication": lambda p: _parse_year(p.year),
    "Education":   lambda e: e.year or 0,
    "Experience":  lambda e: _parse_year(e.years_start),
    "Consulting":  lambda e: _parse_year(e.years),
    "Membership":  lambda e: _parse_year(e.years),
    "Panel":       lambda e: _parse_year(e.date),
    "Patent":      lambda e: e.id,          # no date → insertion order
    "Symposium":   lambda e: _parse_year(e.date),
    "Class":       lambda e: e.year or 0,
    "Grant":       lambda e: _parse_year(e.years_start),
    "Award":       lambda e: _parse_year(e.year or e.date),
    "Press":       lambda e: _parse_year(e.date),
    "Trainee":     lambda e: _parse_year(e.years_start),
    "Seminar":     lambda e: _parse_year(e.date),
    "Committee":   lambda e: _parse_year(e.dates),
    "MiscSection": lambda e: e.id,          # no date → insertion order
}


def sort_items(items: list, model_class, reverse: bool = True) -> list:
    """Return items sorted by their primary date field (default: newest first)."""
    key_fn = SECTION_SORT_KEY.get(model_class.__name__, lambda e: e.id)
    return sorted(items, key=key_fn, reverse=reverse)
