"""CV Template CRUD, preview, PDF export, copy, and YAML export endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, get_current_user_from_token_qs, get_optional_current_user
from app.services.sort import sort_items

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _get_template(db: Session, template_id: int, user_id: int) -> models.CVTemplate:
    """Fetch a template visible to this user (owned or system)."""
    tmpl = db.query(models.CVTemplate).filter(
        models.CVTemplate.id == template_id,
        or_(models.CVTemplate.user_id == user_id, models.CVTemplate.user_id.is_(None)),
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


def _serialize_template(tmpl: models.CVTemplate) -> schemas.CVTemplateOut:
    """Convert a CVTemplate model to the output schema, setting is_system."""
    out = schemas.CVTemplateOut.model_validate(tmpl)
    out.is_system = tmpl.user_id is None
    return out


def _build_cv_data(db: Session, user_id: int, sort_direction: str = "desc") -> dict:
    """Assemble all CV data for template rendering."""
    profile = db.query(models.Profile).filter_by(user_id=user_id).first()
    rev = sort_direction == "desc"

    def _cv_query(section):
        return sort_items(
            db.query(models.CVItem).filter_by(user_id=user_id, section=section).all(),
            models.CVItem, reverse=rev,
        )

    def _cv_query_multi(sections):
        return sort_items(
            db.query(models.CVItem).filter(
                models.CVItem.user_id == user_id,
                models.CVItem.section.in_(sections),
            ).all(),
            models.CVItem, reverse=rev,
        )

    def _works_query(work_type):
        return db.query(models.Work).filter_by(user_id=user_id, work_type=work_type).all()

    _PUB_TYPES = ["papers", "preprints", "chapters", "letters", "scimeetings", "editorials"]

    cv_data = {
        "profile": profile,
        "education": _cv_query("education"),
        "experience": _cv_query("experience"),
        "consulting": _cv_query("consulting"),
        "memberships": _cv_query("memberships"),
        "panels": _cv_query_multi(["panels_advisory", "panels_grantreview"]),
        "patents": sort_items(_works_query("patents"), models.Work, reverse=rev),
        "symposia": _cv_query("symposia"),
        "classes": _cv_query("classes"),
        "grants": _cv_query("grants"),
        "awards": _cv_query("awards"),
        "press": _cv_query("press"),
        "trainees": _cv_query_multi(["trainees_advisees", "trainees_postdocs"]),
        "mentorship": _cv_query("mentorship"),
        "seminars": sort_items(_works_query("seminars"), models.Work, reverse=rev),
        "committees": _cv_query("committees"),
        "editorial": _cv_query_multi(["editor", "assocedit", "otheredit"]),
        "peerrev": _cv_query("peerrev"),
        "software": sort_items(_works_query("software"), models.Work, reverse=rev),
        "policypres": _cv_query("policypres"),
        "policycons": _cv_query("policycons"),
        "otherservice": _cv_query("otherservice"),
        "dissertation": sort_items(_works_query("dissertation"), models.Work, reverse=rev),
        "chairedsessions": _cv_query("chairedsessions"),
        "otherpractice": _cv_query("otherpractice"),
        "departmentalOrals": _cv_query("departmentalOrals"),
        "finaldefense": _cv_query("finaldefense"),
        "schoolwideOrals": _cv_query("schoolwideOrals"),
        "citation_metrics": db.query(models.CVItem).filter_by(
            user_id=user_id, section="citation_metrics"
        ).all(),
        "publications": sort_items(
            db.query(models.Work).filter(
                models.Work.user_id == user_id,
                models.Work.work_type.in_(_PUB_TYPES),
            ).all(),
            models.Work, reverse=rev,
        ),
    }

    # Add custom section definitions and their data
    custom_defs = db.query(models.SectionDefinition).filter_by(user_id=user_id).all()
    section_defs = {}
    for defn in custom_defs:
        section_defs[defn.section_key] = {
            "label": defn.label,
            "layout": defn.layout,
            "fields": defn.fields or [],
            "sort_field": defn.sort_field,
        }
        cv_data[defn.section_key] = sort_items(
            db.query(models.CVItem).filter_by(user_id=user_id, section=defn.section_key).all(),
            models.CVItem, reverse=rev,
        )
    cv_data["_section_defs"] = section_defs

    return cv_data


@router.get("", response_model=list[schemas.CVTemplateOut])
def list_templates(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tmpls = db.query(models.CVTemplate).filter(
        or_(models.CVTemplate.user_id == current_user.id, models.CVTemplate.user_id.is_(None))
    ).all()
    return [_serialize_template(t) for t in tmpls]


@router.get("/{template_id}", response_model=schemas.CVTemplateOut)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tmpl = _get_template(db, template_id, current_user.id)
    return _serialize_template(tmpl)


@router.post("", response_model=schemas.CVTemplateOut)
def create_template(
    data: schemas.CVTemplateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tmpl = models.CVTemplate(
        name=data.name, description=data.description, style=data.style,
        sort_direction=data.sort_direction, user_id=current_user.id,
        author=data.author, author_contact=data.author_contact,
        guidance_url=data.guidance_url,
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
            depth=s.depth,
        ))
    db.commit()
    db.refresh(tmpl)
    return _serialize_template(tmpl)


@router.post("/import-definition", response_model=schemas.CVTemplateOut)
def import_template_definition(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Import a template from a YAML definition file."""
    from app.main import parse_template_yaml, _HEADINGS
    from app.services.pdf import THEME_PRESETS

    content = file.file.read().decode("utf-8")
    parsed = parse_template_yaml(content)
    if not parsed:
        raise HTTPException(status_code=400, detail="Invalid template YAML: missing 'name' field")

    # Resolve preset to style dict
    preset_name = parsed["preset"]
    style = THEME_PRESETS.get(preset_name, THEME_PRESETS.get("academic", {}))

    # Look up valid section keys (built-in + user's custom definitions)
    custom_keys = {
        d.section_key
        for d in db.query(models.SectionDefinition).filter_by(user_id=current_user.id).all()
    }
    valid_keys = set(_HEADINGS.keys()) | custom_keys | {"group_heading"}

    # Filter sections, skipping unknown keys
    valid_sections = []
    skipped = []
    for key, config, depth in parsed["sections"]:
        if key in valid_keys:
            valid_sections.append((key, config, depth))
        else:
            skipped.append(key)

    meta = parsed["metadata"]
    tmpl = models.CVTemplate(
        name=parsed["name"],
        description=parsed["description"],
        style=style,
        sort_direction="desc",
        user_id=current_user.id,
        author=meta.get("author") or None,
        author_contact=meta.get("author_contact") or None,
        guidance_url=meta.get("guidance_url") or None,
    )
    db.add(tmpl)
    db.flush()

    for i, (key, config, depth) in enumerate(valid_sections):
        if key != "group_heading" and config is None:
            heading = _HEADINGS.get(key, key)
            config = {"heading": heading}
        db.add(models.TemplateSection(
            template_id=tmpl.id,
            section_key=key,
            enabled=True,
            section_order=i,
            config=config,
            depth=depth,
        ))

    db.commit()
    db.refresh(tmpl)
    return _serialize_template(tmpl)


