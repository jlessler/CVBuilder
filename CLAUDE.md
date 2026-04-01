# CVBuilder — Claude Code Guide

## Project layout

```
cvbuilder/
├── backend/               # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── main.py        # Startup, migrations, template seeding, _HEADINGS
│   │   ├── models.py      # SQLAlchemy ORM models (User, Profile, Work, CVItem, etc.)
│   │   ├── schemas.py     # Pydantic request/response schemas
│   │   ├── auth.py        # JWT authentication + bcrypt password hashing
│   │   ├── database.py    # SQLAlchemy engine + session factory
│   │   ├── routers/
│   │   │   ├── auth.py           # Register, login, password change
│   │   │   ├── profile.py       # Profile CRUD (name, contact, addresses)
│   │   │   ├── cv_items.py      # CRUD for all CVItem-backed sections
│   │   │   ├── works.py         # CRUD for scholarly works, DOI lookup, sync, enrichment
│   │   │   ├── templates.py     # Template CRUD, preview, PDF export, _build_cv_data
│   │   │   ├── cv_instances.py  # CV instance CRUD, section curation, SECTION_KEY_MAP
│   │   │   ├── export.py        # YAML import/export
│   │   │   ├── citations.py     # Citation metrics from OpenAlex
│   │   │   ├── section_definitions.py  # Custom section type CRUD
│   │   │   └── admin.py         # User management (admin-only)
│   │   └── services/
│   │       ├── sort.py           # sort_items, SECTION_SORT_KEY, SORT_DATE_FIELD_MAP
│   │       ├── pdf.py            # WeasyPrint HTML→PDF, Jinja2, generate_css(), THEME_PRESETS
│   │       ├── fetch_pubs.py     # Publication sync from ORCID, PubMed, Crossref
│   │       ├── doi.py            # DOI lookup, search, metadata diff
│   │       ├── name_parser.py    # Author name parsing (parse_author_name)
│   │       ├── name_format.py    # Citation-style author formatting
│   │       ├── fetch_citations.py # Citation metrics from OpenAlex
│   │       └── yaml_import.py    # YAML CV/refs import logic
│   └── cv_templates/      # Jinja2 templates
│       ├── base.html      # Main CV renderer — one {% elif key == '...' %} block per section
│       └── sections/      # Included partials (publications, grants, panels, trainees, …)
├── frontend/              # React 19 + Vite + Tailwind
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx     # Overview stats (works, teaching, funding, service)
│       │   ├── Sections.tsx      # TABS + BUILTIN_FIELDS for all CV section editors
│       │   ├── Publications.tsx  # Scholarly works: CRUD, sync, DOI enrichment, complete fields
│       │   ├── Templates.tsx     # Template composer + style editor
│       │   ├── CVInstances.tsx   # CV instances: curation, overrides, preview/PDF
│       │   ├── Profile.tsx       # User profile + identifiers
│       │   ├── Export.tsx        # YAML import/export
│       │   ├── Users.tsx         # Admin user management
│       │   ├── Login.tsx         # Authentication
│       │   └── Register.tsx      # Registration
│       ├── components/
│       │   ├── ui.tsx                    # Shared UI primitives (Button, Input, Modal, etc.)
│       │   ├── SectionComposer.tsx       # Drag-and-drop section ordering (ALL_SECTIONS)
│       │   ├── SectionPickerModal.tsx    # Section selector with grouping
│       │   ├── SectionDefinitionEditor.tsx  # Custom section type editor
│       │   ├── Layout.tsx                # Sidebar nav + main content
│       │   └── ProtectedRoute.tsx        # Auth guard
│       └── lib/api.ts            # Axios client + TypeScript interfaces
├── docs/                  # Architecture documentation (see docs/*.md)
└── data/                  # SQLite DB (auto-created; not committed)
```

## Dev servers

```bash
# Backend (port 8000)
cd cvbuilder/backend
.venv/bin/uvicorn app.main:app --reload

# Frontend (port 5173)
cd cvbuilder/frontend
npm run dev
```

## Key conventions

### Adding a new CVItem section (education, grants, service, etc.)
1. **Sort date** — add entry to `SORT_DATE_FIELD_MAP` in `services/sort.py`
2. **Template rendering** — add `{% elif key == '...' %}` block in `cv_templates/base.html`
3. **Headings** — add to `_HEADINGS` dict in `main.py`
4. **Section key map** — add entry to `SECTION_KEY_MAP` in `routers/cv_instances.py`
5. **Data assembly** — add query to `_build_cv_data()` in `routers/templates.py`
6. **Section editor UI** — add entry to `TABS` and `BUILTIN_FIELDS` in `frontend/src/pages/Sections.tsx`
7. **Template composer** — add entry to `ALL_SECTIONS` in `frontend/src/components/SectionComposer.tsx`

### Adding a new Work type (new scholarly output kind)
1. **Work type** — add `work_type` value handling in `routers/works.py`
2. **Template rendering** — add `{% elif key == '...' %}` block in `cv_templates/base.html`
3. **Headings** — add to `_HEADINGS` dict in `main.py`
4. **Section key map** — add entry to `SECTION_KEY_MAP` in `routers/cv_instances.py`
5. **Data assembly** — add query to `_build_cv_data()` in `routers/templates.py`
6. **Publications UI** — add work type option in `frontend/src/pages/Publications.tsx`
7. **Template composer** — add entry to `ALL_SECTIONS` in `frontend/src/components/SectionComposer.tsx`
8. **TypeScript type** — add interface fields if needed in `frontend/src/lib/api.ts`

### Misc sections (editorial, peerrev, policypres, policycons, otherservice)
Stored as `CVItem` rows with a `section` discriminator and `data` JSON blob.
- Edit form fields are defined in `BUILTIN_FIELDS` under the section key in `Sections.tsx`
- Template rendering uses `{{ item.data.get('field') }}` or `__getattr__` access in `base.html`
- Sort is by insertion order (id) since misc sections have no date field

### Schema changes
`create_tables()` runs on startup via SQLAlchemy but won't alter existing tables.
Any new columns must be added to `_run_migrations()` as idempotent `ALTER TABLE` statements.

### Sort order
Items are sorted automatically by their primary date field via `sort_items()` in `services/sort.py`.
Templates have a `sort_direction` field ("desc" = newest first, "asc" = oldest first).
Publications follow the same direction.

### Templates & Styling
CV templates store an ordered list of enabled section keys and a `style` JSON dict.
There are no separate theme CSS files — all styling is generated dynamically by `generate_css()` in `services/pdf.py` from the style properties dict.
`THEME_PRESETS` in `services/pdf.py` maps old theme names (academic, unc, hopkins, etc.) to style dicts for use as presets.
`_build_cv_data()` in `routers/templates.py` assembles all data; `base.html` renders it.
Adding a section to a template requires it to exist in both `_HEADINGS` (main.py) and `ALL_SECTIONS` (components/SectionComposer.tsx).
CV instances can override individual style properties via `style_overrides` (merged over the template's style).

## Database
SQLite by default at `cvbuilder/data/cvbuilder.db`.
Switch to PostgreSQL by setting `DATABASE_URL=postgresql://user:pass@host/db`.
