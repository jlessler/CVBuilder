# CVBuilder Web App

A modern web application for building and managing academic CVs. Enter your data once, then export polished CVs in multiple university formats (UNC, Hopkins, Geneva, etc.) as HTML or PDF.

## Quick Start

### Prerequisites

- Python 3.11+ with pip
- Node.js 18+ with npm

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On first startup the server will:
- Create the SQLite database at `data/cvbuilder.db`
- Run schema migrations automatically
- Create a default admin account (see below)
- Seed default CV templates (Academic, UNC, Hopkins, UNIGE)

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 3. Log in

A default account is created on first startup:

| Field    | Value          |
|----------|----------------|
| Email    | `admin@local`  |
| Password | `changeme`     |

You can also click **Register** to create additional accounts.

## Quick Start (Docker)

```bash
docker compose up --build
```

Then open http://localhost:3000

To import existing YAML data:

```bash
docker compose exec backend python -m app.services.yaml_import \
  --cv mydata/CV.yml --refs mydata/refs.yml
```

## Multi-User Authentication

CVBuilder supports multiple users, each with their own isolated CV data. The auth system uses JWT tokens with bcrypt password hashing.

- **Registration** — `POST /api/auth/register` creates a new user and seeds default templates for them.
- **Login** — `POST /api/auth/login` returns a JWT (24-hour expiry by default).
- **All data is scoped** — every API endpoint filters by the authenticated user's ID. User A cannot see or modify User B's data.
- **YAML import safety** — importing a CV YAML file only replaces the current user's data, never other users'.
- **Rate limiting** — login and registration endpoints are rate-limited (10 attempts per minute per IP).

### Environment variables

| Variable                      | Default                          | Description                    |
|-------------------------------|----------------------------------|--------------------------------|
| `DATABASE_URL`                | `sqlite:///./data/cvbuilder.db`  | Database connection string     |
| `SECRET_KEY`                  | `dev-secret-change-in-production`| JWT signing key                |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 hours)                | Token lifetime                 |

For production deployments, always set `SECRET_KEY` to a strong random value.

## Switching to PostgreSQL

Set the environment variable:

```
DATABASE_URL=postgresql://user:pass@localhost:5432/cvbuilder
```

Or edit `docker-compose.yml` and uncomment the `db` service.

## Tutorial: Import the Einstein Sample CV

The repository includes a complete sample CV for Albert Einstein in `backend/tests/fixtures/`. You can use these files to explore CVBuilder without entering data by hand.

### Step 1: Log in

Open http://localhost:5173 and sign in with `admin@local` / `changeme` (or register a new account).

### Step 2: Import the sample data

Navigate to the **Export** page and use the import form to upload:

- **CV file:** `backend/tests/fixtures/einstein_cv.yml`
- **Refs file:** `backend/tests/fixtures/einstein_refs.yml`

Click **Import**. This populates all CV sections — education, experience, grants, publications, etc. — with Einstein's (historically simplified) academic record.

Or import from the command line:

```bash
cd backend
source .venv/bin/activate
python -m app.services.yaml_import \
  --cv tests/fixtures/einstein_cv.yml \
  --refs tests/fixtures/einstein_refs.yml
```

### Step 3: Browse the data

- **Profile** — Shows "Albert Einstein" with IAS address and contact info.
- **CV Sections** — Browse Education (PhD, University of Zurich, 1905), Experience (IAS, ETH Zurich, Swiss Patent Office), Grants, Awards (Nobel Prize in Physics), and more.
- **Publications** — Lists papers including the photoelectric effect, special relativity, and general relativity publications.

### Step 4: Preview and export

Go to **Templates** and click **Preview** on any template to see the rendered CV:

- **Academic CV** — Full traditional format with all sections
- **UNC CV** — University of North Carolina format with Carolina Blue accents
- **Hopkins CV** — Johns Hopkins format with Heritage Blue headings
- **UNIGE CV** — University of Geneva format with RedViolet section headings

Click **PDF** to download a print-ready PDF of any template.

### Step 5: Try a second user

Register a second account, log in, and confirm that it starts with empty data and its own set of templates — completely isolated from the Einstein data you imported for the first user.

## Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | FastAPI + SQLAlchemy 2.x            |
| Database   | SQLite (local) / PostgreSQL (cloud) |
| Frontend   | React 19 + Vite + Tailwind CSS      |
| PDF        | WeasyPrint (HTML → PDF)             |
| Templates  | Jinja2 HTML/CSS                     |
| Auth       | JWT (python-jose) + bcrypt (passlib)|
| Deployment | Docker Compose                      |

## Project Layout

```
cvbuilder/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + startup + migrations
│   │   ├── database.py        # SQLAlchemy engine + session
│   │   ├── models.py          # ORM models (User + 18 content tables)
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── auth.py            # JWT + password hashing + dependencies
│   │   ├── routers/
│   │   │   ├── auth.py        # Register, login, current user
│   │   │   ├── profile.py     # Profile + all CV sections CRUD
│   │   │   ├── publications.py  # Publications + DOI lookup
│   │   │   ├── templates.py   # Template CRUD + preview + PDF
│   │   │   └── export.py      # YAML import/export
│   │   └── services/
│   │       ├── doi.py         # Crossref DOI lookup
│   │       ├── pdf.py         # WeasyPrint rendering
│   │       └── yaml_import.py # CV.yml + refs.yml importer
│   ├── cv_templates/          # Jinja2 HTML/CSS templates
│   │   ├── base.html
│   │   ├── sections/          # Partial templates per section
│   │   └── themes/            # CSS themes (academic, unc, hopkins, unige, ...)
│   ├── tests/                 # pytest test suite
│   │   └── fixtures/          # Einstein sample YAML + reference outputs
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.tsx            # Router + auth wrapper
│       ├── pages/             # Dashboard, Profile, Sections, Publications, Templates, Export
│       │                        Login, Register
│       ├── contexts/          # AuthContext (login/logout state)
│       ├── components/        # Layout, ProtectedRoute, UI primitives
│       └── lib/api.ts         # Axios client + JWT interceptors + TypeScript types
├── data/                      # SQLite database (created at runtime)
└── docker-compose.yml
```

## Development

```bash
# Run backend tests
cd backend
source .venv/bin/activate
pytest tests/ -q

# Type-check frontend
cd frontend
npx tsc --noEmit
```
