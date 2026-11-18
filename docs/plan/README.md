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

## Suggested delivery order

1. F01–F03: establish trusted source data and a verified local API baseline.
2. F02 and F05: ensure original photos, manifest status, and manual recovery paths are dependable.
3. F04 and F06: verify the core browse, inspect, and outfit workflows.
4. F07: prove a complete export/import round trip before any cloud migration.
5. F09 and F08: close the security gate, then deploy and verify Cloudflare with test data first.
6. F11: verify a clean setup and document the supported release path.
7. F10: design the adapter only after the REST contract is stable and access is explicit.

Dependencies are directional rather than a requirement to finish every local UI feature before cloud work. Never migrate the personal catalog until export integrity, access protection, and rollback are verified.

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
