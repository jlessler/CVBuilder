"""Profile endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["profile"])


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("/profile", response_model=schemas.ProfileOut)
def get_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    profile = db.query(models.Profile).filter_by(user_id=current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/profile", response_model=schemas.ProfileOut)
def upsert_profile(
    data: schemas.ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    profile = db.query(models.Profile).filter_by(user_id=current_user.id).first()
    if not profile:
        profile = models.Profile(user_id=current_user.id)
        db.add(profile)
        db.flush()

    for field, value in data.model_dump(exclude={"addresses"}, exclude_none=True).items():
        setattr(profile, field, value)

    if data.addresses is not None:
        db.query(models.Address).filter(models.Address.profile_id == profile.id).delete()
        for addr in data.addresses:
            db.add(models.Address(profile_id=profile.id, **addr.model_dump()))

    db.commit()
    db.refresh(profile)
    return profile
