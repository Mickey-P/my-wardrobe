# Roadmap Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the roadmap's delivery order, Cloudflare safety gates, and release evidence clear and consistent.

**Architecture:** Keep `docs/plan/README.md` as the roadmap source of truth. Update F07, F08, F09, and F11 where feature-level instructions must align with the central sequence; align the Cloudflare deployment guide's personal-data import instructions with F08.

**Tech Stack:** Markdown documentation; Git diff checks.

**Spec:** `docs/superpowers/specs/2026-11-18-roadmap-refresh-design.md`

## Global Constraints

- Do not change product scope, feature status, or implementation.
- Do not install skills, run tests, deploy Cloudflare, or inspect personal wardrobe data.
- Preserve the local-first workflow and independent local API and Cloudflare adapters.
- Do not import personal data before Access protection, export integrity, and rollback are verified.
- Keep current acceptance requirements unless a wording change is needed to clarify sequencing or evidence.

## Review Focus

- Duplicate or out-of-order feature phases: ensure dependencies appear once in a coherent sequence.
- Personal-data import before prerequisites: require Access, private storage, tested export integrity, backup, and rollback first.
- Hosted exposure before security verification: make the F09 gate apply before production exposure and real-data import.
- Unverified release claims: require exact commands and results; do not invent commands or results.
- Premature assistant integration: keep F10 deferred until API contracts are verified.

---

### Task 1: Clarify roadmap dependencies and sequence

**Files:**
- Modify: `docs/plan/README.md`

**Interfaces:**
- Consumes: Current feature IDs, statuses, and dependencies in `docs/plan/features/`.
- Produces: One central dependency-oriented delivery order and explicit cloud go/no-go gates.

- [x] **Step 1: Define the dependency map and delivery phases**

Add a concise dependency section and replace the current suggested order with this flow: local data/API baseline (F01–F03); photos and UI/outfit flows (F02, F04–F06); portability (F07); security gate (F09); Cloudflare test deployment (F08); release verification (F11). Keep F10 deferred until the local and Worker contracts are verified. Make clear that local verification starts early and F11's release gate is final.

- [x] **Step 2: Separate fixture bootstrap, production exposure, and personal-data migration**

State that production exposure and personal-data import are separate go/no-go decisions. If deployment is needed to configure Access, allow only an empty/test-only bootstrap and protect it immediately. Require the F09 gate before production exposure. Require Access verification, private storage, local and hosted fixture checks, export integrity, and a verified local source backup before importing personal data. Define first-migration rollback as returning to the unchanged local file-based app and quarantining a failed cloud target, not an unverified in-place D1/R2 restore. Preserve local-mode support and the existing status definitions.

- [x] **Step 3: Check the roadmap for internal consistency**

Confirm each feature appears in the intended phase, no phase implies personal-data import before its gates, and README feature statuses remain unchanged.

- [x] **Step 4: Validate Markdown diff hygiene**

Run: `git diff --check`
Expected: no whitespace errors.

### Task 2: Align portability and Cloudflare plans

**Files:**
- Modify: `docs/plan/features/F07-portability.md`
- Modify: `docs/plan/features/F08-cloudflare.md`
- Modify: `docs/cloudflare_deployment.md`

**Interfaces:**
- Consumes: Task 1's central order and Cloudflare go/no-go gates.
- Produces: Feature acceptance criteria that require fixture-based portability evidence and staged Cloudflare verification.

- [x] **Step 1: Make F07 round-trip and rollback evidence an explicit cloud prerequisite**

Clarify that the fixture-based export/import round trip must pass before personal-data migration. Define first-migration rollback as returning to the unchanged local file-based app: preserve source CSVs, photos, manifest, and local SQLite data; quarantine a failed cloud target instead of requiring an unverified in-place D1/R2 restore. Test this fallback with fixtures. Retain the existing archive validation and data-preservation requirements.

- [x] **Step 2: Split F08 verification into local/test, fixture bootstrap, production exposure, and personal-data import stages**

Before hosted work, document exact commands for the Worker tests, local D1 migration and reapplication, frontend build, and local Worker start; require a fixture-based local end-to-end pass. Create root-level `wrangler.local.jsonc` from the tracked template, add `/wrangler.local.jsonc` to `.git/info/exclude`, and confirm `git check-ignore wrangler.local.jsonc` succeeds. Leave its placeholder D1 ID during local checks:

```powershell
$env:PYTHONPATH = "backend"
py -m unittest discover -s backend/tests -p "test_cloudflare_worker.py" -v
pnpm --dir frontend build
pnpm dlx wrangler --config wrangler.local.jsonc d1 migrations apply my-wardrobe-db --local
pnpm dlx wrangler --config wrangler.local.jsonc d1 migrations apply my-wardrobe-db --local
pnpm dlx wrangler --config wrangler.local.jsonc dev
```

After local checks pass, configure the local file with the real ID and verify Wrangler reports the intended database name and ID before any hosted resource operation. If deployment is needed to configure Access, limit the bootstrap to an empty/test-only Worker and data, then enable and verify Access immediately. Apply remote D1 migrations only after Access is verified. Require the F09 gate before production exposure. Before personal-data import, require verified Access, private R2, passing Worker/local end-to-end/hosted fixture checks, F07 round-trip evidence, a verified local source backup, and a tested fallback to the unchanged local file-based app. State that failed cloud targets are quarantined; do not require unverified in-place D1/R2 restoration. Never commit or document the real ID or local config. Keep exact account-specific values and unrun results out of the documentation.

