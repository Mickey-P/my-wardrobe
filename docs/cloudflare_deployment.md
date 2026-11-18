# Cloudflare deployment

This project keeps the local SQLite backend and adds a separate Python Worker adapter. Cloudflare uses D1 for catalog, visual descriptions, outfits, and image metadata; R2 stores original image bytes. The Worker serves the built frontend from the same origin.

## Before deploying

- Do not enable public access or an `r2.dev` URL for the R2 bucket.
- Complete and record the entire local gate below before creating or selecting any hosted resources, applying remote migrations, or deploying.
- Never import personal wardrobe data until Cloudflare Access is protecting the Worker.
- The hosted frontend uses same-origin requests and does not store a shared API token in browser storage. Access is enforced before requests reach the Worker.

Cloudflare supports FastAPI through its Python Workers ASGI adapter. D1 and R2 are accessed through Worker bindings rather than a local SQLite file. See the [FastAPI Worker guide](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/), [D1 Python example](https://developers.cloudflare.com/d1/examples/query-d1-from-python-workers/), and [R2 Worker API](https://developers.cloudflare.com/r2/get-started/workers-api/).

## 1. Prepare local Wrangler configuration

From the project root in PowerShell, copy the tracked configuration. Add the local copy to this clone's exclude list and verify it is ignored. Do not edit `.gitignore`:

```powershell
Copy-Item wrangler.jsonc wrangler.local.jsonc
Add-Content -Path .git/info/exclude -Value "/wrangler.local.jsonc"
git check-ignore -v wrangler.local.jsonc
```

The `git check-ignore` command must report `wrangler.local.jsonc` as ignored. Keep the tracked D1 placeholder unchanged and do not enter a hosted database ID yet. Use the local file with Wrangler's global `--config` option for the local gate.

## 2. Complete the local gate before any hosted resource operation

Run the targeted Worker tests and build the frontend:

```powershell
$env:PYTHONPATH = "backend"
py -m unittest discover -s backend/tests -p "test_cloudflare_worker.py" -v
pnpm --dir frontend build
```

Apply local migrations twice to verify reapplication behavior:

```powershell
pnpm dlx wrangler --config wrangler.local.jsonc d1 migrations apply my-wardrobe-db --local
pnpm dlx wrangler --config wrangler.local.jsonc d1 migrations apply my-wardrobe-db --local
```

Start the local Worker with local bindings:

```powershell
pnpm dlx wrangler --config wrangler.local.jsonc dev
```

While it is running, use test fixtures only and manually verify this workflow in the app:

- Create an item, reload, and confirm its details persist.
- Add a photo to the item; confirm it can be read, then replace it and confirm the replacement is served through the Worker (not a public bucket URL).
- Create an outfit using the fixture item, reload, and confirm the outfit and item association persist.
- Export a fixture archive, import it into the local test catalog, and confirm the item, photo, and outfit are present. Exercise archive conflict/failure handling with fixtures where available.

Stop the local Worker after verification. Do not proceed to hosted resources until the targeted tests, frontend build, both local migration applies, and manual fixture workflow have all passed and their results are recorded. These checks do not authorize production exposure or personal-data import.

## 3. Create or select hosted test resources after the local gate

Only after the entire local gate passes, authenticate Wrangler and select or create the hosted D1 database named `my-wardrobe-db` and private R2 bucket named `my-wardrobe-images`. For each resource, use its `info` command if it already exists; run its `create` command only if it is absent. After creating D1, run `d1 info` to obtain and verify its ID. Keep the bucket private; do not enable public access or an `r2.dev` URL. Use test-only resources/data and keep personal catalog and photo data out.

Authenticate after the local gate:

```powershell
pnpm dlx wrangler login
```

For D1, if the database exists, use:

```powershell
pnpm dlx wrangler --config wrangler.local.jsonc d1 info my-wardrobe-db --json
```

Only if D1 is absent, create it and then verify its name and ID:

```powershell
pnpm dlx wrangler --config wrangler.local.jsonc d1 create my-wardrobe-db
pnpm dlx wrangler --config wrangler.local.jsonc d1 info my-wardrobe-db --json
```

For R2, if the bucket exists, use:

```powershell
pnpm dlx wrangler --config wrangler.local.jsonc r2 bucket info my-wardrobe-images
```

Only if R2 is absent, create it and then verify the bucket:

```powershell
pnpm dlx wrangler --config wrangler.local.jsonc r2 bucket create my-wardrobe-images
pnpm dlx wrangler --config wrangler.local.jsonc r2 bucket info my-wardrobe-images
```

Manually write the actual D1 ID only in the ignored root-level `wrangler.local.jsonc`; do not use `--update-config` or put the ID in this guide, `wrangler.jsonc`, or any other tracked file. Confirm the D1 and R2 binding names remain `WARDROBE_DB` and `WARDROBE_IMAGES`, and do not continue if the reported database name and configured ID do not match the intended hosted test database.

## 4. Configure and verify Access before remote migrations

If a hosted Worker is required to configure Access, deploy only an empty/test-only bootstrap:
```powershell
pnpm dlx wrangler --config wrangler.local.jsonc deploy
```

Keep the D1 database empty and use only test fixtures in R2; do not upload personal data or import an archive. Immediately after bootstrap, protect the Worker with Cloudflare Access in the Cloudflare dashboard:

1. Open **Workers & Pages** and select `my-wardrobe`.
2. Open the Worker's **Access** tab and choose **Protect this Worker behind Access**.
3. Protect all traffic, including production and preview routes. Add an allow policy for your sign-in email and choose a reasonable session duration.
4. Open the Worker URL in a private browser window and confirm Cloudflare Access sign-in is required before the app is shown.

Cloudflare Access can protect a Worker across its associated domains, including its `workers.dev` URL. Refer to [Cloudflare Access for Workers](https://developers.cloudflare.com/workers/configuration/cloudflare-access/) and [workers.dev access settings](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/).

If bootstrap is not needed, configure Access before proceeding to remote migrations. In either case, verify the unauthenticated private-window login gate immediately after configuration. Do not continue until Access is confirmed active.

## 5. Apply remote migrations and run hosted fixture checks

Only after Access is enabled and verified, apply the schema with the local config, then immediately reapply it to confirm safe migration reapplication:

```powershell
pnpm dlx wrangler --config wrangler.local.jsonc d1 migrations apply my-wardrobe-db --remote
pnpm dlx wrangler --config wrangler.local.jsonc d1 migrations apply my-wardrobe-db --remote
```

The second apply must report that there are no unapplied migrations. The migration creates separate tables for catalog records, visual-description source fields, outfits, and image metadata. Then use only test fixtures to verify hosted D1 migration/reapplication behavior, private-R2 upload/read/replacement, frontend/API parity, and fixture export/import including archive and conflict/failure handling. Record passing evidence; hosted fixture checks do not replace the F09 security gate or authorize personal-data import.

## 6. Satisfy the F09 security gate before production exposure

Do not mark the Worker as production-exposed until F09 passes. Before exposure, verify and record Access protection for the production host and preview routes, private R2 configuration, and an unauthenticated private-window login gate. Production exposure is not permission to import personal data.

## 7. Keep all F07/backup/rollback gates before personal-data import

Before starting a personal-data import, confirm every item in this checklist:

- Cloudflare Access is verified by an unauthenticated private-browser-window test.
- R2 remains private with no public bucket access or `r2.dev` URL, and photo reads are protected by the Worker and Cloudflare Access.
- The local Worker test suite and local end-to-end fixture checks pass.
- Hosted fixture verification passes for D1/R2 and export/import/archive behavior using test-only data.
- The F07 fixture-based export/import round trip passes.
- A local export backup has been created and verified, including the catalog, visual descriptions, manifest, and available photos.
- The original source CSVs, visual CSV, photos, photo manifest, and local SQLite database are preserved unchanged and remain available to restart the local file-based app.
- A fixture-only rollback test in a disposable workspace passes: after a simulated hosted-import failure, the fixture file-based app restarts and source record and photo checksums are unchanged.
- The recovery procedure is to stop cloud use and quarantine the remote target without modifying or deleting it, then continue with the unchanged local app. No in-place D1/R2 restore or unverified restore is required or permitted by this initial-migration rollback policy.
- The F09 security gate passes and production exposure requirements are satisfied.

Do not proceed with personal-data import unless every checklist item is confirmed.

## 8. Import the local wardrobe only after all gates

1. Start the local app and export a full ZIP archive containing the catalog, visual descriptions, image manifest, outfits, and available photos.
2. Sign in to the protected Cloudflare Worker in your browser.
3. Use **Import ZIP** in the cloud app and choose the exported archive. Confirm the import report before using the hosted catalog.
4. Check several item IDs and photos, create a test outfit, then export a cloud ZIP and verify its contents.

The R2 bucket remains private; photo reads go through the Access-protected Worker. ZIP imports preserve existing notes and photos when IDs conflict unless you confirm an update.

## 9. Recover from a hosted import failure

For an initial CSV-to-cloud migration, rollback means returning to the unchanged local file-based app. It does not mean restoring D1/R2 in place.

1. Stop using the hosted app immediately. Do not retry the import or make further writes to the remote database or bucket.
2. Quarantine the cloud target: keep it protected and out of use, record which hosted D1/R2 resources were involved, and leave their contents untouched for later investigation. Do not delete, truncate, overwrite, or attempt an unverified restore of the remote target.
3. Continue locally from the preserved original CSVs, visual CSV, photos, photo manifest, and local SQLite database. Restart the local app and confirm it is using its local file/data paths, not Cloudflare bindings. Do not copy cloud data over the local sources or database.
4. If the unchanged local app cannot be restarted, stop and investigate using the verified local export backup and a separately validated recovery procedure; do not improvise an overwrite or restore.
5. Record the failure and keep cloud use paused until the cause and any subsequent migration plan are reviewed. The original source files and local database remain the recovery source for this initial migration.

## Local Worker development

```powershell
pnpm --dir frontend build
pnpm dlx wrangler --config wrangler.local.jsonc dev
```

Wrangler uses local development bindings by default. Avoid adding `--remote` bindings to development commands unless you explicitly intend to access hosted data.

## Current limits

This Worker adapter is intentionally separate from the local SQLAlchemy/SQLite API. The Cloudflare runtime uses D1 and R2 bindings. A future ChatGPT/MCP connection needs its own authentication path; do not expose a bearer token through the browser frontend.
