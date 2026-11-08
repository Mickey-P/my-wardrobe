from __future__ import annotations

import csv
import hashlib
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import ROOT
from ..models import Outfit, WardrobeItem
from .import_service import ID_RE, import_catalog
from .photo_service import IMAGE_ROOT, MANIFEST, image_entries, resolve_image

MAX_ARCHIVE_BYTES = 300 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024
MAX_FILES = 600
MAX_IMAGE_BYTES = 40 * 1024 * 1024
IMAGE_MIME = {"JPEG": (".jpg", "image/jpeg"), "PNG": (".png", "image/png"),
              "WEBP": (".webp", "image/webp"), "GIF": (".gif", "image/gif"),
              "BMP": (".bmp", "image/bmp"), "TIFF": (".tiff", "image/tiff"), "AVIF": (".avif", "image/avif")}


class ArchiveConflict(Exception):
    def __init__(self, item_ids: list[str], outfit_ids: list[int]):
        self.item_ids = item_ids
        self.outfit_ids = outfit_ids
        super().__init__("Archive IDs conflict with existing database records")


def _safe_name(name: str) -> PurePosixPath:
    if "\\" in name or name.startswith("/") or ":" in name:
        raise ValueError(f"Unsafe ZIP path: {name}")
    path = PurePosixPath(name)
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"Unsafe ZIP path: {name}")
    return path


