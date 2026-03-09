"""CVBuilder FastAPI application."""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import create_tables, get_db
from app import models, schemas
from app.auth import get_current_user
from app.routers import auth, profile, templates, export, cv_instances, works, cv_items

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
app.include_router(templates.router)
app.include_router(export.router)
app.include_router(cv_instances.router)
app.include_router(works.router)
app.include_router(cv_items.router)


@app.on_event("startup")
def startup():
    create_tables()
    _run_migrations()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        _ensure_default_user(db)
        _migrate_works_data(db)
        _migrate_cv_items_data(db)
        _seed_templates(db, user_id=1)
    finally:
        db.close()


# Tables that need a user_id column added via migration
# NOTE: Old typed tables kept for migration compatibility (_migrate_works_data, _migrate_cv_items_data)
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
        "ALTER TABLE cv_instance_sections ADD COLUMN config_overrides TEXT",
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


def _migrate_works_data(db):
    """One-time migration: copy publications, patents, seminars, and
    software/dissertation MiscSections into the unified works table.
    Idempotent — skips if works table already has rows."""
    import re, json, logging
    from sqlalchemy import text

    log = logging.getLogger("cvbuilder.migrate")

    # Idempotency guard
    if db.query(models.Work).count() > 0:
        return

    # Check if any source data exists
    pub_count = db.query(models.Publication).count()
    patent_count = db.query(models.Patent).count()
    seminar_count = db.query(models.Seminar).count()
    misc_sw = db.query(models.MiscSection).filter_by(section="software").count()
    misc_dis = db.query(models.MiscSection).filter_by(section="dissertation").count()
    total_source = pub_count + patent_count + seminar_count + misc_sw + misc_dis
    if total_source == 0:
        return

    log.info("Migrating %d source rows to works table", total_source)

    def _parse_year_int(val):
        """Extract 4-digit year from string/int, return (year_int, raw_or_None)."""
        if val is None:
            return None, None
        if isinstance(val, int):
            return val, None
        s = str(val).strip()
        m = re.search(r'\d{4}', s)
        if m:
            year_int = int(m.group())
            # If the string is just the year, no need for year_raw
            if s == m.group():
                return year_int, None
            return year_int, s
        # Non-numeric (e.g., "in press")
        return None, s if s else None

    def _parse_month(date_str):
        """Try to extract month from a date string."""
        if not date_str:
            return None
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        }
        lower = str(date_str).lower()
        for name, num in months.items():
            if name in lower:
                return num
        return None

    # Build ID remapping: (section_key, old_id) → new_work_id
    id_remap = {}

    # --- 1. Publications ---
    for pub in db.query(models.Publication).all():
        year_int, year_raw = _parse_year_int(pub.year)
        data = {}
        if pub.journal:
            data["journal"] = pub.journal
        if pub.volume:
            data["volume"] = pub.volume
        if pub.issue:
            data["issue"] = pub.issue
        if pub.pages:
            data["pages"] = pub.pages
        if pub.select_flag:
            data["select_flag"] = True
        if pub.conference:
            data["conference"] = pub.conference
        if pub.pres_type:
            data["pres_type"] = pub.pres_type
        if pub.publisher:
            data["publisher"] = pub.publisher
        if pub.preprint_doi:
            data["preprint_doi"] = pub.preprint_doi
        if pub.published_doi:
            data["published_doi"] = pub.published_doi
        if year_raw:
            data["year_raw"] = year_raw

        work = models.Work(
            user_id=pub.user_id,
            work_type=pub.type,
            title=pub.title,
            year=year_int,
            doi=pub.doi,
            data=data,
        )
        db.add(work)
        db.flush()

        # Copy authors with role flag conversion
        authors = sorted(pub.authors, key=lambda a: a.author_order)
        for a in authors:
            wa = models.WorkAuthor(
                work_id=work.id,
                author_name=a.author_name,
                author_order=a.author_order,
                student=a.student,
            )
            db.add(wa)
        db.flush()

        # Convert pub-level role markers to per-author flags
        if authors:
            work_authors = sorted(
                db.query(models.WorkAuthor).filter_by(work_id=work.id).all(),
                key=lambda a: a.author_order,
            )
            if pub.corr and work_authors:
                work_authors[0].corresponding = True
            if pub.cofirsts and pub.cofirsts > 0:
                for wa in work_authors[:pub.cofirsts]:
                    wa.cofirst = True
            if pub.coseniors and pub.coseniors > 0:
                for wa in work_authors[-pub.coseniors:]:
                    wa.cosenior = True

        # Map section keys for publications
        section_key = f"publications_{pub.type}"
        id_remap[(section_key, pub.id)] = work.id

    # --- 2. Patents ---
    for patent in db.query(models.Patent).all():
        data = {}
        if patent.number:
            data["identifier"] = patent.number
        if patent.status:
            data["status"] = patent.status

        work = models.Work(
            user_id=patent.user_id,
            work_type="patents",
            title=patent.name,
            data=data,
        )
        db.add(work)
        db.flush()
        for a in (patent.authors or []):
            db.add(models.WorkAuthor(
                work_id=work.id,
                author_name=a.author_name,
                author_order=a.author_order,
            ))
        id_remap[("patents", patent.id)] = work.id

    # --- 3. Seminars ---
    for sem in db.query(models.Seminar).all():
        year_int, year_raw = _parse_year_int(sem.date)
        month_int = _parse_month(sem.date)
        data = {}
        if sem.org:
            data["institution"] = sem.org
        if sem.event:
            data["conference"] = sem.event
        if sem.location:
            data["location"] = sem.location
        if year_raw:
            data["date_raw"] = year_raw

        work = models.Work(
            user_id=sem.user_id,
            work_type="seminars",
            title=sem.title,
            year=year_int,
            month=month_int,
            data=data,
        )
        db.add(work)
        db.flush()
        id_remap[("seminars", sem.id)] = work.id

    # --- 4. Software (MiscSection) ---
    for ms in db.query(models.MiscSection).filter_by(section="software").all():
        ms_data = ms.data or {}
        year_int, year_raw = _parse_year_int(ms_data.get("year"))
        data = {}
        if ms_data.get("publisher"):
            data["publisher"] = ms_data["publisher"]
        if ms_data.get("url"):
            data["url"] = ms_data["url"]
        if year_raw:
            data["year_raw"] = year_raw

        work = models.Work(
            user_id=ms.user_id,
            work_type="software",
            title=ms_data.get("title"),
            year=year_int,
            data=data,
        )
        db.add(work)
        db.flush()

        # Parse comma-separated authors string → WorkAuthor rows
        authors_str = ms_data.get("authors", "")
        if authors_str:
            for i, name in enumerate(a.strip() for a in authors_str.split(",") if a.strip()):
                db.add(models.WorkAuthor(
                    work_id=work.id,
                    author_name=name,
                    author_order=i,
                ))
        id_remap[("software", ms.id)] = work.id

    # --- 5. Dissertation (MiscSection) ---
    for ms in db.query(models.MiscSection).filter_by(section="dissertation").all():
        ms_data = ms.data or {}
        year_int, year_raw = _parse_year_int(ms_data.get("year"))
        data = {}
        if ms_data.get("institution"):
            data["institution"] = ms_data["institution"]
        if year_raw:
            data["year_raw"] = year_raw

        work = models.Work(
            user_id=ms.user_id,
            work_type="dissertation",
            title=ms_data.get("title"),
            year=year_int,
            data=data,
        )
        db.add(work)
        db.flush()
        id_remap[("dissertation", ms.id)] = work.id

    db.flush()

    # --- 6. Remap CVInstanceItem IDs ---
    if id_remap:
        all_items = db.query(models.CVInstanceItem).all()
        for item in all_items:
            section = item.section
            section_key = section.section_key
            new_id = id_remap.get((section_key, item.item_id))
            if new_id is not None:
                item.item_id = new_id

    db.commit()
    log.info("Works migration complete: %d works created, %d IDs remapped",
             db.query(models.Work).count(), len(id_remap))


