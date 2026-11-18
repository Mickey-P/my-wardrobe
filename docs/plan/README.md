# My Wardrobe: delivery plan

**Plan owner:** project owner  
**Last reviewed:** 2026-11-18  
**Purpose:** split delivery into feature-sized work packages that can be continued and tracked in separate chats.

This is the project source of truth for feature scope, acceptance, status, and blockers. Update the relevant feature plan and the status table here whenever work changes. Do not mark a feature done because code exists: its acceptance criteria must be demonstrated.

## Status definitions

| Status | Meaning |
| --- | --- |
| Planned | Scope is written down; implementation has not started. |
| In progress | Work is active or implementation is incomplete. |
| Implemented, needs verification | Code is present, but one or more acceptance checks have not been demonstrated. |
| Blocked | Progress depends on a named external decision, access, or fix. Keep the blocker specific. |
| Done | All acceptance criteria pass and evidence is recorded. |

## Current project snapshot

The local-first application, original-photo downloader, SQLite backend, React frontend, outfit editing, and data export/import are present in the repository. The README reports 139 local images. Treat these as **implemented, needs verification** until the feature plans' acceptance checks have been run against the current checkout and private data. The personal wardrobe files and images are local-only and must remain out of the public repository.

Cloudflare support has a separate Worker adapter, D1 migration, R2 binding configuration, and deployment guide. It is **in progress**: the Worker has not been deployed or verified end-to-end, `wrangler.jsonc` still has a placeholder D1 ID, Access protection has not been confirmed, and the Worker test file needs a clean test run. Do not import personal data or deploy an unprotected Worker.

## Feature register

| ID | Feature | Status | Detailed plan |
| --- | --- | --- | --- |
| F01 | Catalog data and imports | Implemented, needs verification | [F01](features/F01-catalog-data.md) |
| F02 | Original-photo pipeline | Implemented, needs verification | [F02](features/F02-photo-pipeline.md) |
| F03 | Local backend and stable API | Implemented, needs verification | [F03](features/F03-local-api.md) |
| F04 | Wardrobe browsing and item details | Implemented, needs verification | [F04](features/F04-catalog-ui.md) |
| F05 | Photo management and manual matching | Implemented, needs verification | [F05](features/F05-photo-management.md) |
| F06 | Manual outfit builder | Implemented, needs verification | [F06](features/F06-outfits.md) |
| F07 | Export and archive import | Implemented, needs verification | [F07](features/F07-portability.md) |
| F08 | Cloudflare hosting and data adapter | In progress | [F08](features/F08-cloudflare.md) |
| F09 | Privacy and security | In progress | [F09](features/F09-security.md) |
| F10 | Future ChatGPT/MCP integration | Planned | [F10](features/F10-assistant-api.md) |
| F11 | Quality, setup, and release | In progress | [F11](features/F11-release.md) |

## Delivery dependencies and phases

Feature dependencies form one directional delivery sequence. These are implementation and verification phases, not a requirement to finish every local UI feature before beginning independent Cloudflare adapter work.

1. **Local data and API baseline (F01–F03):** establish trusted source data, the local SQLite/API baseline, and stable local API contracts. Local fixture-based checks begin here.
2. **Photos and UI/outfit flows (F02, F04–F06):** verify original photos and recovery paths, browsing and item details, photo management, and manual outfit workflows. F02 and F05 remain dependencies of the photo/management portion of this phase.
3. **Portability (F07):** demonstrate fixture-based export and archive-import integrity, including a documented and tested first-migration rollback path, before any personal-data migration.
4. **Security gate (F09):** verify the applicable privacy and security controls before hosted production exposure or real-data import.
5. **Cloudflare test deployment (F08):** run the local Worker tests and local end-to-end fixture checks before any hosted work. If Access configuration requires an existing hosted Worker, a minimal empty/test-only bootstrap may be deployed only to establish and immediately protect the Worker with Access. Verify Access protection immediately, then continue with hosted fixture verification using test-only data. A successful hosted fixture run does not approve production exposure or personal-data import; F09 must pass before any production exposure.
6. **Release verification (F11):** use F11 for continuous baseline and regression checks during feature work and as the final release gate after the implementation and fixture-based acceptance evidence are complete.

F10 is deferred until the local REST/API and Cloudflare/Worker contracts are both verified and access requirements are explicit. F11 is the final release gate: F10 may not substitute for or accelerate F11 acceptance.

### Cloudflare exposure, test work, and personal-data import

Cloudflare work has three distinct decisions:

- **Local/test work:** local Worker bindings and fixture/test data may be used to verify the separate Cloudflare adapter, independent of local SQLite/API work. Local Worker tests and local end-to-end fixture checks precede hosted work. If Access requires an existing Worker, only an empty/test-only bootstrap is permitted for initial configuration, and Access must be protected and verified immediately afterward. Hosted fixture verification follows, using test-only data.
- **Hosted production exposure:** exposing the Worker or R2-backed interface to a production host requires the F09 security gate to pass first. This is an exposure decision, not approval to import personal data.
- **Personal-data import:** importing the personal catalog or photos is a separate go/no-go decision. In addition to the F09 security gate and any applicable production-exposure requirements, it requires verified Cloudflare Access, private R2 storage, passing local and hosted fixture checks, tested F07 fixture export/import integrity, a verified local export backup, and a passing fixture-only local-app fallback test demonstrating unchanged source files and local DB plus preserved photo checksums. It must not proceed before all of these gates pass.

The local-first workflow and local-mode support remain unchanged. Cloudflare test success, private/production exposure, and personal-data migration are not interchangeable milestones.

### First-migration rollback policy

Before personal-data import, preserve the original local catalog CSV, visual descriptions CSV, photos, photo manifest, and local SQLite database unchanged and available to the local file-based app. These preserved sources are the rollback source for the initial migration. Verify a local export backup, including the catalog, visual descriptions, manifest, and available photos, before import.

If the hosted import fails, stop hosted use, quarantine the cloud target, and continue with the unchanged local file-based app. Quarantine means keep the remote D1/R2 target protected and out of use, record it, and leave its contents untouched for investigation; do not delete, truncate, overwrite, or attempt an in-place D1/R2 restore or other unverified restore. The initial rollback is a return to the preserved local sources and SQLite data, not a cloud-side recovery operation.

## How to continue a feature in a separate chat

Use [`FEATURE_TEMPLATE.md`](FEATURE_TEMPLATE.md) when adding another feature. Start the chat with the link/path to its feature plan and the current code checkout. Ask the chat to:

1. Read `docs/plan/README.md` and that feature's plan.
2. Inspect current code and report any mismatch before changing scope.
3. Work only on that feature and necessary dependencies.
4. Update its status, evidence, unresolved issues, and next action in the plan.
5. Update the register above if status changed.

Keep changes to shared API/schema contracts coordinated in F03/F08 plans and record compatibility decisions there. A feature is not complete until the evidence section names the exact checks and result.

## Open project-wide blockers

- Cloudflare D1 ID still needs to be entered into local Wrangler configuration before deployment.
- Cloudflare Access must be enabled and verified from a private browser session before personal data is imported.
- Cloudflare adapter tests and an end-to-end local Worker run are not yet verified.
- README's cloud-hosting status text should be reconciled with the new Worker adapter and deployment guide.
- Skills have not been installed or added. Candidate review and safety rules are in [skills review](skills-review.md).

## Change log

- 2026-11-18: created feature plan based on current repository structure and documented Cloudflare readiness gaps.