def _read_table(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "id" not in reader.fieldnames:
            raise ValueError(f"{path.name} must include an id column")
        rows = [{key: (value or "").strip() for key, value in row.items() if key} for row in reader]
    seen: set[str] = set()
    for line, row in enumerate(rows, start=2):
        item_id = row.get("id", "")
        if not ID_RE.fullmatch(item_id) or not 1 <= int(item_id[1:]) <= 139:
            raise ValueError(f"{path.name}:{line}: invalid wardrobe ID {item_id!r}")
        if item_id in seen:
            raise ValueError(f"{path.name}:{line}: duplicate ID {item_id}")
        seen.add(item_id)
    return rows


def _inspect_image(path: Path, item_id: str) -> tuple[str, str, str]:
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError(f"{item_id}: image exceeds 40 MiB")
    try:
        with Image.open(path) as image:
            image.verify()
            image_format = (image.format or "").upper()
        with Image.open(path) as image:
            image.load()
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"{item_id}: invalid image: {exc}") from exc
    if image_format not in IMAGE_MIME:
        raise ValueError(f"{item_id}: unsupported image format {image_format}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return image_format, IMAGE_MIME[image_format][1], digest


def import_archive(db: Session, file_bytes: bytes, *, overwrite_conflicts: bool = False) -> dict:
    if len(file_bytes) > MAX_ARCHIVE_BYTES:
        raise ValueError("ZIP archive exceeds 300 MiB")
    staging_root = ROOT / "data" / "imports" / "staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=staging_root) as temporary:
        extracted = Path(temporary)
        try:
            with zipfile.ZipFile(__import__("io").BytesIO(file_bytes)) as archive:
                infos = archive.infolist()
                if len(infos) > MAX_FILES:
                    raise ValueError("ZIP contains too many files")
                if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("Uncompressed ZIP data exceeds 500 MiB")
                if archive.testzip() is not None:
                    raise ValueError("ZIP CRC check failed")
                allowed_roots = {"catalog.csv", "visual_descriptions.csv", "catalog.json", "image_manifest.json", "outfits.json", "README.txt"}
                seen_paths: set[str] = set()
                for info in infos:
                    path = _safe_name(info.filename)
                    normalized = str(path).casefold()
                    if normalized in seen_paths:
                        raise ValueError(f"Duplicate ZIP entry: {info.filename}")
                    seen_paths.add(normalized)
                    mode = info.external_attr >> 16
                    if stat.S_ISLNK(mode):
                        raise ValueError(f"ZIP symlink is not allowed: {info.filename}")
                    if path.parts[0] not in allowed_roots and path.parts[0] != "images":
                        raise ValueError(f"Unexpected ZIP entry: {info.filename}")
                    if info.is_dir():
                        continue
                    if path.parts[0] == "images" and (len(path.parts) != 2 or path.name in {"", ".", ".."}):
                        raise ValueError(f"Invalid image path in ZIP: {info.filename}")
                    destination = extracted.joinpath(*path.parts).resolve()
                    if extracted.resolve() not in destination.parents:
                        raise ValueError(f"ZIP path escapes staging directory: {info.filename}")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as source, destination.open("wb") as target:
                        shutil.copyfileobj(source, target)
        except zipfile.BadZipFile as exc:
            raise ValueError("File is not a valid ZIP archive") from exc

        catalog_path = extracted / "catalog.csv"
        visual_path = extracted / "visual_descriptions.csv"
        manifest_path = extracted / "image_manifest.json"
        outfits_path = extracted / "outfits.json"
        for required in (catalog_path, visual_path, manifest_path, outfits_path):
            if not required.is_file():
                raise ValueError(f"ZIP is missing {required.name}")
        catalog_rows = _read_table(catalog_path)
        visual_rows = _read_table(visual_path)
        catalog_ids = {row["id"] for row in catalog_rows}
        visual_ids = {row["id"] for row in visual_rows}
        if not visual_ids.issubset(catalog_ids):
            raise ValueError("visual_descriptions.csv contains IDs missing from catalog.csv")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_items = manifest.get("items")
        if not isinstance(manifest_items, list):
            raise ValueError("image_manifest.json must contain an items list")
        manifest_by_id: dict[str, dict] = {}
        for row in manifest_items:
            item_id = row.get("id")
            if item_id not in catalog_ids or item_id in manifest_by_id:
                raise ValueError(f"Invalid or duplicate image manifest ID: {item_id!r}")
            manifest_by_id[item_id] = row
            if row.get("exported"):
                image_name = row.get("local_path")
                safe_image = _safe_name(image_name or "")
                if len(safe_image.parts) != 2 or safe_image.parts[0] != "images" or not safe_image.name.startswith(item_id + "."):
                    raise ValueError(f"Invalid image path for {item_id}")
                image_path = extracted.joinpath(*safe_image.parts)
                if not image_path.is_file():
                    raise ValueError(f"Archive is missing the exported image for {item_id}")
                _format, mime, digest = _inspect_image(image_path, item_id)
                if row.get("mime_type") and row["mime_type"] != mime:
                    raise ValueError(f"{item_id}: manifest MIME does not match image data")
                if row.get("sha256") and row["sha256"] != digest:
                    raise ValueError(f"{item_id}: image SHA-256 mismatch")
        if manifest_by_id.keys() != catalog_ids:
            missing = sorted(catalog_ids - manifest_by_id.keys())
            raise ValueError(f"Manifest is missing wardrobe IDs: {', '.join(missing)}")

        outfit_data = json.loads(outfits_path.read_text(encoding="utf-8"))
        if not isinstance(outfit_data, list):
            raise ValueError("outfits.json must contain a list")
        seen_outfits: set[int] = set()
        for outfit in outfit_data:
            source_id = outfit.get("id")
            if not isinstance(source_id, int) or source_id < 1 or source_id in seen_outfits:
                raise ValueError("Outfit IDs must be unique positive integers")
            seen_outfits.add(source_id)
            refs = outfit.get("item_ids", [])
            if not isinstance(refs, list) or any(item_id not in catalog_ids for item_id in refs):
                raise ValueError(f"Outfit {source_id} references an unknown wardrobe ID")

        existing_item_ids = set(db.scalars(select(WardrobeItem.id).where(WardrobeItem.id.in_(catalog_ids))).all()) if catalog_ids else set()
        outfit_source_ids = {row["id"] for row in outfit_data}
        existing_outfit_ids = set(db.scalars(select(Outfit.id).where(Outfit.id.in_(outfit_source_ids))).all()) if outfit_source_ids else set()
        if (existing_item_ids or existing_outfit_ids) and not overwrite_conflicts:
            raise ArchiveConflict(sorted(existing_item_ids), sorted(existing_outfit_ids))

        import_report = import_catalog(db, catalog_path, visual_path)
        current_entries = image_entries()
        imported_photos = 0
        preserved_photos = 0
        for item_id, row in manifest_by_id.items():
            if not row.get("exported"):
                if item_id not in current_entries:
                    current_entries[item_id] = {
                        "id": item_id,
                        "source_url": row.get("source_url", ""),
                        "local_path": None,
                        "status": row.get("source_status") or ("missing_url" if not row.get("source_url") else "download_error"),
                        "mime_type": row.get("mime_type"),
                        "size_bytes": None,
                        "sha256": None,
                        "error": row.get("error") or "Photo was not available in the imported archive",
                    }
                continue
            try:
                resolve_image(item_id)
                preserved_photos += 1
                continue
            except (ValueError, FileNotFoundError, OSError):
                pass
            safe_image = _safe_name(row["local_path"])
            source_path = extracted.joinpath(*safe_image.parts)
            image_format, mime, digest = _inspect_image(source_path, item_id)
            IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
            target = IMAGE_ROOT / f"{item_id}{IMAGE_MIME[image_format][0]}"
            target.write_bytes(source_path.read_bytes())
            current_entries[item_id] = {
                "id": item_id,
                "source_url": row.get("source_url", ""),
                "local_path": target.relative_to(ROOT).as_posix(),
                "status": "downloaded" if row.get("source_type") == "catalog_original" else "manual_upload",
                "source_type": row.get("source_type", "catalog_original"),
                "mime_type": mime,
                "size_bytes": target.stat().st_size,
                "sha256": digest,
                "error": None,
            }
            imported_photos += 1
        current_manifest = {"generated_at": manifest.get("generated_at"), "items": sorted(current_entries.values(), key=lambda row: row["id"])}
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(current_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        outfits_added = outfits_updated = 0
        for source in outfit_data:
            outfit = db.get(Outfit, source["id"])
            values = {key: source.get(key, "") for key in ("name", "description", "season", "occasion", "item_ids")}
            if outfit is None:
                outfit = Outfit(id=source["id"], **values)
                db.add(outfit)
                outfits_added += 1
            else:
                for key, value in values.items():
                    setattr(outfit, key, value)
                outfits_updated += 1
        db.commit()
        return {
            **import_report,
            "photos_imported": imported_photos,
            "photos_preserved_existing": preserved_photos,
            "outfits_added": outfits_added,
            "outfits_updated": outfits_updated,
            "conflicting_item_ids_overwritten": sorted(existing_item_ids),
            "conflicting_outfit_ids_overwritten": sorted(existing_outfit_ids),
        }
