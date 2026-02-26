"""Unit tests for app.services.sort (no DB needed)."""
from types import SimpleNamespace

from app.services.sort import _parse_year, sort_items


# ── _parse_year ──────────────────────────────────────────────────────────

def test_parse_year_int():
    assert _parse_year(2024) == 2024


def test_parse_year_string():
    assert _parse_year("2021") == 2021


def test_parse_year_range():
    assert _parse_year("2019-2023") == 2019


def test_parse_year_none():
    assert _parse_year(None) == 0


def test_parse_year_garbage():
    assert _parse_year("no year here") == 0


def test_parse_year_embedded():
    assert _parse_year("Spring 2022 semester") == 2022


# ── sort_items ───────────────────────────────────────────────────────────

class _FakeEducation:
    """Stand-in whose __name__ matches the SECTION_SORT_KEY entry."""
    pass

# Rename so __name__ is exactly "Education"
_FakeEducation.__name__ = "Education"


def _edu(year, id_=1):
    return SimpleNamespace(year=year, id=id_)


def test_sort_items_descending():
    items = [_edu(2018, 1), _edu(2022, 2), _edu(2020, 3)]
    result = sort_items(items, _FakeEducation, reverse=True)
    years = [i.year for i in result]
    assert years == [2022, 2020, 2018]


def test_sort_items_ascending():
    items = [_edu(2022, 1), _edu(2018, 2), _edu(2020, 3)]
    result = sort_items(items, _FakeEducation, reverse=False)
    years = [i.year for i in result]
    assert years == [2018, 2020, 2022]
