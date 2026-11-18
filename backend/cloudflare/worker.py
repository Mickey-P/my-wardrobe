from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import stat
import zipfile
from datetime import date, datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import Response

try:
    from workers import asgi
except ImportError:  # Allows syntax checks and local unit tests outside Pyodide.
    asgi = None

app = FastAPI(title="My Wardrobe API", version="1.0.0")
ID_RE = re.compile(r"^W\d{3}$")
IMAGE_MIME = {
    "JPEG": (".jpg", "image/jpeg"), "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"), "GIF": (".gif", "image/gif"),
}
MAX_UPLOAD_BYTES = 40 * 1024 * 1024
MAX_ARCHIVE_BYTES = 90 * 1024 * 1024


def _env(request: Request, name: str) -> Any:
    env = request.scope.get("env")
    if env is None:
        raise RuntimeError("Cloudflare Worker bindings are unavailable")
    return getattr(env, name)


def _to_python(value: Any) -> Any:
    converter = getattr(value, "to_py", None)
    return converter() if callable(converter) else value


async def _query(request: Request, sql: str, *values: Any) -> list[dict[str, Any]]:
    statement = _env(request, "WARDROBE_DB").prepare(sql)
    if values:
        statement = statement.bind(*values)
    result = await statement.all()
    rows = _to_python(result.results)
    return [dict(_to_python(row)) for row in rows]


