"""Tests for the name parser service."""
import pytest
from app.services.name_parser import parse_author_name, compose_author_name


class TestParseAuthorName:
    def test_family_single_initial(self):
        r = parse_author_name("Lessler J")
        assert r["family_name"] == "Lessler"
        assert r["given_name"] == "J."
        assert r["middle_name"] is None

    def test_family_two_initials(self):
        r = parse_author_name("Lessler JK")
        assert r["family_name"] == "Lessler"
        assert r["given_name"] == "J."
        assert r["middle_name"] == "K."

    def test_initial_family(self):
        r = parse_author_name("J Lessler")
        assert r["family_name"] == "Lessler"
        assert r["given_name"] == "J."

    def test_two_initials_family(self):
        r = parse_author_name("JK Lessler")
        assert r["family_name"] == "Lessler"
        assert r["given_name"] == "J."
        assert r["middle_name"] == "K."

    def test_given_family(self):
        r = parse_author_name("Justin Lessler")
        assert r["family_name"] == "Lessler"
        assert r["given_name"] == "Justin"

    def test_given_middle_family(self):
        r = parse_author_name("Justin K Lessler")
        assert r["family_name"] == "Lessler"
        assert r["given_name"] == "Justin"
        assert r["middle_name"] == "K"

    def test_comma_format(self):
        r = parse_author_name("Lessler, Justin")
        assert r["family_name"] == "Lessler"
        assert r["given_name"] == "Justin"

    def test_comma_format_with_middle(self):
        r = parse_author_name("Lessler, Justin K")
        assert r["family_name"] == "Lessler"
        assert r["given_name"] == "Justin"
        assert r["middle_name"] == "K"

    def test_comma_format_initials(self):
        r = parse_author_name("Lessler, J. K.")
        assert r["family_name"] == "Lessler"
        assert r["given_name"] == "J."
        assert r["middle_name"] is not None

    def test_particle_van_der(self):
        r = parse_author_name("van der Berg A")
        assert r["family_name"] == "van der Berg"
        assert r["given_name"] == "A."

    def test_comma_particle(self):
        r = parse_author_name("de la Cruz, Maria")
        assert r["family_name"] == "de la Cruz"
        assert r["given_name"] == "Maria"

    def test_suffix_jr(self):
        r = parse_author_name("Smith Jr, J")
        assert r["family_name"] == "Smith"
        assert r["suffix"] == "Jr"
        assert r["given_name"] is not None

    def test_suffix_iii(self):
        r = parse_author_name("Jones, Robert III")
        assert r["family_name"] == "Jones"
        assert r["given_name"] == "Robert"
        assert r["suffix"] == "III"

    def test_mononym(self):
        r = parse_author_name("Madonna")
        assert r["family_name"] == "Madonna"
        assert r["given_name"] is None

    def test_empty(self):
        r = parse_author_name("")
        assert r["family_name"] is None
        assert r["given_name"] is None

    def test_whitespace_only(self):
        r = parse_author_name("   ")
        assert r["family_name"] is None


class TestComposeAuthorName:
    def test_basic(self):
        assert compose_author_name("Justin", "Lessler", "K") == "Lessler JK"

    def test_no_middle(self):
        assert compose_author_name("Justin", "Lessler") == "Lessler J"

    def test_with_suffix(self):
        assert compose_author_name("Robert", "Jones", suffix="III") == "Jones R III"

    def test_family_only(self):
        assert compose_author_name(family_name="Lessler") == "Lessler"

    def test_given_only(self):
        assert compose_author_name(given_name="Justin") == "Justin"

    def test_empty(self):
        assert compose_author_name() == ""
