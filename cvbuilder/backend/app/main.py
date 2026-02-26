"""CVBuilder FastAPI application."""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import create_tables, get_db
from app import models, schemas
from app.routers import profile, publications, templates, export

app = FastAPI(
    title="CVBuilder API",
    description="Backend API for the CVBuilder web application",
    version="1.0.0",
)

# CORS — allow the Vite dev server and same-origin prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(profile.router)
app.include_router(publications.router)
app.include_router(templates.router)
app.include_router(export.router)


@app.on_event("startup")
def startup():
    create_tables()
    _run_migrations()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        _seed_templates(db)
    finally:
        db.close()


def _run_migrations():
    """Apply additive schema changes that create_all() won't handle."""
    from app.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        for stmt in [
            "ALTER TABLE pub_authors ADD COLUMN student INTEGER DEFAULT 0",
            "ALTER TABLE cv_templates ADD COLUMN sort_direction TEXT DEFAULT 'desc'",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # Column already exists


# ---------------------------------------------------------------------------
# Section heading labels used by all templates
# ---------------------------------------------------------------------------
_HEADINGS = {
    "education":                  "Education",
    "experience":                 "Professional Experience",
    "consulting":                 "Consulting Activities",
    "memberships":                "Memberships",
    "panels_advisory":            "Advisory Panels",
    "panels_grantreview":         "Grant Review Panels",
    "patents":                    "Patents",
    "symposia":                   "Organized Sessions",
    "classes":                    "Teaching",
    "grants":                     "Contracts and Grants",
    "awards":                     "Honors and Awards",
    "press":                      "Media and Press",
    "trainees_advisees":          "Advisees",
    "trainees_postdocs":          "Postdoctoral Trainees",
    "publications_papers":        "Peer-Reviewed Publications",
    "publications_preprints":     "Preprints",
    "publications_chapters":      "Books and Chapters",
    "publications_letters":       "Letters",
    "publications_scimeetings":   "Presentations at Scientific Meetings",
    "editorial":                  "Editorial Activities",
    "peerrev":                    "Peer Review",
    "seminars":                   "Invited Seminars and Lectures",
    "committees":                 "Committee Memberships",
    "software":                   "Software",
    "policypres":                 "Policy Presentations",
    "policycons":                 "Policy Consulting",
    "otherservice":               "Other Service",
    "publications_editorials":    "Published Articles and Editorials not Peer Reviewed",
    "dissertation":               "Dissertation",
    "chairedsessions":            "Chaired Sessions",
    "otherpractice":              "Other Practice Activities",
    "departmentalOrals":          "Departmental Oral Exams",
    "finaldefense":               "Final Dissertation Defenses",
    "schoolwideOrals":            "School-wide Oral Exams",
}

# ---------------------------------------------------------------------------
# Template definitions: name → (description, theme_css, ordered section keys)
# ---------------------------------------------------------------------------
_TEMPLATES = {
    "Academic CV": (
        "Full academic CV with all sections",
        "academic",
        [
            "education", "experience", "consulting", "memberships",
            "panels_advisory", "panels_grantreview", "patents", "symposia",
            "committees", "editorial", "peerrev",
            "classes", "grants", "awards", "press",
            "trainees_advisees", "trainees_postdocs",
            "seminars",
            "publications_papers", "publications_preprints",
            "publications_chapters", "publications_letters",
            "publications_scimeetings",
        ],
    ),
    "UNC CV": (
        "University of North Carolina format — sans-serif, Carolina Blue accents, "
        "bibliography-forward section order",
        "unc",
        [
            "education", "experience", "awards", "memberships",
            "dissertation",
            "publications_papers", "patents",
            "publications_editorials",
            "publications_chapters", "publications_preprints",
            "publications_letters", "publications_scimeetings",
            "classes", "trainees_advisees", "trainees_postdocs",
            "grants",
            "panels_advisory", "panels_grantreview", "symposia",
            "chairedsessions",
            "consulting", "press",
            "otherpractice",
        ],
    ),
    "Hopkins CV": (
        "Johns Hopkins format — Times New Roman serif, Heritage Blue headings, "
        "centered CURRICULUM VITAE title, practice-activities section",
        "hopkins",
        [
            "education", "experience",
            "memberships", "panels_advisory", "symposia", "patents",
            "panels_grantreview", "awards",
            "publications_papers", "publications_chapters",
            "publications_letters", "press",
            "trainees_advisees", "trainees_postdocs", "classes",
            "grants", "publications_scimeetings", "consulting",
        ],
    ),
    "UNIGE CV": (
        "University of Geneva format — sans-serif, RedViolet section headings, "
        "research-supervision-forward structure",
        "unige",
        [
            "education", "experience", "grants",
            "trainees_advisees", "trainees_postdocs",
            "panels_advisory", "panels_grantreview", "symposia",
            "publications_scimeetings",
            "publications_papers", "publications_preprints",
            "publications_chapters", "publications_letters",
            "memberships", "press",
        ],
    ),
}


def _seed_templates(db):
    """Insert new templates and add any missing sections to existing templates."""
    existing_tmpls = {t.name: t for t in db.query(models.CVTemplate).all()}
    for name, (description, theme_css, sections) in _TEMPLATES.items():
        if name not in existing_tmpls:
            tmpl = models.CVTemplate(name=name, description=description, theme_css=theme_css)
            db.add(tmpl)
            db.flush()
        else:
            tmpl = existing_tmpls[name]

        existing_keys = {
            s.section_key for s in
            db.query(models.TemplateSection).filter_by(template_id=tmpl.id).all()
        }
        # Append any new section keys at the end of the current order
        next_order = db.query(models.TemplateSection).filter_by(
            template_id=tmpl.id
        ).count()
        for key in sections:
            if key not in existing_keys:
                heading = _HEADINGS.get(key, key.replace("_", " ").title())
                db.add(models.TemplateSection(
                    template_id=tmpl.id,
                    section_key=key,
                    enabled=True,
                    section_order=next_order,
                    config={"heading": heading},
                ))
                next_order += 1
    db.commit()


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/dashboard", response_model=schemas.DashboardStats)
def dashboard(db: Session = Depends(get_db)):
    profile = db.query(models.Profile).first()
    total = db.query(models.Publication).count()

    def count_type(t):
        return db.query(models.Publication).filter(models.Publication.type == t).count()

    trainee_rows = (
        db.query(models.Trainee.trainee_type, func.count(models.Trainee.id))
        .group_by(models.Trainee.trainee_type)
        .all()
    )
    active_grant_rows = (
        db.query(models.Grant.role, func.count(models.Grant.id))
        .filter(
            models.Grant.status == "active",
            models.Grant.role.isnot(None),
            models.Grant.role != "",
        )
        .group_by(models.Grant.role)
        .order_by(func.count(models.Grant.id).desc())
        .all()
    )
    active_grants = db.query(models.Grant).filter(models.Grant.status == "active").count()

    return schemas.DashboardStats(
        total_publications=total,
        papers=count_type("papers"),
        preprints=count_type("preprints"),
        chapters=count_type("chapters"),
        letters=count_type("letters"),
        scimeetings=count_type("scimeetings"),
        editorials=count_type("editorials"),
        trainees=db.query(models.Trainee).count(),
        grants=db.query(models.Grant).count(),
        active_grants=active_grants,
        profile_complete=bool(profile and profile.name),
        trainee_breakdown=[{"type": t, "count": c} for t, c in trainee_rows],
        active_grant_breakdown=[{"role": r, "count": c} for r, c in active_grant_rows],
    )
