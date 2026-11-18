# F10 — Future ChatGPT/MCP integration

**Status:** Planned  
**Goal:** allow an explicitly authorized assistant client to read wardrobe data and save user-approved outfits without making cloud services mandatory for local use.

## Scope

- Stable REST resources for item lists/details, original photos, visual descriptions/critical details, outfit CRUD, and shortlist composition.
- Separate integration adapter for MCP or another local API protocol; reuse application services.
- Explicit authentication, narrow scopes, and read/write consent.
- This is future work; do not implement full MCP as a prerequisite to local/cloud MVP.

## Acceptance criteria

- [ ] REST contract is stable and documented with examples and versioning policy.
- [ ] Integration can list items, retrieve a specified ID, retrieve its photo/visual description, and create/update an outfit through existing services.
- [ ] Client cannot read arbitrary local paths, mutate permanent IDs, or overwrite images without confirmation.
- [ ] Authentication is separate from browser Access/session; no secret is exposed in the frontend.
- [ ] User can disable/revoke the integration without disabling the app.
- [ ] Integration tests use a fake client and do not require ChatGPT/cloud for local app behavior.

## Current implementation / evidence

- REST routes exist in local FastAPI and Worker adapter; no MCP server/client integration exists.

## Blockers / risks

- API parity between local and cloud adapters must be established first.
- Decide later whether the integration runs locally, behind Access, or through a dedicated authenticated endpoint.

## Next action

Wait until F03 and F08 contracts are verified; then draft a protocol-neutral tool/resource map before choosing MCP implementation details.