@router.put("/{template_id}", response_model=schemas.CVTemplateOut)
def update_template(
    template_id: int,
    data: schemas.CVTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tmpl = _get_template(db, template_id, current_user.id)
    if tmpl.user_id is None:
        raise HTTPException(status_code=403, detail="System templates cannot be edited")
    if tmpl.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Template not found")
    tmpl.name = data.name
    tmpl.description = data.description
    tmpl.style = data.style
    tmpl.sort_direction = data.sort_direction
    tmpl.author = data.author
    tmpl.author_contact = data.author_contact
    tmpl.guidance_url = data.guidance_url
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
                depth=s.depth,
            ))
    db.commit()
    db.refresh(tmpl)
    return _serialize_template(tmpl)


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tmpl = _get_template(db, template_id, current_user.id)
    if tmpl.user_id is None:
        raise HTTPException(status_code=403, detail="System templates cannot be deleted")
    if tmpl.user_id != current_user.id:
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


@router.post("/{template_id}/copy", response_model=schemas.CVTemplateOut)
def copy_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Copy any template (system or user-owned) to a new user-owned template."""
    source = _get_template(db, template_id, current_user.id)
    new_tmpl = models.CVTemplate(
        name=f"{source.name} (Copy)",
        description=source.description,
        style=source.style,
        sort_direction=source.sort_direction,
        user_id=current_user.id,
        author=source.author,
        author_contact=source.author_contact,
        guidance_url=source.guidance_url,
    )
    db.add(new_tmpl)
    db.flush()
    for s in source.sections:
        db.add(models.TemplateSection(
            template_id=new_tmpl.id,
            section_key=s.section_key,
            enabled=s.enabled,
            section_order=s.section_order,
            config=s.config,
            depth=s.depth,
        ))
    db.commit()
    db.refresh(new_tmpl)
    return _serialize_template(new_tmpl)


@router.get("/{template_id}/export-definition")
def export_template_definition(
    template_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user),
):
    """Export a template as a YAML definition file."""
    import yaml
    from app.services.pdf import THEME_PRESETS

    user = current_user
    if user is None and token:
        user = get_current_user_from_token_qs(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    tmpl = _get_template(db, template_id, user.id)

    # Find the preset name that matches the template's style
    preset_name = "academic"
    if tmpl.style:
        for name, preset_style in THEME_PRESETS.items():
            if preset_style == tmpl.style:
                preset_name = name
                break

    sections = []
    for s in sorted(tmpl.sections, key=lambda x: x.section_order):
        entry: dict = {"key": s.section_key, "depth": s.depth or 0}
        if s.section_key == "group_heading" and s.config:
            entry["heading"] = s.config.get("heading", "")
        sections.append(entry)

    data = {
        "name": tmpl.name,
        "description": tmpl.description or "",
        "preset": preset_name,
        "author": tmpl.author or "",
        "author_contact": tmpl.author_contact or "",
        "guidance_url": tmpl.guidance_url or "",
        "sections": sections,
    }

    yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    safe_name = tmpl.name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    return Response(
        content=yaml_content,
        media_type="application/x-yaml",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.yml"'},
    )


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
    tmpl = db.query(models.CVTemplate).filter(
        models.CVTemplate.id == template_id,
        or_(models.CVTemplate.user_id == user.id, models.CVTemplate.user_id.is_(None)),
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    cv_data = _build_cv_data(db, user_id=user.id, sort_direction=tmpl.sort_direction)
    enabled_sections = [
        {"key": s.section_key, "config": s.config or {}, "depth": s.depth or 0}
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
    tmpl = _get_template(db, template_id, current_user.id)
    cv_data = _build_cv_data(db, user_id=current_user.id, sort_direction=tmpl.sort_direction)
    enabled_sections = [
        {"key": s.section_key, "config": s.config or {}, "depth": s.depth or 0}
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
