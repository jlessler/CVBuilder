# CVBuilder — Claude Code Guide

## Project layout

```
cvbuilder/
├── backend/               # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── main.py        # Startup, migrations, template seeding, _HEADINGS
│   │   ├── models.py      # SQLAlchemy ORM models
│   │   ├── schemas.py     # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── profile.py    # All CV section CRUD endpoints
│   │   │   ├── templates.py  # Template CRUD, preview, PDF export, _build_cv_data
│   │   │   ├── publications.py
│   │   │   └── export.py     # YAML import/export
│   │   └── services/
│   │       ├── sort.py    # Date-based sort helpers (sort_items, SECTION_SORT_KEY)
│   │       ├── pdf.py     # WeasyPrint HTML→PDF, Jinja2 rendering
│   │       └── yaml_import.py
│   └── cv_templates/      # Jinja2 templates
│       ├── base.html      # Main CV renderer — one {% elif key == '...' %} block per section
│       ├── sections/      # Included partials (publications, grants, panels, trainees, …)
│       └── themes/        # Per-theme CSS files (academic, unc, hopkins, unige, minimal, modern)
├── frontend/              # React 19 + Vite + Tailwind
│   └── src/
│       ├── pages/
│       │   ├── Sections.tsx      # TABS + FIELDS definitions for all CV section editors
│       │   ├── Templates.tsx     # Template composer (ALL_SECTIONS list, sort direction)
│       │   ├── Publications.tsx
│       │   ├── Profile.tsx
│       │   └── Export.tsx
│       ├── components/ui/        # Shared UI primitives (Button, Input, Select, Modal, …)
│       └── lib/api.ts            # Axios client + TypeScript interfaces for all models
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

### Adding a new CV section
1. **Model** — add class to `models.py`
2. **Schema** — add Base/Create/Out to `schemas.py`
3. **Migration** — add `ALTER TABLE` to `_run_migrations()` in `main.py` if needed
4. **Router** — add CRUD endpoints in `routers/profile.py` using `_list/_create/_update/_delete` helpers
5. **Sort key** — add entry to `SECTION_SORT_KEY` in `services/sort.py`
6. **Template rendering** — add `{% elif key == '...' %}` block in `cv_templates/base.html`
7. **Headings** — add to `_HEADINGS` dict in `main.py`
8. **Section editor UI** — add entry to `TABS` and `FIELDS` in `frontend/src/pages/Sections.tsx`
9. **Template composer** — add entry to `ALL_SECTIONS` in `frontend/src/pages/Templates.tsx`
10. **TypeScript type** — add interface to `frontend/src/lib/api.ts`

### Misc sections (editorial, peerrev, software, policypres, policycons, otherservice)
Stored in the `misc_sections` table with a `section` string discriminator and a `data` JSON blob.
- Edit form fields are defined in `FIELDS` under the `misc_*` key
- `dataFields` on the tab definition lists which keys live inside `item.data`
- Template rendering uses `{{ item.data.get('field') }}` in `base.html`
- Sort is by insertion order (id) since misc sections have no date field

### Schema changes
`create_tables()` runs on startup via SQLAlchemy but won't alter existing tables.
Any new columns must be added to `_run_migrations()` as idempotent `ALTER TABLE` statements.

### Sort order
Items are sorted automatically by their primary date field via `sort_items()` in `services/sort.py`.
Templates have a `sort_direction` field ("desc" = newest first, "asc" = oldest first).
Publications follow the same direction. Patent and MiscSection items sort by id (insertion order).

### Templates
CV templates store an ordered list of enabled section keys.
`_build_cv_data()` in `routers/templates.py` assembles all data; `base.html` renders it.
Adding a section to a template requires it to exist in both `_HEADINGS` (main.py) and `ALL_SECTIONS` (Templates.tsx).

## Database
SQLite by default at `cvbuilder/data/cvbuilder.db`.
Switch to PostgreSQL by setting `DATABASE_URL=postgresql://user:pass@host/db`.
