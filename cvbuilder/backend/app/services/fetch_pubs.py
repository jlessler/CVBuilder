"""Fetch new publications from ORCID, PubMed, Crossref, and Semantic Scholar."""
from __future__ import annotations

import asyncio
import re
import unicodedata
from dataclasses import dataclass, field

import httpx

from app import models


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _scalar(value, default=""):
    """Return first element if list, otherwise value itself."""
    if isinstance(value, list):
        return value[0] if value else default
    return value if value is not None else default


def _year_from_date_parts(ref: dict) -> str | None:
    """Extract year from published-print / published-online / issued."""
    for key in ("published-print", "published-online", "issued"):
        parts = ref.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            return str(parts[0][0])
    return None


# ---------------------------------------------------------------------------
# RawCandidate
# ---------------------------------------------------------------------------

@dataclass
class RawCandidate:
    title: str
    year: str | None = None
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    authors: list[str] = field(default_factory=list)
    source: str = ""
    pmid: str | None = None
    pub_type: str = "papers"

    def _field_count(self) -> int:
        """Count non-empty fields (used to prefer richer records during dedup)."""
        return sum(1 for v in (
            self.year, self.journal, self.volume, self.issue,
            self.pages, self.doi, self.pmid,
        ) if v) + len(self.authors)


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def _normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    doi = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi.org/"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
    return doi.lower()


def _normalize_title(title: str) -> str:
    t = unicodedata.normalize("NFD", title)
    t = t.encode("ascii", "ignore").decode("ascii")
    t = t.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _key(c: RawCandidate):
    """Return (doi_key, title_year_key) for a candidate."""
    doi_key = _normalize_doi(c.doi)
    year_str = (c.year or "").strip()
    title_key = (_normalize_title(c.title), year_str) if c.title else None
    return doi_key, title_key


def _dedup_candidates(candidates: list[RawCandidate]) -> list[RawCandidate]:
    """Collapse cross-source duplicates; merge source strings; keep richer record."""
    seen_doi: dict[str, int] = {}     # doi → index in result
    seen_title: dict[tuple, int] = {} # (norm_title, year) → index in result
    result: list[RawCandidate] = []

    for c in candidates:
        doi_key, title_key = _key(c)
        idx: int | None = None

        if doi_key:
            idx = seen_doi.get(doi_key)
        if idx is None and title_key and title_key[0]:
            idx = seen_title.get(title_key)

        if idx is not None:
            existing = result[idx]
            # merge sources
            sources = set(existing.source.split("+")) | {c.source}
            existing.source = "+".join(sorted(sources))
            # keep richer record
            if c._field_count() > existing._field_count():
                c.source = existing.source
                result[idx] = c
                # re-register keys
                if doi_key:
                    seen_doi[doi_key] = idx
                if title_key and title_key[0]:
                    seen_title[title_key] = idx
        else:
            idx = len(result)
            result.append(c)
            if doi_key:
                seen_doi[doi_key] = idx
            if title_key and title_key[0]:
                seen_title[title_key] = idx

    return result


def deduplicate(candidates: list[RawCandidate], db_pubs) -> list[RawCandidate]:
    """Remove candidates already present in the DB."""
    db_dois: set[str] = set()
    db_titles: set[tuple] = set()

    for pub in db_pubs:
        nd = _normalize_doi(pub.doi)
        if nd:
            db_dois.add(nd)
        if pub.title:
            nt = _normalize_title(pub.title)
            yr = (pub.year or "").strip()
            if nt:
                db_titles.add((nt, yr))

    result = []
    for c in candidates:
        doi_key, title_key = _key(c)
        if doi_key and doi_key in db_dois:
            continue
        if title_key and title_key[0] and title_key in db_titles:
            continue
        result.append(c)
    return result


# ---------------------------------------------------------------------------
# Author name matching
# ---------------------------------------------------------------------------

