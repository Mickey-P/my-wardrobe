from __future__ import annotations

import csv
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import ROOT
from ..models import VisualDescription, WardrobeItem

ID_RE = re.compile(r"^W\d{3}$")
DEFAULT_CATALOG = ROOT / "data" / "catalog.csv"
DEFAULT_VISUAL = ROOT / "data" / "visual_descriptions.csv"


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "id" not in reader.fieldnames:
            raise ValueError(f"{path} must contain an id column")
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({key: (value or "").strip() for key, value in row.items() if key is not None})
        return list(reader.fieldnames), rows


def _backup_database(db: Session) -> None:
    bind = db.get_bind()
    if bind.dialect.name != "sqlite" or not bind.url.database:
        return
    db_path = Path(bind.url.database)
    if db_path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_dir = ROOT / "data" / "imports" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"wardrobe-{stamp}.db"
        with sqlite3.connect(db_path) as source, sqlite3.connect(backup_path) as destination:
            source.backup(destination)


def _import_table(db: Session, path: Path, *, visual: bool) -> tuple[int, int, int, list[str]]:
    _, rows = _read_csv(path)
    seen: set[str] = set()
    added = updated = skipped = 0
    errors: list[str] = []
    model = VisualDescription if visual else WardrobeItem
    key_field = "item_id" if visual else "id"

    for line, row in enumerate(rows, start=2):
        item_id = row.get("id", "")
        if not ID_RE.fullmatch(item_id):
            skipped += 1
            errors.append(f"{path.name}:{line}: invalid ID {item_id!r}")
            continue
        if item_id in seen:
            skipped += 1
            errors.append(f"{path.name}:{line}: duplicate ID {item_id}")
            continue
        seen.add(item_id)
        if visual:
            parent = db.get(WardrobeItem, item_id)
            if parent is None:
                skipped += 1
                errors.append(f"{path.name}:{line}: no catalog item for {item_id}")
                continue
            instance = db.get(model, item_id)
            fields = {key: value for key, value in row.items() if key != "id"}
            if instance is None:
                instance = VisualDescription(item_id=item_id, source_fields=fields)
                db.add(instance)
                added += 1
            else:
                instance.source_fields = fields
                updated += 1
        else:
            instance = db.get(model, item_id)
            if instance is None:
                catalog_fields = {key: value for key, value in row.items() if key != "user_notes"}
                instance = WardrobeItem(id=item_id, catalog_fields=catalog_fields, user_notes=row.get("user_notes", ""))
                db.add(instance)
                added += 1
            else:
                instance.catalog_fields = {key: value for key, value in row.items() if key != "user_notes"}
                # user_notes are app-owned and intentionally retained on any update.
                updated += 1
    return added, updated, skipped, errors


def import_catalog(db: Session, catalog_path: Path = DEFAULT_CATALOG,
                   visual_path: Path = DEFAULT_VISUAL) -> dict:
    """Idempotently import the two source tables, keeping their schemas separate."""
    # Parse before making a backup or changing the database, so malformed input is non-destructive.
    _read_csv(catalog_path)
    _read_csv(visual_path)
    _backup_database(db)
    ca, cu, cs, ce = _import_table(db, catalog_path, visual=False)
    db.flush()  # make newly imported items visible to the visual-description import
    va, vu, vs, ve = _import_table(db, visual_path, visual=True)
    db.commit()
    return {
        "catalog_added": ca, "catalog_updated": cu, "catalog_skipped": cs,
        "visual_added": va, "visual_updated": vu, "visual_skipped": vs,
        "errors": ce + ve,
    }


def validate_item_ids(db: Session, item_ids: list[str]) -> None:
    if not item_ids:
        return
    found = set(db.scalars(select(WardrobeItem.id).where(WardrobeItem.id.in_(item_ids))).all())
    missing = [item_id for item_id in item_ids if item_id not in found]
    if missing:
        raise ValueError(f"Unknown wardrobe IDs: {', '.join(missing)}")
