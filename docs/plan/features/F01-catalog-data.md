# F01 — Catalog data and imports

**Status:** Implemented, needs verification  
**Goal:** maintain an accurate, auditable catalog for permanent IDs W001–W139 without inventing values or modifying the user's source files.

## Scope

- Identify the selected catalog CSV and visual-description CSV; preserve their original structures separately.
- Keep ID as the immutable item key. Preserve source URL, user notes, visual descriptions, critical details, and uncertainties independently.
- Import/re-import into SQLite with validation, backup, duplicate handling, and an import report.
- Keep personal source files and normalized local copies out of public Git.

## Acceptance criteria

- [ ] Selected inputs, encoding, headers, row counts, ID coverage, duplicate IDs, and image URL coverage are recorded.
- [ ] Every valid source ID is retained exactly; missing or malformed rows are reported, never guessed or silently dropped.
- [ ] Catalog fields and visual-description fields round-trip without flattening or losing source structure.
- [ ] Re-import updates source fields by ID, does not duplicate rows, preserves user notes, and does not delete photos.
- [ ] Import report distinguishes added, updated, skipped, and invalid rows.
- [ ] Database backup is created before a bulk import/update and can be restored.
- [ ] User-specific corrections listed in the project request remain represented for W016, W017, W019, W092, W104, W108–W110, and W127.

## Current implementation / evidence

- `backend/scripts/import_catalog.py`, `backend/app/services/import_service.py`, `data/catalog.csv`, and `data/visual_descriptions.csv` exist.
- The root README says imports update by permanent ID, preserve notes, and back up an existing database.
- These statements have not yet been rechecked against the acceptance list for this plan.

## Blockers / risks

- The repository's personal source tables are excluded from public Git; use the user's local copies when checking exact row-level details.
- Keep uncertainty explicit when source columns do not encode a requested detail.

## Next action

Run a read-only source audit and record counts/headers/duplicates; then verify importer behavior with fixtures before touching the real database.
