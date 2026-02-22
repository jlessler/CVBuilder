# CVBuilder Web App

A modern, self-contained web application for managing academic CVs.

## Quick Start (Docker)

```bash
cd cvbuilder
docker compose up --build
```

Then open http://localhost:3000

To import your existing YAML data:

```bash
docker compose exec backend python -m app.services.yaml_import \
  --cv mydata/CV.yml --refs mydata/refs.yml
```

## Local Development (no Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

Import YAML data (from `cvbuilder/` directory):

```bash
python -m app.services.yaml_import \
  --cv ../mydata/CV.yml --refs ../mydata/refs.yml
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Switching to PostgreSQL

Set the environment variable:

```
DATABASE_URL=postgresql://user:pass@localhost:5432/cvbuilder
```

Or edit `docker-compose.yml` and uncomment the `db` service.

## Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | FastAPI + SQLAlchemy 2.x            |
| Database   | SQLite (local) / PostgreSQL (cloud) |
| Frontend   | React 19 + Vite + Tailwind CSS      |
| PDF        | WeasyPrint (HTML → PDF)             |
| Templates  | Jinja2 HTML/CSS                     |
| Deployment | Docker Compose                      |

## Project Layout

```
cvbuilder/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app + startup
│   │   ├── database.py      # SQLAlchemy engine + session
│   │   ├── models.py        # ORM models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── profile.py   # Profile + all CV sections
│   │   │   ├── publications.py  # Publications + DOI lookup
│   │   │   ├── templates.py     # Template CRUD + preview + PDF
│   │   │   └── export.py    # YAML import/export
│   │   └── services/
│   │       ├── doi.py       # Crossref DOI lookup
│   │       ├── pdf.py       # WeasyPrint rendering
│   │       └── yaml_import.py  # CV.yml + refs.yml importer
│   └── cv_templates/        # Jinja2 HTML/CSS templates
│       ├── base.html
│       ├── sections/        # Partial templates per section
│       └── themes/          # CSS themes (academic, minimal, modern)
├── frontend/
│   └── src/
│       ├── App.tsx          # Router
│       ├── pages/           # Dashboard, Profile, Sections, Publications, Templates, Export
│       ├── components/      # Layout, UI primitives
│       └── lib/api.ts       # Axios client + TypeScript types
├── data/                    # SQLite database (created at runtime)
└── docker-compose.yml
```
