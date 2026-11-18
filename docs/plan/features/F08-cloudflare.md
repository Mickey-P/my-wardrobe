# F08 — Cloudflare hosting and data adapter

**Status:** In progress  
**Goal:** make the app remotely reachable through a single Access-protected Worker while keeping personal data in private D1/R2 resources.

## Scope

- Python Worker adapter, D1 migrations, private R2 object access, static frontend assets, same-origin API, deployment guide.
- D1 is the system of record for cloud catalog/outfits/manifest; R2 stores photo bytes.
- Protect all Worker URLs with Cloudflare Access before importing personal data.
- Use test data for first deployment and end-to-end checks.

## Verification stages

### 1. Local/test work

- First copy tracked `wrangler.jsonc` to root-level `wrangler.local.jsonc`, add `/wrangler.local.jsonc` to `.git/info/exclude`, and confirm it is ignored with `git check-ignore`. Keep the tracked D1 placeholder in place during this stage.
- Run `$env:PYTHONPATH = "backend"` followed by `py -m unittest discover -s backend/tests -p "test_cloudflare_worker.py" -v`, then build with `pnpm --dir frontend build`.
- Apply local migrations twice with `pnpm dlx wrangler --config wrangler.local.jsonc d1 migrations apply my-wardrobe-db --local`.
- Start the Worker with `pnpm dlx wrangler --config wrangler.local.jsonc dev` and manually verify a fixture workflow covering item persistence, photo upload/read/replacement, outfit persistence/association, and archive export/import behavior.
- Complete and record passing results for the whole local gate before any hosted resource operation.
- This stage validates the separate local/test adapter and does not authorize production exposure or personal-data import.

### 2. Hosted test resources and optional Access bootstrap

- Only after the entire local gate passes—including Worker tests, frontend build, two local migration applies, and the fixture workflow—select or create hosted D1 `my-wardrobe-db` and private R2 `my-wardrobe-images`.
- If D1 exists, select it and verify its name and ID with:

  ```powershell
  pnpm dlx wrangler --config wrangler.local.jsonc d1 info my-wardrobe-db --json
  ```

- Only if D1 is absent, create it and then verify its name and ID:

  ```powershell
  pnpm dlx wrangler --config wrangler.local.jsonc d1 create my-wardrobe-db
  pnpm dlx wrangler --config wrangler.local.jsonc d1 info my-wardrobe-db --json
  ```

- If R2 exists, select it and verify the bucket with:

  ```powershell
  pnpm dlx wrangler --config wrangler.local.jsonc r2 bucket info my-wardrobe-images
  ```

- Only if R2 is absent, create it and then verify the bucket:

  ```powershell
  pnpm dlx wrangler --config wrangler.local.jsonc r2 bucket create my-wardrobe-images
  pnpm dlx wrangler --config wrangler.local.jsonc r2 bucket info my-wardrobe-images
  ```

- Run each `create` only if the corresponding resource is absent; otherwise use `info` without creating it. Write the actual D1 ID only in the ignored root-level `wrangler.local.jsonc`, manually, and never use `--update-config`. Verify the intended database name and ID using Wrangler's global `--config` option.
- Do not edit `.gitignore` or track local deployment values. Keep the bucket private and use test-only resources/data, not personal catalog or photo data.
- If a hosted Worker is required to configure Access, deploy only an empty/test-only bootstrap through Wrangler's global `--config` option.
- Enable and verify Cloudflare Access immediately after the bootstrap, including an unauthenticated private-window check, before continuing.
- If bootstrap is not needed, configure and verify Access before applying any remote migrations.

### 3. Hosted fixture verification

- Apply remote D1 migrations only after Access is enabled and verified. Apply the migration command twice; the second apply must report no unapplied migrations:

  ```powershell
  pnpm dlx wrangler --config wrangler.local.jsonc d1 migrations apply my-wardrobe-db --remote
  pnpm dlx wrangler --config wrangler.local.jsonc d1 migrations apply my-wardrobe-db --remote
  ```

- Keep personal data excluded from the hosted environment, and use test-only fixtures for all hosted D1/R2 and archive checks.
- Verify D1/R2 behavior, frontend/API parity, private photo reads, and fixture-based export/import and archive behavior.
- Passing hosted fixture checks demonstrates adapter behavior only; they do not authorize production exposure or personal-data import.

### 4. Production exposure

- Do not expose the hosted Worker or R2-backed interface until the F09 security gate passes.
- Production exposure requires separate, recorded evidence for Access protection and private storage.
- Exposing a production host is not approval to migrate personal catalog or photo data.

### 5. Personal-data import

