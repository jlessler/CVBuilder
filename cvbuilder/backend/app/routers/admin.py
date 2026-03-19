"""Admin endpoints for user management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_admin
from app.models import (
    User, Profile, Address, Work, WorkAuthor, CVItem,
    CVTemplate, TemplateSection, CVInstance, CVInstanceSection, CVInstanceItem,
    Publication, PubAuthor, MiscSection,
    Education, Experience, Consulting, Membership, Panel, Patent, PatentAuthor,
    Symposium, Class, Grant, Award, Press, Trainee, Seminar, Committee,
)
from app.schemas import UserOut, AdminUserUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).order_by(User.id).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: AdminUserUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Self-protection guards
    if target.id == admin.id:
        if body.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
        if body.is_admin is False:
            raise HTTPException(status_code=400, detail="Cannot remove your own admin privileges")

    if body.is_active is not None:
        target.is_active = body.is_active
    if body.is_admin is not None:
        target.is_admin = body.is_admin
    if body.full_name is not None:
        target.full_name = body.full_name

    db.commit()
    db.refresh(target)
    return target


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    uid = target.id

    # Delete CV instance items → sections → instances
    instance_ids = [i.id for i in db.query(CVInstance.id).filter_by(user_id=uid)]
    if instance_ids:
        section_ids = [
            s.id for s in db.query(CVInstanceSection.id).filter(
                CVInstanceSection.cv_instance_id.in_(instance_ids)
            )
        ]
        if section_ids:
            db.query(CVInstanceItem).filter(
                CVInstanceItem.cv_instance_section_id.in_(section_ids)
            ).delete(synchronize_session=False)
            db.query(CVInstanceSection).filter(
                CVInstanceSection.id.in_(section_ids)
            ).delete(synchronize_session=False)
        db.query(CVInstance).filter(CVInstance.id.in_(instance_ids)).delete(synchronize_session=False)

    # Delete template sections → templates
    tmpl_ids = [t.id for t in db.query(CVTemplate.id).filter_by(user_id=uid)]
    if tmpl_ids:
        db.query(TemplateSection).filter(TemplateSection.template_id.in_(tmpl_ids)).delete(synchronize_session=False)
        db.query(CVTemplate).filter(CVTemplate.id.in_(tmpl_ids)).delete(synchronize_session=False)

    # Delete work authors → works
    work_ids = [w.id for w in db.query(Work.id).filter_by(user_id=uid)]
    if work_ids:
        db.query(WorkAuthor).filter(WorkAuthor.work_id.in_(work_ids)).delete(synchronize_session=False)
        db.query(Work).filter(Work.id.in_(work_ids)).delete(synchronize_session=False)

    # Delete pub authors → publications (legacy)
    pub_ids = [p.id for p in db.query(Publication.id).filter_by(user_id=uid)]
    if pub_ids:
        db.query(PubAuthor).filter(PubAuthor.pub_id.in_(pub_ids)).delete(synchronize_session=False)
        db.query(Publication).filter(Publication.id.in_(pub_ids)).delete(synchronize_session=False)

    # Delete patent authors → patents
    patent_ids = [p.id for p in db.query(Patent.id).filter_by(user_id=uid)]
    if patent_ids:
        db.query(PatentAuthor).filter(PatentAuthor.patent_id.in_(patent_ids)).delete(synchronize_session=False)
        db.query(Patent).filter(Patent.id.in_(patent_ids)).delete(synchronize_session=False)

    # Delete profile addresses → profile
    profile_ids = [p.id for p in db.query(Profile.id).filter_by(user_id=uid)]
    if profile_ids:
        db.query(Address).filter(Address.profile_id.in_(profile_ids)).delete(synchronize_session=False)
        db.query(Profile).filter(Profile.id.in_(profile_ids)).delete(synchronize_session=False)

    # Delete remaining user-owned tables
    for model in [
        CVItem, MiscSection, Education, Experience, Consulting, Membership,
        Panel, Symposium, Class, Grant, Award, Press, Trainee, Seminar, Committee,
    ]:
        db.query(model).filter_by(user_id=uid).delete(synchronize_session=False)

    db.delete(target)
    db.commit()
