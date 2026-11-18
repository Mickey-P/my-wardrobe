# My Wardrobe

A local-first personal wardrobe catalog. The project keeps application code separate from personal data: clothing tables, photos, the image manifest, and the SQLite database stay local and must not be committed to the public Git repository.

## Project status

- Local application features and original-photo downloader are implemented; see the [feature roadmap](docs/plan/README.md) for acceptance status, gaps, and next steps.
- A Cloudflare Worker/D1/R2 adapter and deployment guide are present. Cloud deployment and Access protection have not yet been verified; do not import personal data until the security gate is confirmed.

## Run the backend locally

Requirements: Python 3.12 or newer, Node.js, and pnpm.

Initial setup:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
pnpm install
cd ..
```

Start and stop the app:

```powershell
.\start.ps1
.\stop.ps1
```

Open `http://127.0.0.1:8000/docs` for the REST/OpenAPI documentation. The database is created at `data/wardrobe.db`.

The catalog is read from `data/catalog.csv`; visual descriptions are read from `data/visual_descriptions.csv`. Re-imports update records by their permanent IDs and preserve user notes separately. The app creates a database backup before updating an existing SQLite database.

## Data and privacy

The public GitHub repository contains application code and safe example configuration only. Personal CSV files, the source HTML catalog, local photos, the image manifest, SQLite database, and secrets are excluded by `.gitignore`. After cloning, obtain your private tables and images separately and place them in `data/`.

The API does not require a token for local use. For a hosted deployment, set `WARDROBE_REQUIRE_AUTH=true` and store a long random `WARDROBE_API_TOKEN` in your provider's secret settings. Never put the token in the frontend, public source code, or GitHub Actions logs.

## Photo downloader

```powershell
python backend\scripts\download_images.py --limit 5
python backend\scripts\download_images.py
```

On subsequent runs, valid existing files are checked and skipped. Use `--force` to download them again or `--limit N` to limit a test run.

## Tests

```powershell
$env:PYTHONPATH = "backend"
py -m unittest discover -s backend/tests -v
```

## Cloudflare deployment

Cloudflare support uses a separate Python Worker adapter with D1 and a private R2 bucket. The local FastAPI/SQLite mode remains available. See [the Cloudflare deployment guide](docs/cloudflare_deployment.md) for setup, Access protection, database migration, deployment, and private ZIP import.
