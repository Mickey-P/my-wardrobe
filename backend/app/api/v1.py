from __future__ import annotations

import os
import re

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Outfit, VisualDescription, WardrobeItem
from ..schemas import ItemOut, ItemUpdate, OutfitCreate, OutfitOut, OutfitUpdate
from ..services.import_service import validate_item_ids
from ..services.photo_service import InvalidPhoto, PhotoConflict, image_entries, resolve_image, store_photo
from ..services.archive_service import ArchiveConflict, MAX_ARCHIVE_BYTES, import_archive
from ..services.export_service import make_zip, to_csv, to_json, catalog_rows

router = APIRouter(prefix="/api/v1")
bearer = HTTPBearer(auto_error=False)
ID_RE = re.compile(r"^W\d{3}$")


def require_api_access(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    expected = os.getenv("WARDROBE_API_TOKEN", "").strip()
    required = os.getenv("WARDROBE_REQUIRE_AUTH", "").lower() in {"1", "true", "yes"} or bool(expected)
    if not required:
        return
    if not expected or credentials is None or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Valid bearer token required",
                            headers={"WWW-Authenticate": "Bearer"})


def _item_out(item: WardrobeItem, images: dict[str, dict]) -> ItemOut:
    visual = item.visual_description.source_fields if item.visual_description else None
    entry = images.get(item.id) or {}
    return ItemOut(
        id=item.id,
        catalog_fields=item.catalog_fields,
        user_notes=item.user_notes,
        visual_description=visual,
        local_image_path=entry.get("local_path"),
        image_status=entry.get("status", "missing_url"),
    )


@router.get("/health", tags=["system"])
def health(_: None = Depends(require_api_access)):
    return {"status": "ok"}