def _matches_profile_name(author_str: str, profile_name: str) -> bool:
    """
    Return True if author_str plausibly refers to the same person as profile_name.
    Mirrors the matchesSelf() logic in Publications.tsx:
      - Last name must appear as a whole word (case-insensitive)
      - First initial must match
      - Middle initial must match when present in both names
    """
    if not author_str or not profile_name:
        return False

    parts = profile_name.strip().split()
    if len(parts) < 2:
        return False

    last = parts[-1]
    first_init = parts[0][0].upper()
    mid_init = parts[1][0].upper() if len(parts) >= 3 else ""

    # Last name must appear as a whole word
    if not re.search(rf"\b{re.escape(last)}\b", author_str, re.IGNORECASE):
        return False

    # Strip punctuation and split the candidate author string
    clean = re.sub(r"[,.]", " ", author_str).split()
    last_idx = next((i for i, w in enumerate(clean) if w.lower() == last.lower()), -1)
    if last_idx == -1:
        return False

    other = [w for i, w in enumerate(clean) if i != last_idx]
    if not other:
        return False

    def to_init(w: str) -> str:
        return w if re.match(r"^[A-Z]{1,3}$", w) else w[0].upper()

    initials = "".join(to_init(w) for w in other).upper()

    if not initials or initials[0] != first_init:
        return False
    if mid_init and len(initials) >= 2 and initials[1] != mid_init:
        return False

    return True


def _any_author_matches(c: RawCandidate, profile_name: str) -> bool:
    """Return True if at least one author in the candidate matches profile_name."""
    return any(_matches_profile_name(a, profile_name) for a in c.authors)


# ---------------------------------------------------------------------------
# Type inference
# ---------------------------------------------------------------------------

def _infer_pub_type(c: RawCandidate) -> str:
    journal_lower = (c.journal or "").lower()
    preprint_keywords = ("biorxiv", "medrxiv", "arxiv", "preprint", "ssrn")
    if any(kw in journal_lower for kw in preprint_keywords):
        return "preprints"
    return "papers"


# ---------------------------------------------------------------------------
# Per-source async fetchers
# ---------------------------------------------------------------------------

_HEADERS = {"User-Agent": "CVBuilder/1.0 (mailto:support@cvbuilder.app)"}
_TIMEOUT = 20.0