def _migrate_cv_items_data(db):
    """One-time migration: copy typed section models and remaining MiscSections
    into the unified cv_items table. Idempotent — skips if cv_items already has rows."""
    import re, logging
    from sqlalchemy import text
    from app.services.sort import compute_sort_date

    log = logging.getLogger("cvbuilder.migrate")

    # Idempotency guard
    if db.query(models.CVItem).count() > 0:
        return

    # Check if any source data exists
    source_count = sum(
        db.query(m).count() for m in [
            models.Education, models.Experience, models.Consulting, models.Membership,
            models.Panel, models.Symposium, models.Class, models.Grant,
            models.Award, models.Press, models.Trainee, models.Committee,
        ]
    )
    misc_count = db.query(models.MiscSection).filter(
        models.MiscSection.section.notin_(["software", "dissertation"])
    ).count()
    if source_count + misc_count == 0:
        return

    log.info("Migrating %d typed + %d misc rows to cv_items", source_count, misc_count)

    id_remap: dict[tuple[str, int], int] = {}

    def _add_item(section, data, sort_order, user_id, old_section_key=None, old_id=None):
        item = models.CVItem(
            user_id=user_id, section=section, data=data,
            sort_order=sort_order,
            sort_date=compute_sort_date(section, data),
        )
        db.add(item)
        db.flush()
        if old_section_key and old_id:
            id_remap[(old_section_key, old_id)] = item.id
        return item

    # --- Education ---
    for e in db.query(models.Education).all():
        data = {}
        if e.degree: data["degree"] = e.degree
        if e.year is not None: data["year"] = e.year
        if e.subject: data["subject"] = e.subject
        if e.school: data["school"] = e.school
        _add_item("education", data, e.sort_order, e.user_id, "education", e.id)

    # --- Experience ---
    for e in db.query(models.Experience).all():
        data = {}
        if e.title: data["title"] = e.title
        if e.years_start: data["years_start"] = e.years_start
        if e.years_end: data["years_end"] = e.years_end
        if e.employer: data["employer"] = e.employer
        _add_item("experience", data, e.sort_order, e.user_id, "experience", e.id)

    # --- Consulting ---
    for e in db.query(models.Consulting).all():
        data = {}
        if e.title: data["title"] = e.title
        if e.years: data["years"] = e.years
        if e.employer: data["employer"] = e.employer
        _add_item("consulting", data, e.sort_order, e.user_id, "consulting", e.id)

    # --- Memberships ---
    for e in db.query(models.Membership).all():
        data = {}
        if e.org: data["org"] = e.org
        if e.years: data["years"] = e.years
        _add_item("memberships", data, e.sort_order, e.user_id, "memberships", e.id)

    # --- Panels (split by type) ---
    for p in db.query(models.Panel).all():
        section = "panels_advisory" if p.type == "advisory" else "panels_grantreview"
        data = {"type": p.type}
        if p.panel: data["panel"] = p.panel
        if p.org: data["org"] = p.org
        if p.role: data["role"] = p.role
        if p.date: data["date"] = p.date
        if p.panel_id: data["panel_id"] = p.panel_id
        _add_item(section, data, p.sort_order, p.user_id, section, p.id)

    # --- Symposia ---
    for s in db.query(models.Symposium).all():
        data = {}
        if s.title: data["title"] = s.title
        if s.meeting: data["meeting"] = s.meeting
        if s.date: data["date"] = s.date
        if s.role: data["role"] = s.role
        _add_item("symposia", data, s.sort_order, s.user_id, "symposia", s.id)

    # --- Classes ---
    for c in db.query(models.Class).all():
        data = {}
        if c.class_name: data["class_name"] = c.class_name
        if c.year is not None: data["year"] = c.year
        if c.role: data["role"] = c.role
        if c.school: data["school"] = c.school
        if c.students: data["students"] = c.students
        if c.lectures: data["lectures"] = c.lectures
        if c.in_three_year: data["in_three_year"] = True
        _add_item("classes", data, c.sort_order, c.user_id, "classes", c.id)

    # --- Grants ---
    for g in db.query(models.Grant).all():
        data = {}
        if g.title: data["title"] = g.title
        if g.agency: data["agency"] = g.agency
        if g.pi: data["pi"] = g.pi
        if g.amount: data["amount"] = g.amount
        if g.years_start: data["years_start"] = g.years_start
        if g.years_end: data["years_end"] = g.years_end
        if g.role: data["role"] = g.role
        if g.id_number: data["id_number"] = g.id_number
        if g.description: data["description"] = g.description
        if g.grant_type: data["grant_type"] = g.grant_type
        if g.pcteffort is not None: data["pcteffort"] = g.pcteffort
        if g.status: data["status"] = g.status
        _add_item("grants", data, g.sort_order, g.user_id, "grants", g.id)

    # --- Awards ---
    for a in db.query(models.Award).all():
        data = {}
        if a.name: data["name"] = a.name
        if a.year: data["year"] = a.year
        if a.org: data["org"] = a.org
        if a.date: data["date"] = a.date
        _add_item("awards", data, a.sort_order, a.user_id, "awards", a.id)

    # --- Press ---
    for p in db.query(models.Press).all():
        data = {}
        if p.outlet: data["outlet"] = p.outlet
        if p.title: data["title"] = p.title
        if p.date: data["date"] = p.date
        if p.url: data["url"] = p.url
        if p.topic: data["topic"] = p.topic
        _add_item("press", data, p.sort_order, p.user_id, "press", p.id)

    # --- Trainees (split by trainee_type) ---
    for t in db.query(models.Trainee).all():
        section = "trainees_advisees" if t.trainee_type == "advisee" else "trainees_postdocs"
        data = {"trainee_type": t.trainee_type}
        if t.name: data["name"] = t.name
        if t.degree: data["degree"] = t.degree
        if t.years_start: data["years_start"] = t.years_start
        if t.years_end: data["years_end"] = t.years_end
        if t.type: data["type"] = t.type
        if t.school: data["school"] = t.school
        if t.thesis: data["thesis"] = t.thesis
        if t.current_position: data["current_position"] = t.current_position
        _add_item(section, data, t.sort_order, t.user_id, section, t.id)

    # --- Committees ---
    for c in db.query(models.Committee).all():
        data = {}
        if c.committee: data["committee"] = c.committee
        if c.org: data["org"] = c.org
        if c.role: data["role"] = c.role
        if c.dates: data["dates"] = c.dates
        _add_item("committees", data, c.sort_order, c.user_id, "committees", c.id)

    # --- MiscSections (skip software/dissertation, already in Works) ---
    for ms in db.query(models.MiscSection).filter(
        models.MiscSection.section.notin_(["software", "dissertation"])
    ).all():
        # Map misc section names to appropriate section keys
        _add_item(ms.section, ms.data or {}, ms.sort_order, ms.user_id, ms.section, ms.id)

    db.flush()

    # --- Remap CVInstanceItem IDs ---
    if id_remap:
        all_items = db.query(models.CVInstanceItem).all()
        for item in all_items:
            section = item.section
            section_key = section.section_key
            # Skip Work-based sections (already remapped in works migration)
            if section_key in ("patents", "seminars", "software", "dissertation") or section_key.startswith("publications_"):
                continue
            new_id = id_remap.get((section_key, item.item_id))
            if new_id is not None:
                item.item_id = new_id

    db.commit()
    log.info("CVItem migration complete: %d items created, %d IDs remapped",
             db.query(models.CVItem).count(), len(id_remap))


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
    _PUB_TYPES = ["papers", "preprints", "chapters", "letters", "scimeetings", "editorials"]
    total = db.query(models.Work).filter(
        models.Work.user_id == uid,
        models.Work.work_type.in_(_PUB_TYPES),
    ).count()

    def count_type(t):
        return db.query(models.Work).filter(
            models.Work.user_id == uid,
            models.Work.work_type == t,
        ).count()

    # Trainee breakdown from CVItem
    from sqlalchemy import cast, String
    trainee_items = db.query(models.CVItem).filter(
        models.CVItem.user_id == uid,
        models.CVItem.section.in_(["trainees_advisees", "trainees_postdocs"]),
    ).all()
    trainee_type_counts: dict[str, int] = {}
    for t in trainee_items:
        tt = (t.data or {}).get("trainee_type", t.section.replace("trainees_", ""))
        trainee_type_counts[tt] = trainee_type_counts.get(tt, 0) + 1
    trainee_rows = list(trainee_type_counts.items())

    # Grant breakdown from CVItem
    grant_items = db.query(models.CVItem).filter_by(user_id=uid, section="grants").all()
    active_grant_roles: dict[str, int] = {}
    active_grants = 0
    for g in grant_items:
        gd = g.data or {}
        if gd.get("status") == "active":
            active_grants += 1
            role = gd.get("role", "")
            if role:
                active_grant_roles[role] = active_grant_roles.get(role, 0) + 1
    active_grant_rows = sorted(active_grant_roles.items(), key=lambda x: -x[1])

    return schemas.DashboardStats(
        total_publications=total,
        papers=count_type("papers"),
        preprints=count_type("preprints"),
        chapters=count_type("chapters"),
        letters=count_type("letters"),
        scimeetings=count_type("scimeetings"),
        editorials=count_type("editorials"),
        trainees=len(trainee_items),
        grants=len(grant_items),
        active_grants=active_grants,
        profile_complete=bool(profile and profile.name),
        trainee_breakdown=[{"type": t, "count": c} for t, c in trainee_rows],
        active_grant_breakdown=[{"role": r, "count": c} for r, c in active_grant_rows],
    )
