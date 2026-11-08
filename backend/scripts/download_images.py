#!/usr/bin/env python3
"""Download original wardrobe photos and write a per-item image manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from PIL import Image, UnidentifiedImageError
except ImportError as exc:
    raise SystemExit("Pillow is required. Install backend/requirements.txt first.") from exc


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "data" / "catalog.csv"
IMAGE_DIR = ROOT / "data" / "images"
MANIFEST_PATH = ROOT / "data" / "image_manifest.json"
ID_PATTERN = re.compile(r"^W\d{3}$")
EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "GIF": ".gif",
    "BMP": ".bmp",
    "TIFF": ".tiff",
    "AVIF": ".avif",
}
MIME_BY_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "BMP": "image/bmp",
    "TIFF": "image/tiff",
    "AVIF": "image/avif",
}
MAX_BYTES = 40 * 1024 * 1024
TIMEOUT_SECONDS = 20
RETRIES = 3
RETRY_DELAY_SECONDS = 1.5
REQUEST_DELAY_SECONDS = 0.5


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_image(path: Path) -> tuple[str, str]:
    """Fully decode an image and return actual format and normalized MIME."""
    with Image.open(path) as image:
        image.verify()
        actual_format = (image.format or "").upper()
    if actual_format not in EXTENSIONS:
        raise ValueError(f"Unsupported image format: {actual_format or 'unknown'}")
    # verify() checks structure; reopen and load pixels to catch truncated data.
    with Image.open(path) as image:
        image.load()
    return actual_format, MIME_BY_FORMAT[actual_format]


def record(item_id: str, url: str, status: str, **values: Any) -> dict[str, Any]:
    return {
        "id": item_id,
        "source_url": url,
        "local_path": values.pop("local_path", None),
        "status": status,
        "mime_type": values.pop("mime_type", None),
        "size_bytes": values.pop("size_bytes", None),
        "sha256": values.pop("sha256", None),
        "error": values.pop("error", None),
        **values,
    }


def validate_existing(path: Path) -> tuple[str, str, int, str] | None:
    if not path.is_file():
        return None
    try:
        actual_format, mime = inspect_image(path)
        return actual_format, mime, path.stat().st_size, sha256_file(path)
    except (OSError, ValueError, UnidentifiedImageError):
        return None


def fetch(url: str, target: Path) -> tuple[str, str, int, str]:
    last_error = "unknown download error"
    for attempt in range(1, RETRIES + 1):
        temp_path: Path | None = None
        try:
            request = Request(url, headers={"User-Agent": "MyWardrobe-local/1.0"})
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                status = getattr(response, "status", 200)
                if status < 200 or status >= 300:
                    raise HTTPError(url, status, "Non-success HTTP status", response.headers, None)
                content_type = response.headers.get_content_type().lower()
                if not content_type.startswith("image/"):
                    raise ValueError(f"Expected image MIME type, received {content_type}")
                target.parent.mkdir(parents=True, exist_ok=True)
                temp_path = target.with_name(target.name + ".part")
                size = 0
                with temp_path.open("wb") as out:
                    while True:
                        chunk = response.read(64 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise ValueError(f"Image exceeds {MAX_BYTES} byte limit")
                        out.write(chunk)
            actual_format, actual_mime = inspect_image(temp_path)
            if content_type not in (actual_mime, "image/jpg"):
                raise ValueError(
                    f"MIME mismatch: response says {content_type}, file is {actual_mime}"
                )
            final_path = target.with_suffix(EXTENSIONS[actual_format])
            if final_path != target:
                temp_path.replace(final_path)
            else:
                temp_path.replace(target)
            return actual_format, actual_mime, size, sha256_file(final_path)
        except HTTPError:
            if temp_path and temp_path.exists():
                temp_path.unlink()
            raise
        except (URLError, TimeoutError, OSError, ValueError, UnidentifiedImageError) as exc:
            last_error = str(exc)
            if temp_path and temp_path.exists():
                temp_path.unlink()
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
    raise RuntimeError(last_error)


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {"id", "image_url"}.issubset(reader.fieldnames):
            raise ValueError("CSV must include id and image_url columns")
        return list(reader)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Source catalog CSV")
    parser.add_argument("--images-dir", type=Path, default=IMAGE_DIR, help="Image output directory")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH, help="Manifest output JSON")
    parser.add_argument("--limit", type=int, help="Process at most this many CSV rows")
    parser.add_argument("--force", action="store_true", help="Re-download valid existing files")
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY_SECONDS, help="Delay between requests")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be zero or greater")
    if args.delay < 0:
        parser.error("--delay must be zero or greater")

    rows = load_rows(args.csv)
    if args.limit is not None:
        rows = rows[: args.limit]
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    http_errors = invalid_images = downloaded = existed = 0
    missing_ids: list[str] = []

    for index, row in enumerate(rows):
        item_id = (row.get("id") or "").strip()
        url = (row.get("image_url") or "").strip()
        if not ID_PATTERN.fullmatch(item_id) or not 1 <= int(item_id[1:]) <= 139:
            results.append(record(item_id, url, "download_error", error="Invalid or missing ID"))
            logging.error("Invalid ID in CSV row %d: %r", index + 2, item_id)
            continue
        if item_id in seen:
            results.append(record(item_id, url, "download_error", error="Duplicate ID in CSV"))
            logging.error("Duplicate ID %s; skipped", item_id)
            continue
        seen.add(item_id)
        if not url:
            results.append(record(item_id, url, "missing_url", error="No image_url in catalog"))
            missing_ids.append(item_id)
            continue

        existing = None
        if not args.force:
            for candidate in args.images_dir.glob(item_id + ".*"):
                if candidate.name.endswith(".part"):
                    continue
                existing = validate_existing(candidate)
                if existing:
                    _, mime, size, digest = existing
                    results.append(record(item_id, url, "already_exists", local_path=candidate.relative_to(ROOT).as_posix(),
                                          mime_type=mime, size_bytes=size, sha256=digest))
                    existed += 1
                    break
        if existing:
            continue

        target = args.images_dir / (item_id + ".jpg")
        try:
            image_format, mime, size, digest = fetch(url, target)
            final_path = target.with_suffix(EXTENSIONS[image_format])
            results.append(record(item_id, url, "downloaded", local_path=final_path.relative_to(ROOT).as_posix(),
                                  mime_type=mime, size_bytes=size, sha256=digest))
            downloaded += 1
        except HTTPError as exc:
            results.append(record(item_id, url, "http_error", error=f"HTTP {exc.code}: {exc.reason}"))
            missing_ids.append(item_id)
            http_errors += 1
            logging.error("%s: HTTP %s %s", item_id, exc.code, exc.reason)
        except (ValueError, UnidentifiedImageError) as exc:
            results.append(record(item_id, url, "invalid_image", error=str(exc)))
            missing_ids.append(item_id)
            invalid_images += 1
            logging.error("%s: invalid image: %s", item_id, exc)
        except (RuntimeError, URLError, TimeoutError, OSError) as exc:
            results.append(record(item_id, url, "download_error", error=str(exc)))
            missing_ids.append(item_id)
            logging.error("%s: download failed: %s", item_id, exc)
        if index < len(rows) - 1:
            time.sleep(args.delay)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_csv": str(args.csv),
        "items": results,
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nDownload report")
    print(f"Total items: {len(rows)}")
    print(f"Downloaded: {downloaded}")
    print(f"Already existed: {existed}")
    print(f"Missing URL: {sum(item['status'] == 'missing_url' for item in results)}")
    print(f"Download/HTTP errors: {sum(item['status'] in ('download_error', 'http_error') for item in results)}")
    print(f"Invalid images: {invalid_images}")
    print(f"Missing photos: {', '.join(missing_ids) if missing_ids else 'none'}")
    print(f"Manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