- [x] **Step 3: Align the deployment guide's personal-data import checklist**

In `docs/cloudflare_deployment.md`, put hosted resource creation/selection after local verification. Document these Wrangler commands, using create only when the resource does not exist and info when selecting an existing resource:

```powershell
pnpm dlx wrangler --config wrangler.local.jsonc d1 create my-wardrobe-db
pnpm dlx wrangler --config wrangler.local.jsonc r2 bucket create my-wardrobe-images
pnpm dlx wrangler --config wrangler.local.jsonc d1 info my-wardrobe-db --json
pnpm dlx wrangler --config wrangler.local.jsonc r2 bucket info my-wardrobe-images
```

Do not pass `--update-config`; copy the returned D1 ID only into the ignored local config and verify it identifies the intended database. Apply remote migrations only after Access is verified, run the same remote migration command twice, and expect the second run to report no unapplied migrations. Then run hosted fixtures before production exposure and personal-data import. Require verified Access and private R2, passing Worker/local end-to-end/hosted fixture checks, F07 round-trip evidence, a verified local source backup, and a tested fallback to the unchanged local file-based app before personal-data import. If hosted import fails, quarantine the cloud target and continue locally; do not document or imply an unverified in-place D1/R2 restore. Do not document or commit the actual ID or unrun results.

- [x] **Step 4: Check the portability and Cloudflare instructions against the design**

Confirm F07, F08, and the deployment guide agree with the README and do not imply that a successful test deployment or Access check alone authorizes importing personal data.

- [x] **Step 5: Validate Markdown diff hygiene**

Run: `git diff --check`
Expected: no whitespace errors.

### Task 3: Make security and release gates actionable

**Files:**
- Modify: `docs/plan/features/F09-security.md`
- Modify: `docs/plan/features/F11-release.md`

**Interfaces:**
- Consumes: Task 1's phase order and Task 2's staged cloud prerequisites.
- Produces: A security gate before hosted exposure and real-data import, plus continuous verification and a final release evidence gate.

- [x] **Step 1: Clarify F09 gate timing and evidence**

State that security acceptance is required before hosted production exposure and personal-data import. Require separate recorded unauthenticated private-window evidence for the production host and every enabled preview route, plus private R2 access, staged-file hygiene, and applicable negative tests. Do not claim checks have passed unless results are recorded.

- [x] **Step 2: Separate F11 continuous checks from final release acceptance**

Keep baseline and regression checks running during feature work. Define release acceptance as the current-checkout backend/frontend checks and full local scenario with exact commands, outcomes, known limitations, and rollback evidence recorded. Add isolated tests in `backend/tests/test_release_scenario.py`: `test_fixture_release_round_trip` and `test_hosted_import_failure_keeps_local_fallback`. Use synthetic fixtures, temporary storage, and test-only path injection; never read `data/` or call `start.ps1` because that script requires private CSVs. The round-trip test imports fixture data, verifies item/photo reads, persists an outfit, exports an archive, imports it into an empty database, checks records/links/image bytes, and confirms rejected imports leave no partial mutation. The fallback test simulates hosted-import failure, captures source/file and local-database state, instantiates a fresh local app instance from temporary paths, and verifies fixture records and photo checksums remain unchanged. Run both with:

```powershell
$env:PYTHONPATH = "backend"
py -m unittest discover -s backend/tests -p "test_release_scenario.py" -v
```

Also run the repository's documented release checks:

```powershell
$env:PYTHONPATH = "backend"
py -m unittest discover -s backend/tests -v
pnpm --dir frontend build
```

Preserve the requirement that tests use fixtures rather than live production services or data.

Define rollback evidence as a fixture-only check in a disposable workspace: capture checksums and state for synthetic source files and the local database, simulate a hosted-import failure against test resources, quarantine the cloud target, restart the local file-based app, and verify the same fixture records and photo checksums remain available. Record the exact procedure and outcomes; never use personal data for this test.

- [x] **Step 3: Check the F09/F11 gate boundaries**

Confirm F09 does not imply deployment approval by itself and F11 does not imply personal-data migration approval.

- [x] **Step 4: Validate Markdown diff hygiene**

Run: `git diff --check`
Expected: no whitespace errors.

### Task 4: Review the coordinated roadmap

**Files:**
- Review: `docs/plan/README.md`
- Review: `docs/plan/features/F07-portability.md`
- Review: `docs/plan/features/F08-cloudflare.md`
- Review: `docs/plan/features/F09-security.md`
- Review: `docs/plan/features/F11-release.md`
- Review: `docs/cloudflare_deployment.md`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: A consistent set of roadmap documents with no invented completion evidence.

- [x] **Step 1: Compare every changed criterion with the design**

Verify scope, constraints, staged cloud gates, and continuous-versus-final verification are covered.

- [x] **Step 2: Check unchanged roadmap state**

Confirm feature statuses, product scope, F01–F06 feature requirements, and F10's deferred status did not change.

- [x] **Step 3: Review the final diff**

Run: `git diff --check` and inspect `git diff -- docs/plan`.
Expected: only the intended roadmap, four feature plans, and Cloudflare deployment guide changed; no whitespace errors or unsupported claims.