- Personal-data import is a separate go/no-go decision.
- Before importing personal data, verify Cloudflare Access, private R2, passing local and hosted fixture checks (including D1/R2 and archive behavior), passing F07 fixture export/import round-trip evidence, and a verified local export backup.
- Preserve the original source CSVs, visual CSV, photos, photo manifest, and local SQLite database unchanged and available to the file-based app. Test the fallback in a disposable fixture-only workspace: after a simulated hosted-import failure, restart the fixture app and verify source record and photo checksums remain unchanged.
- Initial migration rollback means stopping cloud use, quarantining the hosted target without modifying or deleting it, and continuing with the unchanged local file-based app. Do not attempt an in-place D1/R2 restore or other unverified restore.
- Do not proceed on test-deployment success alone.

## Acceptance criteria

- [ ] Before hosted resource operations, the root local config is copied from `wrangler.jsonc`, excluded by `.git/info/exclude`, and confirmed with `git check-ignore`; the targeted Worker tests and frontend build pass, local D1 migrations apply twice, and a local Worker fixture workflow verifies item, photo, outfit, and archive behavior.
- [ ] Only after the local gate passes, the intended hosted D1 database name and real, validated ID are verified through ignored root-level `wrangler.local.jsonc` using Wrangler's global `--config` option. The config has matching D1/R2 binding names. Do not put the actual database ID or any secret in tracked documentation or tracked config.
- [ ] After Access is enabled and verified, hosted D1 migrations apply cleanly; a second apply reports no unapplied migrations, demonstrating safe hosted migration reapplication.
- [ ] In local/test work, the Worker starts with local bindings and frontend/API work on the same origin.
- [ ] All local contract endpoints used by the UI have equivalent Worker behavior, including useful error responses.
- [ ] In local/test work, image upload/read/replacement uses private R2; no public bucket URL is enabled.
- [ ] If hosted bootstrap is needed for Access setup, it is empty/test-only, and Access is enabled and verified immediately after bootstrap and before remote D1 migrations.
- [ ] Remote D1 migrations occur only after Access verification; hosted fixture verification then passes for D1/R2 and archive behavior using test-only data, but does not waive F09 or production gates.
- [ ] Before production exposure, the F09 security gate passes; Cloudflare Access protects production Worker and preview routes, and an unauthenticated private-window check is recorded.
- [ ] Fixture-based export/import on cloud preserves catalog, visual details, outfits, and photos; conflicts and failures are safe.
- [ ] Before personal-data import, F07 fixture round-trip evidence passes; Access and private R2 are verified; local and hosted fixture checks pass for D1/R2 and archives; and a verified local export backup exists.
- [ ] Before personal-data import, original source CSVs, visual CSV, photos, photo manifest, and local SQLite database are preserved unchanged and available to the local file-based app; a disposable fixture-only rollback test proves the fixture app restarts after simulated hosted-import failure and source record/photo checksums are unchanged.
- [ ] Initial-migration recovery stops cloud use and quarantines the remote target without modifying or deleting it, then continues with the unchanged local app; no in-place D1/R2 restore or unverified restore is part of this rollback policy.
- [ ] Personal data is not imported until the separate verification stages above pass; successful test deployment does not waive those gates.

## Current implementation / evidence

- `backend/cloudflare/worker.py`, `backend/cloudflare/migrations/0001_initial.sql`, and `wrangler.jsonc` exist.
- `wrangler.jsonc` still contains `REPLACE_WITH_D1_DATABASE_ID`; deployment has not been demonstrated.
- `docs/cloudflare_deployment.md` describes setup, Access, migration, deployment, and import steps.
- `backend/tests/test_cloudflare_worker.py` has a test harness but still needs a syntax/test run and broader integration coverage.

## Blockers

- Actual D1 ID has not been added to local Wrangler configuration.
- Access gate has not been verified from an unauthenticated browser session.
- Worker runtime compatibility, API parity, D1/R2 behavior, and archive flow remain unverified.

## Next action

Check test file syntax and understand local Windows async test constraints, then use targeted Worker tests and local bindings for fixture-based verification. Production exposure requires the F09 security gate and confirmed Access; personal-data import additionally requires all F07, private-R2, backup, and tested-rollback gates.

## Operational guardrails

- Local/test work may use local bindings and fixtures without production exposure.
- No production exposure before the F09 security gate passes.
- No personal-data import before verified Access, private R2, passing local and hosted fixture checks including D1/R2 and archive behavior, F07 round-trip evidence, a verified local export backup, preservation of the unchanged local sources/database, and a passing disposable-workspace local-fallback test.
- On initial hosted-import failure, stop cloud use and quarantine the remote target without destructive changes; continue with the unchanged local app rather than attempting an in-place D1/R2 restore.
- Hosted work must not begin until the local Worker tests and local end-to-end fixture checks have passing recorded evidence.
- An optional Access bootstrap must remain empty/test-only and be protected immediately.
- No bucket public access.
- Do not include actual database IDs in docs or commit local configuration containing them; do not put API tokens in frontend code.
- Local mode remains supported independently of Cloudflare.
