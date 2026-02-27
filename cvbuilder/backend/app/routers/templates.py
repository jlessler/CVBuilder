"""CV Template CRUD, preview, and PDF export endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, get_current_user_from_token_qs, get_optional_current_user
from app.services.sort import sort_items

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _build_cv_data(db: Session, user_id: int, sort_direction: str = "desc") -> dict:
    """Assemble all CV data for template rendering."""
    profile = db.query(models.Profile).filter_by(user_id=user_id).first()
    rev = sort_direction == "desc"

    def _user_query(model_class):
        return db.query(model_class).filter_by(user_id=user_id).all()

    def _misc_query(section_key):
        return db.query(models.MiscSection).filter(
            models.MiscSection.user_id == user_id,
            models.MiscSection.section == section_key,
        ).all()

    return {
        "profile": profile,
        "education": sort_items(_user_query(models.Education), models.Education, reverse=rev),
        "experience": sort_items(_user_query(models.Experience), models.Experience, reverse=rev),
        "consulting": sort_items(_user_query(models.Consulting), models.Consulting, reverse=rev),
        "memberships": sort_items(_user_query(models.Membership), models.Membership, reverse=rev),
        "panels": sort_items(_user_query(models.Panel), models.Panel, reverse=rev),
        "patents": sort_items(_user_query(models.Patent), models.Patent, reverse=rev),
        "symposia": sort_items(_user_query(models.Symposium), models.Symposium, reverse=rev),
        "classes": sort_items(_user_query(models.Class), models.Class, reverse=rev),
        "grants": sort_items(_user_query(models.Grant), models.Grant, reverse=rev),
        "awards": sort_items(_user_query(models.Award), models.Award, reverse=rev),
        "press": sort_items(_user_query(models.Press), models.Press, reverse=rev),
        "trainees": sort_items(_user_query(models.Trainee), models.Trainee, reverse=rev),
        "seminars": sort_items(_user_query(models.Seminar), models.Seminar, reverse=rev),
        "committees": sort_items(_user_query(models.Committee), models.Committee, reverse=rev),
        "editorial": sort_items(
            db.query(models.MiscSection).filter(
                models.MiscSection.user_id == user_id,
                models.MiscSection.section.in_(["editor", "assocedit", "otheredit"]),
            ).all(),
            models.MiscSection, reverse=rev,
        ),
        "peerrev": sort_items(_misc_query("peerrev"), models.MiscSection, reverse=rev),
        "software": sort_items(_misc_query("software"), models.MiscSection, reverse=rev),
        "policypres": sort_items(_misc_query("policypres"), models.MiscSection, reverse=rev),
        "policycons": sort_items(_misc_query("policycons"), models.MiscSection, reverse=rev),
        "otherservice": sort_items(_misc_query("otherservice"), models.MiscSection, reverse=rev),
        "dissertation": sort_items(_misc_query("dissertation"), models.MiscSection, reverse=rev),
        "chairedsessions": sort_items(_misc_query("chairedsessions"), models.MiscSection, reverse=rev),
        "otherpractice": sort_items(_misc_query("otherpractice"), models.MiscSection, reverse=rev),
        "departmentalOrals": sort_items(_misc_query("departmentalOrals"), models.MiscSection, reverse=rev),
        "finaldefense": sort_items(_misc_query("finaldefense"), models.MiscSection, reverse=rev),
        "schoolwideOrals": sort_items(_misc_query("schoolwideOrals"), models.MiscSection, reverse=rev),
        "publications": sort_items(
            db.query(models.Publication).filter_by(user_id=user_id).all(),
            models.Publication, reverse=rev,
        ),
    }


@router.get("", response_model=list[schemas.CVTemplateOut])
def list_templates(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.CVTemplate).filter_by(user_id=current_user.id).all()


@router.get("/{template_id}", response_model=schemas.CVTemplateOut)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tmpl = db.query(models.CVTemplate).filter_by(id=template_id, user_id=current_user.id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.post("", response_model=schemas.CVTemplateOut)
def create_template(
    data: schemas.CVTemplateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tmpl = models.CVTemplate(
        name=data.name, description=data.description, style=data.style,
        sort_direction=data.sort_direction, user_id=current_user.id,
    )
    db.add(tmpl)
    db.flush()
    for i, s in enumerate(data.sections):
        db.add(models.TemplateSection(
            template_id=tmpl.id,
            section_key=s.section_key,
            enabled=s.enabled,
            section_order=s.section_order or i,
            config=s.config,
        ))
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.put("/{template_id}", response_model=schemas.CVTemplateOut)
def update_template(
    template_id: int,
    data: schemas.CVTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tmpl = db.query(models.CVTemplate).filter_by(id=template_id, user_id=current_user.id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    tmpl.name = data.name
    tmpl.description = data.description
    tmpl.style = data.style
    tmpl.sort_direction = data.sort_direction
    if data.sections is not None:
        db.query(models.TemplateSection).filter(
            models.TemplateSection.template_id == template_id
        ).delete()
        for i, s in enumerate(data.sections):
            db.add(models.TemplateSection(
                template_id=template_id,
                section_key=s.section_key,
                enabled=s.enabled,
                section_order=s.section_order or i,
                config=s.config,
            ))
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tmpl = db.query(models.CVTemplate).filter_by(id=template_id, user_id=current_user.id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    # Prevent deletion if CV instances reference this template
    instance_count = db.query(models.CVInstance).filter_by(template_id=template_id).count()
    if instance_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete template: {instance_count} CV instance(s) reference it. Delete those first.",
        )
    db.delete(tmpl)
    db.commit()
    return {"ok": True}


@router.get("/{template_id}/preview", response_class=HTMLResponse)
def preview_template(
    template_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user),
):
    # Use the header-based user if available; fall back to ?token= query param
    user = current_user
    if user is None and token:
        user = get_current_user_from_token_qs(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    tmpl = db.query(models.CVTemplate).filter_by(id=template_id, user_id=user.id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    cv_data = _build_cv_data(db, user_id=user.id, sort_direction=tmpl.sort_direction)
    enabled_sections = [
        {"key": s.section_key, "config": s.config or {}}
        for s in tmpl.sections if s.enabled
    ]
    from app.services.pdf import render_cv_html
    html = render_cv_html(cv_data, style=tmpl.style, sections=enabled_sections)
    return HTMLResponse(content=html)


@router.post("/{template_id}/export/pdf")
def export_pdf(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tmpl = db.query(models.CVTemplate).filter_by(id=template_id, user_id=current_user.id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    cv_data = _build_cv_data(db, user_id=current_user.id, sort_direction=tmpl.sort_direction)
    enabled_sections = [
        {"key": s.section_key, "config": s.config or {}}
        for s in tmpl.sections if s.enabled
    ]
    from app.services.pdf import render_cv_html, html_to_pdf
    html = render_cv_html(cv_data, style=tmpl.style, sections=enabled_sections)
    pdf_bytes = html_to_pdf(html)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cv_{template_id}.pdf"'},
    )
