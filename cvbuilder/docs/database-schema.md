# Database Schema

> For procedural instructions (adding sections, schema changes), see [CLAUDE.md](../../CLAUDE.md).

## ER Diagram

```mermaid
erDiagram
    %% ── User & Profile ──
    users {
        int id PK
        string email UK
        string hashed_password
        string full_name
        bool is_active
        bool is_admin
        datetime created_at
    }
    profile {
        int id PK
        int user_id FK
        string name
        string email
        string phone
        string website
        string orcid
        string semantic_scholar_id
        string linkedin
        string given_name
        string family_name
        string suffix
    }
    addresses {
        int id PK
        int profile_id FK
        string type "home | work"
        int line_order
        string text
    }

    users ||--o| profile : has
    profile ||--o{ addresses : has

    %% ── Content: Works ──
    works {
        int id PK
        int user_id FK
        string work_type "papers|preprints|chapters|..."
        string title
        int year
        int month
        int day
        string doi
        json data "type-specific fields"
    }
    work_authors {
        int id PK
        int work_id FK
        string author_name
        int author_order
        string given_name
        string family_name
        string suffix
        bool student
        bool corresponding
        bool cofirst
        bool cosenior
    }

    users ||--o{ works : owns
    works ||--o{ work_authors : has

    %% ── Content: CV Items ──
    cv_items {
        int id PK
        int user_id FK
        string section "education|grants|..."
        json data "all fields"
        int sort_order
        int sort_date "computed YYYYMMDD"
    }
    section_definitions {
        int id PK
        int user_id FK
        string section_key "custom_slug"
        string label
        string layout "entry | list"
        json fields "array of field defs"
        string sort_field
        datetime created_at
    }

    users ||--o{ cv_items : owns
    users ||--o{ section_definitions : defines

    %% ── Templates ──
    cv_templates {
        int id PK
        int user_id FK "NULL = system"
        string name
        string description
        json style
        string sort_direction "asc | desc"
        string author
        string author_contact
        string guidance_url
        datetime created_at
        datetime updated_at
    }
    template_sections {
        int id PK
        int template_id FK
        string section_key
        bool enabled
        int section_order
        json config "heading etc."
        int depth "0-3 nesting"
    }

    users ||--o{ cv_templates : owns
    cv_templates ||--o{ template_sections : contains

    %% ── CV Instances ──
    cv_instances {
        int id PK
        int user_id FK
        int template_id FK
        string name
        string description
        json style_overrides
        string sort_direction_override
        datetime created_at
        datetime updated_at
    }
    cv_instance_sections {
        int id PK
        int cv_instance_id FK
        string section_key
        bool enabled "null = inherit"
        int section_order
        string heading_override
        json config_overrides
        int depth
        bool curated
    }
    cv_instance_items {
        int id PK
        int cv_instance_section_id FK
        int item_id "works.id or cv_items.id"
    }

    users ||--o{ cv_instances : owns
    cv_templates ||--o{ cv_instances : "based on"
    cv_instances ||--o{ cv_instance_sections : has
    cv_instance_sections ||--o{ cv_instance_items : curates
```

## The Two Content Models

All CV content is stored in one of two tables, distinguished by whether the content is an authored scholarly output or a general CV entry.

### Work (`works` + `work_authors`)

Scholarly outputs with structured authorship. The `work_type` discriminator determines which fields are relevant in the `data` JSON blob.

| work_type | Typical data fields |
|-----------|-------------------|
| papers | journal, volume, issue, pages, select_flag, preprint_doi, published_doi |
| preprints | journal, volume, pages, published_doi |
| chapters | publisher, pages |
| letters | journal, volume, issue, pages, parent_doi |
| scimeetings | conference, institution, pres_type |
| editorials | journal, volume, issue, pages |
| patents | identifier, status |
| seminars | institution, conference, location |
| software | publisher, url |
| dissertation | institution |

Top-level columns (`title`, `year`, `month`, `day`, `doi`) are shared across all types. Both `Work` and `CVItem` define `__getattr__` so `work.journal` transparently reads `work.data["journal"]`.

Each `WorkAuthor` carries structured name fields (`given_name`, `family_name`, `suffix`) and role flags (`student`, `corresponding`, `cofirst`, `cosenior`).

### CVItem (`cv_items`)

Everything else — education, experience, grants, service, etc. The `section` string discriminator identifies the section type. All fields live in the `data` JSON blob.

`sort_date` is a computed integer (YYYYMMDD format) derived from date fields in `data`, used for chronological ordering. `sort_order` provides manual ordering.

## Section Key Registry

Maps section keys used in templates/instances to their storage model. Source of truth: `SECTION_KEY_MAP` in `routers/cv_instances.py`.

| Section Key | Model | Filter |
|-------------|-------|--------|
| education | CVItem | section="education" |
| experience | CVItem | section="experience" |
| consulting | CVItem | section="consulting" |
| memberships | CVItem | section="memberships" |
| panels_advisory | CVItem | section="panels_advisory" |
| panels_grantreview | CVItem | section="panels_grantreview" |
| symposia | CVItem | section="symposia" |
| committees | CVItem | section="committees" |
| classes | CVItem | section="classes" |
| grants | CVItem | section="grants" |
| awards | CVItem | section="awards" |
| press | CVItem | section="press" |
| trainees_advisees | CVItem | section="trainees_advisees" |
| trainees_postdocs | CVItem | section="trainees_postdocs" |
| mentorship | CVItem | section="mentorship" |
| editorial | CVItem | section IN (editor, assocedit, otheredit) |
| peerrev | CVItem | section="peerrev" |
| policypres | CVItem | section="policypres" |
| policycons | CVItem | section="policycons" |
| otherservice | CVItem | section="otherservice" |
| chairedsessions | CVItem | section="chairedsessions" |
| otherpractice | CVItem | section="otherpractice" |
| departmentalOrals | CVItem | section="departmentalOrals" |
| finaldefense | CVItem | section="finaldefense" |
| schoolwideOrals | CVItem | section="schoolwideOrals" |
| citation_metrics | CVItem | section="citation_metrics" |
| publications_papers | Work | work_type="papers" |
| publications_preprints | Work | work_type="preprints" |
| publications_chapters | Work | work_type="chapters" |
| publications_letters | Work | work_type="letters" |
| publications_scimeetings | Work | work_type="scimeetings" |
| publications_editorials | Work | work_type="editorials" |
| patents | Work | work_type="patents" |
| seminars | Work | work_type="seminars" |
| software | Work | work_type="software" |
| dissertation | Work | work_type="dissertation" |
| custom_* | CVItem | section="{section_key}" |

## Custom Sections

Users can create custom section types via `SectionDefinition`:

1. User provides a label (e.g., "Board Memberships") → system generates `section_key = "custom_board_memberships"`
2. User defines fields as a JSON array: `[{key: "org", label: "Organization", type: "text"}, ...]`
3. `layout` controls rendering: `"entry"` (one item per block) or `"list"` (compact list)
4. `sort_field` optionally names a data field for chronological sorting
5. CVItems are created with `section = section_key` and `data` matching the field definitions
6. Templates/instances reference custom sections by their `section_key`
7. Deletion is blocked if any CVItems exist for that section
