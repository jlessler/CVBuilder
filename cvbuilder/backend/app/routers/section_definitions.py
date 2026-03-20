"""CRUD endpoints for custom user-defined section types."""
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/section-definitions", tags=["section-definitions"])


def _slugify(label: str) -> str:
    """Convert a label to a URL-safe slug for use as section_key."""
    slug = re.sub(r'[^a-z0-9]+', '_', label.lower().strip()).strip('_')
    return f"custom_{slug}"


@router.get("", response_model=list[schemas.SectionDefinitionOut])
def list_section_definitions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.SectionDefinition)
        .filter_by(user_id=current_user.id)
        .order_by(models.SectionDefinition.created_at)
        .all()
    )


@router.post("", response_model=schemas.SectionDefinitionOut, status_code=201)
def create_section_definition(
    data: schemas.SectionDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    section_key = _slugify(data.label)
    # Ensure uniqueness for this user
    existing = (
        db.query(models.SectionDefinition)
        .filter_by(user_id=current_user.id, section_key=section_key)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Section key '{section_key}' already exists")

    defn = models.SectionDefinition(
        user_id=current_user.id,
        section_key=section_key,
        label=data.label,
        layout=data.layout,
        fields=[f.model_dump() for f in data.fields],
        sort_field=data.sort_field,
    )
    db.add(defn)
    db.commit()
    db.refresh(defn)
    return defn


@router.put("/{defn_id}", response_model=schemas.SectionDefinitionOut)
def update_section_definition(
    defn_id: int,
    data: schemas.SectionDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    defn = (
        db.query(models.SectionDefinition)
        .filter_by(id=defn_id, user_id=current_user.id)
        .first()
    )
    if not defn:
        raise HTTPException(status_code=404, detail="Section definition not found")

    defn.label = data.label
    defn.layout = data.layout
    defn.fields = [f.model_dump() for f in data.fields]
    defn.sort_field = data.sort_field
    db.commit()
    db.refresh(defn)
    return defn


@router.delete("/{defn_id}", status_code=204)
def delete_section_definition(
    defn_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    defn = (
        db.query(models.SectionDefinition)
        .filter_by(id=defn_id, user_id=current_user.id)
        .first()
    )
    if not defn:
        raise HTTPException(status_code=404, detail="Section definition not found")

    # Check for existing CVItems using this section_key
    item_count = (
        db.query(models.CVItem)
        .filter_by(user_id=current_user.id, section=defn.section_key)
        .count()
    )
    if item_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {item_count} item(s) exist for this section. Delete them first.",
        )

    db.delete(defn)
    db.commit()