@router.get("/stats", tags=["wardrobe"])
def stats(db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    items = db.scalars(select(WardrobeItem)).all()
    categories: dict[str, int] = {}
    seasons: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for item in items:
        fields = item.catalog_fields
        for counter, key in ((categories, "category"), (seasons, "season"), (statuses, "status")):
            value = (fields.get(key) or "Unspecified").strip() or "Unspecified"
            counter[value] = counter.get(value, 0) + 1
    images = image_entries()
    available = sum(entry.get("status") in {"downloaded", "already_exists", "manual_upload"}
                    for entry in images.values())
    return {"total_items": len(items), "by_category": categories, "by_season": seasons,
            "by_status": statuses, "with_photos": available, "without_photos": max(0, len(items) - available)}


@router.get("/exports/catalog.csv", tags=["exports"])
def export_csv(db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    return Response(content=to_csv(catalog_rows(db)), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=catalog.csv"})


@router.get("/exports/catalog.json", tags=["exports"])
def export_json(db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    return Response(content=to_json(db), media_type="application/json; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=catalog.json"})


@router.get("/exports/zip", tags=["exports"])
def export_zip(db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    content, filename = make_zip(db)
    return Response(content=content, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/imports/zip", tags=["imports"])
async def import_zip(
    file: UploadFile = File(...),
    overwrite_conflicts: bool = Query(False, description="Confirm updates to existing wardrobe and outfit IDs"),
    db: Session = Depends(get_db), _: None = Depends(require_api_access),
):
    content = await file.read(MAX_ARCHIVE_BYTES + 1)
    try:
        return import_archive(db, content, overwrite_conflicts=overwrite_conflicts)
    except ArchiveConflict as exc:
        raise HTTPException(status_code=409, detail={
            "message": "Archive contains IDs already present in this wardrobe. Confirm overwrite to continue.",
            "item_ids": exc.item_ids,
            "outfit_ids": exc.outfit_ids,
        }) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/items", response_model=list[ItemOut], tags=["wardrobe"])
def list_items(
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
    db: Session = Depends(get_db), _: None = Depends(require_api_access),
):
    items = db.scalars(select(WardrobeItem).options(joinedload(WardrobeItem.visual_description))).all()
    images = image_entries()
    needle = q.casefold().strip() if q else None
    results = []
    for item in items:
        fields = item.catalog_fields
        searchable = " ".join(str(value) for value in fields.values()) + " " + item.user_notes
        if item.visual_description:
            searchable += " " + " ".join(str(value) for value in item.visual_description.source_fields.values())
        if needle and needle not in (item.id + " " + searchable).casefold():
            continue
        if category and (fields.get("category") or "").casefold() != category.casefold():
            continue
        if subcategory and subcategory.casefold() not in (fields.get("subcategory") or "").casefold():
            continue
        if color and color.casefold() not in ((fields.get("primary_color") or "") + " " + (fields.get("secondary_colors") or "")).casefold():
            continue
        if season and season.casefold() not in (fields.get("season") or "").casefold():
            continue
        if brand and brand.casefold() not in (fields.get("brand") or "").casefold():
            continue
        if formality and formality.casefold() not in (fields.get("formality") or "").casefold():
            continue
        if warmth and warmth.casefold() not in (fields.get("warmth") or "").casefold():
            continue
        if fit and fit.casefold() not in (fields.get("fit") or "").casefold():
            continue
        if item_status and item_status.casefold() not in (fields.get("status") or "").casefold():
            continue
        has = (images.get(item.id, {}).get("status") in {"downloaded", "already_exists", "manual_upload"})
        if has_photo is not None and has != has_photo:
            continue
        results.append(item)
    field_map = {"id": lambda x: x.id, "category": lambda x: str(x.catalog_fields.get("category") or "").casefold(),
                 "color": lambda x: str(x.catalog_fields.get("primary_color") or "").casefold(),
                 "brand": lambda x: str(x.catalog_fields.get("brand") or "").casefold()}
    results.sort(key=field_map[sort])
    return [_item_out(item, images) for item in results[offset: offset + limit]]


@router.get("/items/{item_id}", response_model=ItemOut, tags=["wardrobe"])
def get_item(item_id: str, db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    item = db.scalar(select(WardrobeItem).options(joinedload(WardrobeItem.visual_description)).where(WardrobeItem.id == item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")
    return _item_out(item, image_entries())


@router.put("/items/{item_id}", response_model=ItemOut, tags=["wardrobe"])
def update_item(item_id: str, payload: ItemUpdate, db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    item = db.get(WardrobeItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")
    if payload.catalog_fields is not None:
        if payload.catalog_fields.get("id", item_id) != item_id:
            raise HTTPException(status_code=422, detail="Item ID is immutable")
        updated = dict(payload.catalog_fields)
        updated["id"] = item_id
        item.catalog_fields = updated
    if payload.user_notes is not None:
        item.user_notes = payload.user_notes
    db.commit()
    db.refresh(item)
    return _item_out(item, image_entries())


@router.get("/items/{item_id}/visual-description", tags=["wardrobe"])
def get_visual_description(item_id: str, db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    visual = db.get(VisualDescription, item_id)
    if visual is None:
        raise HTTPException(status_code=404, detail="Visual description not found")
    return {"id": item_id, **visual.source_fields}


@router.get("/items/{item_id}/photo", tags=["photos"])
def get_photo(item_id: str, _: None = Depends(require_api_access)):
    try:
        path, mime, _entry = resolve_image(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid wardrobe ID") from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Photo not found") from None
    return FileResponse(path, media_type=mime, filename=path.name, content_disposition_type="inline")


@router.post("/items/{item_id}/photo", status_code=201, tags=["photos"])
async def upload_photo(
    item_id: str,
    file: UploadFile = File(...),
    replace: bool = Query(False, description="Must be true to replace an existing catalog photo"),
    db: Session = Depends(get_db), _: None = Depends(require_api_access),
):
    if not ID_RE.fullmatch(item_id) or not 1 <= int(item_id[1:]) <= 139:
        raise HTTPException(status_code=400, detail="Invalid wardrobe ID")
    if db.get(WardrobeItem, item_id) is None:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")
    data = await file.read(40 * 1024 * 1024 + 1)
    if len(data) > 40 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image exceeds 40 MiB limit")
    try:
        return store_photo(item_id, data, file.content_type, replace=replace)
    except PhotoConflict:
        raise HTTPException(status_code=409, detail="A photo already exists; confirm replacement with replace=true") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidPhoto as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _outfit_or_404(db: Session, outfit_id: int) -> Outfit:
    outfit = db.get(Outfit, outfit_id)
    if outfit is None:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return outfit


@router.get("/outfits", response_model=list[OutfitOut], tags=["outfits"])
def list_outfits(db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    return db.scalars(select(Outfit).order_by(Outfit.updated_at.desc())).all()


@router.post("/outfits", response_model=OutfitOut, status_code=201, tags=["outfits"])
def create_outfit(payload: OutfitCreate, db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    try:
        validate_item_ids(db, payload.item_ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    outfit = Outfit(**payload.model_dump())
    db.add(outfit)
    db.commit()
    db.refresh(outfit)
    return outfit


@router.get("/outfits/{outfit_id}", response_model=OutfitOut, tags=["outfits"])
def get_outfit(outfit_id: int, db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    return _outfit_or_404(db, outfit_id)


@router.put("/outfits/{outfit_id}", response_model=OutfitOut, tags=["outfits"])
def update_outfit(outfit_id: int, payload: OutfitUpdate, db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    outfit = _outfit_or_404(db, outfit_id)
    try:
        validate_item_ids(db, payload.item_ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for key, value in payload.model_dump().items():
        setattr(outfit, key, value)
    db.commit()
    db.refresh(outfit)
    return outfit


@router.delete("/outfits/{outfit_id}", status_code=204, tags=["outfits"])
def delete_outfit(outfit_id: int, db: Session = Depends(get_db), _: None = Depends(require_api_access)):
    outfit = _outfit_or_404(db, outfit_id)
    db.delete(outfit)
    db.commit()
