"""Publications CRUD + DOI lookup endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services.doi import lookup_doi
from app.services.fetch_pubs import fetch_new_publications

router = APIRouter(prefix="/api/publications", tags=["publications"])


@router.get("", response_model=list[schemas.PublicationOut])
def list_publications(
    type: Optional[str] = None,
    year: Optional[str] = None,
    keyword: Optional[str] = None,
    select_only: bool = False,
    skip: int = 0,
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db),
):
    q = db.query(models.Publication)
    if type:
        q = q.filter(models.Publication.type == type)
    if year:
        q = q.filter(models.Publication.year == year)
    if select_only:
        q = q.filter(models.Publication.select_flag == True)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            models.Publication.title.ilike(kw) |
            models.Publication.journal.ilike(kw)
        )
    return q.order_by(models.Publication.year.desc(), models.Publication.id.desc()).offset(skip).limit(limit).all()


# Fixed-path routes must come before /{pub_id} to avoid being swallowed by it

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
async def sync_check(db: Session = Depends(get_db)):
    profile = db.query(models.Profile).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found — add your name/ORCID first")
    return await fetch_new_publications(db, profile.name, profile.orcid)


@router.post("/sync-add", response_model=list[schemas.PublicationOut])
def sync_add(request: schemas.SyncAddRequest, db: Session = Depends(get_db)):
    created = []
    for candidate in request.publications:
        pub = models.Publication(
            type=candidate.pub_type,
            title=candidate.title,
            year=candidate.year,
            journal=candidate.journal,
            volume=candidate.volume,
            issue=candidate.issue,
            pages=candidate.pages,
            doi=candidate.doi,
        )
        db.add(pub)
        db.flush()
        for i, name in enumerate(candidate.authors):
            db.add(models.PubAuthor(pub_id=pub.id, author_name=name, author_order=i, student=False))
        created.append(pub)
    db.commit()
    for pub in created:
        db.refresh(pub)
    return created


@router.get("/{pub_id}", response_model=schemas.PublicationOut)
def get_publication(pub_id: int, db: Session = Depends(get_db)):
    pub = db.get(models.Publication, pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    return pub


@router.post("", response_model=schemas.PublicationOut)
def create_publication(data: schemas.PublicationCreate, db: Session = Depends(get_db)):
    pub = models.Publication(**data.model_dump(exclude={"authors"}))
    db.add(pub)
    db.flush()
    for i, a in enumerate(data.authors):
        db.add(models.PubAuthor(pub_id=pub.id, author_name=a.author_name, author_order=a.author_order or i))
    db.commit()
    db.refresh(pub)
    return pub


@router.put("/{pub_id}", response_model=schemas.PublicationOut)
def update_publication(pub_id: int, data: schemas.PublicationUpdate, db: Session = Depends(get_db)):
    pub = db.get(models.Publication, pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")

    for field, value in data.model_dump(exclude={"authors"}, exclude_none=True).items():
        setattr(pub, field, value)

    if data.authors is not None:
        db.query(models.PubAuthor).filter(models.PubAuthor.pub_id == pub_id).delete()
        for i, a in enumerate(data.authors):
            db.add(models.PubAuthor(pub_id=pub_id, author_name=a.author_name, author_order=a.author_order or i))

    db.commit()
    db.refresh(pub)
    return pub


@router.delete("/{pub_id}")
def delete_publication(pub_id: int, db: Session = Depends(get_db)):
    pub = db.get(models.Publication, pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    db.delete(pub)
    db.commit()
    return {"ok": True}
