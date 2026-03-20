"""Verify that section key lists are consistent across backend and frontend.

The section keys defined in the backend (_HEADINGS in main.py,
_build_cv_data keys in templates.py, and the base.html template) must
stay in sync with the frontend ALL_SECTIONS arrays in Templates.tsx and
CVInstances.tsx.  This test parses all sources and flags any drift.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent  # cvbuilder/


# ---------------------------------------------------------------------------
# Helpers to extract section keys from each source
# ---------------------------------------------------------------------------

def _extract_headings_keys() -> set[str]:
    """Parse _HEADINGS dict keys from main.py."""
    text = (ROOT / "backend" / "app" / "main.py").read_text()
    # Match lines like:  "some_key":  "Some Label",
    return set(re.findall(r'^\s*"([a-zA-Z_]+)":\s*"', text, re.MULTILINE))


def _extract_build_cv_data_keys() -> set[str]:
    """Parse keys from _build_cv_data() return dict in templates.py."""
    text = (ROOT / "backend" / "app" / "routers" / "templates.py").read_text()
    # Find the return dict block — keys like:  "education": ...,
    # Start after "return {" and end at the closing "}"
    m = re.search(r'return\s*\{(.+?)^\s*\}', text, re.DOTALL | re.MULTILINE)
    assert m, "_build_cv_data return dict not found"
    block = m.group(1)
    # Extract top-level string keys (skip "publications" which is a combined key)
    return set(re.findall(r'^\s*"([a-zA-Z_]+)":', block, re.MULTILINE))


def _extract_base_html_keys() -> set[str]:
    """Parse section keys from {% elif key == '...' %} blocks in base.html."""
    text = (ROOT / "backend" / "cv_templates" / "base.html").read_text()
    keys = set(re.findall(r"key\s*==\s*'([a-zA-Z_]+)'", text))
    return keys


def _extract_frontend_all_sections() -> set[str]:
    """Parse ALL_SECTIONS array keys from the shared SectionComposer component."""
    text = (ROOT / "frontend" / "src" / "components" / "SectionComposer.tsx").read_text()
    # Find the ALL_SECTIONS block
    m = re.search(r'const ALL_SECTIONS\s*=\s*\[(.+?)\]', text, re.DOTALL)
    assert m, "ALL_SECTIONS not found in SectionComposer.tsx"
    block = m.group(1)
    return set(re.findall(r"key:\s*'([a-zA-Z_]+)'", block))


def _extract_section_key_map_keys() -> set[str]:
    """Parse SECTION_KEY_MAP keys from cv_instances.py."""
    text = (ROOT / "backend" / "app" / "routers" / "cv_instances.py").read_text()
    # Match from SECTION_KEY_MAP = { to the closing ^}
    m = re.search(r'SECTION_KEY_MAP[^=]*=\s*\{(.+?)^\}', text, re.DOTALL | re.MULTILINE)
    assert m, "SECTION_KEY_MAP not found"
    return set(re.findall(r'^\s*"([a-zA-Z_]+)":', m.group(1), re.MULTILINE))


def _extract_cv_data_key_map_keys() -> set[str]:
    """Parse _CV_DATA_KEY_MAP keys from cv_instances.py."""
    text = (ROOT / "backend" / "app" / "routers" / "cv_instances.py").read_text()
    m = re.search(r'_CV_DATA_KEY_MAP\s*=\s*\{(.+?)^\s{4}\}', text, re.DOTALL | re.MULTILINE)
    assert m, "_CV_DATA_KEY_MAP not found"
    return set(re.findall(r'^\s*"([a-zA-Z_]+)":', m.group(1), re.MULTILINE))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSectionConsistency:
    """All section key registries must contain the same keys."""

    def test_all_sections_shared_component_exists(self):
        """ALL_SECTIONS is defined in the shared SectionComposer component."""
        sections = _extract_frontend_all_sections()
        assert len(sections) > 0, "ALL_SECTIONS is empty in SectionComposer.tsx"

    def test_frontend_matches_headings(self):
        """Every frontend section key must have a _HEADINGS entry."""
        frontend = _extract_frontend_all_sections()
        headings = _extract_headings_keys()
        missing = frontend - headings
        assert not missing, (
            f"Frontend ALL_SECTIONS keys missing from _HEADINGS: {missing}"
        )

    def test_headings_matches_frontend(self):
        """Every _HEADINGS key should appear in the frontend ALL_SECTIONS.

        group_heading is excluded — it's a meta-entry for visual hierarchy,
        not a data section, so it doesn't belong in ALL_SECTIONS.
        """
        headings = _extract_headings_keys() - {"group_heading"}
        frontend = _extract_frontend_all_sections()
        missing = headings - frontend
        assert not missing, (
            f"_HEADINGS keys missing from frontend ALL_SECTIONS: {missing}"
        )

    def test_base_html_covers_frontend_sections(self):
        """Every frontend section key must have a rendering block in base.html."""
        frontend = _extract_frontend_all_sections()
        html_keys = _extract_base_html_keys()
        missing = frontend - html_keys
        assert not missing, (
            f"Frontend section keys with no base.html rendering block: {missing}"
        )

    def test_build_cv_data_covers_frontend_sections(self):
        """Every non-publication frontend key must be queried in _build_cv_data."""
        frontend = _extract_frontend_all_sections()
        cv_data_keys = _extract_build_cv_data_keys()

        # Publication sub-types are rendered from the combined "publications" key
        pub_keys = {k for k in frontend if k.startswith("publications_")}
        # These section keys map to different cv_data keys
        key_mapping = {
            "panels_advisory": "panels",
            "panels_grantreview": "panels",
            "trainees_advisees": "trainees",
            "trainees_postdocs": "trainees",
        }

        non_pub = frontend - pub_keys
        missing = set()
        for k in non_pub:
            mapped = key_mapping.get(k, k)
            if mapped not in cv_data_keys:
                missing.add(k)

        assert not missing, (
            f"Frontend section keys not queried in _build_cv_data: {missing}"
        )

    def test_section_key_map_covers_frontend(self):
        """Every non-publication frontend key must be in SECTION_KEY_MAP (cv_instances.py)."""
        frontend = _extract_frontend_all_sections()
        skm = _extract_section_key_map_keys()
        # Publication sub-types map via _PUB_TYPE_MAP, not SECTION_KEY_MAP
        pub_keys = {k for k in frontend if k.startswith("publications_")}
        missing = (frontend - pub_keys) - skm
        assert not missing, (
            f"Frontend section keys missing from SECTION_KEY_MAP: {missing}"
        )

    def test_cv_data_key_map_covers_frontend(self):
        """Every non-publication frontend key must be in _CV_DATA_KEY_MAP (cv_instances.py)."""
        frontend = _extract_frontend_all_sections()
        cdkm = _extract_cv_data_key_map_keys()
        # Publication sub-types are handled separately
        pub_keys = {k for k in frontend if k.startswith("publications_")}
        missing = (frontend - pub_keys) - cdkm
        assert not missing, (
            f"Frontend section keys missing from _CV_DATA_KEY_MAP: {missing}"
        )
