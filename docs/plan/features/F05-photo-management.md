# F05 — Photo management and manual matching

**Status:** Implemented, needs verification  
**Goal:** make every photo's provenance and relationship to its wardrobe ID explicit.

## Scope

- Show all catalog IDs, thumbnails, photo source, manifest status, and missing images.
- Retry catalog URL downloads and manually upload a local image.
- Preview a candidate image, choose an ID, confirm the match, and save as that ID's image.
- Replacing a valid photo requires an explicit confirmation.

## Acceptance criteria

- [ ] Manager lists all IDs, including those with no image row in the manifest.
- [ ] Original catalog image and manual upload are visually labeled distinctly.
- [ ] Upload rejects unsupported/corrupt/oversize files and does not trust extension or browser MIME alone.
- [ ] Manual matching requires preview, selected ID, and explicit confirmation.
- [ ] Replacing a correct image requires confirmation and updates manifest hash/type/size/source.
- [ ] Retry failures are reported per ID and do not stop other work.

## Current implementation / evidence

- Photo routes exist in the local API and Cloudflare Worker; `frontend/src/ItemPhoto.tsx` and photo-manager UI are present in the app.
- Verify whether the local uploader, retry action, and confirmed ID-matching flow meet this plan.

## Blockers / risks

- Do not infer item ID from an image filename when manually recovering from a cache.
- Preserve a recoverable copy or backup when replacing originals.

## Next action

Walk the photo manager through missing, catalog-original, manual, invalid upload, and confirmed replacement scenarios.
