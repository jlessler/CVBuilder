"""CVBuilder FastAPI application."""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        _seed_templates(db)
    finally:
        db.close()


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
            "classes", "grants", "awards", "press",
            "trainees_advisees", "trainees_postdocs",
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
            "publications_papers", "patents",
            "publications_chapters", "publications_preprints",
            "publications_letters", "publications_scimeetings",
            "classes", "trainees_advisees", "trainees_postdocs",
            "grants",
            "panels_advisory", "panels_grantreview", "symposia",
            "consulting", "press",
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
    """Insert any templates that don't already exist (matched by name)."""
    existing = {t.name for t in db.query(models.CVTemplate).all()}
    for name, (description, theme_css, sections) in _TEMPLATES.items():
        if name in existing:
            continue
        tmpl = models.CVTemplate(name=name, description=description, theme_css=theme_css)
        db.add(tmpl)
        db.flush()
        for i, key in enumerate(sections):
            heading = _HEADINGS.get(key, key.replace("_", " ").title())
            db.add(models.TemplateSection(
                template_id=tmpl.id,
                section_key=key,
                enabled=True,
                section_order=i,
                config={"heading": heading},
            ))
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

    return schemas.DashboardStats(
        total_publications=total,
        papers=count_type("papers"),
        preprints=count_type("preprints"),
        chapters=count_type("chapters"),
        letters=count_type("letters"),
        scimeetings=count_type("scimeetings"),
        trainees=db.query(models.Trainee).count(),
        grants=db.query(models.Grant).count(),
        profile_complete=bool(profile and profile.name),
    )
