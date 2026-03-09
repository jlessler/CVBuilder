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
    cv_data["grants"] = _cv_item_dicts("grants", ["title", "agency", "amount", "role", "status"],
        lambda r: {"years": f"{r.data.get('years_start', '')}-{r.data.get('years_end', '')}".strip("-"),
                    "id": r.data.get("id_number")})
    cv_data["honor"] = _cv_item_dicts("awards", ["name", "date"],
        lambda r: {"grantee": r.data.get("org")})

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
    """Accept uploaded CV.yml and/or refs.yml and import them."""
    import tempfile, os
    from app.services.yaml_import import import_cv_yaml, import_refs_yaml

    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        if cv_file:
            cv_path = os.path.join(tmpdir, "CV.yml")
            with open(cv_path, "wb") as f:
                f.write(await cv_file.read())
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
