# Data Flows

> For procedural instructions (adding sections, schema changes), see [CLAUDE.md](../../CLAUDE.md).
> For table structures and section key mappings, see [database-schema.md](database-schema.md).

## 1. PDF Generation

The most complex data flow — assembles all CV data, renders HTML via Jinja2, and converts to PDF.

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant R as Router (templates / cv_instances)
    participant BD as _build_cv_data()
    participant J as Jinja2 (base.html)
    participant CSS as generate_css()
    participant WP as WeasyPrint

    FE->>R: POST /api/templates/{id}/export/pdf<br/>or POST /api/cv-instances/{id}/export/pdf
    R->>BD: Assemble all sections for user
    BD->>BD: Query CVItems by section<br/>Query Works by work_type<br/>Query custom SectionDefinitions<br/>Sort each section (sort_items)
    BD-->>R: cv_data dict {section_key: [items]}
    Note over R: For CV instances:<br/>merge style_overrides over template style,<br/>filter curated sections
    R->>CSS: generate_css(resolved_style)
    CSS-->>R: CSS string
    R->>J: render(cv_data, sections, css, style)
    Note over J: For each section in order:<br/>{% elif key == 'education' %} block<br/>Applies format_author_list, bold_self
    J-->>R: HTML string
    R->>WP: html_to_pdf(html)
    WP-->>R: PDF bytes
    R-->>FE: Response (application/pdf)
```

**Key files:**
- `routers/templates.py` — `_build_cv_data()`, template preview/export endpoints
- `routers/cv_instances.py` — `_build_cv_instance_data()`, instance preview/export endpoints
- `services/pdf.py` — `generate_css()`, `render_cv_html()`, `html_to_pdf()`
- `cv_templates/base.html` — Jinja2 template with per-section rendering blocks

**Style resolution:** Template `style` dict → merged with instance `style_overrides` → passed to `generate_css()` which maps properties to CSS classes (`.cv-page`, `.cv-header`, `.cv-section`, `.pub-entry`, etc.).

## 2. Publication Sync

Discovers new publications from external APIs and presents candidates for user review.

```mermaid
sequenceDiagram
    participant FE as Frontend (Publications.tsx)
    participant R as Router (works)
    participant FP as fetch_pubs service
    participant ORCID as ORCID API
    participant PM as PubMed API
    participant CR as Crossref API

    FE->>R: GET /api/works/sync-check
    R->>R: Load user profile (name, ORCID)
    R->>FP: fetch_new_publications(name, orcid)
    par Parallel external queries
        FP->>ORCID: GET /v3.0/{orcid}/works
        ORCID-->>FP: titles, DOIs, years
        FP->>PM: esearch + esummary (author query)
        PM-->>FP: full metadata + PMIDs
        FP->>CR: query.author={name}
        CR-->>FP: full metadata
    end
    FP->>FP: Dedup across sources (by DOI, then title)
    FP->>FP: Dedup against existing DB works<br/>(exact match → drop, fuzzy → warn)
    FP->>FP: Enrich candidates missing metadata via Crossref
    FP-->>R: {candidates, searched_sources, errors}
    R->>R: Filter out ignored candidates (IgnoredCandidate table)
    R-->>FE: Candidate list with match_warnings + ignored_count

    Note over FE: User arrows through candidates one at a time,<br/>choosing Add / Ignore / Skip per candidate

    FE->>R: POST /api/works/sync-add (single candidate)
    R->>R: Create Work + WorkAuthor records<br/>Parse author names<br/>Sync cross-ref DOIs
    R-->>FE: Created work

    FE->>R: POST /api/works/sync-ignore (candidate identity)
    R->>R: Create IgnoredCandidate row (per-source dedup)
    R-->>FE: Ignored row

    Note over FE: Skipped candidates reappear on next sync.<br/>Ignored candidates are filtered server-side.
