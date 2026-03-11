# Migration Guide: CVItem & Works Restructure

This guide is for anyone running CVBuilder **before** the unified CVItem/Works
restructure who wants to upgrade to the current version. If you are setting up
CVBuilder for the first time, you can ignore this document.

## What changed

The database was restructured from many per-section tables (Education,
Experience, Grant, Publication, Patent, Seminar, etc.) into two unified tables:

| Old structure | New structure |
|---|---|
| 12+ typed tables (Education, Experience, Grant, Award, …) | **`cv_items`** — one table with a `section` discriminator and a `data` JSON blob |
| Publications, Patents, Seminars, Software, Dissertation tables | **`works`** + **`work_authors`** — unified scholarly output table |
| `MiscSection` catch-all for editorial boards, peer review, etc. | Also migrated to `cv_items` (software and dissertation go to `works`) |

The old tables are **not dropped** — they remain in the database as read-only
archives after migration. All new reads and writes go through the new tables.

## Before you upgrade

### 1. Back up your database

**This is the most important step.** Copy your SQLite database file before
starting the new server version.

```bash
# Default location
cp cvbuilder/data/cvbuilder.db cvbuilder/data/cvbuilder.db.backup

# Verify the backup
ls -la cvbuilder/data/cvbuilder.db.backup
```

If you are using PostgreSQL, use `pg_dump` instead:

```bash
pg_dump -U your_user cvbuilder > cvbuilder_backup.sql
```

### 2. Update the code

Pull or check out the version with the CVItem/Works restructure:

```bash
git pull origin main
# or
git checkout main
```

### 3. Install any new dependencies

```bash
cd cvbuilder/backend
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the migration

**The migration is fully automatic.** Simply start the server:

```bash
cd cvbuilder/backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

On startup, the server will:

1. **Schema migration** (`_run_migrations`) — adds new columns and tables via
   idempotent `ALTER TABLE` statements. Existing columns are silently skipped.
2. **User backfill** (`_ensure_default_user`) — assigns any orphaned rows
   (with `NULL user_id`) to the default admin account.
3. **Works migration** (`_migrate_works_data`) — copies Publications, Patents,
   Seminars, and Software/Dissertation MiscSections into the unified `works`
   table. Author role flags (corresponding, co-first, co-senior) are converted
   from per-publication to per-author.
4. **CVItem migration** (`_migrate_cv_items_data`) — copies all typed section
   models (Education, Experience, Consulting, Memberships, Panels, Symposia,
   Classes, Grants, Awards, Press, Trainees, Committees) and remaining
   MiscSections into the unified `cv_items` table.
5. **ID remapping** — any CV instance items that reference old table IDs are
   updated to point at the new `works` or `cv_items` IDs.
6. **Theme migration** — old `theme_css` string values are converted to `style`
   JSON dicts using the built-in theme presets.

The migration is **per-user idempotent**: if a user's data has already been
migrated (i.e., they already have rows in `works` or `cv_items`), they are
skipped. This means it is safe to restart the server multiple times.

## Verifying the migration

After the server starts, check these things:

### 1. Check the logs

Look for migration log lines in the server output:

```
INFO:cvbuilder.migrate:Migrating works data for 1 user(s)
INFO:cvbuilder.migrate:Works migration complete: 42 works created, 42 IDs remapped
INFO:cvbuilder.migrate:Migrating cv_items data for 1 user(s)
INFO:cvbuilder.migrate:CVItem migration complete: 87 items created, 87 IDs remapped
```

If you see no migration log lines, either the migration already ran on a
previous startup or there was no data to migrate.

### 2. Spot-check your data in the UI

- **Scholarly Works** — confirm all publications, patents, seminars, software,
  and dissertations appear with correct titles, authors, and years.
- **CV Sections** — confirm education, experience, grants, awards, and other
  sections have all their entries.
- **CV Preview** — preview an existing template and compare against a
  previously exported PDF to confirm the rendered output looks the same.

### 3. Export a backup

Use the **Export** page (or the API) to download your data as YAML. This gives
you a portable, human-readable backup independent of the database:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/export/yaml > cv_export.yml
```

## Known edge cases

| Scenario | How it's handled |
|---|---|
| Non-numeric years (e.g., "in press", "2024a") | The numeric portion is extracted to `year`; the original string is preserved in `data.year_raw` |
| MiscSection `authors` stored as comma-separated string | Parsed into individual `WorkAuthor` rows |
| MiscSection `authors` stored as JSON list | Each list entry becomes a `WorkAuthor` row |
| Publication `corr` / `cofirsts` / `coseniors` flags | Converted from per-publication counts to boolean flags on individual `WorkAuthor` rows |
| Panels split by type | `advisory` panels → `panels_advisory` section; grant review panels → `panels_grantreview` |
| Trainees split by type | `advisee` → `trainees_advisees`; postdocs → `trainees_postdocs` |

## Rollback

If something goes wrong, restore your database backup and run the previous
version of the code:

```bash
# Stop the server, then:
cp cvbuilder/data/cvbuilder.db.backup cvbuilder/data/cvbuilder.db

# Check out the previous version
git checkout <previous-commit>

# Restart the server
uvicorn app.main:app --reload
```

For PostgreSQL:

```bash
psql -U your_user -d cvbuilder < cvbuilder_backup.sql
```

## Questions

If the migration fails or data looks incorrect, check the backup and open an
issue with:
- The error message or traceback from the server logs
- Your database engine (SQLite or PostgreSQL)
- The approximate number of records in your database
