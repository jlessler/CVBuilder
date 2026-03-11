"""Generic CRUD for CVItem — unified CV section data."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.sort import compute_sort_date

router = APIRouter(prefix="/api/cv", tags=["cv-items"])


@router.get("/{section}", response_model=list[schemas.CVItemOut])
def list_items(
    section: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    sections = [s.strip() for s in section.split(",")]
    q = db.query(models.CVItem).filter(models.CVItem.user_id == current_user.id)
    if len(sections) == 1:
        q = q.filter(models.CVItem.section == sections[0])
    else:
        q = q.filter(models.CVItem.section.in_(sections))
    return q.order_by(
        models.CVItem.sort_date.desc().nullslast(),
        models.CVItem.sort_order,
        models.CVItem.id,
    ).all()


@router.post("", response_model=schemas.CVItemOut)
def create_item(
    payload: schemas.CVItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = models.CVItem(
        user_id=current_user.id,
        section=payload.section,
        data=payload.data,
        sort_order=payload.sort_order,
        sort_date=compute_sort_date(payload.section, payload.data),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=schemas.CVItemOut)
def update_item(
    item_id: int,
    payload: schemas.CVItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = db.query(models.CVItem).filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if payload.data is not None:
        item.data = payload.data
        item.sort_date = compute_sort_date(item.section, payload.data)
    if payload.sort_order is not None:
        item.sort_order = payload.sort_order
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = db.query(models.CVItem).filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