async def _run(request: Request, sql: str, *values: Any) -> Any:
    statement = _env(request, "WARDROBE_DB").prepare(sql)
    if values:
        statement = statement.bind(*values)
    return await statement.run()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _image_type(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif", "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    raise ValueError("Unsupported or invalid image format")


async def _item(request: Request, item_id: str) -> dict[str, Any] | None:
    rows = await _query(
        request,
        """SELECT w.id, w.catalog_fields, w.user_notes, v.source_fields,
                  m.source_url, m.object_key, m.status, m.source_type,
                  m.mime_type, m.size_bytes, m.sha256, m.error
           FROM wardrobe_items w
           LEFT JOIN visual_descriptions v ON v.item_id = w.id
           LEFT JOIN image_manifest m ON m.id = w.id
           WHERE w.id = ? LIMIT 1""",
        item_id,
    )
    return _item_out(rows[0]) if rows else None


def _item_out(row: dict[str, Any]) -> dict[str, Any]:
    fields = _json(row.get("catalog_fields"), {})
    visual_fields = _json(row.get("source_fields"), None)
    manifest = {
        "id": row["id"], "source_url": row.get("source_url") or fields.get("image_url", ""),
        "local_path": row.get("object_key"),
        "object_key": row.get("object_key"), "status": row.get("status") or "missing_url",
        "source_type": row.get("source_type") or "catalog_original", "mime_type": row.get("mime_type"),
        "size_bytes": row.get("size_bytes"), "sha256": row.get("sha256"), "error": row.get("error"),
    }
    return {
        "id": row["id"], "catalog_fields": fields, "user_notes": row.get("user_notes") or "",
        "visual_description": visual_fields, "local_image_path": manifest["local_path"],
        "image_status": manifest["status"],
    }


def _valid_id(item_id: str) -> bool:
    return bool(ID_RE.fullmatch(item_id) and 1 <= int(item_id[1:]) <= 139)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/items")
async def list_items(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    color: str | None = None,
    season: str | None = None,
    brand: str | None = None,
    formality: str | None = None,
    warmth: str | None = None,
    fit: str | None = None,
    item_status: str | None = None,
    has_photo: bool | None = None,
    sort: str = Query("id", pattern="^(id|category|color|brand)$"),
    limit: int = Query(139, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    rows = await _query(
        request,
        """SELECT w.id, w.catalog_fields, w.user_notes, v.source_fields,
                  m.source_url, m.object_key, m.status, m.source_type,
                  m.mime_type, m.size_bytes, m.sha256, m.error
           FROM wardrobe_items w
           LEFT JOIN visual_descriptions v ON v.item_id = w.id
           LEFT JOIN image_manifest m ON m.id = w.id""",
    )
    tests = {
        "category": category, "subcategory": subcategory, "season": season, "brand": brand,
        "formality": formality, "warmth": warmth, "fit": fit, "status": item_status,
    }
    results = []
    for row in rows:
        item = _item_out(row)
        fields = item["catalog_fields"]
        for key, value in tests.items():
            actual = str(fields.get(key) or "").casefold()
            if value and ((key == "category" and actual != value.casefold()) or
                          (key != "category" and value.casefold() not in actual)):
                break
        else:
            if color and color.casefold() not in f"{fields.get('primary_color', '')} {fields.get('secondary_colors', '')}".casefold():
                continue
            if has_photo is not None and (item["image_status"] in {"downloaded", "already_exists", "manual_upload"}) != has_photo:
                continue
            searchable = " ".join([item["id"], *map(str, fields.values()), item["user_notes"]])
            searchable += " " + " ".join(map(str, (item["visual_description"] or {}).values()))
            if q and q.casefold().strip() not in searchable.casefold():
                continue
            results.append(item)
    field = {"id": lambda x: x["id"], "category": lambda x: x["catalog_fields"].get("category", ""),
             "color": lambda x: x["catalog_fields"].get("primary_color", ""),
             "brand": lambda x: x["catalog_fields"].get("brand", "")}[sort]
    return sorted(results, key=lambda x: str(field(x)).casefold())[offset:offset + limit]


@app.get("/api/v1/items/{item_id}")
async def get_item(item_id: str, request: Request):
    item = await _item(request, item_id)
    if item is None:
        raise HTTPException(404, "Wardrobe item not found")
    return item


@app.put("/api/v1/items/{item_id}")
async def update_item(item_id: str, request: Request):
    if not _valid_id(item_id):
        raise HTTPException(400, "Invalid wardrobe ID")
    payload = await request.json()
    current = await _query(request, "SELECT catalog_fields, user_notes FROM wardrobe_items WHERE id = ?", item_id)
    if not current:
        raise HTTPException(404, "Wardrobe item not found")
    fields = payload.get("catalog_fields")
    if fields is not None:
        if fields.get("id", item_id) != item_id:
            raise HTTPException(422, "Item ID is immutable")
        fields = dict(fields)
        fields["id"] = item_id
    else:
        fields = _json(current[0].get("catalog_fields"), {})
    notes = payload.get("user_notes", current[0].get("user_notes") or "")
    await _run(request, "UPDATE wardrobe_items SET catalog_fields = ?, user_notes = ?, updated_at = ? WHERE id = ?",
               json.dumps(fields, ensure_ascii=False), notes, _now(), item_id)
    return await _item(request, item_id)


@app.get("/api/v1/items/{item_id}/visual-description")
async def get_visual_description(item_id: str, request: Request):
    rows = await _query(request, "SELECT source_fields FROM visual_descriptions WHERE item_id = ?", item_id)
    if not rows:
        raise HTTPException(404, "Visual description not found")
    return {"id": item_id, **_json(rows[0]["source_fields"], {})}


@app.get("/api/v1/items/{item_id}/photo")
async def get_photo(item_id: str, request: Request):
    if not _valid_id(item_id):
        raise HTTPException(400, "Invalid wardrobe ID")
    rows = await _query(request, "SELECT object_key, mime_type FROM image_manifest WHERE id = ?", item_id)
    if not rows or not rows[0].get("object_key"):
        raise HTTPException(404, "Photo not found")
    obj = await _env(request, "WARDROBE_IMAGES").get(rows[0]["object_key"])
    if obj is None:
        raise HTTPException(404, "Photo not found")
    body = _to_python(await obj.body.arrayBuffer())
    return Response(content=bytes(body), media_type=rows[0].get("mime_type") or "application/octet-stream",
                    headers={"Cache-Control": "private, no-store"})


@app.post("/api/v1/items/{item_id}/photo", status_code=201)
async def upload_photo(item_id: str, request: Request, file: UploadFile = File(...),
                       replace: bool = Query(False)):
    if not _valid_id(item_id):
        raise HTTPException(400, "Invalid wardrobe ID")
    if await _item(request, item_id) is None:
        raise HTTPException(404, "Wardrobe item not found")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image exceeds 40 MiB limit")
    try:
        extension, mime = _image_type(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if file.content_type and file.content_type not in {mime, "image/jpg" if mime == "image/jpeg" else mime}:
        raise HTTPException(422, f"Uploaded MIME type does not match {mime}")
    old = await _query(request, "SELECT object_key FROM image_manifest WHERE id = ?", item_id)
    if old and old[0].get("object_key") and not replace:
        raise HTTPException(409, "A photo already exists; confirm replacement with replace=true")
    key = f"images/{item_id}{extension}"
    digest = hashlib.sha256(data).hexdigest()
    await _env(request, "WARDROBE_IMAGES").put(key, data)
    await _run(request, """INSERT INTO image_manifest(id, source_url, object_key, status, source_type,
        mime_type, size_bytes, sha256, error) VALUES(?, '', ?, 'manual_upload', 'manual_upload', ?, ?, ?, NULL)
        ON CONFLICT(id) DO UPDATE SET object_key=excluded.object_key, status='manual_upload',
        source_type='manual_upload', mime_type=excluded.mime_type, size_bytes=excluded.size_bytes,
        sha256=excluded.sha256, error=NULL""", item_id, key, mime, len(data), digest)
    return {"id": item_id, "status": "manual_upload", "local_path": key,
            "mime_type": mime, "size_bytes": len(data), "sha256": digest}


@app.get("/api/v1/outfits")
async def list_outfits(request: Request):
    rows = await _query(request, "SELECT * FROM outfits ORDER BY updated_at DESC")
    return [{**row, "item_ids": _json(row.get("item_ids"), [])} for row in rows]


async def _save_outfit(request: Request, payload: dict[str, Any], outfit_id: int | None = None):
    name = str(payload.get("name") or "").strip()
    ids = payload.get("item_ids") or []
    if not name or len(name) > 200:
        raise HTTPException(422, "Outfit name is required and must be 200 characters or fewer")
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "item_ids must not contain duplicates")
    if ids:
        found = await _query(request, f"SELECT id FROM wardrobe_items WHERE id IN ({','.join('?' for _ in ids)})", *ids)
        if {row["id"] for row in found} != set(ids):
            raise HTTPException(422, "Outfit contains unknown wardrobe item IDs")
    now = _now()
    values = (name, str(payload.get("description") or ""), str(payload.get("season") or ""),
              str(payload.get("occasion") or ""), json.dumps(ids), now)
    if outfit_id is None:
        result = await _run(request, "INSERT INTO outfits(name, description, season, occasion, item_ids, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?)", *values, now)
        meta = _to_python(result.meta)
        return int(meta["last_row_id"])
    await _run(request, "UPDATE outfits SET name=?, description=?, season=?, occasion=?, item_ids=?, updated_at=? WHERE id=?", *values, outfit_id)


@app.post("/api/v1/outfits", status_code=201)
async def create_outfit(request: Request):
    payload = await request.json()
    outfit_id = await _save_outfit(request, payload)
    rows = await _query(request, "SELECT * FROM outfits WHERE id = ?", outfit_id)
    return {**rows[0], "item_ids": _json(rows[0].get("item_ids"), [])}


@app.put("/api/v1/outfits/{outfit_id}")
async def update_outfit(outfit_id: int, request: Request):
    payload = await request.json()
    await _save_outfit(request, payload, outfit_id)
    rows = await _query(request, "SELECT * FROM outfits WHERE id = ?", outfit_id)
    if not rows:
        raise HTTPException(404, "Outfit not found")
    return {**rows[0], "item_ids": _json(rows[0].get("item_ids"), [])}


@app.delete("/api/v1/outfits/{outfit_id}", status_code=204)
async def delete_outfit(outfit_id: int, request: Request):
    await _run(request, "DELETE FROM outfits WHERE id = ?", outfit_id)
    return Response(status_code=204)


@app.get("/api/v1/outfits/{outfit_id}")
async def get_outfit(outfit_id: int, request: Request):
    rows = await _query(request, "SELECT * FROM outfits WHERE id = ?", outfit_id)
    if not rows:
        raise HTTPException(404, "Outfit not found")
    return {**rows[0], "item_ids": _json(rows[0].get("item_ids"), [])}


@app.get("/api/v1/stats")
async def stats(request: Request):
    rows = await _query(request, "SELECT catalog_fields FROM wardrobe_items")
    counts: dict[str, dict[str, int]] = {"by_category": {}, "by_season": {}, "by_status": {}}
    for row in rows:
        fields = _json(row.get("catalog_fields"), {})
        for target, key in (("by_category", "category"), ("by_season", "season"), ("by_status", "status")):
            value = str(fields.get(key) or "Unspecified").strip() or "Unspecified"
            counts[target][value] = counts[target].get(value, 0) + 1
    photos = await _query(request, "SELECT COUNT(*) AS n FROM image_manifest WHERE status IN ('downloaded','already_exists','manual_upload')")
    with_photos = photos[0]["n"] if photos else 0
    return {"total_items": len(rows), **counts, "with_photos": with_photos,
            "without_photos": max(0, len(rows) - with_photos)}


@app.get("/api/v1/exports/catalog.csv")
async def export_csv(request: Request):
    rows = await _query(request, "SELECT id, catalog_fields, user_notes FROM wardrobe_items ORDER BY id")
    data = []
    for row in rows:
        item = _json(row["catalog_fields"], {})
        item["id"] = row["id"]
        if row.get("user_notes"):
            item["user_notes"] = row["user_notes"]
        data.append(item)
    columns = list(dict.fromkeys(key for row in data for key in row)) or ["id"]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(data)
    return Response(output.getvalue().encode("utf-8-sig"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=catalog.csv"})


@app.get("/api/v1/exports/catalog.json")
async def export_json(request: Request):
    rows = await _query(request, """SELECT w.id, w.catalog_fields, w.user_notes, v.source_fields
        FROM wardrobe_items w LEFT JOIN visual_descriptions v ON v.item_id=w.id ORDER BY w.id""")
    data = [{"id": row["id"], "catalog_fields": _json(row["catalog_fields"], {}),
             "user_notes": row.get("user_notes") or "",
             "visual_description": _json(row.get("source_fields"), None)} for row in rows]
    return Response(json.dumps(data, ensure_ascii=False, indent=2), media_type="application/json; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=catalog.json"})


@app.get("/api/v1/exports/zip")
async def export_zip(request: Request):
    items = await _query(request, """SELECT w.id, w.catalog_fields, w.user_notes, v.source_fields,
        m.source_url, m.object_key, m.status, m.source_type, m.mime_type, m.size_bytes, m.sha256
        FROM wardrobe_items w LEFT JOIN visual_descriptions v ON v.item_id=w.id
        LEFT JOIN image_manifest m ON m.id=w.id ORDER BY w.id""")
    outfits = await _query(request, "SELECT * FROM outfits ORDER BY id")
    catalog, visual, manifest, item_data = [], [], [], []
    images = _env(request, "WARDROBE_IMAGES")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for row in items:
            fields = _json(row["catalog_fields"], {})
            catalog.append({**fields, "id": row["id"], **({"user_notes": row["user_notes"]} if row.get("user_notes") else {})})
            vfields = _json(row.get("source_fields"), {})
            visual.append({"id": row["id"], **vfields})
            photo = {"id": row["id"], "source_url": row.get("source_url") or fields.get("image_url", ""),
                     "local_path": None, "status": "not_exported", "source_status": row.get("status"),
                     "source_type": row.get("source_type") or "catalog_original", "mime_type": row.get("mime_type"),
                     "size_bytes": None, "sha256": None, "exported": False, "error": "Photo is missing"}
            key = row.get("object_key")
            if key:
                obj = await images.get(key)
                if obj is not None:
                    data = _to_python(await obj.body.arrayBuffer())
                    data = bytes(data)
                    filename = key.split("/")[-1]
                    zip_path = f"images/{filename}"
                    archive.writestr(zip_path, data)
                    photo.update({"local_path": zip_path, "status": "exported", "size_bytes": len(data),
                                  "sha256": hashlib.sha256(data).hexdigest(), "exported": True, "error": None})
            manifest.append(photo)
            item_data.append({"id": row["id"], "catalog_fields": fields, "user_notes": row.get("user_notes") or "",
                              "visual_description": _json(row.get("source_fields"), None)})
        outfit_data = [{**row, "item_ids": _json(row.get("item_ids"), [])} for row in outfits]
        archive.writestr("catalog.csv", _csv_bytes(catalog))
        archive.writestr("catalog.json", json.dumps(item_data, ensure_ascii=False, indent=2))
        archive.writestr("visual_descriptions.csv", _csv_bytes(visual))
        archive.writestr("image_manifest.json", json.dumps({"generated_at": _now(), "items": manifest}, ensure_ascii=False, indent=2))
        archive.writestr("outfits.json", json.dumps(outfit_data, ensure_ascii=False, indent=2))
        archive.writestr("README.txt", f"My Wardrobe export\nGenerated: {date.today().isoformat()}\nItems: {len(catalog)}\n")
    return Response(output.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="wardrobe_export_{date.today().isoformat()}.zip"'})


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    columns = list(dict.fromkeys(key for row in rows for key in row)) or ["id"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


@app.post("/api/v1/imports/zip")
async def import_zip(request: Request, file: UploadFile = File(...),
                     overwrite_conflicts: bool = Query(False)):
    raw = await file.read(MAX_ARCHIVE_BYTES + 1)
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise HTTPException(413, "Archive exceeds 90 MiB limit")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        infos = archive.infolist()
        if len({info.filename for info in infos}) != len(infos):
            raise ValueError("Archive contains duplicate paths")
        names = [info.filename for info in infos]
        if sum(info.file_size for info in infos) > 100 * 1024 * 1024:
            raise ValueError("Archive expands beyond the 100 MiB safety limit")
        if archive.testzip() is not None:
            raise ValueError("ZIP checksum validation failed")
        for info in infos:
            name = info.filename
            path = name.replace("\\", "/")
            if path.startswith("/") or ".." in path.split("/") or "\x00" in path:
                raise ValueError("Unsafe path in archive")
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Symbolic links are not allowed in the archive")
            if info.file_size > MAX_UPLOAD_BYTES:
                raise ValueError("Archive member exceeds the 40 MiB safety limit")
        catalog = list(csv.DictReader(io.StringIO(archive.read("catalog.csv").decode("utf-8-sig"))))
        visual = list(csv.DictReader(io.StringIO(archive.read("visual_descriptions.csv").decode("utf-8-sig"))))
        outfits = json.loads(archive.read("outfits.json"))
        manifest = json.loads(archive.read("image_manifest.json"))
    except (KeyError, OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise HTTPException(400, f"Invalid wardrobe archive: {exc}") from exc
    for record in catalog:
        if not _valid_id(record.get("id", "")):
            raise HTTPException(400, "Archive contains an invalid wardrobe ID")
    catalog_ids = [record["id"] for record in catalog]
    if len(catalog_ids) != len(set(catalog_ids)):
        raise HTTPException(400, "Archive contains duplicate wardrobe IDs")
    visual_ids = [record.get("id", "") for record in visual]
    if any(not _valid_id(item_id) for item_id in visual_ids) or len(visual_ids) != len(set(visual_ids)):
        raise HTTPException(400, "Visual descriptions contain invalid or duplicate wardrobe IDs")
    try:
        outfit_ids = [int(row["id"]) for row in outfits if row.get("id") is not None]
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Archive contains an invalid outfit ID") from exc
    if any(outfit_id < 1 for outfit_id in outfit_ids) or len(outfit_ids) != len(set(outfit_ids)):
        raise HTTPException(400, "Archive contains duplicate outfit IDs")
    if any(not isinstance(row.get("name"), str) or not row["name"].strip() or len(row["name"]) > 200 for row in outfits):
        raise HTTPException(400, "Archive contains an invalid outfit name")
    existing_items = {row["id"] for row in await _query(request, "SELECT id FROM wardrobe_items")}
    existing_outfits = {row["id"] for row in await _query(request, "SELECT id FROM outfits")}
    all_item_ids = existing_items | set(catalog_ids)
    if not set(visual_ids).issubset(all_item_ids):
        raise HTTPException(400, "Visual descriptions reference an item missing from the catalog")
    for outfit in outfits:
        ids = outfit.get("item_ids", [])
        if (not isinstance(ids, list) or any(not isinstance(item_id, str) or not _valid_id(item_id) for item_id in ids)
                or len(ids) != len(set(ids)) or not set(ids).issubset(all_item_ids)):
            raise HTTPException(400, "Outfit contains duplicate or unknown wardrobe item IDs")
    incoming_outfits = {int(row["id"]) for row in outfits if row.get("id") is not None}
    item_conflicts = sorted(existing_items & {row["id"] for row in catalog})
    outfit_conflicts = sorted(existing_outfits & incoming_outfits)
    if (item_conflicts or outfit_conflicts) and not overwrite_conflicts:
        raise HTTPException(409, detail={"message": "Confirm updates to matching IDs", "item_ids": item_conflicts,
                                         "outfit_ids": outfit_conflicts})
    now = _now()
    for record in catalog:
        item_id = record["id"]
        fields = {key: value for key, value in record.items() if key not in {"id", "user_notes"}}
        old = await _query(request, "SELECT user_notes FROM wardrobe_items WHERE id = ?", item_id)
        notes = old[0].get("user_notes", "") if old else record.get("user_notes", "")
        await _run(request, """INSERT INTO wardrobe_items(id,catalog_fields,user_notes,created_at,updated_at)
            VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET catalog_fields=excluded.catalog_fields,
            updated_at=excluded.updated_at""", item_id, json.dumps(fields, ensure_ascii=False), notes, now, now)
    for record in visual:
        item_id = record.get("id", "")
        if not _valid_id(item_id):
            raise HTTPException(400, "Visual descriptions contain an invalid wardrobe ID")
        fields = {key: value for key, value in record.items() if key != "id"}
        await _run(request, "INSERT INTO visual_descriptions(item_id,source_fields) VALUES(?,?) ON CONFLICT(item_id) DO UPDATE SET source_fields=excluded.source_fields",
                   item_id, json.dumps(fields, ensure_ascii=False))
    photos_added = photos_preserved = 0
    image_binding = _env(request, "WARDROBE_IMAGES")
    for entry in manifest.get("items", []):
        item_id = entry.get("id", "")
        if not _valid_id(item_id):
            continue
        local = entry.get("local_path") or ""
        member = local.replace("\\", "/")
        if not entry.get("exported") or not member.startswith("images/") or member not in names:
            continue
        filename = member.rsplit("/", 1)[-1]
        if member.count("/") != 1 or filename.rsplit(".", 1)[0] != item_id:
            raise HTTPException(400, "Image path does not match its wardrobe ID")
        if await _query(request, "SELECT id FROM image_manifest WHERE id = ? AND object_key IS NOT NULL", item_id):
            photos_preserved += 1
            continue
        data = archive.read(member)
        if len(data) > MAX_UPLOAD_BYTES:
            continue
        try:
            extension, mime = _image_type(data)
        except ValueError:
            continue
        if entry.get("sha256") and hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise HTTPException(400, f"Image checksum does not match for {item_id}")
        key = f"images/{item_id}{extension}"
        await image_binding.put(key, data)
        await _run(request, """INSERT INTO image_manifest(id,source_url,object_key,status,source_type,
            mime_type,size_bytes,sha256,error) VALUES(?,?,?,'downloaded',?,?,?, ?,NULL)
            ON CONFLICT(id) DO UPDATE SET object_key=excluded.object_key,status=excluded.status,
            mime_type=excluded.mime_type,size_bytes=excluded.size_bytes,sha256=excluded.sha256,error=NULL""",
            item_id, entry.get("source_url") or "", key, entry.get("source_type") or "catalog_original",
            mime, len(data), hashlib.sha256(data).hexdigest())
        photos_added += 1
    for outfit in outfits:
        ids = outfit.get("item_ids", [])
        if len(ids) != len(set(ids)):
            raise HTTPException(400, "Outfit contains duplicate item IDs")
        if ids:
            found = {row["id"] for row in await _query(request, f"SELECT id FROM wardrobe_items WHERE id IN ({','.join('?' for _ in ids)})", *ids)}
            if found != set(ids):
                raise HTTPException(400, "Outfit references an unknown wardrobe item")
        created = outfit.get("created_at") or now
        updated = outfit.get("updated_at") or now
        values = (outfit.get("name", "Imported outfit"), outfit.get("description", ""), outfit.get("season", ""),
                  outfit.get("occasion", ""), json.dumps(ids), created, updated)
        outfit_id = int(outfit["id"]) if outfit.get("id") is not None else None
        if outfit_id in existing_outfits and overwrite_conflicts:
            await _run(request, "UPDATE outfits SET name=?,description=?,season=?,occasion=?,item_ids=?,updated_at=? WHERE id=?",
                       *values[:5], updated, outfit_id)
        elif outfit_id is not None:
            await _run(request, "INSERT INTO outfits(id,name,description,season,occasion,item_ids,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                       outfit_id, *values)
        else:
            await _run(request, "INSERT INTO outfits(name,description,season,occasion,item_ids,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", *values)
    return {"catalog_added": len(set(row["id"] for row in catalog) - existing_items),
            "catalog_updated": len(item_conflicts), "photos_imported": photos_added,
            "photos_preserved_existing": photos_preserved}


@app.get("/{asset_path:path}")
async def serve_frontend(asset_path: str, request: Request):
    assets = _env(request, "ASSETS")
    path = asset_path or "index.html"
    response = await assets.fetch(f"https://assets.local/{path}")
    return Response(content=await response.bytes(), status_code=response.status, headers=response.headers)


Default = asgi.entrypoint(app) if asgi else None
