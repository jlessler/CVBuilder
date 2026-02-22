"""Profile and CV section endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api", tags=["profile"])


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("/profile", response_model=schemas.ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    profile = db.query(models.Profile).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/profile", response_model=schemas.ProfileOut)
def upsert_profile(data: schemas.ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(models.Profile).first()
    if not profile:
        profile = models.Profile()
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

def _list(model_class, db: Session):
    return db.query(model_class).order_by(model_class.sort_order).all()


def _create(model_class, data, db: Session):
    item = model_class(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _update(model_class, item_id: int, data, db: Session):
    item = db.get(model_class, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def _delete(model_class, item_id: int, db: Session):
    item = db.get(model_class, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------

@router.get("/education", response_model=list[schemas.EducationOut])
def list_education(db: Session = Depends(get_db)):
    return _list(models.Education, db)

@router.post("/education", response_model=schemas.EducationOut)
def create_education(data: schemas.EducationCreate, db: Session = Depends(get_db)):
    return _create(models.Education, data, db)

@router.put("/education/{item_id}", response_model=schemas.EducationOut)
def update_education(item_id: int, data: schemas.EducationCreate, db: Session = Depends(get_db)):
    return _update(models.Education, item_id, data, db)

@router.delete("/education/{item_id}")
def delete_education(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Education, item_id, db)


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------

@router.get("/experience", response_model=list[schemas.ExperienceOut])
def list_experience(db: Session = Depends(get_db)):
    return _list(models.Experience, db)

@router.post("/experience", response_model=schemas.ExperienceOut)
def create_experience(data: schemas.ExperienceCreate, db: Session = Depends(get_db)):
    return _create(models.Experience, data, db)

@router.put("/experience/{item_id}", response_model=schemas.ExperienceOut)
def update_experience(item_id: int, data: schemas.ExperienceCreate, db: Session = Depends(get_db)):
    return _update(models.Experience, item_id, data, db)

@router.delete("/experience/{item_id}")
def delete_experience(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Experience, item_id, db)


# ---------------------------------------------------------------------------
# Consulting
# ---------------------------------------------------------------------------

@router.get("/consulting", response_model=list[schemas.ConsultingOut])
def list_consulting(db: Session = Depends(get_db)):
    return _list(models.Consulting, db)

@router.post("/consulting", response_model=schemas.ConsultingOut)
def create_consulting(data: schemas.ConsultingCreate, db: Session = Depends(get_db)):
    return _create(models.Consulting, data, db)

@router.put("/consulting/{item_id}", response_model=schemas.ConsultingOut)
def update_consulting(item_id: int, data: schemas.ConsultingCreate, db: Session = Depends(get_db)):
    return _update(models.Consulting, item_id, data, db)

@router.delete("/consulting/{item_id}")
def delete_consulting(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Consulting, item_id, db)


# ---------------------------------------------------------------------------
# Memberships
# ---------------------------------------------------------------------------

@router.get("/memberships", response_model=list[schemas.MembershipOut])
def list_memberships(db: Session = Depends(get_db)):
    return _list(models.Membership, db)

@router.post("/memberships", response_model=schemas.MembershipOut)
def create_membership(data: schemas.MembershipCreate, db: Session = Depends(get_db)):
    return _create(models.Membership, data, db)

@router.put("/memberships/{item_id}", response_model=schemas.MembershipOut)
def update_membership(item_id: int, data: schemas.MembershipCreate, db: Session = Depends(get_db)):
    return _update(models.Membership, item_id, data, db)

@router.delete("/memberships/{item_id}")
def delete_membership(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Membership, item_id, db)


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

@router.get("/panels", response_model=list[schemas.PanelOut])
def list_panels(panel_type: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Panel).order_by(models.Panel.sort_order)
    if panel_type:
        q = q.filter(models.Panel.type == panel_type)
    return q.all()

@router.post("/panels", response_model=schemas.PanelOut)
def create_panel(data: schemas.PanelCreate, db: Session = Depends(get_db)):
    return _create(models.Panel, data, db)

@router.put("/panels/{item_id}", response_model=schemas.PanelOut)
def update_panel(item_id: int, data: schemas.PanelCreate, db: Session = Depends(get_db)):
    return _update(models.Panel, item_id, data, db)

@router.delete("/panels/{item_id}")
def delete_panel(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Panel, item_id, db)


# ---------------------------------------------------------------------------
# Patents
# ---------------------------------------------------------------------------

@router.get("/patents", response_model=list[schemas.PatentOut])
def list_patents(db: Session = Depends(get_db)):
    return _list(models.Patent, db)

@router.post("/patents", response_model=schemas.PatentOut)
def create_patent(data: schemas.PatentCreate, db: Session = Depends(get_db)):
    patent = models.Patent(
        name=data.name, number=data.number,
        status=data.status, sort_order=data.sort_order,
    )
    db.add(patent)
    db.flush()
    for i, a in enumerate(data.authors):
        db.add(models.PatentAuthor(patent_id=patent.id, author_name=a.author_name, author_order=a.author_order or i))
    db.commit()
    db.refresh(patent)
    return patent

@router.put("/patents/{item_id}", response_model=schemas.PatentOut)
def update_patent(item_id: int, data: schemas.PatentCreate, db: Session = Depends(get_db)):
    patent = db.get(models.Patent, item_id)
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")
    patent.name = data.name
    patent.number = data.number
    patent.status = data.status
    patent.sort_order = data.sort_order
    db.query(models.PatentAuthor).filter(models.PatentAuthor.patent_id == item_id).delete()
    for i, a in enumerate(data.authors):
        db.add(models.PatentAuthor(patent_id=item_id, author_name=a.author_name, author_order=a.author_order or i))
    db.commit()
    db.refresh(patent)
    return patent

@router.delete("/patents/{item_id}")
def delete_patent(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Patent, item_id, db)


# ---------------------------------------------------------------------------
# Symposia
# ---------------------------------------------------------------------------

@router.get("/symposia", response_model=list[schemas.SymposiumOut])
def list_symposia(db: Session = Depends(get_db)):
    return _list(models.Symposium, db)

@router.post("/symposia", response_model=schemas.SymposiumOut)
def create_symposium(data: schemas.SymposiumCreate, db: Session = Depends(get_db)):
    return _create(models.Symposium, data, db)

@router.put("/symposia/{item_id}", response_model=schemas.SymposiumOut)
def update_symposium(item_id: int, data: schemas.SymposiumCreate, db: Session = Depends(get_db)):
    return _update(models.Symposium, item_id, data, db)

@router.delete("/symposia/{item_id}")
def delete_symposium(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Symposium, item_id, db)


# ---------------------------------------------------------------------------
# Classes (Teaching)
# ---------------------------------------------------------------------------

@router.get("/classes", response_model=list[schemas.ClassOut])
def list_classes(db: Session = Depends(get_db)):
    return _list(models.Class, db)

@router.post("/classes", response_model=schemas.ClassOut)
def create_class(data: schemas.ClassCreate, db: Session = Depends(get_db)):
    return _create(models.Class, data, db)

@router.put("/classes/{item_id}", response_model=schemas.ClassOut)
def update_class(item_id: int, data: schemas.ClassCreate, db: Session = Depends(get_db)):
    return _update(models.Class, item_id, data, db)

@router.delete("/classes/{item_id}")
def delete_class(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Class, item_id, db)


# ---------------------------------------------------------------------------
# Grants
# ---------------------------------------------------------------------------

@router.get("/grants", response_model=list[schemas.GrantOut])
def list_grants(db: Session = Depends(get_db)):
    return _list(models.Grant, db)

@router.post("/grants", response_model=schemas.GrantOut)
def create_grant(data: schemas.GrantCreate, db: Session = Depends(get_db)):
    return _create(models.Grant, data, db)

@router.put("/grants/{item_id}", response_model=schemas.GrantOut)
def update_grant(item_id: int, data: schemas.GrantCreate, db: Session = Depends(get_db)):
    return _update(models.Grant, item_id, data, db)

@router.delete("/grants/{item_id}")
def delete_grant(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Grant, item_id, db)


# ---------------------------------------------------------------------------
# Awards
# ---------------------------------------------------------------------------

@router.get("/awards", response_model=list[schemas.AwardOut])
def list_awards(db: Session = Depends(get_db)):
    return _list(models.Award, db)

@router.post("/awards", response_model=schemas.AwardOut)
def create_award(data: schemas.AwardCreate, db: Session = Depends(get_db)):
    return _create(models.Award, data, db)

@router.put("/awards/{item_id}", response_model=schemas.AwardOut)
def update_award(item_id: int, data: schemas.AwardCreate, db: Session = Depends(get_db)):
    return _update(models.Award, item_id, data, db)

@router.delete("/awards/{item_id}")
def delete_award(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Award, item_id, db)


# ---------------------------------------------------------------------------
# Press
# ---------------------------------------------------------------------------

@router.get("/press", response_model=list[schemas.PressOut])
def list_press(db: Session = Depends(get_db)):
    return _list(models.Press, db)

@router.post("/press", response_model=schemas.PressOut)
def create_press(data: schemas.PressCreate, db: Session = Depends(get_db)):
    return _create(models.Press, data, db)

@router.put("/press/{item_id}", response_model=schemas.PressOut)
def update_press(item_id: int, data: schemas.PressCreate, db: Session = Depends(get_db)):
    return _update(models.Press, item_id, data, db)

@router.delete("/press/{item_id}")
def delete_press(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Press, item_id, db)


# ---------------------------------------------------------------------------
# Trainees
# ---------------------------------------------------------------------------

@router.get("/trainees", response_model=list[schemas.TraineeOut])
def list_trainees(trainee_type: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Trainee).order_by(models.Trainee.sort_order)
    if trainee_type:
        q = q.filter(models.Trainee.trainee_type == trainee_type)
    return q.all()

@router.post("/trainees", response_model=schemas.TraineeOut)
def create_trainee(data: schemas.TraineeCreate, db: Session = Depends(get_db)):
    return _create(models.Trainee, data, db)

@router.put("/trainees/{item_id}", response_model=schemas.TraineeOut)
def update_trainee(item_id: int, data: schemas.TraineeCreate, db: Session = Depends(get_db)):
    return _update(models.Trainee, item_id, data, db)

@router.delete("/trainees/{item_id}")
def delete_trainee(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Trainee, item_id, db)


# ---------------------------------------------------------------------------
# Seminars
# ---------------------------------------------------------------------------

@router.get("/seminars", response_model=list[schemas.SeminarOut])
def list_seminars(db: Session = Depends(get_db)):
    return _list(models.Seminar, db)

@router.post("/seminars", response_model=schemas.SeminarOut)
def create_seminar(data: schemas.SeminarCreate, db: Session = Depends(get_db)):
    return _create(models.Seminar, data, db)

@router.put("/seminars/{item_id}", response_model=schemas.SeminarOut)
def update_seminar(item_id: int, data: schemas.SeminarCreate, db: Session = Depends(get_db)):
    return _update(models.Seminar, item_id, data, db)

@router.delete("/seminars/{item_id}")
def delete_seminar(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Seminar, item_id, db)


# ---------------------------------------------------------------------------
# Committees
# ---------------------------------------------------------------------------

@router.get("/committees", response_model=list[schemas.CommitteeOut])
def list_committees(db: Session = Depends(get_db)):
    return _list(models.Committee, db)

@router.post("/committees", response_model=schemas.CommitteeOut)
def create_committee(data: schemas.CommitteeCreate, db: Session = Depends(get_db)):
    return _create(models.Committee, data, db)

@router.put("/committees/{item_id}", response_model=schemas.CommitteeOut)
def update_committee(item_id: int, data: schemas.CommitteeCreate, db: Session = Depends(get_db)):
    return _update(models.Committee, item_id, data, db)

@router.delete("/committees/{item_id}")
def delete_committee(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.Committee, item_id, db)


# ---------------------------------------------------------------------------
# Misc sections
# ---------------------------------------------------------------------------

@router.get("/misc/editorial", response_model=list[schemas.MiscSectionOut])
def list_editorial(db: Session = Depends(get_db)):
    """Return all editorial entries (editor + assocedit + otheredit) combined."""
    return db.query(models.MiscSection).filter(
        models.MiscSection.section.in_(["editor", "assocedit", "otheredit"])
    ).order_by(models.MiscSection.sort_order).all()

@router.get("/misc/{section}", response_model=list[schemas.MiscSectionOut])
def list_misc(section: str, db: Session = Depends(get_db)):
    return db.query(models.MiscSection).filter(
        models.MiscSection.section == section
    ).order_by(models.MiscSection.sort_order).all()

@router.post("/misc", response_model=schemas.MiscSectionOut)
def create_misc(data: schemas.MiscSectionCreate, db: Session = Depends(get_db)):
    return _create(models.MiscSection, data, db)

@router.put("/misc/{item_id}", response_model=schemas.MiscSectionOut)
def update_misc(item_id: int, data: schemas.MiscSectionCreate, db: Session = Depends(get_db)):
    return _update(models.MiscSection, item_id, data, db)

@router.delete("/misc/{item_id}")
def delete_misc(item_id: int, db: Session = Depends(get_db)):
    return _delete(models.MiscSection, item_id, db)
