from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import Outfit, WardrobeItem
from .photo_service import image_entries, resolve_image


def catalog_rows(db: Session) -> list[dict]:
    items = db.scalars(select(WardrobeItem).options(joinedload(WardrobeItem.visual_description)).order_by(WardrobeItem.id)).all()
    rows = []
    for item in items:
        row = dict(item.catalog_fields)
        row["id"] = item.id
        if item.user_notes:
            row["user_notes"] = item.user_notes
        rows.append(row)
    return rows


def visual_rows(db: Session) -> list[dict]:
    items = db.scalars(select(WardrobeItem).options(joinedload(WardrobeItem.visual_description)).order_by(WardrobeItem.id)).all()
    return [{"id": item.id, **(item.visual_description.source_fields if item.visual_description else {})} for item in items]


def to_csv(rows: list[dict]) -> bytes:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    if not columns:
        columns = ["id"]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def to_json(db: Session) -> bytes:
    items = db.scalars(select(WardrobeItem).options(joinedload(WardrobeItem.visual_description)).order_by(WardrobeItem.id)).all()
    data = [{
        "id": item.id,
        "catalog_fields": item.catalog_fields,
        "user_notes": item.user_notes,
        "visual_description": item.visual_description.source_fields if item.visual_description else None,
    } for item in items]
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def make_zip(db: Session) -> tuple[bytes, str]:
    items = db.scalars(select(WardrobeItem).options(joinedload(WardrobeItem.visual_description)).order_by(WardrobeItem.id)).all()
    outfits = db.scalars(select(Outfit).order_by(Outfit.id)).all()
    visual = visual_rows(db)
    manifest_source = image_entries()
    exported_manifest = []
    photos: list[tuple[Path, str]] = []
    for item in items:
        source = manifest_source.get(item.id, {})
        try:
            path, mime, _entry = resolve_image(item.id)
            zip_path = f"images/{path.name}"
            photos.append((path, zip_path))
            exported_manifest.append({
                "id": item.id, "source_url": source.get("source_url") or item.catalog_fields.get("image_url", ""),
                "local_path": zip_path, "status": "exported", "source_status": source.get("status"),
                "source_type": source.get("source_type", "catalog_original"), "mime_type": mime,
                "size_bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "exported": True, "error": None,
            })
        except (OSError, ValueError, FileNotFoundError) as exc:
            exported_manifest.append({
                "id": item.id, "source_url": source.get("source_url") or item.catalog_fields.get("image_url", ""),
                "local_path": None, "status": "not_exported", "source_status": source.get("status"),
                "mime_type": source.get("mime_type"), "size_bytes": None, "sha256": None,
                "exported": False, "error": str(exc) or "Local image is missing or invalid",
            })

    catalog = catalog_rows(db)
    outfit_data = [{"id": outfit.id, "name": outfit.name, "description": outfit.description,
                    "season": outfit.season, "occasion": outfit.occasion,
                    "item_ids": outfit.item_ids, "created_at": outfit.created_at.isoformat(),
                    "updated_at": outfit.updated_at.isoformat()} for outfit in outfits]
    manifest = {"generated_at": datetime.now(timezone.utc).isoformat(),
                "items": exported_manifest}
    readme = (
        "My Wardrobe export\n"
        f"Generated: {date.today().isoformat()}\n"
        f"Items: {len(catalog)}\n"
        f"Photos exported: {sum(x['exported'] for x in exported_manifest)}\n"
        f"Photos missing: {sum(not x['exported'] for x in exported_manifest)}\n\n"
        "Files: catalog.csv, catalog.json, visual_descriptions.csv, image_manifest.json, "
        "images/, outfits.json.\n"
        "The image manifest includes every item and marks any unavailable image as not_exported.\n"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("catalog.csv", to_csv(catalog))
        archive.writestr("catalog.json", to_json(db))
        archive.writestr("visual_descriptions.csv", to_csv(visual))
        archive.writestr("image_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        archive.writestr("outfits.json", json.dumps(outfit_data, ensure_ascii=False, indent=2) + "\n")
        for path, archive_path in photos:
            archive.write(path, archive_path)
        archive.writestr("README.txt", readme)
    return buffer.getvalue(), f"wardrobe_export_{date.today().isoformat()}.zip"
