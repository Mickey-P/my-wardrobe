# F06 — Manual outfit builder

**Status:** Implemented, needs verification  
**Goal:** save user-created outfits composed of explicit item IDs.

## Scope

- Create, list, inspect, edit, and delete saved outfits.
- Add/replace/remove catalog items; show selected IDs and photos.
- Store name, description, season, and occasion.
- Keep recommendations out of the first release.

## Acceptance criteria

- [ ] User can create and reopen an outfit; all metadata and item IDs persist.
- [ ] Duplicate and unknown item IDs are rejected or prevented in the UI.
- [ ] Add/remove/replace operations update the saved outfit without altering wardrobe items.
- [ ] Empty outfit and empty catalog states are handled.
- [ ] Outfit records are included in ZIP and JSON exports and survive an import round trip.

## Current implementation / evidence

- Outfit UI and local/Worker API endpoints are present; ZIP export/import contains outfit handling.
- End-to-end persistence and archive round-trip still need recorded verification.

## Blockers / risks

- Archive imports must validate all referenced IDs before writing outfit data.

## Next action

Create a small outfit, edit it, restart the app, then verify its exported and re-imported representation.
