# F02 — Original-photo pipeline

**Status:** Implemented, needs verification  
**Goal:** preserve and audit the exact original image associated with each wardrobe ID.

## Scope

- Downloader reads catalog `image_url`, uses IDs as local filenames, validates HTTP result, MIME, file signature, and image decoding.
- Manifest records URL, local path, status, MIME, size, SHA-256, and error for each ID.
- Retry safely, rate-limit requests, skip valid existing images, and support force/limit options.
- Recovery guidance explains Brave cache recovery without claiming that item identity can be inferred from cache names.

## Acceptance criteria

- [ ] A limited run and full run produce a per-ID report without aborting on a failed URL.
- [ ] HTML/error payloads and corrupt images are rejected; supported formats are detected by bytes and can be opened.
- [ ] Re-running skips validated files; `--force` re-downloads; missing URL and failure statuses remain distinguishable.
- [ ] Manifest includes every catalog ID, including missing URL and failed downloads.
- [ ] Manual cache recovery never assigns a photo to an ID without user confirmation and never overwrites a good photo silently.
- [ ] Source photos are not transformed by the downloader.

## Current implementation / evidence

- `backend/scripts/download_images.py`, `data/image_manifest.json`, `data/images/`, and `docs/brave_cache_recovery.md` exist.
- The README reports 139 downloaded local images; the current manifest should be audited before relying on this count.

## Blockers / risks

- CloudFront URL availability can change; use the manifest and existing originals as the baseline.
- Brave cache recovery may find images but cannot reliably prove ID correspondence.

## Next action

Summarize current manifest statuses and missing IDs, then verify downloader behavior against mocked HTTP/image inputs.
