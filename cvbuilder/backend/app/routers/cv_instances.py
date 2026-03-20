"""CV Instance CRUD, curation, preview, and PDF export endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, get_current_user_from_token_qs, get_optional_current_user

router = APIRouter(prefix="/api/cv-instances", tags=["cv-instances"])

# ---------------------------------------------------------------------------
# Section key → (Model, filter_dict) mapping
# ---------------------------------------------------------------------------

SECTION_KEY_MAP: dict[str, tuple[type, dict]] = {
    "education":                (models.CVItem, {"section": "education"}),
    "experience":               (models.CVItem, {"section": "experience"}),
    "consulting":               (models.CVItem, {"section": "consulting"}),
    "memberships":              (models.CVItem, {"section": "memberships"}),
    "panels_advisory":          (models.CVItem, {"section": "panels_advisory"}),
    "panels_grantreview":       (models.CVItem, {"section": "panels_grantreview"}),
    "patents":                  (models.Work, {"work_type": "patents"}),
    "symposia":                 (models.CVItem, {"section": "symposia"}),
    "committees":               (models.CVItem, {"section": "committees"}),
    "classes":                  (models.CVItem, {"section": "classes"}),
    "grants":                   (models.CVItem, {"section": "grants"}),
    "awards":                   (models.CVItem, {"section": "awards"}),
    "press":                    (models.CVItem, {"section": "press"}),
    "trainees_advisees":        (models.CVItem, {"section": "trainees_advisees"}),
    "trainees_postdocs":        (models.CVItem, {"section": "trainees_postdocs"}),
    "mentorship":               (models.CVItem, {"section": "mentorship"}),
    "seminars":                 (models.Work, {"work_type": "seminars"}),
    "publications_papers":      (models.Work, {"work_type": "papers"}),
    "publications_preprints":   (models.Work, {"work_type": "preprints"}),
    "publications_chapters":    (models.Work, {"work_type": "chapters"}),
    "publications_letters":     (models.Work, {"work_type": "letters"}),
    "publications_scimeetings": (models.Work, {"work_type": "scimeetings"}),
    "publications_editorials":  (models.Work, {"work_type": "editorials"}),
    "editorial":                (models.CVItem, {"_in": {"section": ["editor", "assocedit", "otheredit"]}}),
    "peerrev":                  (models.CVItem, {"section": "peerrev"}),
    "software":                 (models.Work, {"work_type": "software"}),
    "policypres":               (models.CVItem, {"section": "policypres"}),
    "policycons":               (models.CVItem, {"section": "policycons"}),
    "otherservice":             (models.CVItem, {"section": "otherservice"}),
    "dissertation":             (models.Work, {"work_type": "dissertation"}),
    "chairedsessions":          (models.CVItem, {"section": "chairedsessions"}),
    "otherpractice":            (models.CVItem, {"section": "otherpractice"}),
    "departmentalOrals":        (models.CVItem, {"section": "departmentalOrals"}),
    "finaldefense":             (models.CVItem, {"section": "finaldefense"}),
    "schoolwideOrals":          (models.CVItem, {"section": "schoolwideOrals"}),
    "citation_metrics":         (models.CVItem, {"section": "citation_metrics"}),
}


def _query_section_items(db: Session, user_id: int, section_key: str):
    """Query all items for a section key, applying type/section filters."""
    mapping = SECTION_KEY_MAP.get(section_key)
    if not mapping:
        return []
    model_cls, filters = mapping
    q = db.query(model_cls).filter(model_cls.user_id == user_id)
    for col, val in filters.items():
        if col == "_in":
            for in_col, in_vals in val.items():
                q = q.filter(getattr(model_cls, in_col).in_(in_vals))
        else:
            q = q.filter(getattr(model_cls, col) == val)
    return q.all()


def _item_label(item, section_key: str) -> str:
    """Generate a human-readable label for an item."""
    if isinstance(item, models.Work):
        authors = ", ".join(a.author_name for a in (item.authors or [])[:3])
        suffix = " et al." if len(item.authors or []) > 3 else ""
        year = f" ({item.year})" if item.year else ""
        title = (item.title or "Untitled")[:80]
        return f"{authors}{suffix}{year} {title}"
    if isinstance(item, models.CVItem):
        # Try common label fields via __getattr__ → data dict
        for attr in ("name", "title", "committee", "org", "panel", "degree", "outlet", "class_name"):
            val = getattr(item, attr, None)
            if val:
                extra = getattr(item, "year", None) or getattr(item, "date", None) or getattr(item, "years", None) or ""
                if extra:
                    return f"{val} ({extra})"
                return str(val)
        # Fallback: show first few data values
        data = item.data or {}
        parts = [str(v) for v in data.values() if v]
        return " — ".join(parts[:3]) if parts else f"Item #{item.id}"
    return f"Item #{item.id}"


def _get_instance(db: Session, instance_id: int, user_id: int) -> models.CVInstance:
    inst = db.query(models.CVInstance).filter_by(id=instance_id, user_id=user_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="CV instance not found")
    return inst


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[schemas.CVInstanceOut])
def list_cv_instances(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    instances = db.query(models.CVInstance).filter_by(user_id=current_user.id).all()
    result = []
    for inst in instances:
        out = schemas.CVInstanceOut.model_validate(inst)
        out.template_name = inst.template.name if inst.template else None
        result.append(out)
    return result


@router.post("", response_model=schemas.CVInstanceOut)
def create_cv_instance(
    data: schemas.CVInstanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Verify template exists and belongs to user
    tmpl = db.query(models.CVTemplate).filter_by(
        id=data.template_id, user_id=current_user.id
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    inst = models.CVInstance(
        user_id=current_user.id,
        template_id=data.template_id,
        name=data.name,
        description=data.description,
        style_overrides=data.style_overrides,
        sort_direction_override=data.sort_direction_override,
    )
    db.add(inst)
    db.flush()

    # Copy sections from template as defaults
    for ts in tmpl.sections:
        db.add(models.CVInstanceSection(
            cv_instance_id=inst.id,
            section_key=ts.section_key,
            enabled=ts.enabled,
            section_order=ts.section_order,
            heading_override=ts.config.get("heading") if ts.config else None,
            depth=ts.depth or 0,
            curated=False,
        ))
    db.commit()
    db.refresh(inst)
    out = schemas.CVInstanceOut.model_validate(inst)
    out.template_name = tmpl.name
    return out


@router.get("/{instance_id}", response_model=schemas.CVInstanceOut)
def get_cv_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    inst = _get_instance(db, instance_id, current_user.id)
    out = schemas.CVInstanceOut.model_validate(inst)
    out.template_name = inst.template.name if inst.template else None
    return out


@router.put("/{instance_id}", response_model=schemas.CVInstanceOut)
def update_cv_instance(
    instance_id: int,
    data: schemas.CVInstanceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    inst = _get_instance(db, instance_id, current_user.id)
    if data.name is not None:
        inst.name = data.name
    if data.description is not None:
        inst.description = data.description
    # These can be explicitly set to None to clear the override
    inst.style_overrides = data.style_overrides
    inst.sort_direction_override = data.sort_direction_override
    db.commit()
    db.refresh(inst)
    out = schemas.CVInstanceOut.model_validate(inst)
    out.template_name = inst.template.name if inst.template else None
    return out


@router.delete("/{instance_id}")
def delete_cv_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    inst = _get_instance(db, instance_id, current_user.id)
    db.delete(inst)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Section management
# ---------------------------------------------------------------------------

@router.put("/{instance_id}/sections", response_model=list[schemas.CVInstanceSectionOut])
def update_sections(
    instance_id: int,
    data: schemas.CVInstanceSectionsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    inst = _get_instance(db, instance_id, current_user.id)

    # Delete-and-recreate approach: handles duplicate keys (group_heading)
    # cleanly while preserving curated item selections for data sections.
    # Build a map of existing sections with their curated items for preservation.
    existing_by_key: dict[str, list[models.CVInstanceSection]] = {}
    for s in inst.sections:
        existing_by_key.setdefault(s.section_key, []).append(s)

    # Delete all existing sections
    for s in list(inst.sections):
        db.delete(s)
    db.flush()

    # Re-create from the incoming data
    for sec_data in data.sections:
        new_sec = models.CVInstanceSection(
            cv_instance_id=inst.id,
            section_key=sec_data.section_key,
            enabled=sec_data.enabled,
            section_order=sec_data.section_order,
            heading_override=sec_data.heading_override,
            config_overrides=sec_data.config_overrides,
            depth=sec_data.depth,
            curated=sec_data.curated,
        )
        db.add(new_sec)
        db.flush()

        # Restore curated items for data sections (not group_heading)
        if sec_data.section_key != "group_heading" and sec_data.curated:
            old_sections = existing_by_key.get(sec_data.section_key, [])
            for old_sec in old_sections:
                for item in old_sec.items:
                    db.add(models.CVInstanceItem(
                        cv_instance_section_id=new_sec.id,
                        item_id=item.item_id,
                    ))

    db.commit()
    db.refresh(inst)
    return inst.sections


# ---------------------------------------------------------------------------
# Item curation
# ---------------------------------------------------------------------------

@router.get("/{instance_id}/sections/{section_key}/items", response_model=list[schemas.AvailableItem])
def get_available_items(
    instance_id: int,
    section_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    inst = _get_instance(db, instance_id, current_user.id)
    section = next((s for s in inst.sections if s.section_key == section_key), None)
    selected_ids = set()
    if section:
        selected_ids = {item.item_id for item in section.items}

    all_items = _query_section_items(db, current_user.id, section_key)
    return [
        schemas.AvailableItem(
            id=item.id,
            label=_item_label(item, section_key),
            selected=item.id in selected_ids,
        )
        for item in all_items
    ]


@router.put("/{instance_id}/sections/{section_key}/items")
def update_section_items(
    instance_id: int,
    section_key: str,
    data: schemas.CVInstanceItemBulkUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    inst = _get_instance(db, instance_id, current_user.id)
    section = next((s for s in inst.sections if s.section_key == section_key), None)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section '{section_key}' not found on this CV instance")

    # Replace existing items
    db.query(models.CVInstanceItem).filter_by(cv_instance_section_id=section.id).delete()
    for item_id in data.item_ids:
        db.add(models.CVInstanceItem(
            cv_instance_section_id=section.id,
            item_id=item_id,
        ))
    db.commit()
    return {"ok": True, "count": len(data.item_ids)}


# ---------------------------------------------------------------------------
# Preview & PDF export
# ---------------------------------------------------------------------------

def _build_cv_instance_data(db: Session, inst: models.CVInstance) -> tuple[dict, list[dict], dict]:
    """Build CV data filtered by instance curation settings.

    Returns (cv_data, sections_list, style).
    """
    from app.routers.templates import _build_cv_data

    tmpl = inst.template
    # Merge template style with instance overrides (instance keys win)
    style = dict(tmpl.style or {})
    if inst.style_overrides:
        for k, v in inst.style_overrides.items():
            if v is not None and v != "":
                style[k] = v
    sort_direction = inst.sort_direction_override or tmpl.sort_direction

    # Get all CV data
    cv_data = _build_cv_data(db, user_id=inst.user_id, sort_direction=sort_direction)

    # Build ordered section list
    effective_sections = []
    for sec in sorted(inst.sections, key=lambda s: s.section_order or 0):
        enabled = sec.enabled if sec.enabled is not None else True
        if not enabled:
            continue

        if sec.section_key == "group_heading":
            # Group headings carry their text in heading_override
            effective_sections.append({
                "key": "group_heading",
                "config": {"heading": sec.heading_override or ""},
                "depth": sec.depth or 0,
                "_curated": False,
                "_item_ids": None,
            })
            continue

        # For data sections, start with an empty config and apply overrides + heading
        config: dict = {}
        if sec.config_overrides:
            config.update(sec.config_overrides)
        if sec.heading_override:
            config["heading"] = sec.heading_override
        effective_sections.append({
            "key": sec.section_key,
            "config": config,
            "depth": sec.depth or 0,
            "_curated": sec.curated,
            "_item_ids": {item.item_id for item in sec.items} if sec.curated else None,
        })

    # Filter curated items from cv_data
    # Map section keys to cv_data keys and filter
    _CV_DATA_KEY_MAP = {
        "education": "education",
        "experience": "experience",
        "consulting": "consulting",
        "memberships": "memberships",
        "panels_advisory": "panels",
        "panels_grantreview": "panels",
        "patents": "patents",
        "symposia": "symposia",
        "committees": "committees",
        "classes": "classes",
        "grants": "grants",
        "awards": "awards",
        "press": "press",
        "trainees_advisees": "trainees",
        "trainees_postdocs": "trainees",
        "mentorship": "mentorship",
        "seminars": "seminars",
        "editorial": "editorial",
        "peerrev": "peerrev",
        "software": "software",
        "policypres": "policypres",
        "policycons": "policycons",
        "otherservice": "otherservice",
        "dissertation": "dissertation",
        "chairedsessions": "chairedsessions",
        "otherpractice": "otherpractice",
        "departmentalOrals": "departmentalOrals",
        "finaldefense": "finaldefense",
        "schoolwideOrals": "schoolwideOrals",
        "citation_metrics": "citation_metrics",
    }

    # Publication section keys map to the "publications" data key with type filtering
    _PUB_TYPE_MAP = {
        "publications_papers": "papers",
        "publications_preprints": "preprints",
        "publications_chapters": "chapters",
        "publications_letters": "letters",
        "publications_scimeetings": "scimeetings",
        "publications_editorials": "editorials",
    }

    for sec_info in effective_sections:
        key = sec_info["key"]
        if not sec_info.get("_curated") or sec_info.get("_item_ids") is None:
            continue

        item_ids = sec_info["_item_ids"]

        if key in _PUB_TYPE_MAP:
            # Filter publications list — remove pubs with matching type but not in inclusion list
            pub_type = _PUB_TYPE_MAP[key]
            cv_data["publications"] = [
                p for p in cv_data["publications"]
                if p.work_type != pub_type or p.id in item_ids
            ]
        elif key in _CV_DATA_KEY_MAP:
            data_key = _CV_DATA_KEY_MAP[key]
            items = cv_data.get(data_key, [])
            cv_data[data_key] = [item for item in items if item.id in item_ids]

    # Clean up internal keys from sections
    clean_sections = [
        {"key": s["key"], "config": s["config"], "depth": s.get("depth", 0)}
        for s in effective_sections
    ]

    return cv_data, clean_sections, style


@router.get("/{instance_id}/preview", response_class=HTMLResponse)
def preview_cv_instance(
    instance_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user),
):
    user = current_user
    if user is None and token:
        user = get_current_user_from_token_qs(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    inst = _get_instance(db, instance_id, user.id)
    cv_data, sections, style = _build_cv_instance_data(db, inst)

    from app.services.pdf import render_cv_html
    html = render_cv_html(cv_data, style=style, sections=sections)
    return HTMLResponse(content=html)


@router.post("/{instance_id}/export/pdf")
def export_cv_instance_pdf(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    inst = _get_instance(db, instance_id, current_user.id)
    cv_data, sections, style = _build_cv_instance_data(db, inst)

    from app.services.pdf import render_cv_html, html_to_pdf
    html = render_cv_html(cv_data, style=style, sections=sections)
    pdf_bytes = html_to_pdf(html)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cv_{inst.name}.pdf"'},
    )
