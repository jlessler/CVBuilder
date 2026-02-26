"""Tests for fetch_pubs dedup author merging and Crossref enrichment."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.fetch_pubs import (
    RawCandidate,
    _dedup_candidates,
    _enrich_authors_via_crossref,
)


# ---------------------------------------------------------------------------
# _dedup_candidates – author merging
# ---------------------------------------------------------------------------

class TestDedupAuthorMerge:
    """When ORCID (no authors) merges with Crossref/PubMed (has authors),
    the merged record should keep the authors."""

    def test_crossref_wins_keeps_its_authors(self):
        """Crossref record is richer (more fields) and has authors → authors kept."""
        orcid = RawCandidate(
            title="Some Paper", year="2024", doi="10.1234/test", source="orcid",
        )
        crossref = RawCandidate(
            title="Some Paper", year="2024", doi="10.1234/test",
            journal="Nature", volume="1", issue="2", pages="10-20",
            authors=["Smith John", "Doe Jane"], source="crossref",
        )
        merged = _dedup_candidates([orcid, crossref])
        assert len(merged) == 1
        assert merged[0].authors == ["Smith John", "Doe Jane"]
        assert "orcid" in merged[0].source
        assert "crossref" in merged[0].source

    def test_orcid_wins_inherits_authors(self):
        """ORCID record is richer in metadata but has no authors →
        should inherit authors from the Crossref record."""
        orcid = RawCandidate(
            title="Some Paper", year="2024", doi="10.1234/test",
            journal="Nature", volume="1", issue="2", pages="10-20",
            pmid="12345", source="orcid",
        )
        crossref = RawCandidate(
            title="Some Paper", year="2024", doi="10.1234/test",
            authors=["Smith John", "Doe Jane"], source="crossref",
        )
        merged = _dedup_candidates([orcid, crossref])
        assert len(merged) == 1
        assert merged[0].authors == ["Smith John", "Doe Jane"]

    def test_both_have_authors_richer_wins(self):
        """When both records have authors, the richer record's authors win."""
        pubmed = RawCandidate(
            title="Some Paper", year="2024", doi="10.1234/test",
            journal="Nature", authors=["Smith J"], source="pubmed",
        )
        crossref = RawCandidate(
            title="Some Paper", year="2024", doi="10.1234/test",
            journal="Nature", volume="1", issue="2", pages="10-20",
            authors=["Smith John", "Doe Jane"], source="crossref",
        )
        merged = _dedup_candidates([pubmed, crossref])
        assert len(merged) == 1
        # Crossref is richer → its authors should be kept
        assert "Doe Jane" in merged[0].authors

    def test_title_based_dedup_merges_authors(self):
        """Records matched by title (no DOI) should also merge authors."""
        orcid = RawCandidate(
            title="A Great Discovery", year="2023", source="orcid",
        )
        pubmed = RawCandidate(
            title="A Great Discovery", year="2023",
            journal="Science", authors=["Lee K", "Park S"], source="pubmed",
        )
        merged = _dedup_candidates([orcid, pubmed])
        assert len(merged) == 1
        assert merged[0].authors == ["Lee K", "Park S"]

    def test_no_duplicate_no_merge(self):
        """Distinct records should not be merged."""
        a = RawCandidate(title="Paper A", year="2024", doi="10.1/a", source="orcid")
        b = RawCandidate(
            title="Paper B", year="2024", doi="10.1/b",
            authors=["X Y"], source="crossref",
        )
        merged = _dedup_candidates([a, b])
        assert len(merged) == 2
        assert merged[0].authors == []
        assert merged[1].authors == ["X Y"]


# ---------------------------------------------------------------------------
# _enrich_authors_via_crossref
# ---------------------------------------------------------------------------

class TestEnrichAuthorsViaCrossref:
    """Test that ORCID-only candidates with DOIs get authors from Crossref."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _mock_client(self, responses: dict[str, dict]):
        """Create a mock httpx.AsyncClient that returns canned responses by DOI."""
        client = MagicMock()

        async def _get(url, **kwargs):
            resp = MagicMock()
            # Extract DOI from URL (https://api.crossref.org/works/{doi})
            doi = url.replace("https://api.crossref.org/works/", "")
            if doi in responses:
                resp.status_code = 200
                resp.json.return_value = responses[doi]
            else:
                resp.status_code = 404
                resp.json.return_value = {}
            return resp

        client.get = _get
        return client

    def test_enriches_candidate_with_doi(self):
        candidates = [
            RawCandidate(title="Paper", doi="10.1234/test", source="orcid"),
        ]
        mock_client = self._mock_client({
            "10.1234/test": {
                "message": {
                    "author": [
                        {"family": "Smith", "given": "John"},
                        {"family": "Doe", "given": "Jane"},
                    ]
                }
            }
        })
        self._run(_enrich_authors_via_crossref(candidates, mock_client))
        assert candidates[0].authors == ["Smith John", "Doe Jane"]

    def test_skips_candidates_with_existing_authors(self):
        candidates = [
            RawCandidate(
                title="Paper", doi="10.1234/test",
                authors=["Already Here"], source="pubmed",
            ),
        ]
        mock_client = self._mock_client({
            "10.1234/test": {
                "message": {
                    "author": [{"family": "Other", "given": "Person"}]
                }
            }
        })
        self._run(_enrich_authors_via_crossref(candidates, mock_client))
        # Should NOT overwrite existing authors
        assert candidates[0].authors == ["Already Here"]

    def test_skips_candidates_without_doi(self):
        candidates = [
            RawCandidate(title="Paper", source="orcid"),
        ]
        mock_client = self._mock_client({})
        self._run(_enrich_authors_via_crossref(candidates, mock_client))
        assert candidates[0].authors == []

    def test_handles_crossref_failure_gracefully(self):
        candidates = [
            RawCandidate(title="Paper", doi="10.1234/missing", source="orcid"),
        ]
        mock_client = self._mock_client({})  # 404 for this DOI
        self._run(_enrich_authors_via_crossref(candidates, mock_client))
        # Should remain empty, no exception raised
        assert candidates[0].authors == []

    def test_enriches_multiple_candidates(self):
        candidates = [
            RawCandidate(title="Paper A", doi="10.1/a", source="orcid"),
            RawCandidate(title="Paper B", doi="10.1/b", source="orcid"),
            RawCandidate(title="Paper C", doi="10.1/c", authors=["Has Author"], source="crossref"),
        ]
        mock_client = self._mock_client({
            "10.1/a": {"message": {"author": [{"family": "Alpha", "given": "A"}]}},
            "10.1/b": {"message": {"author": [{"family": "Beta", "given": "B"}]}},
        })
        self._run(_enrich_authors_via_crossref(candidates, mock_client))
        assert candidates[0].authors == ["Alpha A"]
        assert candidates[1].authors == ["Beta B"]
        assert candidates[2].authors == ["Has Author"]  # untouched
