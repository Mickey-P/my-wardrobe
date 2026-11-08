#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401
from app.services.import_service import DEFAULT_CATALOG, DEFAULT_VISUAL, import_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Import catalog and visual descriptions into SQLite")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--visual", type=Path, default=DEFAULT_VISUAL)
    args = parser.parse_args()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        report = import_catalog(db, args.catalog, args.visual)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