async def _fetch_orcid(orcid: str, client: httpx.AsyncClient) -> tuple[list[RawCandidate], str | None]:
    if not orcid:
        return [], None
    orcid = orcid.strip()
    url = f"https://pub.orcid.org/v3.0/{orcid}/works"
    try:
        r = await client.get(url, headers={**_HEADERS, "Accept": "application/json"}, timeout=_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        return [], str(e)

    data = r.json()
    candidates: list[RawCandidate] = []

    for group in data.get("group", []):
        for summary in group.get("work-summary", []):
            raw_title = summary.get("title", {})
            title_str = ""
            if isinstance(raw_title, dict):
                tv = raw_title.get("title", {})
                if isinstance(tv, dict):
                    title_str = tv.get("value", "") or ""
                elif isinstance(tv, str):
                    title_str = tv

            if not title_str:
                continue

            year: str | None = None
            pub_date = summary.get("publication-date") or {}
            if isinstance(pub_date, dict):
                y_obj = pub_date.get("year") or {}
                if isinstance(y_obj, dict):
                    year = y_obj.get("value")
                elif isinstance(y_obj, str):
                    year = y_obj

            doi: str | None = None
            ext_ids = summary.get("external-ids", {}).get("external-id", [])
            for eid in ext_ids:
                if eid.get("external-id-type") == "doi":
                    doi = eid.get("external-id-value")
                    break

            journal_title = summary.get("journal-title", {})
            journal: str | None = None
            if isinstance(journal_title, dict):
                journal = journal_title.get("value")
            elif isinstance(journal_title, str):
                journal = journal_title

            candidates.append(RawCandidate(
                title=title_str, year=year, doi=doi, journal=journal, source="orcid"
            ))

    return candidates, None


async def _fetch_pubmed(name: str, client: httpx.AsyncClient) -> tuple[list[RawCandidate], str | None]:
    if not name:
        return [], None

    # Build author query: "Last FI"[Author] — PubMed syntax
    parts = name.strip().split()
    if len(parts) >= 2:
        last = parts[-1]
        first_init = parts[0][0]
        query = f"{last} {first_init}[Author]"
    else:
        query = f"{name}[Author]"

    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    try:
        r = await client.get(
            f"{base}/esearch.fcgi",
            params={"db": "pubmed", "term": query, "retmode": "json", "retmax": 200},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        search_data = r.json()
    except Exception as e:
        return [], str(e)

    ids = search_data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return [], None

    try:
        r2 = await client.get(
            f"{base}/esummary.fcgi",
            params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        r2.raise_for_status()
        summary_data = r2.json()
    except Exception as e:
        return [], str(e)

    candidates: list[RawCandidate] = []
    result = summary_data.get("result", {})

    for pmid in ids:
        doc = result.get(pmid, {})
        title = doc.get("title", "")
        if not title:
            continue

        # Extract year from pubdate field (e.g. "2023 Jan", "2023")
        pubdate = doc.get("pubdate", "")
        year_match = re.search(r"\b(19|20)\d{2}\b", pubdate)
        year = year_match.group(0) if year_match else None

        journal = doc.get("source")
        volume = doc.get("volume") or None
        issue = doc.get("issue") or None
        pages = doc.get("pages") or None

        doi: str | None = None
        for aid in doc.get("articleids", []):
            if aid.get("idtype") == "doi":
                doi = aid.get("value")
                break

        authors = [a.get("name", "") for a in doc.get("authors", []) if a.get("name")]

        c = RawCandidate(
            title=title, year=year, journal=journal, volume=volume,
            issue=issue, pages=pages, doi=doi, authors=authors,
            source="pubmed", pmid=pmid,
        )
        if _any_author_matches(c, name):
            candidates.append(c)

    return candidates, None


async def _fetch_crossref(name: str, client: httpx.AsyncClient) -> tuple[list[RawCandidate], str | None]:
    if not name:
        return [], None

    try:
        r = await client.get(
            "https://api.crossref.org/works",
            params={
                "query.author": name,
                "rows": 100,
                "select": "DOI,title,published,published-print,published-online,issued,container-title,volume,issue,page,author",
            },
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return [], str(e)

    candidates: list[RawCandidate] = []
    for item in data.get("message", {}).get("items", []):
        title = _scalar(item.get("title", []))
        if not title:
            continue
        year = _year_from_date_parts(item)
        journal = _scalar(item.get("container-title", []))
        volume = _scalar(item.get("volume"))
        issue = _scalar(item.get("issue"))
        pages = _scalar(item.get("page"))
        doi = item.get("DOI")

        authors = []
        for a in item.get("author", []):
            family = a.get("family", "")
            given = a.get("given", "")
            full = f"{family} {given}".strip()
            if full:
                authors.append(full)

        c = RawCandidate(
            title=str(title), year=year,
            journal=str(journal) if journal else None,
            volume=str(volume) if volume else None,
            issue=str(issue) if issue else None,
            pages=str(pages) if pages else None,
            doi=doi, authors=authors, source="crossref",
        )
        if _any_author_matches(c, name):
            candidates.append(c)

    return candidates, None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def fetch_new_publications(db, name: str | None, orcid: str | None) -> dict:
    """
    Fan out to all 4 sources, dedup against DB, return structured result.
    Returns: {candidates: [...], searched: [...], errors: {...}}
    """
    db_pubs = db.query(models.Publication).all()

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            _fetch_orcid(orcid or "", client),
            _fetch_pubmed(name or "", client),
            _fetch_crossref(name or "", client),
            return_exceptions=True,
        )

    source_names = ["orcid", "pubmed", "crossref"]
    all_candidates: list[RawCandidate] = []
    errors: dict[str, str] = {}
    searched: list[str] = []

    for source, result in zip(source_names, results):
        if isinstance(result, Exception):
            errors[source] = str(result)
        else:
            candidates, err = result
            if err:
                errors[source] = err
            elif (source == "orcid" and orcid) or (source != "orcid" and name):
                searched.append(source)
            all_candidates.extend(candidates)

    # Infer pub type for all candidates
    for c in all_candidates:
        c.pub_type = _infer_pub_type(c)

    # Dedup within results, then against DB
    merged = _dedup_candidates(all_candidates)
    new_pubs = deduplicate(merged, db_pubs)

    # Sort by year desc, then title
    new_pubs.sort(key=lambda c: (-(int(c.year) if c.year and c.year.isdigit() else 0), c.title or ""))

    # Convert to dicts for Pydantic
    return {
        "candidates": [
            {
                "title": c.title,
                "year": c.year,
                "journal": c.journal,
                "volume": c.volume,
                "issue": c.issue,
                "pages": c.pages,
                "doi": c.doi,
                "authors": c.authors,
                "source": c.source,
                "pmid": c.pmid,
                "pub_type": c.pub_type,
            }
            for c in new_pubs
        ],
        "searched": searched,
        "errors": errors,
    }
