# F09 — Privacy and security

**Status:** In progress  
**Goal:** keep the personal catalog private and constrain all file/archive operations to explicitly approved data.

## Scope

- Separate public source code from private wardrobe data and photos.
- Local-only defaults; explicit authentication for hosted deployments.
- Cloudflare Access at the Worker edge; private D1/R2; no browser-held shared secret.
- Validate ZIP/image uploads, IDs, object keys, and file paths; avoid path traversal and arbitrary file reads.
- Keep backups before destructive/bulk mutation; avoid deleting images during catalog refresh.

## Acceptance criteria

- [ ] `.gitignore` excludes personal source CSV/HTML, images, manifest, DB, exports/imports, `.env`, and tool state.
- [ ] A pre-push check confirms only application code and safe examples are staged.
- [ ] Hosted routes are inaccessible without Access/authentication; local defaults bind to loopback.
- [ ] R2 remains private; object reads go through the protected Worker.
- [ ] No token, connection string, or secret enters frontend build artifacts, logs, docs, or Git history.
- [ ] Upload and import validations enforce size/type/checksum/path/ID rules and do not permit arbitrary local file reads.
- [ ] Bulk mutations have backups or transactional rollback; replacement preserves a recovery path.
- [ ] Threat review covers unauthorized access, malicious ZIP/image, data loss, and accidental public publication.

## Current implementation / evidence

- `.gitignore` excludes personal tables, source HTML, DB, images, manifest, exports/imports, and `.env`.
- Local auth settings and Cloudflare deployment guide exist; Access has not yet been confirmed active.
- Worker upload/import code exists but has not had a security review or full negative-test pass.

## Blockers / risks

- An undeployed or deployed-but-unprotected Worker could expose a public app surface. Do not import data until the gate is verified.
- Public repository history is persistent; prevent secrets/personal data from being staged in the first place.

## Next action

Review auth defaults and bind addresses, inspect staged-file hygiene, and exercise unauthenticated hosted access before the first real-data import.
