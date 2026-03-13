"""Citation metrics: fetch from OpenAlex and aggregate from Works."""
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.auth import get_current_user
from app.services.fetch_citations import (
    fetch_openalex_by_dois,
    compute_aggregate,
    _normalize_doi,
)

router = APIRouter(prefix="/api/citations", tags=["citations"])


@router.post("/fetch")
async def fetch_citations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Fetch citation data from OpenAlex for all Works with DOIs.

    Updates each Work's data blob with cited_by_count and
    citation_counts_by_year, then returns the aggregate summary.
    """
    uid = current_user.id

    # Get all works with DOIs
    works = db.query(models.Work).filter(
        models.Work.user_id == uid,
        models.Work.doi.isnot(None),
        models.Work.doi != "",
    ).all()

    if not works:
        raise HTTPException(
            status_code=400,
            detail="No works with DOIs found. Add some scholarly works first.",
        )

    # Build DOI → Work mapping
    doi_to_works: dict[str, list[models.Work]] = {}
    for w in works:
        norm = _normalize_doi(w.doi)
        doi_to_works.setdefault(norm, []).append(w)

    all_dois = list(doi_to_works.keys())
    oa_results, error = await fetch_openalex_by_dois(all_dois)
    if error:
        raise HTTPException(status_code=502, detail=error)

    # Update each matched Work
    updated_count = 0
    for norm_doi, citation_data in oa_results.items():
        for work in doi_to_works.get(norm_doi, []):
            # Copy dict to trigger SQLAlchemy mutation detection
            data = dict(work.data or {})
            data["cited_by_count"] = citation_data["cited_by_count"]
            data["citation_counts_by_year"] = citation_data["citation_counts_by_year"]
            work.data = data
            updated_count += 1

    db.commit()

    # Compute aggregate from all works (including those without DOIs that
    # may have had citation data set previously)
    all_works = db.query(models.Work).filter_by(user_id=uid).all()
    works_with_citations = []
    for w in all_works:
        wd = w.data or {}
        if "cited_by_count" in wd:
            works_with_citations.append(wd)

    aggregate = compute_aggregate(works_with_citations)
    aggregate["source"] = "OpenAlex"
    aggregate["retrieved_at"] = date.today().isoformat()
    aggregate["works_updated"] = updated_count
    aggregate["works_matched"] = len(oa_results)
    aggregate["works_queried"] = len(all_dois)

    # Save/update the citation_metrics CVItem with the aggregate
    cv_item = db.query(models.CVItem).filter_by(
        user_id=uid, section="citation_metrics"
    ).first()
    item_data = {
        "yearly_counts": aggregate["yearly_counts"],
        "total_citations": aggregate["total_citations"],
        "h_index": aggregate["h_index"],
        "i10_index": aggregate["i10_index"],
        "source": "OpenAlex",
        "retrieved_at": date.today().isoformat(),
    }
    if cv_item:
        cv_item.data = item_data
    else:
        cv_item = models.CVItem(
            user_id=uid,
            section="citation_metrics",
            data=item_data,
            sort_order=0,
        )
        db.add(cv_item)
    db.commit()

    return aggregate


@router.get("/summary")
def get_citation_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Compute citation summary from per-work data (no external calls)."""
    all_works = db.query(models.Work).filter_by(user_id=current_user.id).all()
    works_with_citations = []
    for w in all_works:
        wd = w.data or {}
        if "cited_by_count" in wd:
            works_with_citations.append(wd)

    if not works_with_citations:
        return {
            "yearly_counts": {},
            "total_citations": 0,
            "h_index": 0,
            "i10_index": 0,
        }

    return compute_aggregate(works_with_citations)
