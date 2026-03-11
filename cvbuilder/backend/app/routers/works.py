"""Works CRUD + DOI lookup endpoints (unified scholarly outputs)."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.doi import lookup_doi
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
        for i, name in enumerate(candidate.authors):
            db.add(models.WorkAuthor(
                work_id=work.id, author_name=name, author_order=i,
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
        db.add(models.WorkAuthor(
            work_id=work.id,
            author_name=a.author_name,
            author_order=a.author_order or i,
            student=a.student,
            corresponding=a.corresponding,
            cofirst=a.cofirst,
            cosenior=a.cosenior,
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

    for field, value in payload.model_dump(exclude={"authors"}, exclude_none=True).items():
        setattr(work, field, value)

    if payload.authors is not None:
        db.query(models.WorkAuthor).filter(models.WorkAuthor.work_id == work_id).delete()
        for i, a in enumerate(payload.authors):
            db.add(models.WorkAuthor(
                work_id=work_id,
                author_name=a.author_name,
                author_order=a.author_order or i,
                student=a.student,
                corresponding=a.corresponding,
                cofirst=a.cofirst,
                cosenior=a.cosenior,
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
