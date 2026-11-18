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

- [ ] The F09 security gate passes and evidence is recorded before any hosted production exposure or personal-data import.
- [ ] `.gitignore` excludes personal source CSV/HTML, images, manifest, DB, exports/imports, `.env`, and tool state.
- [ ] A pre-push or staged-file-hygiene check confirms only application code and safe examples are staged, and its evidence records the exact check and files examined.
- [ ] An unauthenticated private-browser-window test demonstrates that hosted routes require Cloudflare Access/authentication before the app is shown; record the URL type, private-window result, and sign-in outcome. Local defaults bind to loopback.
- [ ] Record separate unauthenticated private-window evidence for the production host and for every enabled preview route. For each URL, record the route type, unauthenticated result, and sign-in outcome; do not infer one route's result from another.
- [ ] A private-R2 access check demonstrates that R2 has no public URL or `r2.dev` endpoint and that object reads go only through the protected Worker; record bucket and object-read evidence.
- [ ] No token, connection string, or secret enters frontend build artifacts, logs, docs, or Git history.
- [ ] Upload and import validations enforce size/type/checksum/path/ID rules and do not permit arbitrary local file reads.
- [ ] Bulk mutations have backups or transactional rollback; replacement preserves a recovery path.
- [ ] Threat review covers unauthorized access, malicious ZIP/image, data loss, and accidental public publication.
- [ ] Applicable negative tests cover unauthenticated access, direct/private-R2 access attempts, staged personal/secret files, traversal and arbitrary-read attempts, invalid upload/import data, and ID/path failures. Record the test, setup, observed outcome, and whether it passed or remains open.

The security acceptance evidence is required before hosted production exposure and before any personal-data import. F09 passing is a necessary security gate, but F09 alone does not approve Cloudflare deployment or personal-data import; the remaining F08, F07, backup, and rollback gates must also pass.

## Current implementation / evidence

- `.gitignore` excludes personal tables, source HTML, DB, images, manifest, exports/imports, and `.env`.
- Local auth settings and Cloudflare deployment guide exist; Access has not yet been confirmed active.
- Worker upload/import code exists but has not had a security review or full negative-test pass.

## Blockers / risks

- An undeployed or deployed-but-unprotected Worker could expose a public app surface. Do not import data until the gate is verified.
- Public repository history is persistent; prevent secrets/personal data from being staged in the first place.

## Next action

Before any hosted production exposure or personal-data import, review auth defaults and bind addresses, run and record staged-file-hygiene evidence, verify unauthenticated private-window Access separately for the production host and every enabled preview route, verify private R2 and protected object reads, and complete applicable negative tests. Do not record these checks as passed until their results are captured.
