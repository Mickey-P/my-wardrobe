# Cloudflare deployment

This project keeps the local SQLite backend and adds a separate Python Worker adapter. Cloudflare uses D1 for catalog, visual descriptions, outfits, and image metadata; R2 stores original image bytes. The Worker serves the built frontend from the same origin.

## Before deploying

- Create a D1 database named `my-wardrobe-db` and a private R2 bucket named `my-wardrobe-images`.
- Do not enable public access or an `r2.dev` URL for the R2 bucket.
- Never import personal wardrobe data until Cloudflare Access is protecting the Worker.
- The hosted frontend uses same-origin requests and does not store a shared API token in browser storage. Access is enforced before requests reach the Worker.

Cloudflare supports FastAPI through its Python Workers ASGI adapter. D1 and R2 are accessed through Worker bindings rather than a local SQLite file. See the [FastAPI Worker guide](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/), [D1 Python example](https://developers.cloudflare.com/d1/examples/query-d1-from-python-workers/), and [R2 Worker API](https://developers.cloudflare.com/r2/get-started/workers-api/).

## 1. Install and authenticate the tools

From the project folder in PowerShell:

```powershell
pnpm dlx wrangler login
pnpm dlx wrangler d1 info my-wardrobe-db
```

Copy the database ID from the D1 information output into `wrangler.jsonc`, replacing `REPLACE_WITH_D1_DATABASE_ID`. The database ID is configuration, not a secret. Confirm the D1 database and R2 bucket names match the bindings in that file.

## 2. Apply the D1 schema

```powershell
pnpm dlx wrangler d1 migrations apply my-wardrobe-db --remote
```

The migration creates separate tables for catalog records, visual-description source fields, outfits, and image metadata.

## 3. Install Worker dependencies and build the frontend

```powershell
python -m pip install uv
uv sync
pnpm --dir frontend install
pnpm --dir frontend build
```

The production build automatically uses Cloudflare Access authentication mode and same-origin API URLs. No bearer token is embedded in the frontend.

## 4. Deploy the Worker

```powershell
uv run pywrangler deploy
```

Wrangler prints the Worker URL on `workers.dev`. At this point the D1 database should still be empty.

## 5. Protect the Worker with Cloudflare Access

In the Cloudflare dashboard:

1. Open **Workers & Pages** and select `my-wardrobe`.
2. Open the Worker's **Access** tab and choose **Protect this Worker behind Access**.
3. Protect **all traffic**, including production. Add an allow policy for your sign-in email and choose a reasonable session duration.
4. Open the `workers.dev` URL in a private browser window. Confirm it requires Cloudflare Access sign-in before showing the app.

Cloudflare Access can protect a Worker across its associated domains, including its `workers.dev` URL. Refer to [Cloudflare Access for Workers](https://developers.cloudflare.com/workers/configuration/cloudflare-access/) and [workers.dev access settings](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/).

Do not proceed with personal data import until the private-window check confirms the Access login gate is active.

## 6. Import the local wardrobe

1. Start the local app and export a full ZIP archive containing the catalog, visual descriptions, image manifest, outfits, and available photos.
2. Sign in to the protected Cloudflare Worker in your browser.
3. Use **Import ZIP** in the cloud app and choose the exported archive. Confirm the import report before using the hosted catalog.
4. Check several item IDs and photos, create a test outfit, then export a cloud ZIP and verify its contents.

The R2 bucket remains private; photo reads go through the Access-protected Worker. ZIP imports preserve existing notes and photos when IDs conflict unless you confirm an update.

## Local Worker development

```powershell
pnpm --dir frontend build
uv run pywrangler dev
```

Wrangler uses local development bindings by default. Avoid adding `--remote` bindings to development commands unless you explicitly intend to access production data.

## Current limits

This Worker adapter is intentionally separate from the local SQLAlchemy/SQLite API. The Cloudflare runtime uses D1 and R2 bindings. A future ChatGPT/MCP connection needs its own authentication path; do not expose a bearer token through the browser frontend.
