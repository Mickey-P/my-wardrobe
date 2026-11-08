from __future__ import annotations

import json
import hashlib
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ..database import ROOT

ID_RE = re.compile(r"^W\d{3}$")
IMAGE_ROOT = (ROOT / "data" / "images").resolve()
MANIFEST = ROOT / "data" / "image_manifest.json"
IMAGE_MIME = {"JPEG": (".jpg", "image/jpeg"), "PNG": (".png", "image/png"),
              "WEBP": (".webp", "image/webp"), "GIF": (".gif", "image/gif"),
              "BMP": (".bmp", "image/bmp"), "TIFF": (".tiff", "image/tiff"), "AVIF": (".avif", "image/avif")}


class PhotoConflict(Exception):
    pass


class InvalidPhoto(Exception):
    pass


def image_entries() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {entry.get("id"): entry for entry in payload.get("items", []) if entry.get("id")}


def resolve_image(item_id: str) -> tuple[Path, str, dict]:
    if not ID_RE.fullmatch(item_id):
        raise ValueError("Invalid wardrobe ID")
    entry = image_entries().get(item_id)
    if not entry or entry.get("status") not in {"downloaded", "already_exists", "manual_upload"}:
        raise FileNotFoundError(item_id)
    relative = entry.get("local_path")
    if not relative:
        raise FileNotFoundError(item_id)
    path = (ROOT / relative).resolve()
    if IMAGE_ROOT not in path.parents or not path.is_file():
        raise FileNotFoundError(item_id)
    return path, entry.get("mime_type") or "application/octet-stream", entry


def store_photo(item_id: str, data: bytes, content_type: str | None, *, replace: bool = False) -> dict:
    if not ID_RE.fullmatch(item_id) or not 1 <= int(item_id[1:]) <= 139:
        raise ValueError("Invalid wardrobe ID")
    current_path = None
    try:
        current_path, _mime, _entry = resolve_image(item_id)
    except (ValueError, FileNotFoundError, OSError):
        pass
    if current_path and not replace:
        raise PhotoConflict(item_id)
    if len(data) > 40 * 1024 * 1024:
        raise InvalidPhoto("Image exceeds 40 MiB limit")
    try:
        import io
        from PIL import Image

        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            image_format = (image.format or "").upper()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
    except Exception as exc:
        raise InvalidPhoto(f"Invalid image: {exc}") from exc
    if image_format not in IMAGE_MIME:
        raise InvalidPhoto(f"Unsupported image format: {image_format}")
    extension, mime = IMAGE_MIME[image_format]
    if content_type and content_type.lower() not in {mime, "image/jpg" if mime == "image/jpeg" else mime}:
        raise InvalidPhoto(f"Uploaded MIME type {content_type} does not match {mime}")
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    target = IMAGE_ROOT / f"{item_id}{extension}"
    if current_path:
        backup_dir = IMAGE_ROOT.parent / "imports" / "photo-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(current_path, backup_dir / f"{item_id}-{stamp}{current_path.suffix}")
    temp_path = target.with_name(target.name + ".part")
    temp_path.write_bytes(data)
    temp_path.replace(target)
    digest = hashlib.sha256(data).hexdigest()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"items": []}
    entries = {entry.get("id"): entry for entry in manifest.get("items", []) if entry.get("id")}
    old = entries.get(item_id, {})
    local_path = target.relative_to(IMAGE_ROOT.parent.parent).as_posix()
    entries[item_id] = {
        "id": item_id, "source_url": old.get("source_url", ""), "local_path": local_path,
        "status": "manual_upload", "source_type": "manual_upload", "mime_type": mime,
        "size_bytes": len(data), "sha256": digest, "error": None,
    }
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["items"] = sorted(entries.values(), key=lambda entry: entry["id"])
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"id": item_id, "status": "manual_upload", "local_path": local_path,
            "mime_type": mime, "size_bytes": len(data), "sha256": digest}
