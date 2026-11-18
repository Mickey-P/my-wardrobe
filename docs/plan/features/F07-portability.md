# F07 — Export and archive import

**Status:** Implemented, needs verification  
**Goal:** provide a complete, inspectable backup that preserves records, relationships, and available original images.

## Scope

- Export CSV and JSON catalogs; export a ZIP containing catalog, visual descriptions, manifest, images, outfits, and README.
- Omit missing photos and mark them missing in the manifest.
- Import ZIP with integrity checks, path traversal defense, ID conflict reporting, and an explicit overwrite choice.
- Preserve user notes and existing good photos unless replacement is confirmed.

## Acceptance criteria

- [ ] CSV and JSON include all catalog fields and all item IDs.
- [ ] ZIP contains the documented entries and every included image has a matching manifest entry, type, size, and checksum.
- [ ] Missing/unavailable photos are explicitly reported and never represented as existing files.
- [ ] Bad CRC, invalid archive structure, oversized inputs, traversal paths, duplicate IDs, and unknown outfit item references are rejected before mutation.
- [ ] Import conflict preview identifies item and outfit IDs; overwrite behavior is explicit.
- [ ] A fixture-only export → import into an empty database → re-export round trip passes and preserves IDs, visual structures, notes, outfits, image bytes, and photo links.
- [ ] The fixture round-trip evidence is recorded and passing before cloud migration of any personal catalog or photo data.
- [ ] Before the initial CSV-to-cloud migration, a verified local export backup exists, and the original source CSVs, visual CSV, photos, photo manifest, and local SQLite database remain unchanged and available for the file-based app.
- [ ] Initial migration rollback is a return to the unchanged local file-based app, not an in-place D1/R2 restore. On hosted import failure, stop cloud use and quarantine the cloud target without modifying or deleting it; continue locally from the preserved source files and SQLite database.
- [ ] A fixture-only rollback test in a disposable workspace demonstrates that the fixture file-based app can restart after a simulated hosted-import failure and that source record and photo checksums are unchanged. Record the test procedure and outcome before personal-data migration.
- [ ] Import failure does not leave a partially written database or orphaned R2 objects.

## Current implementation / evidence

- Local export/archive services and Worker CSV/JSON/ZIP endpoints exist; frontend exposes export/import actions.
- Transactional/rollback behavior and full round-trip have not been verified here.
- The fixture round trip, verified local export backup, and disposable-workspace local-fallback test remain prerequisites for F08 personal-data import.

## Blockers / risks

- Multi-resource imports across D1 and R2 need a deliberate rollback/cleanup strategy.
- ZIP validation must be complete before the first database or object-store write.
- Personal-data migration is blocked until fixture round-trip and local-fallback evidence exist. The initial migration policy is to quarantine a failed cloud target and continue locally, not to perform an unverified in-place D1/R2 restore.

## Next action

Inspect local and Worker import implementations for transaction boundaries, then prove the export/import round trip using safe fixtures and test the disposable-workspace local fallback, including unchanged source record and photo checksums. Record exact commands and outcomes without using personal wardrobe data. The existing archive validation, transactional/no-partial-mutation, and data-preservation requirements remain required.
