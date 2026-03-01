"""CVBuilder FastAPI application."""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import create_tables, get_db
from app import models, schemas
from app.auth import get_current_user
from app.routers import auth, profile, publications, templates, export, cv_instances

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
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(publications.router)
app.include_router(templates.router)
app.include_router(export.router)
app.include_router(cv_instances.router)


@app.on_event("startup")
def startup():
    create_tables()
    _run_migrations()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        _ensure_default_user(db)
        _seed_templates(db, user_id=1)
    finally:
        db.close()


# Tables that need a user_id column added via migration
_USER_ID_TABLES = [
    "profile", "education", "experience", "consulting", "memberships",
    "panels", "patents", "symposia", "classes", "grants", "awards",
    "press", "trainees", "seminars", "committees", "misc_sections",
    "publications", "cv_templates",
]


def _run_migrations():
    """Apply additive schema changes that create_all() won't handle."""
    from app.database import engine
    from app.services.pdf import THEME_PRESETS
    from sqlalchemy import text
    import json
    stmts = [
        "ALTER TABLE pub_authors ADD COLUMN student INTEGER DEFAULT 0",
        "ALTER TABLE cv_templates ADD COLUMN sort_direction TEXT DEFAULT 'desc'",
        "ALTER TABLE cv_templates ADD COLUMN style TEXT",
        "ALTER TABLE cv_instances ADD COLUMN style_overrides TEXT",
        "ALTER TABLE publications ADD COLUMN preprint_doi VARCHAR(500)",
        "ALTER TABLE publications ADD COLUMN published_doi VARCHAR(500)",
    ]
    # Add user_id column to all content tables
    for table in _USER_ID_TABLES:
        stmts.append(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)")

    with engine.connect() as conn:
        for stmt in stmts:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # Column already exists

        # Backfill style from theme_css for existing templates
        try:
            rows = conn.execute(text(
                "SELECT id, theme_css FROM cv_templates WHERE style IS NULL AND theme_css IS NOT NULL"
            )).fetchall()
            for row in rows:
                preset = THEME_PRESETS.get(row[1])
                if preset:
                    conn.execute(
                        text("UPDATE cv_templates SET style = :style WHERE id = :id"),
                        {"style": json.dumps(preset), "id": row[0]},
                    )
            conn.commit()
        except Exception:
            pass

        # Drop legacy theme columns (SQLite 3.35.0+ supports DROP COLUMN)
        for drop_stmt in [
            "ALTER TABLE cv_templates DROP COLUMN theme_css",
            "ALTER TABLE cv_instances DROP COLUMN theme_css_override",
        ]:
            try:
                conn.execute(text(drop_stmt))
                conn.commit()
            except Exception:
                pass  # Column already dropped or doesn't exist


def _ensure_default_user(db):
    """Create default admin user and backfill existing rows."""
    from app.auth import get_password_hash
    from sqlalchemy import text

    user = db.query(models.User).filter(models.User.email == "admin@local").first()
    if not user:
        user = models.User(
            email="admin@local",
            hashed_password=get_password_hash("changeme"),
            full_name="Admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Backfill any rows that have NULL user_id with the default user
    for table in _USER_ID_TABLES:
        db.execute(
            text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": user.id},
        )
    db.commit()

    # Create indexes for user_id lookups
    for table in _USER_ID_TABLES:
        try:
            db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_user ON {table}(user_id)"))
        except Exception:
            pass
    db.commit()


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
# Template definitions: name → (description, style_preset_name, ordered section keys)
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


def _seed_templates(db, user_id: int = 1):
    """Insert new templates and add any missing sections to existing templates."""
    from app.services.pdf import THEME_PRESETS

    existing_tmpls = {
        t.name: t for t in
        db.query(models.CVTemplate).filter_by(user_id=user_id).all()
    }
    for name, (description, preset_name, sections) in _TEMPLATES.items():
        if name not in existing_tmpls:
            tmpl = models.CVTemplate(
                name=name, description=description,
                style=THEME_PRESETS.get(preset_name, THEME_PRESETS["academic"]),
                user_id=user_id,
            )
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
def dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    uid = current_user.id
    profile = db.query(models.Profile).filter_by(user_id=uid).first()
    total = db.query(models.Publication).filter_by(user_id=uid).count()

    def count_type(t):
        return db.query(models.Publication).filter(
            models.Publication.user_id == uid,
            models.Publication.type == t,
        ).count()

    trainee_rows = (
        db.query(models.Trainee.trainee_type, func.count(models.Trainee.id))
        .filter(models.Trainee.user_id == uid)
        .group_by(models.Trainee.trainee_type)
        .all()
    )
    active_grant_rows = (
        db.query(models.Grant.role, func.count(models.Grant.id))
        .filter(
            models.Grant.user_id == uid,
            models.Grant.status == "active",
            models.Grant.role.isnot(None),
            models.Grant.role != "",
        )
        .group_by(models.Grant.role)
        .order_by(func.count(models.Grant.id).desc())
        .all()
    )
    active_grants = db.query(models.Grant).filter(
        models.Grant.user_id == uid,
        models.Grant.status == "active",
    ).count()

    return schemas.DashboardStats(
        total_publications=total,
        papers=count_type("papers"),
        preprints=count_type("preprints"),
        chapters=count_type("chapters"),
        letters=count_type("letters"),
        scimeetings=count_type("scimeetings"),
        editorials=count_type("editorials"),
        trainees=db.query(models.Trainee).filter_by(user_id=uid).count(),
        grants=db.query(models.Grant).filter_by(user_id=uid).count(),
        active_grants=active_grants,
        profile_complete=bool(profile and profile.name),
        trainee_breakdown=[{"type": t, "count": c} for t, c in trainee_rows],
        active_grant_breakdown=[{"role": r, "count": c} for r, c in active_grant_rows],
    )
