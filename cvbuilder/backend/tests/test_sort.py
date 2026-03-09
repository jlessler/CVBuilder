"""Unit tests for app.services.sort (no DB needed)."""
from types import SimpleNamespace

from app.services.sort import _parse_year, sort_items, compute_sort_date


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


# ── sort_items (Work) ───────────────────────────────────────────────────

class _FakeWork:
    pass

_FakeWork.__name__ = "Work"


def _work(year, month=0, day=0, id_=1):
    return SimpleNamespace(year=year, month=month, day=day, id=id_)


def test_sort_items_work_descending():
    items = [_work(2018, id_=1), _work(2022, id_=2), _work(2020, id_=3)]
    result = sort_items(items, _FakeWork, reverse=True)
    years = [i.year for i in result]
    assert years == [2022, 2020, 2018]


def test_sort_items_work_ascending():
    items = [_work(2022, id_=1), _work(2018, id_=2), _work(2020, id_=3)]
    result = sort_items(items, _FakeWork, reverse=False)
    years = [i.year for i in result]
    assert years == [2018, 2020, 2022]


# ── sort_items (CVItem) ────────────────────────────────────────────────

class _FakeCVItem:
    pass

_FakeCVItem.__name__ = "CVItem"


def _cvitem(sort_date, id_=1):
    return SimpleNamespace(sort_date=sort_date, id=id_)


def test_sort_items_cvitem_descending():
    items = [_cvitem(2018, 1), _cvitem(2022, 2), _cvitem(2020, 3)]
    result = sort_items(items, _FakeCVItem, reverse=True)
    dates = [i.sort_date for i in result]
    assert dates == [2022, 2020, 2018]


def test_sort_items_cvitem_ascending():
    items = [_cvitem(2022, 1), _cvitem(2018, 2), _cvitem(2020, 3)]
    result = sort_items(items, _FakeCVItem, reverse=False)
    dates = [i.sort_date for i in result]
    assert dates == [2018, 2020, 2022]


# ── compute_sort_date ──────────────────────────────────────────────────

def test_compute_sort_date_education():
    assert compute_sort_date("education", {"degree": "PhD", "year": 2020}) == 2020


def test_compute_sort_date_grants():
    assert compute_sort_date("grants", {"title": "Grant A", "years_start": "2018"}) == 2018


def test_compute_sort_date_unknown_section():
    assert compute_sort_date("unknown", {"date": "2023"}) == 2023


def test_compute_sort_date_no_date():
    assert compute_sort_date("education", {"degree": "PhD"}) is None
