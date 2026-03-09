"""Profile and CV section endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.sort import sort_items

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


# ---------------------------------------------------------------------------
# Generic CRUD factory
# ---------------------------------------------------------------------------

def _list(model_class, db: Session, user_id: int):
    items = db.query(model_class).filter_by(user_id=user_id).all()
    return sort_items(items, model_class, reverse=True)


def _create(model_class, data, db: Session, user_id: int):
    item = model_class(**data.model_dump(), user_id=user_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _update(model_class, item_id: int, data, db: Session, user_id: int):
    item = db.query(model_class).filter_by(id=item_id, user_id=user_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def _delete(model_class, item_id: int, db: Session, user_id: int):
    item = db.query(model_class).filter_by(id=item_id, user_id=user_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------

@router.get("/education", response_model=list[schemas.EducationOut])
def list_education(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _list(models.Education, db, current_user.id)

@router.post("/education", response_model=schemas.EducationOut)
def create_education(data: schemas.EducationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Education, data, db, current_user.id)

@router.put("/education/{item_id}", response_model=schemas.EducationOut)
def update_education(item_id: int, data: schemas.EducationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Education, item_id, data, db, current_user.id)

@router.delete("/education/{item_id}")
def delete_education(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Education, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------

@router.get("/experience", response_model=list[schemas.ExperienceOut])
def list_experience(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _list(models.Experience, db, current_user.id)

@router.post("/experience", response_model=schemas.ExperienceOut)
def create_experience(data: schemas.ExperienceCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Experience, data, db, current_user.id)

@router.put("/experience/{item_id}", response_model=schemas.ExperienceOut)
def update_experience(item_id: int, data: schemas.ExperienceCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Experience, item_id, data, db, current_user.id)

@router.delete("/experience/{item_id}")
def delete_experience(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Experience, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Consulting
# ---------------------------------------------------------------------------

@router.get("/consulting", response_model=list[schemas.ConsultingOut])
def list_consulting(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _list(models.Consulting, db, current_user.id)

@router.post("/consulting", response_model=schemas.ConsultingOut)
def create_consulting(data: schemas.ConsultingCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Consulting, data, db, current_user.id)

@router.put("/consulting/{item_id}", response_model=schemas.ConsultingOut)
def update_consulting(item_id: int, data: schemas.ConsultingCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Consulting, item_id, data, db, current_user.id)

@router.delete("/consulting/{item_id}")
def delete_consulting(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Consulting, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Memberships
# ---------------------------------------------------------------------------

@router.get("/memberships", response_model=list[schemas.MembershipOut])
def list_memberships(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _list(models.Membership, db, current_user.id)

@router.post("/memberships", response_model=schemas.MembershipOut)
def create_membership(data: schemas.MembershipCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Membership, data, db, current_user.id)

@router.put("/memberships/{item_id}", response_model=schemas.MembershipOut)
def update_membership(item_id: int, data: schemas.MembershipCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Membership, item_id, data, db, current_user.id)

@router.delete("/memberships/{item_id}")
def delete_membership(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Membership, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

@router.get("/panels", response_model=list[schemas.PanelOut])
def list_panels(panel_type: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    q = db.query(models.Panel).filter_by(user_id=current_user.id)
    if panel_type:
        q = q.filter(models.Panel.type == panel_type)
    return sort_items(q.all(), models.Panel, reverse=True)

@router.post("/panels", response_model=schemas.PanelOut)
def create_panel(data: schemas.PanelCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Panel, data, db, current_user.id)

@router.put("/panels/{item_id}", response_model=schemas.PanelOut)
def update_panel(item_id: int, data: schemas.PanelCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Panel, item_id, data, db, current_user.id)

@router.delete("/panels/{item_id}")
def delete_panel(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Panel, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Symposia
# ---------------------------------------------------------------------------

@router.get("/symposia", response_model=list[schemas.SymposiumOut])
def list_symposia(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _list(models.Symposium, db, current_user.id)

@router.post("/symposia", response_model=schemas.SymposiumOut)
def create_symposium(data: schemas.SymposiumCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Symposium, data, db, current_user.id)

@router.put("/symposia/{item_id}", response_model=schemas.SymposiumOut)
def update_symposium(item_id: int, data: schemas.SymposiumCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Symposium, item_id, data, db, current_user.id)

@router.delete("/symposia/{item_id}")
def delete_symposium(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Symposium, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Classes (Teaching)
# ---------------------------------------------------------------------------

@router.get("/classes", response_model=list[schemas.ClassOut])
def list_classes(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _list(models.Class, db, current_user.id)

@router.post("/classes", response_model=schemas.ClassOut)
def create_class(data: schemas.ClassCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Class, data, db, current_user.id)

@router.put("/classes/{item_id}", response_model=schemas.ClassOut)
def update_class(item_id: int, data: schemas.ClassCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Class, item_id, data, db, current_user.id)

@router.delete("/classes/{item_id}")
def delete_class(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Class, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Grants
# ---------------------------------------------------------------------------

@router.get("/grants", response_model=list[schemas.GrantOut])
def list_grants(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _list(models.Grant, db, current_user.id)

@router.post("/grants", response_model=schemas.GrantOut)
def create_grant(data: schemas.GrantCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Grant, data, db, current_user.id)

@router.put("/grants/{item_id}", response_model=schemas.GrantOut)
def update_grant(item_id: int, data: schemas.GrantCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Grant, item_id, data, db, current_user.id)

@router.delete("/grants/{item_id}")
def delete_grant(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Grant, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Awards
# ---------------------------------------------------------------------------

@router.get("/awards", response_model=list[schemas.AwardOut])
def list_awards(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _list(models.Award, db, current_user.id)

@router.post("/awards", response_model=schemas.AwardOut)
def create_award(data: schemas.AwardCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Award, data, db, current_user.id)

@router.put("/awards/{item_id}", response_model=schemas.AwardOut)
def update_award(item_id: int, data: schemas.AwardCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Award, item_id, data, db, current_user.id)

@router.delete("/awards/{item_id}")
def delete_award(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Award, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Press
# ---------------------------------------------------------------------------

@router.get("/press", response_model=list[schemas.PressOut])
def list_press(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _list(models.Press, db, current_user.id)

@router.post("/press", response_model=schemas.PressOut)
def create_press(data: schemas.PressCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Press, data, db, current_user.id)

@router.put("/press/{item_id}", response_model=schemas.PressOut)
def update_press(item_id: int, data: schemas.PressCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Press, item_id, data, db, current_user.id)

@router.delete("/press/{item_id}")
def delete_press(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Press, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Trainees
# ---------------------------------------------------------------------------

@router.get("/trainees", response_model=list[schemas.TraineeOut])
def list_trainees(trainee_type: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    q = db.query(models.Trainee).filter_by(user_id=current_user.id)
    if trainee_type:
        q = q.filter(models.Trainee.trainee_type == trainee_type)
    return sort_items(q.all(), models.Trainee, reverse=True)

@router.post("/trainees", response_model=schemas.TraineeOut)
def create_trainee(data: schemas.TraineeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Trainee, data, db, current_user.id)

@router.put("/trainees/{item_id}", response_model=schemas.TraineeOut)
def update_trainee(item_id: int, data: schemas.TraineeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Trainee, item_id, data, db, current_user.id)

@router.delete("/trainees/{item_id}")
def delete_trainee(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Trainee, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Committees
# ---------------------------------------------------------------------------

@router.get("/committees", response_model=list[schemas.CommitteeOut])
def list_committees(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _list(models.Committee, db, current_user.id)

@router.post("/committees", response_model=schemas.CommitteeOut)
def create_committee(data: schemas.CommitteeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.Committee, data, db, current_user.id)

@router.put("/committees/{item_id}", response_model=schemas.CommitteeOut)
def update_committee(item_id: int, data: schemas.CommitteeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.Committee, item_id, data, db, current_user.id)

@router.delete("/committees/{item_id}")
def delete_committee(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.Committee, item_id, db, current_user.id)


# ---------------------------------------------------------------------------
# Misc sections
# ---------------------------------------------------------------------------

@router.get("/misc/editorial", response_model=list[schemas.MiscSectionOut])
def list_editorial(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Return all editorial entries (editor + assocedit + otheredit) combined."""
    items = db.query(models.MiscSection).filter(
        models.MiscSection.user_id == current_user.id,
        models.MiscSection.section.in_(["editor", "assocedit", "otheredit"]),
    ).all()
    return sort_items(items, models.MiscSection, reverse=True)

@router.get("/misc/{section}", response_model=list[schemas.MiscSectionOut])
def list_misc(section: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    items = db.query(models.MiscSection).filter(
        models.MiscSection.user_id == current_user.id,
        models.MiscSection.section == section,
    ).all()
    return sort_items(items, models.MiscSection, reverse=True)

@router.post("/misc", response_model=schemas.MiscSectionOut)
def create_misc(data: schemas.MiscSectionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _create(models.MiscSection, data, db, current_user.id)

@router.put("/misc/{item_id}", response_model=schemas.MiscSectionOut)
def update_misc(item_id: int, data: schemas.MiscSectionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _update(models.MiscSection, item_id, data, db, current_user.id)

@router.delete("/misc/{item_id}")
def delete_misc(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _delete(models.MiscSection, item_id, db, current_user.id)
