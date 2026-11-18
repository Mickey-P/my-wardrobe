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
- [ ] Export → import into an empty database → re-export preserves IDs, visual structures, notes, outfits, image bytes, and photo links.
- [ ] Import failure does not leave a partially written database or orphaned R2 objects.

## Current implementation / evidence

- Local export/archive services and Worker CSV/JSON/ZIP endpoints exist; frontend exposes export/import actions.
- Transactional/rollback behavior and full round-trip have not been verified here.

## Blockers / risks

- Multi-resource imports across D1 and R2 need a deliberate rollback/cleanup strategy.
- ZIP validation must be complete before the first database or object-store write.

## Next action

Inspect local and Worker import implementations for transaction boundaries, then prove a round trip using fixtures.
