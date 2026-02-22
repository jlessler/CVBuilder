"""CV Template CRUD, preview, and PDF export endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _build_cv_data(db: Session) -> dict:
    """Assemble all CV data for template rendering."""
    profile = db.query(models.Profile).first()
    return {
        "profile": profile,
        "education": db.query(models.Education).order_by(models.Education.sort_order).all(),
        "experience": db.query(models.Experience).order_by(models.Experience.sort_order).all(),
        "consulting": db.query(models.Consulting).order_by(models.Consulting.sort_order).all(),
        "memberships": db.query(models.Membership).order_by(models.Membership.sort_order).all(),
        "panels": db.query(models.Panel).order_by(models.Panel.sort_order).all(),
        "patents": db.query(models.Patent).order_by(models.Patent.sort_order).all(),
        "symposia": db.query(models.Symposium).order_by(models.Symposium.sort_order).all(),
        "classes": db.query(models.Class).order_by(models.Class.sort_order).all(),
        "grants": db.query(models.Grant).order_by(models.Grant.sort_order).all(),
        "awards": db.query(models.Award).order_by(models.Award.sort_order).all(),
        "press": db.query(models.Press).order_by(models.Press.sort_order).all(),
        "trainees": db.query(models.Trainee).order_by(models.Trainee.sort_order).all(),
        "seminars": db.query(models.Seminar).order_by(models.Seminar.sort_order).all(),
        "committees": db.query(models.Committee).order_by(models.Committee.sort_order).all(),
        "editorial": db.query(models.MiscSection).filter(
            models.MiscSection.section.in_(["editor", "assocedit", "otheredit"])
        ).order_by(models.MiscSection.sort_order).all(),
        "peerrev": db.query(models.MiscSection).filter(
            models.MiscSection.section == "peerrev"
        ).order_by(models.MiscSection.sort_order).all(),
        "publications": db.query(models.Publication).order_by(
            models.Publication.year.desc(), models.Publication.id.desc()
        ).all(),
    }


@router.get("", response_model=list[schemas.CVTemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return db.query(models.CVTemplate).all()


@router.get("/{template_id}", response_model=schemas.CVTemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db)):
    tmpl = db.get(models.CVTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.post("", response_model=schemas.CVTemplateOut)
def create_template(data: schemas.CVTemplateCreate, db: Session = Depends(get_db)):
    tmpl = models.CVTemplate(
        name=data.name, description=data.description, theme_css=data.theme_css
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
def update_template(template_id: int, data: schemas.CVTemplateUpdate, db: Session = Depends(get_db)):
    tmpl = db.get(models.CVTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    tmpl.name = data.name
    tmpl.description = data.description
    tmpl.theme_css = data.theme_css
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
def delete_template(template_id: int, db: Session = Depends(get_db)):
    tmpl = db.get(models.CVTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tmpl)
    db.commit()
    return {"ok": True}


@router.get("/{template_id}/preview", response_class=HTMLResponse)
def preview_template(template_id: int, db: Session = Depends(get_db)):
    tmpl = db.get(models.CVTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    cv_data = _build_cv_data(db)
    enabled_sections = [
        {"key": s.section_key, "config": s.config or {}}
        for s in tmpl.sections if s.enabled
    ]
    from app.services.pdf import render_cv_html
    html = render_cv_html(cv_data, theme=tmpl.theme_css, sections=enabled_sections)
    return HTMLResponse(content=html)


@router.post("/{template_id}/export/pdf")
def export_pdf(template_id: int, db: Session = Depends(get_db)):
    tmpl = db.get(models.CVTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    cv_data = _build_cv_data(db)
    enabled_sections = [
        {"key": s.section_key, "config": s.config or {}}
        for s in tmpl.sections if s.enabled
    ]
    from app.services.pdf import render_cv_html, html_to_pdf
    html = render_cv_html(cv_data, theme=tmpl.theme_css, sections=enabled_sections)
    pdf_bytes = html_to_pdf(html)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cv_{template_id}.pdf"'},
    )