```

**Key files:**
- `services/fetch_pubs.py` — `fetch_new_publications()`, per-source fetchers, deduplication
- `routers/works.py` — `/sync-check`, `/sync-add`, `/sync-ignore`, `/sync-ignored` endpoints
- `models.py` — `IgnoredCandidate` model for persistent ignore
- `services/name_parser.py` — `parse_author_name()` for structured name extraction

**Author matching:** PubMed and Crossref results are filtered to only include works where the user appears as author. Matching checks: last name (whole word) + first initial + middle initial guard.

**Dedup logic:** Exact matches by DOI or normalized title+year are dropped. Fuzzy matches (title similarity ≥ 0.75 + year within 2 years or year unknown) are kept but flagged with warnings. Cross-ref DOIs (preprint ↔ published) are auto-linked.

**Ignore logic:** Ignored candidates are stored per-source in the `ignored_candidates` table. Identity matching is source-specific: PubMed uses PMID, Crossref uses DOI, ORCID uses DOI (or normalized title+year as fallback). Ignored candidates are filtered from `sync-check` results server-side. Users can manage (list/un-ignore) via `GET /sync-ignored` and `DELETE /sync-ignored/{id}`.

## 3. DOI Enrichment & Complete Fields

Fills in missing metadata for existing works using Crossref.

```mermaid
flowchart TD
    A[User selects works → POST /works/complete-fields] --> B{Work has DOI?}
    B -- No --> C[search_doi_by_metadata<br/>title + year + first author → Crossref]
    C --> D{DOI found?}
    D -- Yes --> E[lookup_doi_raw → full Crossref metadata]
    D -- No --> F[Skip — no match]
    B -- Yes --> E
    E --> G[compute_work_diffs<br/>compare existing vs Crossref]
    G --> H[Return diffs per work:<br/>field_diffs, author_diffs,<br/>proposed_authors, additional_authors]
    H --> I[Frontend shows diff review UI<br/>green = accepted, red = conflict]
    I --> J[User accepts/rejects per field]
    J --> K[PUT /works/id for each accepted diff]
```

**Key files:**
- `services/doi.py` — `lookup_doi()`, `search_doi_by_metadata()`, `compute_work_diffs()`
- `routers/works.py` — `/complete-fields` endpoint (read-only), `/enrich-authors` and `/enrich-authors-bulk`

**DOI discovery thresholds:** Title similarity ≥ 0.80 + ≥2 corroborating signals (year, first author, journal), OR title similarity ≥ 0.95 standalone. Similarity uses max(Jaccard, overlap coefficient) on normalized word sets.

## 4. CV Instance Curation

CV instances inherit from templates but allow per-section overrides and item curation.

```mermaid
flowchart TD
    T[CVTemplate] --> |sections, style, sort_direction| I[CVInstance]
    I --> SO[style_overrides merged over template style]
    I --> SD[sort_direction_override or inherit]

    subgraph "Per Section Resolution"
        TS[TemplateSection] --> IS[CVInstanceSection]
        IS --> EN{enabled override?}
        EN -- null --> EN2[Inherit from template]
        EN -- true/false --> EN3[Force enabled/disabled]
        IS --> HO[heading_override replaces default]
        IS --> CU{curated?}
        CU -- false --> ALL[Show all items for this section]
        CU -- true --> SEL[Show only CVInstanceItem selections]
    end

    SEL --> IID[item_id references<br/>works.id or cv_items.id<br/>depending on section_key]

    subgraph "Pseudo-sections"
        GH[group_heading] --> |depth 0-3| NEST[Visual heading only,<br/>no data items]
    end
```

**Key files:**
- `routers/cv_instances.py` — CRUD, section management, `_build_cv_instance_data()`
- `routers/cv_instances.py:SECTION_KEY_MAP` — determines which table to query per section_key

**Curation flow:** When `curated=True` on a section, only items whose IDs appear in `cv_instance_items` are rendered. The frontend provides a checklist UI via `GET /cv-instances/{id}/sections/{key}/items` (returns items with `selected` flag) and `PUT .../items` to save selections.

## 5. YAML Import/Export

Full backup and restore of CV data.

```mermaid
sequenceDiagram
    participant FE as Frontend (Export.tsx)
    participant R as Router (export)
    participant YI as yaml_import service
    participant DB as Database

    Note over FE,DB: Export
    FE->>R: GET /api/export/yaml
    R->>DB: Query profile, all CVItems, all Works + authors
    R->>R: Serialize to YAML structure<br/>(cv: {profile, sections...}, refs: {papers, preprints...})
    R-->>FE: StreamingResponse (cvbuilder_backup.yml)

    Note over FE,DB: Import
    FE->>R: POST /api/export/yaml/import (file upload)
    R->>R: Detect format: combined (cv+refs) or flat
    R->>R: Write temp files for cv and/or refs YAML
    R->>YI: import_cv_yaml(cv_path, session, user_id)
    YI->>DB: Delete existing CVItems for user<br/>Create Profile + Addresses<br/>Create CVItems per section<br/>Compute sort_date for each
    R->>YI: import_refs_yaml(refs_path, session, user_id)
    YI->>DB: Delete existing Works for user<br/>Create Work + WorkAuthor per publication<br/>Parse author names (dict or string)
    R-->>FE: {imported: ["CV data", "Publications"]}
```

**Key files:**
- `routers/export.py` — `/yaml` export, `/yaml/import` import
- `services/yaml_import.py` — `import_cv_yaml()`, `import_refs_yaml()`, `_author_fields()` for name parsing

**Import is destructive:** Deletes all existing CVItems and Works for the user before importing. The YAML format supports structured author dicts (`{name, family, given, suffix}`) or plain strings.
