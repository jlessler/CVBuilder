"""Works CRUD + DOI lookup endpoints (unified scholarly outputs)."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.doi import lookup_doi, lookup_doi_raw, compute_work_diffs, search_doi_by_metadata
from app.services.fetch_pubs import fetch_new_publications

router = APIRouter(prefix="/api/works", tags=["works"])


def _sync_crossref_links(work: models.Work, db: Session,
                         old_preprint_doi: str | None = None,
                         old_published_doi: str | None = None) -> None:
    """Ensure cross-reference DOIs are reciprocal between works."""
    user_id = work.user_id
    data = work.data or {}
    published_doi = data.get("published_doi")
    preprint_doi = data.get("preprint_doi")
    work_doi = work.doi

    if published_doi != old_published_doi:
        if old_published_doi:
            old_match = db.query(models.Work).filter_by(
                user_id=user_id, doi=old_published_doi
            ).first()
            if old_match:
                od = dict(old_match.data or {})
                if od.get("preprint_doi") == work_doi:
                    od.pop("preprint_doi", None)
                    old_match.data = od
        if published_doi and work_doi:
            match = db.query(models.Work).filter_by(
                user_id=user_id, doi=published_doi
            ).first()
            if match:
                md = dict(match.data or {})
                md["preprint_doi"] = work_doi
                match.data = md

    if preprint_doi != old_preprint_doi:
        if old_preprint_doi:
            old_match = db.query(models.Work).filter_by(
                user_id=user_id, doi=old_preprint_doi
            ).first()
            if old_match:
                od = dict(old_match.data or {})
                if od.get("published_doi") == work_doi:
                    od.pop("published_doi", None)
                    old_match.data = od
        if preprint_doi and work_doi:
            match = db.query(models.Work).filter_by(
                user_id=user_id, doi=preprint_doi
            ).first()
            if match:
                md = dict(match.data or {})
                md["published_doi"] = work_doi
                match.data = md


@router.get("", response_model=list[schemas.WorkOut])
def list_works(
    type: Optional[str] = None,
    year: Optional[int] = None,
    keyword: Optional[str] = None,
    select_only: bool = False,
    skip: int = 0,
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Work).filter_by(user_id=current_user.id)
    if type:
        q = q.filter(models.Work.work_type == type)
    if year:
        q = q.filter(models.Work.year == year)
    if select_only:
        q = q.filter(models.Work.data["select_flag"].as_boolean() == True)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            or_(
                models.Work.title.ilike(kw),
                models.Work.doi.ilike(kw),
                models.Work.data.ilike(kw),
                models.Work.authors.any(models.WorkAuthor.author_name.ilike(kw)),
            )
        )
    return q.order_by(models.Work.year.desc(), models.Work.id.desc()).offset(skip).limit(limit).all()


# Fixed-path routes must come before /{work_id}

@router.post("/doi-lookup", response_model=schemas.DOILookupResponse)
def doi_lookup(request: schemas.DOILookupRequest):
    try:
        result = lookup_doi(request.doi)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-check", response_model=schemas.SyncCheckResponse)
async def sync_check(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    profile = db.query(models.Profile).filter_by(user_id=current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found — add your name/ORCID first")
    return await fetch_new_publications(db, profile.name, profile.orcid)


@router.post("/sync-add", response_model=list[schemas.WorkOut])
def sync_add(
    request: schemas.SyncAddRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    created = []
    for candidate in request.publications:
        data = {}
        if candidate.journal:
            data["journal"] = candidate.journal
        if candidate.volume:
            data["volume"] = candidate.volume
        if candidate.issue:
            data["issue"] = candidate.issue
        if candidate.pages:
            data["pages"] = candidate.pages
        if candidate.preprint_doi:
            data["preprint_doi"] = candidate.preprint_doi
        if candidate.published_doi:
            data["published_doi"] = candidate.published_doi

        # Parse year string to integer
        year_int = None
        if candidate.year:
            import re
            m = re.search(r'\d{4}', candidate.year)
            if m:
                year_int = int(m.group())
            else:
                data["year_raw"] = candidate.year

        work = models.Work(
            work_type=candidate.pub_type,
            title=candidate.title,
            year=year_int,
            doi=candidate.doi,
            data=data,
            user_id=current_user.id,
        )
        db.add(work)
        db.flush()
        if candidate.authors_structured:
            for i, ad in enumerate(candidate.authors_structured):
                db.add(models.WorkAuthor(
                    work_id=work.id,
                    author_name=ad.get("name", ""),
                    author_order=i,
                    given_name=ad.get("given_name"),
                    family_name=ad.get("family_name"),
                    suffix=ad.get("suffix"),
                ))
        else:
            from app.services.name_parser import parse_author_name
            for i, name in enumerate(candidate.authors):
                parsed = parse_author_name(name)
                db.add(models.WorkAuthor(
                    work_id=work.id, author_name=name, author_order=i,
                    given_name=parsed.get("given_name"),
                    family_name=parsed.get("family_name"),
                    suffix=parsed.get("suffix"),
                ))
        _sync_crossref_links(work, db)
        created.append(work)
    db.commit()
    for work in created:
        db.refresh(work)
    return created


@router.get("/{work_id}", response_model=schemas.WorkOut)
def get_work(
    work_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    work = db.query(models.Work).filter_by(id=work_id, user_id=current_user.id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return work


@router.post("", response_model=schemas.WorkOut)
def create_work(
    payload: schemas.WorkCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    work = models.Work(
        **payload.model_dump(exclude={"authors"}),
        user_id=current_user.id,
    )
    db.add(work)
    db.flush()
    for i, a in enumerate(payload.authors):
        # Auto-parse structured name fields if not provided
        given = a.given_name
        family = a.family_name
        suffix = a.suffix
        if not family and a.author_name:
            from app.services.name_parser import parse_author_name
            parsed = parse_author_name(a.author_name)
            given = given or parsed.get("given_name")
            family = family or parsed.get("family_name")
            suffix = suffix or parsed.get("suffix")
        db.add(models.WorkAuthor(
            work_id=work.id,
            author_name=a.author_name,
            author_order=a.author_order or i,
            student=a.student,
            corresponding=a.corresponding,
            cofirst=a.cofirst,
            cosenior=a.cosenior,
            given_name=given,
            family_name=family,
            suffix=suffix,
        ))
    _sync_crossref_links(work, db)
    db.commit()
    db.refresh(work)
    return work


@router.put("/{work_id}", response_model=schemas.WorkOut)
def update_work(
    work_id: int,
    payload: schemas.WorkUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    work = db.query(models.Work).filter_by(id=work_id, user_id=current_user.id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")

    old_data = work.data or {}
    old_preprint_doi = old_data.get("preprint_doi")
    old_published_doi = old_data.get("published_doi")

    for field, value in payload.model_dump(exclude={"authors"}, exclude_unset=True).items():
        setattr(work, field, value)

    if payload.authors is not None:
        db.query(models.WorkAuthor).filter(models.WorkAuthor.work_id == work_id).delete()
        for i, a in enumerate(payload.authors):
            given = a.given_name
            family = a.family_name
            suffix = a.suffix
            if not family and a.author_name:
                from app.services.name_parser import parse_author_name
                parsed = parse_author_name(a.author_name)
                given = given or parsed.get("given_name")
                family = family or parsed.get("family_name")
                suffix = suffix or parsed.get("suffix")
            db.add(models.WorkAuthor(
                work_id=work_id,
                author_name=a.author_name,
                author_order=a.author_order or i,
                student=a.student,
                corresponding=a.corresponding,
                cofirst=a.cofirst,
                cosenior=a.cosenior,
                given_name=given,
                family_name=family,
                suffix=suffix,
            ))

    _sync_crossref_links(work, db, old_preprint_doi, old_published_doi)
    db.commit()
    db.refresh(work)
    return work


@router.delete("/{work_id}")
def delete_work(
    work_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    work = db.query(models.Work).filter_by(id=work_id, user_id=current_user.id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    # Clear reciprocal cross-ref links before deleting
    data = work.data or {}
    if data.get("published_doi") and work.doi:
        match = db.query(models.Work).filter_by(
            user_id=current_user.id, doi=data["published_doi"]
        ).first()
        if match:
            md = dict(match.data or {})
            if md.get("preprint_doi") == work.doi:
                md.pop("preprint_doi", None)
                match.data = md
    if data.get("preprint_doi") and work.doi:
        match = db.query(models.Work).filter_by(
            user_id=current_user.id, doi=data["preprint_doi"]
        ).first()
        if match:
            md = dict(match.data or {})
            if md.get("published_doi") == work.doi:
                md.pop("published_doi", None)
                match.data = md
    db.delete(work)
    db.commit()
    return {"ok": True}


@router.post("/{work_id}/enrich-authors")
def enrich_authors(
    work_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Enrich a work's authors with structured name data from CrossRef."""
    import httpx

    work = db.query(models.Work).filter_by(id=work_id, user_id=current_user.id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    if not work.doi:
        raise HTTPException(status_code=400, detail="Work has no DOI — cannot enrich")

    try:
        r = httpx.get(
            f"https://api.crossref.org/works/{work.doi}",
            timeout=15,
            headers={"User-Agent": "CVBuilder/1.0"},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="CrossRef lookup failed")
        cr_authors = r.json().get("message", {}).get("author", [])
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error: {e}")

    # Match CrossRef authors to existing WorkAuthors by order
    db_authors = sorted(work.authors, key=lambda a: a.author_order)
    updated = 0

    for i, cr_a in enumerate(cr_authors):
        family = cr_a.get("family", "")
        given = cr_a.get("given", "")
        if not family:
            continue

        if i < len(db_authors):
            wa = db_authors[i]
            wa.family_name = family
            wa.given_name = given or None
            wa.suffix = cr_a.get("suffix")
            updated += 1

    db.commit()
    return {"updated": updated, "total_crossref": len(cr_authors), "total_db": len(db_authors)}


@router.post("/enrich-authors-bulk")
def enrich_authors_bulk(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Bulk enrich all works with DOIs that lack structured author names."""
    import httpx
    import time

    works = db.query(models.Work).filter(
        models.Work.user_id == current_user.id,
        models.Work.doi.isnot(None),
    ).all()

    # Filter to works that have authors missing family_name
    to_enrich = []
    for w in works:
        if any(not a.family_name for a in w.authors):
            to_enrich.append(w)

    total_updated = 0
    errors = 0

    for w in to_enrich:
        try:
            r = httpx.get(
                f"https://api.crossref.org/works/{w.doi}",
                timeout=10,
                headers={"User-Agent": "CVBuilder/1.0"},
            )
            if r.status_code != 200:
                errors += 1
                continue
            cr_authors = r.json().get("message", {}).get("author", [])
            db_authors = sorted(w.authors, key=lambda a: a.author_order)

            for i, cr_a in enumerate(cr_authors):
                family = cr_a.get("family", "")
                given = cr_a.get("given", "")
                if not family or i >= len(db_authors):
                    continue
                wa = db_authors[i]
                if wa.family_name:
                    continue  # Already has structured name
                wa.family_name = family
                wa.given_name = given or None
                wa.suffix = cr_a.get("suffix")
                total_updated += 1

            # Rate limit: ~2 requests per second
            time.sleep(0.5)
        except Exception:
            errors += 1

    db.commit()
    return {
        "works_checked": len(to_enrich),
        "authors_updated": total_updated,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Complete missing fields via Crossref
# ---------------------------------------------------------------------------

@router.post("/complete-fields", response_model=schemas.CompleteFieldsResponse)
def complete_fields(
    req: schemas.CompleteFieldsRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Fetch Crossref metadata for the given works and return all differences.
    Read-only — no database writes.
    """
    import time

    works = (
        db.query(models.Work)
        .filter(models.Work.id.in_(req.work_ids), models.Work.user_id == current_user.id)
        .all()
    )

    diffs = []
    skipped_no_match = 0
    errors = 0

    has_doi = [w for w in works if w.doi]
    no_doi = [w for w in works if not w.doi]

    # Phase 1: DOI discovery for works without DOIs
    for work in no_doi:
        try:
            data = work.data or {}
            authors = sorted(work.authors, key=lambda a: a.author_order)
            first_author = authors[0].family_name if authors else None
            discovered_doi = search_doi_by_metadata(
                title=work.title or "",
                first_author=first_author,
                year=work.year,
                journal=data.get("journal"),
                volume=data.get("volume"),
                issue=data.get("issue"),
                pages=data.get("pages"),
            )
            if discovered_doi:
                # Fetch full metadata and compute diffs (DOI itself will be a diff)
                raw = lookup_doi_raw(discovered_doi)
                work_diffs = compute_work_diffs(work, raw)
                diffs.append(schemas.WorkDiff(
                    work_id=work.id,
                    title=work.title,
                    doi=None,
                    **work_diffs,
                ))
            else:
                skipped_no_match += 1
            time.sleep(0.5)
        except Exception:
            errors += 1

    # Phase 2: Field completion for works with DOIs
    for work in has_doi:
        try:
            raw = lookup_doi_raw(work.doi)
            work_diffs = compute_work_diffs(work, raw)

            # Only include works that have at least one diff
            has_diffs = (
                work_diffs["field_diffs"]
                or work_diffs["author_diffs"]
                or work_diffs["proposed_authors"]
                or work_diffs["additional_authors"]
            )
            if has_diffs:
                diffs.append(schemas.WorkDiff(
                    work_id=work.id,
                    title=work.title,
                    doi=work.doi,
                    **work_diffs,
                ))
            time.sleep(0.5)
        except Exception:
            errors += 1

    return schemas.CompleteFieldsResponse(
        diffs=diffs,
        skipped_no_match=skipped_no_match,
        errors=errors,
    )
