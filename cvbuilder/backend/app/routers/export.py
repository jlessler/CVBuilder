"""YAML export/import endpoints for backup and migration."""
import io
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import yaml

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/export", tags=["export"])


def _dump(value) -> str:
    """Convert SQLAlchemy model attribute to a plain Python value."""
    if hasattr(value, "__dict__"):
        return str(value)
    return value


@router.get("/yaml")
def export_yaml(db: Session = Depends(get_db)):
    """Export all data as a YAML backup (CV.yml + refs.yml combined)."""
    profile = db.query(models.Profile).first()

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

    def model_list(model_class, fields, extra_fn=None):
        rows = db.query(model_class).order_by(model_class.sort_order).all()
        result = []
        for r in rows:
            d = {f: getattr(r, f) for f in fields if getattr(r, f) is not None}
            if extra_fn:
                d.update(extra_fn(r))
            result.append(d)
        return result

    cv_data["education"] = model_list(models.Education, ["degree", "year", "subject", "school"])
    cv_data["experience"] = model_list(models.Experience, ["title", "employer"],
        lambda r: {"years": f"{r.years_start}-{r.years_end}".strip("-")})
    cv_data["consulting"] = model_list(models.Consulting, ["title", "years", "employer"])
    cv_data["membership"] = model_list(models.Membership, ["org", "years"])
    cv_data["panel"] = [
        {"panel": r.panel, "org": r.org, "role": r.role, "date": r.date}
        for r in db.query(models.Panel).filter(models.Panel.type == "advisory").order_by(models.Panel.sort_order).all()
    ]
    cv_data["grantrev"] = [
        {"panel": r.panel, "org": r.org, "date": r.date, "type": r.role, "id": r.panel_id}
        for r in db.query(models.Panel).filter(models.Panel.type == "grant_review").order_by(models.Panel.sort_order).all()
    ]
    cv_data["patent"] = []
    for p in db.query(models.Patent).order_by(models.Patent.sort_order).all():
        cv_data["patent"].append({
            "name": p.name, "number": p.number, "status": p.status,
            "authors": [a.author_name for a in p.authors],
        })
    cv_data["symposium"] = model_list(models.Symposium, ["title", "meeting", "date", "role"])
    cv_data["classes"] = [
        {"class": r.class_name, "year": r.year, "role": r.role, "school": r.school,
         "students": r.students, "lectures": r.lectures, "inthreeyear": r.in_three_year}
        for r in db.query(models.Class).order_by(models.Class.sort_order).all()
    ]
    cv_data["grants"] = model_list(models.Grant, ["title", "agency", "amount", "role", "status"],
        lambda r: {"years": f"{r.years_start}-{r.years_end}".strip("-"), "id": r.id_number})
    cv_data["honor"] = model_list(models.Award, ["name", "date"],
        lambda r: {"grantee": r.org})

    # Publications
    pub_data: dict = {"myname": profile.name if profile else ""}
    for pub_type in ["papers", "preprints", "papersNoPeer", "chapters", "letters", "scimeetings"]:
        pubs = db.query(models.Publication).filter(
            models.Publication.type == pub_type
        ).order_by(models.Publication.year.desc()).all()
        pub_data[pub_type] = []
        for p in pubs:
            entry = {
                "authors": [a.author_name for a in p.authors],
                "title": p.title,
                "year": p.year,
                "journal": p.journal,
            }
            for f in ["volume", "issue", "pages", "doi"]:
                v = getattr(p, f)
                if v:
                    entry[f] = v
            if p.corr:
                entry["corr"] = True
            if p.select_flag:
                entry["select"] = "1"
            if p.cofirsts:
                entry["cofirsts"] = p.cofirsts
            if p.coseniors:
                entry["coseniors"] = p.coseniors
            pub_data[pub_type].append(entry)

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
            import_cv_yaml(cv_path, db)
            results.append("CV.yml imported")

        if refs_file:
            refs_path = os.path.join(tmpdir, "refs.yml")
            with open(refs_path, "wb") as f:
                f.write(await refs_file.read())
            import_refs_yaml(refs_path, db)
            results.append("refs.yml imported")

    if not results:
        raise HTTPException(status_code=400, detail="No files uploaded")

    return {"imported": results}
