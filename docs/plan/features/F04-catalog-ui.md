# F04 — Wardrobe browsing and item details

**Status:** Implemented, needs verification  
**Goal:** make real wardrobe photos the primary way to browse and understand items.

## Scope

- Responsive dashboard with item, category, photo, season, and status summaries.
- Search across ID, name/description, brand, color, notes, and visual descriptions.
- Filter by category/subcategory, color, season, formality, warmth, fit, brand, photo presence, and item status; sort by ID/category/color/brand.
- Item detail shows original photo, all catalog fields, visual details, critical details, uncertainties, source URL, and photo status.
- Edit catalog fields and notes without changing ID.

## Acceptance criteria

- [ ] Dashboard counts agree with API/database values and show incomplete data clearly.
- [ ] Search and every required filter/sort can be used together and cleared.
- [ ] Item detail displays original-photo status and all source structures without hiding unknown values.
- [ ] ID is read-only; save, cancel, loading, empty, and error states are clear.
- [ ] Layout works at desktop and tablet widths; image grid lazy-loads photos.
- [ ] Keyboard and screen-reader basics: labels, focus, dialog semantics, and useful image alt text.

## Current implementation / evidence

- React/Vite UI is in `frontend/src/App.tsx`; shared API client is in `frontend/src/api.ts`; styles are under `frontend/src/`.
- Current code exists; acceptance checks have not been recorded in this plan.

## Blockers / risks

- Cloudflare Access browser behavior may differ from local token mode; keep API error/loading states useful in both.

## Next action

Perform a browser walkthrough with representative real items, including missing photo and incomplete-description cases.
