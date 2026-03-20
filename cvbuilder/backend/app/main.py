"""CVBuilder FastAPI application."""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import create_tables, get_db
from app import models, schemas
from app.auth import get_current_user
from app.routers import admin, auth, profile, templates, export, cv_instances, works, cv_items, citations

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
app.include_router(citations.router)
app.include_router(admin.router)


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
        _migrate_press_outlets(db)
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
        # Ensure works/work_authors/cv_items tables have all columns
        # (create_all() won't alter tables that already exist)
        "ALTER TABLE works ADD COLUMN work_type VARCHAR(50)",
        "ALTER TABLE works ADD COLUMN title TEXT",
        "ALTER TABLE works ADD COLUMN year INTEGER",
        "ALTER TABLE works ADD COLUMN month INTEGER",
        "ALTER TABLE works ADD COLUMN day INTEGER",
        "ALTER TABLE works ADD COLUMN doi VARCHAR(500)",
        "ALTER TABLE works ADD COLUMN data TEXT",
        "ALTER TABLE works ADD COLUMN user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE work_authors ADD COLUMN author_name VARCHAR(300)",
        "ALTER TABLE work_authors ADD COLUMN author_order INTEGER DEFAULT 0",
        "ALTER TABLE work_authors ADD COLUMN student INTEGER DEFAULT 0",
        "ALTER TABLE work_authors ADD COLUMN corresponding INTEGER DEFAULT 0",
        "ALTER TABLE work_authors ADD COLUMN cofirst INTEGER DEFAULT 0",
        "ALTER TABLE work_authors ADD COLUMN cosenior INTEGER DEFAULT 0",
        "ALTER TABLE work_authors ADD COLUMN work_id INTEGER REFERENCES works(id)",
        "ALTER TABLE cv_items ADD COLUMN section VARCHAR(100)",
        "ALTER TABLE cv_items ADD COLUMN data TEXT",
        "ALTER TABLE cv_items ADD COLUMN sort_order INTEGER DEFAULT 0",
        "ALTER TABLE cv_items ADD COLUMN sort_date INTEGER",
        "ALTER TABLE cv_items ADD COLUMN user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE profile ADD COLUMN semantic_scholar_id VARCHAR(200)",
        "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0",
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
            is_admin=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.is_admin:
        user.is_admin = True
        db.commit()

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
    """Migration: copy publications, patents, seminars, and
    software/dissertation MiscSections into the unified works table.
    Per-user idempotent — only migrates users who have source data but no works."""
    import re, json, logging
    from sqlalchemy import text

    log = logging.getLogger("cvbuilder.migrate")

    # Build set of user IDs that have source data
    source_uids = set()
    for row in db.query(models.Publication.user_id).distinct():
        source_uids.add(row[0])
    for row in db.query(models.Patent.user_id).distinct():
        source_uids.add(row[0])
    for row in db.query(models.Seminar.user_id).distinct():
        source_uids.add(row[0])
    for row in db.query(models.MiscSection.user_id).filter(
        models.MiscSection.section.in_(["software", "dissertation"])
    ).distinct():
        source_uids.add(row[0])

    if not source_uids:
        return

    # Skip users who already have works (already migrated)
    migrated_uids = set()
    for row in db.query(models.Work.user_id).distinct():
        migrated_uids.add(row[0])
    uids_to_migrate = source_uids - migrated_uids
    if not uids_to_migrate:
        return

    log.info("Migrating works data for %d user(s)", len(uids_to_migrate))

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
    for pub in db.query(models.Publication).filter(
        models.Publication.user_id.in_(uids_to_migrate)
    ).all():
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
    for patent in db.query(models.Patent).filter(
        models.Patent.user_id.in_(uids_to_migrate)
    ).all():
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
    for sem in db.query(models.Seminar).filter(
        models.Seminar.user_id.in_(uids_to_migrate)
    ).all():
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
    for ms in db.query(models.MiscSection).filter(
        models.MiscSection.section == "software",
        models.MiscSection.user_id.in_(uids_to_migrate),
    ).all():
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

        # Parse authors (may be a list or comma-separated string)
        authors_raw = ms_data.get("authors", "")
        if isinstance(authors_raw, list):
            author_names = [a.strip() for a in authors_raw if isinstance(a, str) and a.strip()]
        elif isinstance(authors_raw, str) and authors_raw:
            author_names = [a.strip() for a in authors_raw.split(",") if a.strip()]
        else:
            author_names = []
        for i, name in enumerate(author_names):
            db.add(models.WorkAuthor(
                work_id=work.id,
                author_name=name,
                author_order=i,
            ))
        id_remap[("software", ms.id)] = work.id

    # --- 5. Dissertation (MiscSection) ---
    for ms in db.query(models.MiscSection).filter(
        models.MiscSection.section == "dissertation",
        models.MiscSection.user_id.in_(uids_to_migrate),
    ).all():
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
    """Migration: copy typed section models and remaining MiscSections
    into the unified cv_items table.
    Per-user idempotent — only migrates users who have source data but no cv_items."""
    import re, logging
    from sqlalchemy import text
    from app.services.sort import compute_sort_date

    log = logging.getLogger("cvbuilder.migrate")

    # Build set of user IDs that have source data
    _typed_models = [
        models.Education, models.Experience, models.Consulting, models.Membership,
        models.Panel, models.Symposium, models.Class, models.Grant,
        models.Award, models.Press, models.Trainee, models.Committee,
    ]
    source_uids = set()
    for m in _typed_models:
        for row in db.query(m.user_id).distinct():
            source_uids.add(row[0])
    for row in db.query(models.MiscSection.user_id).filter(
        models.MiscSection.section.notin_(["software", "dissertation"])
    ).distinct():
        source_uids.add(row[0])

    if not source_uids:
        return

    # Skip users who already have cv_items (already migrated)
    migrated_uids = set()
    for row in db.query(models.CVItem.user_id).distinct():
        migrated_uids.add(row[0])
    uids_to_migrate = source_uids - migrated_uids
    if not uids_to_migrate:
        return

    log.info("Migrating cv_items data for %d user(s)", len(uids_to_migrate))

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
    for e in db.query(models.Education).filter(models.Education.user_id.in_(uids_to_migrate)).all():
        data = {}
        if e.degree: data["degree"] = e.degree
        if e.year is not None: data["year"] = e.year
        if e.subject: data["subject"] = e.subject
        if e.school: data["school"] = e.school
        _add_item("education", data, e.sort_order, e.user_id, "education", e.id)

    # --- Experience ---
    for e in db.query(models.Experience).filter(models.Experience.user_id.in_(uids_to_migrate)).all():
        data = {}
        if e.title: data["title"] = e.title
        if e.years_start: data["years_start"] = e.years_start
        if e.years_end: data["years_end"] = e.years_end
        if e.employer: data["employer"] = e.employer
        _add_item("experience", data, e.sort_order, e.user_id, "experience", e.id)

    # --- Consulting ---
    for e in db.query(models.Consulting).filter(models.Consulting.user_id.in_(uids_to_migrate)).all():
        data = {}
        if e.title: data["title"] = e.title
        if e.years: data["years"] = e.years
        if e.employer: data["employer"] = e.employer
        _add_item("consulting", data, e.sort_order, e.user_id, "consulting", e.id)

    # --- Memberships ---
    for e in db.query(models.Membership).filter(models.Membership.user_id.in_(uids_to_migrate)).all():
        data = {}
        if e.org: data["org"] = e.org
        if e.years: data["years"] = e.years
        _add_item("memberships", data, e.sort_order, e.user_id, "memberships", e.id)

    # --- Panels (split by type) ---
    for p in db.query(models.Panel).filter(models.Panel.user_id.in_(uids_to_migrate)).all():
        section = "panels_advisory" if p.type == "advisory" else "panels_grantreview"
        data = {"type": p.type}
        if p.panel: data["panel"] = p.panel
        if p.org: data["org"] = p.org
        if p.role: data["role"] = p.role
        if p.date: data["date"] = p.date
        if p.panel_id: data["panel_id"] = p.panel_id
        _add_item(section, data, p.sort_order, p.user_id, section, p.id)

    # --- Symposia ---
    for s in db.query(models.Symposium).filter(models.Symposium.user_id.in_(uids_to_migrate)).all():
        data = {}
        if s.title: data["title"] = s.title
        if s.meeting: data["meeting"] = s.meeting
        if s.date: data["date"] = s.date
        if s.role: data["role"] = s.role
        _add_item("symposia", data, s.sort_order, s.user_id, "symposia", s.id)

    # --- Classes ---
    for c in db.query(models.Class).filter(models.Class.user_id.in_(uids_to_migrate)).all():
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
    for g in db.query(models.Grant).filter(models.Grant.user_id.in_(uids_to_migrate)).all():
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
    for a in db.query(models.Award).filter(models.Award.user_id.in_(uids_to_migrate)).all():
        data = {}
        if a.name: data["name"] = a.name
        if a.year: data["year"] = a.year
        if a.org: data["org"] = a.org
        if a.date: data["date"] = a.date
        _add_item("awards", data, a.sort_order, a.user_id, "awards", a.id)

    # --- Press ---
    for p in db.query(models.Press).filter(models.Press.user_id.in_(uids_to_migrate)).all():
        data = {}
        if p.outlet: data["outlet"] = p.outlet
        if p.title: data["title"] = p.title
        if p.date: data["date"] = p.date
        if p.url: data["url"] = p.url
        if p.topic: data["topic"] = p.topic
        _add_item("press", data, p.sort_order, p.user_id, "press", p.id)

    # --- Trainees (split by trainee_type) ---
    for t in db.query(models.Trainee).filter(models.Trainee.user_id.in_(uids_to_migrate)).all():
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
    for c in db.query(models.Committee).filter(models.Committee.user_id.in_(uids_to_migrate)).all():
        data = {}
        if c.committee: data["committee"] = c.committee
        if c.org: data["org"] = c.org
        if c.role: data["role"] = c.role
        if c.dates: data["dates"] = c.dates
        _add_item("committees", data, c.sort_order, c.user_id, "committees", c.id)

    # --- MiscSections (skip software/dissertation, already in Works) ---
    for ms in db.query(models.MiscSection).filter(
        models.MiscSection.section.notin_(["software", "dissertation"]),
        models.MiscSection.user_id.in_(uids_to_migrate),
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


def _migrate_press_outlets(db):
    """Convert press CVItems from data.outlet (string) → data.outlets (list)."""
    import json as _json
    items = db.query(models.CVItem).filter_by(section="press").all()
    for item in items:
        d = dict(item.data or {})
        if "outlets" in d and isinstance(d["outlets"], list):
            continue  # already migrated
        if "outlet" in d:
            outlet_str = d.pop("outlet")
            d["outlets"] = [o.strip() for o in outlet_str.split(", ")] if outlet_str else []
            item.data = d
    db.commit()


# ---------------------------------------------------------------------------
# Section heading labels used by all templates
# ---------------------------------------------------------------------------
_HEADINGS = {
    "group_heading":              "",
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
    "mentorship":                 "Mentorship",
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
    "citation_metrics":           "Citation Metrics",
}

# ---------------------------------------------------------------------------
# Template definitions: name → (description, style_preset_name, ordered sections)
# Each section is a tuple of (section_key, config_override_or_None).
# Group headings use section_key="group_heading" with {"heading": "..."}.
# ---------------------------------------------------------------------------
_TEMPLATES = {
    "Academic CV": (
        "Full academic CV with all sections",
        "academic",
        [
            ("group_heading", {"heading": "Education and Training"}),
            ("education", None),
            ("experience", None),
            ("group_heading", {"heading": "Professional Activities"}),
            ("memberships", None),
            ("panels_advisory", None),
            ("panels_grantreview", None),
            ("symposia", None),
            ("patents", None),
            ("group_heading", {"heading": "Editorial and Other Peer Review Activities"}),
            ("editorial", None),
            ("peerrev", None),
            ("group_heading", {"heading": "Honors and Awards"}),
            ("awards", None),
            ("group_heading", {"heading": "Publications"}),
            ("publications_papers", None),
            ("publications_editorials", None),
            ("publications_preprints", None),
            ("publications_chapters", None),
            ("publications_letters", None),
            ("group_heading", {"heading": "Practice Activities"}),
            ("policypres", None),
            ("policycons", None),
            ("press", None),
            ("software", None),
            ("otherpractice", None),
            ("group_heading", {"heading": "Teaching"}),
            ("trainees_advisees", None),
            ("trainees_postdocs", None),
            ("mentorship", None),
            ("departmentalOrals", None),
            ("finaldefense", None),
            ("schoolwideOrals", None),
            ("classes", None),
            ("group_heading", {"heading": "Research Grant Participation"}),
            ("grants", None),
            ("group_heading", {"heading": "Academic Service"}),
            ("committees", None),
            ("otherservice", None),
            ("group_heading", {"heading": "Presentations"}),
            ("publications_scimeetings", None),
            ("chairedsessions", None),
            ("seminars", None),
            ("consulting", None),
            ("dissertation", None),
            ("citation_metrics", None),
        ],
    ),
    "UNC CV": (
        "University of North Carolina format — sans-serif, Carolina Blue accents, "
        "bibliography-forward section order",
        "unc",
        [
            ("education", None),
            ("experience", None),
            ("group_heading", {"heading": "Honors and Awards"}),
            ("awards", None),
            ("group_heading", {"heading": "Memberships"}),
            ("memberships", None),
            ("group_heading", {"heading": "Bibliography and Products of Scholarship"}),
            ("publications_papers", None),
            ("patents", None),
            ("publications_editorials", None),
            ("publications_chapters", None),
            ("publications_preprints", None),
            ("publications_letters", None),
            ("publications_scimeetings", None),
            ("seminars", None),
            ("software", None),
            ("dissertation", None),
            ("group_heading", {"heading": "Teaching Record"}),
            ("classes", None),
            ("trainees_advisees", None),
            ("trainees_postdocs", None),
            ("mentorship", None),
            ("departmentalOrals", None),
            ("finaldefense", None),
            ("schoolwideOrals", None),
            ("group_heading", {"heading": "Contracts and Grants"}),
            ("grants", None),
            ("group_heading", {"heading": "Professional Service"}),
            ("committees", None),
            ("otherservice", None),
            ("panels_advisory", None),
            ("panels_grantreview", None),
            ("symposia", None),
            ("chairedsessions", None),
            ("editorial", None),
            ("peerrev", None),
            ("consulting", None),
            ("group_heading", {"heading": "Public Health Practice and Communication"}),
            ("policypres", None),
            ("policycons", None),
            ("press", None),
            ("otherpractice", None),
            ("citation_metrics", None),
        ],
    ),
    "Hopkins CV": (
        "Johns Hopkins format — Times New Roman serif, Heritage Blue headings, "
        "centered CURRICULUM VITAE title, practice-activities section",
        "hopkins",
        [
            ("group_heading", {"heading": "Education and Training"}),
            ("education", None),
            ("experience", None),
            ("group_heading", {"heading": "Professional Activities"}),
            ("memberships", None),
            ("panels_advisory", None),
            ("symposia", None),
            ("patents", None),
            ("panels_grantreview", None),
            ("group_heading", {"heading": "Editorial and Other Peer Review Activities"}),
            ("editorial", None),
            ("peerrev", None),
            ("group_heading", {"heading": "Honors and Awards"}),
            ("awards", None),
            ("group_heading", {"heading": "Publications"}),
            ("publications_papers", None),
            ("publications_editorials", None),
            ("publications_chapters", None),
            ("publications_letters", None),
            ("group_heading", {"heading": "Practice Activities"}),
            ("policypres", None),
            ("policycons", None),
            ("press", None),
            ("software", None),
            ("otherpractice", None),
            ("group_heading", {"heading": "Teaching"}),
            ("trainees_advisees", None),
            ("trainees_postdocs", None),
            ("mentorship", None),
            ("departmentalOrals", None),
            ("finaldefense", None),
            ("schoolwideOrals", None),
            ("classes", None),
            ("group_heading", {"heading": "Research Grant Participation"}),
            ("grants", None),
            ("group_heading", {"heading": "Academic Service"}),
            ("committees", None),
            ("otherservice", None),
            ("group_heading", {"heading": "Presentations"}),
            ("publications_scimeetings", None),
            ("chairedsessions", None),
            ("seminars", None),
            ("publications_preprints", None),
            ("dissertation", None),
            ("consulting", None),
            ("citation_metrics", None),
        ],
    ),
    "UNIGE CV": (
        "University of Geneva format — sans-serif, RedViolet section headings, "
        "research-supervision-forward structure",
        "unige",
        [
            ("group_heading", {"heading": "Personal Data"}),
            ("education", None),
            ("experience", None),
            ("group_heading", {"heading": "Research Outputs"}),
            ("publications_papers", None),
            ("publications_preprints", None),
            ("publications_chapters", None),
            ("publications_letters", None),
            ("publications_editorials", None),
            ("group_heading", {"heading": "Research Funding and Grants"}),
            ("grants", None),
            ("group_heading", {"heading": "Research Supervision and Mentoring"}),
            ("trainees_advisees", None),
            ("trainees_postdocs", None),
            ("mentorship", None),
            ("group_heading", {"heading": "Other Scientific Activities"}),
            ("policypres", None),
            ("policycons", None),
            ("press", None),
            ("otherpractice", None),
            ("panels_advisory", None),
            ("panels_grantreview", None),
            ("symposia", None),
            ("seminars", None),
            ("publications_scimeetings", None),
            ("chairedsessions", None),
            ("editorial", None),
            ("peerrev", None),
            ("memberships", None),
            ("classes", None),
            ("awards", None),
            ("patents", None),
            ("software", None),
            ("dissertation", None),
            ("committees", None),
            ("otherservice", None),
            ("consulting", None),
            ("departmentalOrals", None),
            ("finaldefense", None),
            ("schoolwideOrals", None),
            ("citation_metrics", None),
        ],
    ),
}


def _seed_templates(db, user_id: int = 1):
    """Insert new templates and add any missing sections to existing templates.

    Each entry in the sections list is a tuple of (section_key, config_override_or_None).
    Group headings (section_key="group_heading") are always appended since multiple
    can exist; regular sections are only added if not already present.
    """
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

        existing_rows = (
            db.query(models.TemplateSection)
            .filter_by(template_id=tmpl.id)
            .all()
        )
        existing_keys = {s.section_key for s in existing_rows}
        has_group_headings = any(
            s.section_key == "group_heading" for s in existing_rows
        )

        # If the template already has group headings, skip re-seeding entirely
        if has_group_headings:
            continue

        # For brand-new templates, add all sections in order.
        # For existing templates, append only missing regular sections.
        next_order = len(existing_rows)
        for key, config_override in sections:
            if key == "group_heading":
                # Group headings are always new rows (multiple allowed)
                db.add(models.TemplateSection(
                    template_id=tmpl.id,
                    section_key="group_heading",
                    enabled=True,
                    section_order=next_order,
                    config=config_override or {},
                ))
                next_order += 1
            elif key not in existing_keys:
                heading = (
                    (config_override or {}).get("heading")
                    or _HEADINGS.get(key, key.replace("_", " ").title())
                )
                db.add(models.TemplateSection(
                    template_id=tmpl.id,
                    section_key=key,
                    enabled=True,
                    section_order=next_order,
                    config={"heading": heading},
                ))
                existing_keys.add(key)
                next_order += 1

        # For existing templates that just got group headings added,
        # reorder all sections to match the canonical template order.
        if name in existing_tmpls:
            all_rows = (
                db.query(models.TemplateSection)
                .filter_by(template_id=tmpl.id)
                .order_by(models.TemplateSection.section_order)
                .all()
            )
            # Build target order from _TEMPLATES definition
            target_keys = [k for k, _ in sections]
            # Index existing rows by key (group_headings: collect in order)
            keyed_rows: dict[str, list] = {}
            for row in all_rows:
                keyed_rows.setdefault(row.section_key, []).append(row)
            # Assign new order following the template definition
            order = 0
            used_group_idx = 0
            for tkey in target_keys:
                if tkey == "group_heading":
                    # Pick group headings added during this seed (they have
                    # the config from the template definition)
                    gh_rows = keyed_rows.get("group_heading", [])
                    if used_group_idx < len(gh_rows):
                        gh_rows[used_group_idx].section_order = order
                        used_group_idx += 1
                        order += 1
                else:
                    rows = keyed_rows.get(tkey, [])
                    if rows:
                        rows[0].section_order = order
                        order += 1
            # Any remaining rows not in the template definition go at the end
            placed = set()
            for tkey in target_keys:
                if tkey == "group_heading":
                    continue
                placed.add(tkey)
            for row in all_rows:
                if row.section_key not in placed and row.section_key != "group_heading":
                    row.section_order = order
                    order += 1

    db.commit()


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/dashboard", response_model=schemas.DashboardData)
def dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    uid = current_user.id
    profile = db.query(models.Profile).filter_by(user_id=uid).first()
    profile_complete = bool(profile and profile.name)

    # ---- Scholarly Output ----
    _PUB_TYPES = ["papers", "preprints", "chapters", "letters", "scimeetings", "editorials"]
    all_works = db.query(models.Work).filter(
        models.Work.user_id == uid,
        models.Work.work_type.in_(_PUB_TYPES),
    ).all()

    counts_by_type: dict[str, int] = {}
    year_counts: dict[int, int] = {}
    first_author = 0
    corresponding_author = 0
    senior_author = 0
    student_led = 0

    # Use profile name to identify the CV owner in author lists
    from app.services.pdf import _bold_self
    profile_name = profile.name if profile else ""

    def _is_me(author_name: str) -> bool:
        """Check if an author name matches the CV owner."""
        if not profile_name or not author_name:
            return False
        return "<strong>" in _bold_self(author_name, profile_name)

    for w in all_works:
        counts_by_type[w.work_type] = counts_by_type.get(w.work_type, 0) + 1
        if w.year:
            year_counts[w.year] = year_counts.get(w.year, 0) + 1

        authors = sorted(w.authors, key=lambda a: a.author_order)
        if authors:
            # Find which author is the CV owner
            my_author = next((a for a in authors if _is_me(a.author_name)), None)
            if my_author:
                # First/co-first: I'm the first author or marked cofirst
                if my_author.author_order == authors[0].author_order or my_author.cofirst:
                    first_author += 1
                # Corresponding
                if my_author.corresponding:
                    corresponding_author += 1
                # Senior/co-senior: I'm the last author or marked cosenior
                if my_author.author_order == authors[-1].author_order or my_author.cosenior:
                    senior_author += 1
            # Student-led: first author is a student
            if authors[0].student:
                student_led += 1

    works_by_year = sorted(
        [{"year": y, "count": c} for y, c in year_counts.items()],
        key=lambda x: x["year"],
    )

    # Citation metrics from Work data blobs
    from app.services.fetch_citations import compute_aggregate
    works_with_citations = []
    for w in all_works:
        wd = w.data or {}
        if "cited_by_count" in wd:
            works_with_citations.append(wd)
    if works_with_citations:
        agg = compute_aggregate(works_with_citations)
        h_index = agg["h_index"]
        i10_index = agg["i10_index"]
        total_citations = agg["total_citations"]
        citations_by_year = sorted(
            [{"year": y, "count": c} for y, c in agg.get("yearly_counts", {}).items()],
            key=lambda x: x["year"],
        )
    else:
        h_index = i10_index = total_citations = 0
        citations_by_year = []

    scholarly = schemas.ScholarlyOutputStats(
        total_works=len(all_works),
        counts_by_type=counts_by_type,
        works_by_year=works_by_year,
        first_author_count=first_author,
        corresponding_author_count=corresponding_author,
        senior_author_count=senior_author,
        student_led_count=student_led,
        h_index=h_index,
        i10_index=i10_index,
        total_citations=total_citations,
        citations_by_year=citations_by_year,
    )

    # ---- Teaching & Mentorship ----
    import datetime as _dt
    five_year_cutoff = _dt.date.today().year - 4  # inclusive 5-year window
    class_items = db.query(models.CVItem).filter_by(user_id=uid, section="classes").all()
    unique_courses = set()
    courses_three_year = 0
    role_counts: dict[str, int] = {}
    role_counts_5y: dict[str, int] = {}
    for c in class_items:
        cd = c.data or {}
        name = cd.get("class_name", "")
        if name:
            unique_courses.add(name)
        if cd.get("in_three_year"):
            courses_three_year += 1
        role = (cd.get("role") or "Unknown").strip()
        role_counts[role] = role_counts.get(role, 0) + 1
        yr = cd.get("year")
        if yr and int(yr) >= five_year_cutoff:
            role_counts_5y[role] = role_counts_5y.get(role, 0) + 1

    trainee_items = db.query(models.CVItem).filter(
        models.CVItem.user_id == uid,
        models.CVItem.section.in_(["trainees_advisees", "trainees_postdocs"]),
    ).all()

    # Classify trainees into mentorship categories
    def _classify_trainee(item: models.CVItem) -> str:
        if item.section == "trainees_postdocs":
            return "postdoctoral"
        d = item.data or {}
        degree = (d.get("degree") or "").strip().upper()
        if not degree:
            return "other"
        doctoral_kw = ("PHD", "DRPH", "SCD", "DVM", "MD", "DO", "DPHIL",
                        "EDD", "DBA", "JD", "DNAP", "DNS", "DOCTOR")
        masters_kw = ("MS", "MPH", "MA", "MSPH", "MHS", "MPHIL", "MBA",
                       "MSC", "MPA", "MSW", "MFA", "MED", "MASTER")
        undergrad_kw = ("BS", "BA", "BSC", "BFA", "AB", "UNDERGRAD", "BACHELOR")
        for kw in doctoral_kw:
            if kw in degree:
                return "doctoral"
        for kw in masters_kw:
            if kw in degree:
                return "masters"
        for kw in undergrad_kw:
            if kw in degree:
                return "undergraduate"
        return "other"

    def _trainee_detail(item: models.CVItem) -> schemas.TraineeDetail:
        d = item.data or {}
        ys = d.get("years_start", "")
        ye = d.get("years_end", "")
        period = f"{ys}–{ye}" if ye else f"{ys}–present" if ys else ""
        return schemas.TraineeDetail(
            name=d.get("name", ""),
            degree=d.get("degree", ""),
            advisor_type=d.get("type", ""),
            institution=d.get("school", ""),
            period=period,
            current_position=d.get("current_position", ""),
            is_current=not ye or ye.lower().strip() == "present",
        )

    mentorship_cats: dict[str, schemas.MentorshipCategory] = {
        k: schemas.MentorshipCategory() for k in
        ("postdoctoral", "doctoral", "masters", "undergraduate", "other")
    }
    trainee_type_counts: dict[str, int] = {}
    current_trainees = 0
    for t in trainee_items:
        td = t.data or {}
        tt = td.get("trainee_type", t.section.replace("trainees_", ""))
        trainee_type_counts[tt] = trainee_type_counts.get(tt, 0) + 1
        ye_val = (td.get("years_end") or "").strip().lower()
        is_current = not ye_val or ye_val == "present"
        if is_current:
            current_trainees += 1

        cat_key = _classify_trainee(t)
        cat = mentorship_cats[cat_key]
        cat.count += 1
        if is_current:
            cat.current += 1
        cat.trainees.append(_trainee_detail(t))

    teaching = schemas.TeachingMentorshipStats(
        teaching=schemas.TeachingStats(
            courses_total=len(class_items),
            courses_three_year=courses_three_year,
            unique_courses=len(unique_courses),
            by_role=sorted(
                [schemas.RoleCount(role=r, count=n) for r, n in role_counts.items()],
                key=lambda x: x.count, reverse=True,
            ),
            by_role_five_year=sorted(
                [schemas.RoleCount(role=r, count=n) for r, n in role_counts_5y.items()],
                key=lambda x: x.count, reverse=True,
            ),
        ),
        mentorship=schemas.MentorshipStats(
            total=len(trainee_items),
            current=current_trainees,
            **mentorship_cats,
        ),
        # Legacy flat fields
        courses_total=len(class_items),
        courses_three_year=courses_three_year,
        unique_courses=len(unique_courses),
        trainees_total=len(trainee_items),
        trainee_breakdown=[{"type": t, "count": c} for t, c in trainee_type_counts.items()],
        current_trainees=current_trainees,
    )

    # ---- Funding ----
    import re as _re
    grant_items = db.query(models.CVItem).filter_by(user_id=uid, section="grants").all()
    total_amount = 0.0

    # Buckets for active / completed
    buckets: dict[str, dict] = {
        "active": {"roles": {}, "grants": [], "amount": 0.0},
        "completed": {"roles": {}, "grants": [], "amount": 0.0},
    }

    def _parse_amount(amt_str: str) -> float:
        if not amt_str:
            return 0.0
        nums = _re.findall(r'[\d,]+\.?\d*', str(amt_str))
        if nums:
            try:
                return float(nums[0].replace(",", ""))
            except ValueError:
                pass
        return 0.0

    def _fmt_amount(val: float) -> str:
        if val >= 1_000_000:
            return f"${val/1_000_000:,.1f}M"
        if val > 0:
            return f"${val:,.0f}"
        return ""

    for g in grant_items:
        gd = g.data or {}
        amt_str = gd.get("amount", "")
        amt = _parse_amount(amt_str)
        total_amount += amt

        status = gd.get("status", "")
        if status not in buckets:
            continue
        bucket = buckets[status]
        bucket["amount"] += amt

        role = gd.get("role", "")
        if role:
            role_key = "PI" if role.upper().strip() in ("PI", "MPI", "CONTACT PI") else "Other"
            bucket["roles"][role_key] = bucket["roles"].get(role_key, 0) + 1

        period_start = gd.get("years_start", "")
        period_end = gd.get("years_end", "")
        period = f"{period_start}–{period_end}" if period_end else f"{period_start}–present" if period_start else ""
        bucket["grants"].append(schemas.GrantDetail(
            title=gd.get("title", ""),
            agency=gd.get("agency", ""),
            role=role,
            period=period,
            amount=str(amt_str),
            id_number=gd.get("id_number", ""),
        ))

    def _build_category(bucket: dict) -> schemas.GrantCategoryStats:
        return schemas.GrantCategoryStats(
            count=len(bucket["grants"]),
            total_amount=bucket["amount"],
            total_amount_display=_fmt_amount(bucket["amount"]),
            by_role=sorted(
                [{"role": r, "count": c} for r, c in bucket["roles"].items()],
                key=lambda x: -x["count"],
            ),
            grants=bucket["grants"],
        )

    funding = schemas.FundingStats(
        grants_total=len(grant_items),
        total_funding_amount=_fmt_amount(total_amount),
        total_funding_raw=total_amount,
        active=_build_category(buckets["active"]),
        completed=_build_category(buckets["completed"]),
    )

    # ---- Service ----
    def _count_section(section: str) -> int:
        return db.query(models.CVItem).filter_by(user_id=uid, section=section).count()

    committees = _count_section("committees")
    advisory = _count_section("panels_advisory")
    grantreview = _count_section("panels_grantreview")
    symposia = _count_section("symposia")
    editorial = _count_section("editorial")
    peerrev = _count_section("peerrev")

    service_breakdown = []
    for label, count in [
        ("Committees", committees),
        ("Advisory Panels", advisory),
        ("Grant Review Panels", grantreview),
        ("Organized Sessions", symposia),
        ("Editorial", editorial),
        ("Peer Review", peerrev),
    ]:
        if count > 0:
            service_breakdown.append({"label": label, "count": count})

    service = schemas.ServiceStats(
        committees=committees,
        advisory_panels=advisory,
        grant_review_panels=grantreview,
        symposia=symposia,
        editorial=editorial,
        peer_review=peerrev,
        service_breakdown=service_breakdown,
    )

    return schemas.DashboardData(
        profile_complete=profile_complete,
        scholarly_output=scholarly,
        teaching_mentorship=teaching,
        funding=funding,
        service=service,
    )
