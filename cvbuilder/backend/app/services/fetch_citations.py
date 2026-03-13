"""Fetch per-work citation metrics from OpenAlex (by DOI)."""
from __future__ import annotations

import asyncio
from datetime import date

import httpx


_TIMEOUT = 30.0
_HEADERS = {"User-Agent": "CVBuilder/1.0 (mailto:admin@cvbuilder.local)"}
_OA_WORKS_URL = "https://api.openalex.org/works"
_DOI_BATCH_SIZE = 50


def _normalize_doi(doi: str) -> str:
    """Strip URL prefixes, lowercase."""
    doi = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi


async def fetch_openalex_by_dois(dois: list[str]) -> tuple[dict[str, dict], str | None]:
    """Fetch per-work citation data from OpenAlex for a list of DOIs.

    Args:
        dois: List of bare DOI strings (e.g. "10.1234/example").

    Returns:
        (results_dict, error_string).

        results_dict maps each DOI (lowercased) to::

            {
                "cited_by_count": int,
                "citation_counts_by_year": {"2020": 42, "2021": 88, ...},
            }

        DOIs not found on OpenAlex are omitted from the dict.
    """
    if not dois:
        return {}, None

    results: dict[str, dict] = {}
    semaphore = asyncio.Semaphore(5)

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:

        async def _query_batch(batch: list[str]) -> None:
            piped = "|".join(batch)
            async with semaphore:
                try:
                    r = await client.get(
                        _OA_WORKS_URL,
                        params={
                            "filter": f"doi:{piped}",
                            "select": "doi,cited_by_count,counts_by_year",
                            "per_page": str(len(batch)),
                        },
                    )
                    r.raise_for_status()
                except httpx.HTTPError:
                    # Retry once
                    await asyncio.sleep(1)
                    try:
                        r = await client.get(
                            _OA_WORKS_URL,
                            params={
                                "filter": f"doi:{piped}",
                                "select": "doi,cited_by_count,counts_by_year",
                                "per_page": str(len(batch)),
                            },
                        )
                        r.raise_for_status()
                    except httpx.HTTPError:
                        return

                for work in r.json().get("results", []):
                    raw_doi = work.get("doi", "")
                    if not raw_doi:
                        continue
                    norm = _normalize_doi(raw_doi)

                    yearly: dict[str, int] = {}
                    for entry in work.get("counts_by_year", []):
                        yr = entry.get("year")
                        cnt = entry.get("cited_by_count", 0)
                        if yr is not None and cnt > 0:
                            yearly[str(yr)] = cnt

                    results[norm] = {
                        "cited_by_count": work.get("cited_by_count", 0),
                        "citation_counts_by_year": yearly,
                    }

        # Handle pagination: OpenAlex returns at most per_page results,
        # so if a batch has more results than per_page we might miss some.
        # With _DOI_BATCH_SIZE=50 and per_page=50 this is fine since each
        # DOI maps to at most one work.
        batches = [
            dois[i : i + _DOI_BATCH_SIZE]
            for i in range(0, len(dois), _DOI_BATCH_SIZE)
        ]
        await asyncio.gather(*[_query_batch(b) for b in batches])

    return results, None


def compute_aggregate(
    works_citation_data: list[dict],
) -> dict:
    """Compute aggregate citation metrics from per-work citation data.

    Args:
        works_citation_data: List of dicts, each with
            ``cited_by_count`` (int) and
            ``citation_counts_by_year`` (dict[str, int]).

    Returns:
        Dict with yearly_counts, total_citations, h_index, i10_index.
    """
    yearly_counts: dict[str, int] = {}
    total_citations = 0
    cite_counts: list[int] = []

    for wd in works_citation_data:
        cbc = wd.get("cited_by_count", 0)
        total_citations += cbc
        cite_counts.append(cbc)

        for yr, cnt in wd.get("citation_counts_by_year", {}).items():
            yearly_counts[yr] = yearly_counts.get(yr, 0) + cnt

    # h-index: largest h such that h papers have >= h citations
    cite_counts.sort(reverse=True)
    h_index = 0
    for i, c in enumerate(cite_counts):
        if c >= i + 1:
            h_index = i + 1
        else:
            break

    # i10-index: papers with >= 10 citations
    i10_index = sum(1 for c in cite_counts if c >= 10)

    return {
        "yearly_counts": yearly_counts,
        "total_citations": total_citations,
        "h_index": h_index,
        "i10_index": i10_index,
    }
