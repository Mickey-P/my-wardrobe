# My Wardrobe

A local-first personal wardrobe catalog. The project keeps application code separate from personal data: clothing tables, photos, the image manifest, and the SQLite database stay local and must not be committed to the public Git repository.

## Project status

- Stage 1: original-photo downloader, image manifest, and 139 local images.
- Stages 2–4: SQLite storage, catalog imports, REST API, visual catalog interface, manual outfit builder, photo manager, ZIP/CSV/JSON exports, and ZIP import.
- Public frontend/API hosting and moving photos/database to the cloud are not configured yet.

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
