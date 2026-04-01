# Component Architecture

> For procedural instructions (adding sections, schema changes), see [CLAUDE.md](../../CLAUDE.md).
> For table structures, see [database-schema.md](database-schema.md). For data flows, see [data-flows.md](data-flows.md).

## System Overview

```mermaid
graph TD
    Browser["Browser (React SPA)"]
    API["FastAPI Backend"]
    DB["SQLite / PostgreSQL"]
    ORCID["ORCID API"]
    PM["PubMed API"]
    CR["Crossref API"]
    OA["OpenAlex API"]

    Browser <-->|REST / JWT| API
    API <--> DB
    API -->|Publication sync| ORCID
    API -->|Publication sync| PM
    API -->|DOI lookup, sync, enrichment| CR
    API -->|Citation metrics| OA
```

## Backend Layers

```mermaid
graph TD
    subgraph Routers["Routers (FastAPI APIRouter)"]
        auth["auth"]
        profile_r["profile"]
        cv_items["cv_items"]
        works["works"]
        templates["templates"]
        cv_instances["cv_instances"]
        export["export"]
        citations["citations"]
        section_defs["section_definitions"]
        admin["admin"]
    end

    subgraph Services["Services (stateless helpers)"]
        pdf["pdf.py"]
        fetch_pubs["fetch_pubs.py"]
        doi["doi.py"]
        sort["sort.py"]
        name_parser["name_parser.py"]
        name_format["name_format.py"]
        fetch_citations["fetch_citations.py"]
        yaml_import["yaml_import.py"]
    end

    subgraph Data["Data Layer"]
        models["models.py (SQLAlchemy ORM)"]
        schemas["schemas.py (Pydantic)"]
        authmod["auth.py (JWT + bcrypt)"]
        database["database.py (engine + session)"]
    end

    Routers --> Services
    Routers --> Data
    Services --> Data
```

### Router Responsibilities

| Router | Prefix | Manages |
|--------|--------|---------|
| auth | `/api/auth` | Register, login, password change, current user |
| profile | `/api` | Profile CRUD (name, contact, addresses, identifiers) |
| cv_items | `/api/cv` | CRUD for all CVItem-backed sections |
| works | `/api/works` | CRUD for scholarly works, DOI lookup, sync, enrichment |
| templates | `/api/templates` | Template CRUD, copy, preview, PDF export, definition import/export |
| cv_instances | `/api/cv-instances` | Instance CRUD, section overrides, item curation, preview/PDF |
| export | `/api/export` | Full YAML backup and restore |
| citations | `/api/citations` | Fetch/summarize citation metrics from OpenAlex |
| section_definitions | `/api/section-definitions` | Custom section type CRUD |
| admin | `/api/admin` | User management (requires is_admin) |

### Authentication

- JWT (HS256) with configurable expiry (default 24h)
- Passwords hashed with bcrypt
- Per-IP rate limiting on `/register` and `/login` (10 attempts / 60s)
- Dependencies: `get_current_user()`, `get_current_admin()`, `get_optional_current_user()`

## Frontend Pages & Routing

```mermaid
graph TD
    App["App.tsx"]
    App --> Login["/login — Login"]
    App --> Register["/register — Register"]
    App --> PR["ProtectedRoute + AppLayout"]

    PR --> Dash["/ — Dashboard"]
    PR --> Prof["/profile — Profile"]
    PR --> Sec["/sections — Sections (CV Items)"]
    PR --> Pub["/publications — Publications (Works)"]
    PR --> Tmpl["/templates — Templates"]
    PR --> CVs["/cvs — CV Instances"]
    PR --> Exp["/export — Import/Export"]
    PR --> Usr["/users — Admin Users"]
```

### Three Frontend Data Patterns

**1. TABS/FIELDS-driven forms** (`Sections.tsx`)
- Declarative configuration drives a generic form renderer
- `TABS` array defines available sections (key, label, group, API section)
- `BUILTIN_FIELDS` record defines form fields per section (key, label, type, options)
- Custom `SectionDefinition`s fetched from API extend both at runtime
- Supports search, copy, delete, and NavigableModal for editing

**2. Direct API pages** (`Profile.tsx`, `Publications.tsx`)
- Page-specific forms with `useQuery` / `useMutation` (TanStack React Query)
- Publications has rich features: DOI lookup, sync candidates, complete-fields diff review, author name parsing, citation preview, work type filtering

**3. Composer pattern** (`Templates.tsx`, `CVInstances.tsx`)
- Drag-and-drop section ordering via `@dnd-kit`
- `SectionComposer` component shared between both pages
- Templates define style + sections; instances add overrides + curation
- Style editing with 20+ properties and theme presets

## Dynamic Form System

```mermaid
flowchart LR
    TABS["TABS array<br/>(key, label, group, section)"]
    FIELDS["BUILTIN_FIELDS<br/>(per-section field defs)"]
    SD["SectionDefinition<br/>(custom sections from API)"]
    MERGE["Merge at runtime"]

    TABS --> MERGE
    FIELDS --> MERGE
    SD --> MERGE

    MERGE --> RENDER["Generic form renderer<br/>Input / Textarea / Select<br/>per field type"]
    RENDER --> MODAL["NavigableModal<br/>(prev/next with auto-save)"]
    MODAL --> API["POST/PUT /api/cv<br/>(create/update CVItem)"]
```

**Field types supported:**
- `text` (default) — standard input
- `number` — numeric input
- `textarea` — multi-line text
- `options` — select dropdown (e.g., trainee_type, grant_type, status)
- `list` — JSON array with add/remove UI (e.g., press outlets)

**Tab features:**
- `section` can be comma-separated to fetch from multiple sections (e.g., `"trainees_advisees,trainees_postdocs"`)
- `subtypeField` — form field that determines which section to create in (e.g., trainee_type → section)
- Groups: "Education & Experience", "Teaching & Mentorship", "Grants", "Service", "Other", "Custom Sections"

## Shared Components

All in `components/ui.tsx` — Tailwind-based, no external component library:

| Component | Purpose |
|-----------|---------|
| `Button` | Variants: primary, secondary, danger, ghost. Sizes: sm, md, lg. Loading state. |
| `Input` | Labeled text input with error display |
| `Textarea` | Labeled multi-line input |
| `Select` | Labeled dropdown with `{value, label}[]` options |
| `Modal` | Overlay dialog with title and close |
| `NavigableModal` | Modal with prev/next arrow navigation + auto-save |
| `Card` | Content container |
| `PageHeader` | Title + subtitle + action buttons |
| `Badge` | Colored label (blue, green, yellow, red, gray, purple) |
| `Spinner` | Loading indicator |
| `Checkbox` | Labeled checkbox |

### Cross-cutting components

| Component | Used by |
|-----------|---------|
| `SectionComposer` | Templates.tsx, CVInstances.tsx — drag-and-drop section ordering |
| `SectionPickerModal` | SectionComposer — grouped section selector with multi-select |
| `ProtectedRoute` | App.tsx — auth guard wrapping all non-login routes |
| `Layout` (AppLayout) | App.tsx — sidebar navigation + main content area |
| `AuthProvider` | App.tsx — global auth context (token in localStorage, auto-load user) |

### State Management

- **TanStack React Query** for server state (staleTime: 30s, retry: 1)
- **React Context** for auth state only (`AuthProvider`)
- **Local state** for form data, modals, and UI toggles
- Cache invalidation after mutations via `queryClient.invalidateQueries()`
