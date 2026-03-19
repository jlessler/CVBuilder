"""YAML export/import endpoints for backup and migration."""
import io
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import yaml

from app.database import get_db
from app import models
from app.auth import get_current_user

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/yaml")
def export_yaml(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Export all data as a YAML backup (CV.yml + refs.yml combined)."""
    uid = current_user.id
    profile = db.query(models.Profile).filter_by(user_id=uid).first()

    cv_data: dict = {}
    if profile:
        cv_data["name"] = profile.name
        cv_data["email"] = profile.email
        cv_data["phone"] = profile.phone
        cv_data["website"] = profile.website
        cv_data["orcid"] = profile.orcid

        home_addrs = [a.text for a in profile.addresses if a.type == "home"]
        work_addrs = [a.text for a in profile.addresses if a.type == "work"]
        if home_addrs:
            cv_data["address-home"] = home_addrs
        if work_addrs:
            cv_data["address-work"] = work_addrs

    def _cv_items(section):
        return db.query(models.CVItem).filter_by(user_id=uid, section=section).order_by(models.CVItem.sort_order).all()

    def _cv_item_dicts(section, fields, extra_fn=None):
        result = []
        for r in _cv_items(section):
            d = {f: r.data.get(f) for f in fields if r.data.get(f) is not None}
            if extra_fn:
                d.update(extra_fn(r))
            result.append(d)
        return result

    cv_data["education"] = _cv_item_dicts("education", ["degree", "year", "subject", "school"])
    cv_data["experience"] = _cv_item_dicts("experience", ["title", "employer"],
        lambda r: {"years": f"{r.data.get('years_start', '')}-{r.data.get('years_end', '')}".strip("-")})
    cv_data["consulting"] = _cv_item_dicts("consulting", ["title", "years", "employer"])
    cv_data["membership"] = _cv_item_dicts("memberships", ["org", "years"])
    cv_data["panel"] = [
        {"panel": r.data.get("panel"), "org": r.data.get("org"), "role": r.data.get("role"), "date": r.data.get("date")}
        for r in _cv_items("panels_advisory")
    ]
    cv_data["grantrev"] = [
        {"panel": r.data.get("panel"), "org": r.data.get("org"), "date": r.data.get("date"),
         "type": r.data.get("role"), "id": r.data.get("panel_id")}
        for r in _cv_items("panels_grantreview")
    ]
    cv_data["patent"] = []
    for p in db.query(models.Work).filter_by(user_id=uid, work_type="patents").order_by(models.Work.id).all():
        cv_data["patent"].append({
            "name": p.title, "number": p.identifier, "status": p.status,
            "authors": [a.author_name for a in p.authors],
        })
    cv_data["symposium"] = _cv_item_dicts("symposia", ["title", "meeting", "date", "role"])
    cv_data["classes"] = [
        {"class": r.data.get("class_name"), "year": r.data.get("year"), "role": r.data.get("role"),
         "school": r.data.get("school"), "students": r.data.get("students"),
         "lectures": r.data.get("lectures"), "inthreeyear": r.data.get("in_three_year")}
        for r in _cv_items("classes")
    ]
    def _grant_dicts(status):
        result = []
        for r in _cv_items("grants"):
            if r.data.get("status") != status:
                continue
            d = {
                "title": r.data.get("title"), "org": r.data.get("agency"),
                "amount": r.data.get("amount"), "role": r.data.get("role"),
                "dates": f"{r.data.get('years_start', '')}-{r.data.get('years_end', '')}".strip("-"),
                "number": r.data.get("id_number"), "PI": r.data.get("pi"),
                "type": r.data.get("grant_type"),
                "pcteffort": r.data.get("pcteffort"),
                "description": r.data.get("description"),
            }
            result.append({k: v for k, v in d.items() if v is not None and v != ""})
        return result

    cv_data["activegrants"] = _grant_dicts("active")
    cv_data["completedgrants"] = _grant_dicts("completed")
    cv_data["honor"] = _cv_item_dicts("awards", ["name", "date"],
        lambda r: {"grantee": r.data.get("org")})

    # --- Press / media ---
    cv_data["media"] = [{"topic": r.data.get("topic"), "date": r.data.get("date"),
        "outlets": r.data.get("outlets", [])} for r in _cv_items("press")]

    # --- Trainees ---
    cv_data["advisees"] = [{"name": r.data.get("name"), "degree": r.data.get("degree"),
        "dates": f"{r.data.get('years_start', '')}-{r.data.get('years_end', '')}".strip("-"),
        "type": r.data.get("type"), "school": r.data.get("school"),
        "thesis": r.data.get("thesis"), "wherenow": r.data.get("current_position")}
        for r in _cv_items("trainees_advisees")]
    cv_data["postdocs"] = [{"name": r.data.get("name"),
        "dates": f"{r.data.get('years_start', '')}-{r.data.get('years_end', '')}".strip("-"),
        "wherenow": r.data.get("current_position")}
        for r in _cv_items("trainees_postdocs")]

    # --- Committees ---
    cv_data["committees"] = _cv_item_dicts("committees", ["committee", "org", "role", "dates"])

    # --- Misc sections (editorial, peerrev, service, exams, etc.) ---
    for key in ["editor", "assocedit", "otheredit", "peerrev", "policypres", "policycons",
                "otherservice", "schoolwideOrals", "departmentalOrals", "finaldefense"]:
        items = _cv_items(key)
        if items:
            cv_data[key] = [r.data for r in items]

    # --- Chaired sessions ---
    cv_data["chairedsessions"] = [{"title": r.data.get("title"),
        "year": r.data.get("date"), "conference": r.data.get("meeting")}
        for r in _cv_items("chairedsessions")]

    # --- Other practice → policyother ---
    cv_data["policyother"] = [r.data for r in _cv_items("otherpractice")]

    # Publications (from works table)
    pub_data: dict = {"myname": profile.name if profile else ""}
    # Map DB work_type → YAML key (editorials → papersNoPeer for YAML compat)
    _WORK_TYPE_TO_YAML = {
        "papers": "papers", "preprints": "preprints", "chapters": "chapters",
        "letters": "letters", "scimeetings": "scimeetings", "editorials": "papersNoPeer",
    }
    for work_type, yaml_key in _WORK_TYPE_TO_YAML.items():
        works = db.query(models.Work).filter(
            models.Work.user_id == uid,
            models.Work.work_type == work_type,
        ).order_by(models.Work.year.desc()).all()
        pub_data[yaml_key] = []
        for w in works:
            d = w.data or {}
            # Reconstruct year string for YAML (prefer year_raw, else integer year)
            year_val = d.get("year_raw") or (str(w.year) if w.year else "")
            entry = {
                "authors": [a.author_name for a in w.authors],
                "title": w.title,
                "year": year_val,
                "journal": d.get("journal", ""),
            }
            for f in ["volume", "issue", "pages"]:
                v = d.get(f)
                if v:
                    entry[f] = v
            if w.doi:
                entry["doi"] = w.doi
            # Reconstruct corr/cofirsts/coseniors from per-author flags
            authors = sorted(w.authors, key=lambda a: a.author_order)
            if any(a.corresponding for a in authors):
                entry["corr"] = True
            cofirsts = sum(1 for a in authors if a.cofirst)
            if cofirsts:
                entry["cofirsts"] = cofirsts
            coseniors = sum(1 for a in authors if a.cosenior)
            if coseniors:
                entry["coseniors"] = coseniors
            if d.get("select_flag"):
                entry["select"] = "1"
            if d.get("preprint_doi"):
                entry["preprint_doi"] = d["preprint_doi"]
            if d.get("published_doi"):
                entry["published_doi"] = d["published_doi"]
            pub_data[yaml_key].append(entry)

    # --- Seminars (Work records) ---
    cv_data["seminars"] = []
    for w in db.query(models.Work).filter_by(user_id=uid, work_type="seminars").order_by(models.Work.id).all():
        d = w.data or {}
        entry = {"title": w.title, "org": d.get("institution"), "event": d.get("conference"),
                 "loc": d.get("location"), "date": d.get("date_raw") or (str(w.year) if w.year else "")}
        cv_data["seminars"].append({k: v for k, v in entry.items() if v})

    # --- Software (Work records) ---
    cv_data["software"] = []
    for w in db.query(models.Work).filter_by(user_id=uid, work_type="software").order_by(models.Work.id).all():
        d = w.data or {}
        entry = {"title": w.title, "year": d.get("year_raw") or (str(w.year) if w.year else ""),
                 "publisher": d.get("publisher"), "url": d.get("url"),
                 "authors": ", ".join(a.author_name for a in w.authors)}
        cv_data["software"].append({k: v for k, v in entry.items() if v})

    # --- Dissertation (Work record, singular dict) ---
    diss = db.query(models.Work).filter_by(user_id=uid, work_type="dissertation").first()
    if diss:
        d = diss.data or {}
        inst = d.get("institution", "")
        parts = inst.split(", ", 1) if inst else ["", ""]
        cv_data["dissertation"] = {"title": diss.title,
            "year": d.get("year_raw") or (str(diss.year) if diss.year else ""),
            "department": parts[0] if len(parts) > 1 else "",
            "institution": parts[1] if len(parts) > 1 else parts[0]}

    combined = {"cv": cv_data, "refs": pub_data}
    yaml_str = yaml.dump(combined, allow_unicode=True, sort_keys=False, default_flow_style=False)

    return StreamingResponse(
        io.BytesIO(yaml_str.encode("utf-8")),
        media_type="application/x-yaml",
        headers={"Content-Disposition": 'attachment; filename="cvbuilder_backup.yml"'},
    )


@router.post("/yaml/import")
async def import_yaml_upload(
    cv_file: UploadFile = File(None),
    refs_file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Accept uploaded CV.yml and/or refs.yml and import them.

    Supports three modes:
    - Two separate files (cv_file + refs_file) in the original flat format
    - A single combined backup file (cv_file) with top-level ``cv`` and ``refs`` keys
      (the format produced by the export endpoint)
    - A single flat CV or refs file
    """
    import tempfile, os
    from app.services.yaml_import import import_cv_yaml, import_refs_yaml

    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        if cv_file:
            raw = await cv_file.read()
            # Detect combined backup format (has top-level 'cv' and/or 'refs' keys)
            parsed = yaml.safe_load(raw)
            if isinstance(parsed, dict) and ("cv" in parsed or "refs" in parsed):
                # Combined format — split into separate files
                if parsed.get("cv"):
                    cv_path = os.path.join(tmpdir, "CV.yml")
                    with open(cv_path, "w", encoding="utf-8") as f:
                        yaml.dump(parsed["cv"], f, allow_unicode=True, sort_keys=False)
                    import_cv_yaml(cv_path, db, user_id=current_user.id)
                    results.append("CV data imported")
                if parsed.get("refs"):
                    refs_path = os.path.join(tmpdir, "refs.yml")
                    with open(refs_path, "w", encoding="utf-8") as f:
                        yaml.dump(parsed["refs"], f, allow_unicode=True, sort_keys=False)
                    import_refs_yaml(refs_path, db, user_id=current_user.id)
                    results.append("Publications imported")
            else:
                # Flat CV file
                cv_path = os.path.join(tmpdir, "CV.yml")
                with open(cv_path, "wb") as f:
                    f.write(raw)
                import_cv_yaml(cv_path, db, user_id=current_user.id)
                results.append("CV.yml imported")

        if refs_file:
            refs_path = os.path.join(tmpdir, "refs.yml")
            with open(refs_path, "wb") as f:
                f.write(await refs_file.read())
            import_refs_yaml(refs_path, db, user_id=current_user.id)
            results.append("refs.yml imported")

    if not results:
        raise HTTPException(status_code=400, detail="No files uploaded")

    return {"imported": results}
