"""CV Template CRUD, preview, and PDF export endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services.sort import sort_items

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _build_cv_data(db: Session, sort_direction: str = "desc") -> dict:
    """Assemble all CV data for template rendering."""
    profile = db.query(models.Profile).first()
    rev = sort_direction == "desc"
    return {
        "profile": profile,
        "education": sort_items(db.query(models.Education).all(), models.Education, reverse=rev),
        "experience": sort_items(db.query(models.Experience).all(), models.Experience, reverse=rev),
        "consulting": sort_items(db.query(models.Consulting).all(), models.Consulting, reverse=rev),
        "memberships": sort_items(db.query(models.Membership).all(), models.Membership, reverse=rev),
        "panels": sort_items(db.query(models.Panel).all(), models.Panel, reverse=rev),
        "patents": sort_items(db.query(models.Patent).all(), models.Patent, reverse=rev),
        "symposia": sort_items(db.query(models.Symposium).all(), models.Symposium, reverse=rev),
        "classes": sort_items(db.query(models.Class).all(), models.Class, reverse=rev),
        "grants": sort_items(db.query(models.Grant).all(), models.Grant, reverse=rev),
        "awards": sort_items(db.query(models.Award).all(), models.Award, reverse=rev),
        "press": sort_items(db.query(models.Press).all(), models.Press, reverse=rev),
        "trainees": sort_items(db.query(models.Trainee).all(), models.Trainee, reverse=rev),
        "seminars": sort_items(db.query(models.Seminar).all(), models.Seminar, reverse=rev),
        "committees": sort_items(db.query(models.Committee).all(), models.Committee, reverse=rev),
        "editorial": sort_items(
            db.query(models.MiscSection).filter(
                models.MiscSection.section.in_(["editor", "assocedit", "otheredit"])
            ).all(),
            models.MiscSection, reverse=rev,
        ),
        "peerrev": sort_items(
            db.query(models.MiscSection).filter(
                models.MiscSection.section == "peerrev"
            ).all(),
            models.MiscSection, reverse=rev,
        ),
        "software": sort_items(
            db.query(models.MiscSection).filter(
                models.MiscSection.section == "software"
            ).all(),
            models.MiscSection, reverse=rev,
        ),
        "policypres": sort_items(
            db.query(models.MiscSection).filter(
                models.MiscSection.section == "policypres"
            ).all(),
            models.MiscSection, reverse=rev,
        ),
        "policycons": sort_items(
            db.query(models.MiscSection).filter(
                models.MiscSection.section == "policycons"
            ).all(),
            models.MiscSection, reverse=rev,
        ),
        "otherservice": sort_items(
            db.query(models.MiscSection).filter(
                models.MiscSection.section == "otherservice"
            ).all(),
            models.MiscSection, reverse=rev,
        ),
        "dissertation": db.query(models.MiscSection).filter(
            models.MiscSection.section == "dissertation"
        ).order_by(models.MiscSection.id.desc()).all(),
        "chairedsessions": db.query(models.MiscSection).filter(
            models.MiscSection.section == "chairedsessions"
        ).order_by(models.MiscSection.id.desc()).all(),
        "otherpractice": db.query(models.MiscSection).filter(
            models.MiscSection.section == "otherpractice"
        ).order_by(models.MiscSection.id.desc()).all(),
        "publications": sort_items(db.query(models.Publication).all(), models.Publication, reverse=rev),
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
        name=data.name, description=data.description, theme_css=data.theme_css,
        sort_direction=data.sort_direction,
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
    cv_data = _build_cv_data(db, sort_direction=tmpl.sort_direction)
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
    cv_data = _build_cv_data(db, sort_direction=tmpl.sort_direction)
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
