"""Tests for the name formatting service."""
import pytest
from app.services.name_format import format_author_name, format_author_list, format_citation


class _Author:
    """Simple author-like object for testing."""
    def __init__(self, **kwargs):
        self.author_name = kwargs.get("author_name", "")
        self.given_name = kwargs.get("given_name")
        self.family_name = kwargs.get("family_name")
        self.middle_name = kwargs.get("middle_name")
        self.suffix = kwargs.get("suffix")
        self.student = kwargs.get("student", False)
        self.corresponding = kwargs.get("corresponding", False)
        self.cofirst = kwargs.get("cofirst", False)
        self.cosenior = kwargs.get("cosenior", False)


class TestFormatAuthorName:
    def test_display_returns_author_name(self):
        a = _Author(author_name="Lessler JK", family_name="Lessler", given_name="Justin", middle_name="K")
        assert format_author_name(a, "display") == "Lessler JK"

    def test_apa_format(self):
        a = _Author(author_name="Lessler JK", family_name="Lessler", given_name="Justin", middle_name="K")
        result = format_author_name(a, "apa")
        assert result == "Lessler, J. K."

    def test_vancouver_format(self):
        a = _Author(author_name="Lessler JK", family_name="Lessler", given_name="Justin", middle_name="K")
        result = format_author_name(a, "vancouver")
        assert result == "Lessler JK"

    def test_chicago_format(self):
        a = _Author(author_name="Lessler JK", family_name="Lessler", given_name="Justin", middle_name="K")
        result = format_author_name(a, "chicago")
        assert result == "Lessler, Justin K."

    def test_full_format(self):
        a = _Author(author_name="Lessler JK", family_name="Lessler", given_name="Justin", middle_name="K")
        result = format_author_name(a, "full")
        assert result == "Justin K. Lessler"

    def test_fallback_no_family_name(self):
        a = _Author(author_name="Some Author")
        assert format_author_name(a, "apa") == "Some Author"

    def test_with_suffix(self):
        a = _Author(author_name="Smith Jr J", family_name="Smith", given_name="John", suffix="Jr")
        result = format_author_name(a, "apa")
        assert "Jr" in result

    def test_dict_input(self):
        d = {"author_name": "Lessler J", "family_name": "Lessler", "given_name": "Justin"}
        result = format_author_name(d, "apa")
        assert result == "Lessler, J."


class TestFormatAuthorList:
    def test_single_author(self):
        authors = [_Author(author_name="Lessler J", family_name="Lessler", given_name="Justin")]
        result = format_author_list(authors, "apa")
        assert "Lessler" in result

    def test_two_authors_apa(self):
        authors = [
            _Author(author_name="Smith J", family_name="Smith", given_name="John"),
            _Author(author_name="Doe J", family_name="Doe", given_name="Jane"),
        ]
        result = format_author_list(authors, "apa")
        assert "& " in result  # APA uses ampersand

    def test_role_superscripts(self):
        authors = [
            _Author(author_name="Smith J", family_name="Smith", given_name="John", student=True),
        ]
        result = format_author_list(authors, "display")
        assert "&dagger;" in result

    def test_corresponding_marker(self):
        authors = [
            _Author(author_name="Smith J", family_name="Smith", given_name="John", corresponding=True),
        ]
        result = format_author_list(authors, "display")
        assert "<sup>*</sup>" in result

    def test_empty_list(self):
        assert format_author_list([], "apa") == ""

    def test_max_authors_et_al(self):
        authors = [_Author(author_name=f"Author{i}", family_name=f"Author{i}", given_name="A") for i in range(10)]
        result = format_author_list(authors, "display", max_authors=3)
        assert "et al." in result


class TestFormatCitation:
    def test_apa_full_citation(self):
        work = {
            "title": "A Great Paper",
            "year": "2024",
            "doi": "10.1234/test",
            "data": {"journal": "Nature", "volume": "1", "issue": "2", "pages": "10-20"},
            "authors": [
                {"author_name": "Smith J", "family_name": "Smith", "given_name": "John"},
            ],
        }
        result = format_citation(work, "apa")
        assert "(2024)" in result
        assert "A Great Paper" in result
        assert "<em>Nature</em>" in result

    def test_vancouver_full_citation(self):
        work = {
            "title": "A Great Paper",
            "year": "2024",
            "doi": "10.1234/test",
            "data": {"journal": "Nature", "volume": "1", "issue": "2", "pages": "10-20"},
            "authors": [
                {"author_name": "Smith J", "family_name": "Smith", "given_name": "John"},
            ],
        }
        result = format_citation(work, "vancouver")
        assert "2024" in result
        assert "1(2):10-20" in result

    def test_chicago_full_citation(self):
        work = {
            "title": "A Great Paper",
            "year": "2024",
            "data": {"journal": "Nature", "volume": "1", "issue": "2", "pages": "10-20"},
            "authors": [
                {"author_name": "Smith J", "family_name": "Smith", "given_name": "John"},
            ],
        }
        result = format_citation(work, "chicago")
        assert "&ldquo;" in result  # Chicago quotes title

    def test_display_returns_empty(self):
        work = {
            "title": "Paper",
            "year": "2024",
            "data": {},
            "authors": [],
        }
        assert format_citation(work, "display") == ""
