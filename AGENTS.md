# AGENTS.md

## Project overview

My Wardrobe is a local-first wardrobe catalog with a FastAPI/SQLite backend, a React/TypeScript/Vite frontend, and a separate Cloudflare Worker adapter. The feature roadmap in `docs/plan/README.md` is the source of truth for scope, status, and acceptance evidence.

## Repository map

- `backend/app/`: local API, SQLAlchemy models, and catalog, photo, archive, and export services.
- `backend/cloudflare/`: separate Worker adapter and D1 migrations.
- `backend/scripts/`: catalog import and photo download utilities.
- `backend/tests/`: backend and Worker tests.
- `frontend/src/`: React UI and API client.
- `docs/`: deployment instructions and feature plans.

## Setup and checks

Follow `README.md` for environment setup. From the repository root, run the backend tests in PowerShell:

```powershell
$env:PYTHONPATH = "backend"
py -m unittest discover -s backend/tests -v
```

Build and type-check the frontend with:

```powershell
pnpm --dir frontend build
```

Run the relevant checks for the code you change. If a check fails, distinguish pre-existing failures from regressions and report them.

## Implementation guidance

- Read the existing implementation and relevant feature plan before changing behavior. Keep the local SQLite API and Cloudflare Worker adapter separate; do not assume one adapter's behavior or tests prove the other.
- Follow established patterns in nearby code: typed Python services and SQLAlchemy models, and React function components with TypeScript in the frontend.
- Keep API and data-schema changes consistent across their callers, tests, and applicable feature plans. Add focused tests for behavior changes.
- Keep changes scoped. Do not mark roadmap work complete without running and recording its acceptance checks.

## Data safety and deployment

- Treat wardrobe tables, photos, exports, local databases, and secrets as private user data. Do not inspect, print, copy, upload, or include their contents in commits, logs, prompts, or test output unless the task specifically requires it.
- Keep personal data and credentials out of Git. Preserve `.gitignore` protections; use safe fixtures or temporary test data rather than the local wardrobe database.
- Do not deploy, use remote Cloudflare bindings, or import personal data into a hosted environment unless explicitly requested. Cloudflare deployment and Access protection are not yet verified; never import personal data before confirming Access protects the Worker.
- Never put an API token in frontend code or public configuration. Do not make the R2 bucket public.
