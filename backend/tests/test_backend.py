from __future__ import annotations

import csv
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from PIL import Image
from fastapi.security import HTTPAuthorizationCredentials
import zipfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, ROOT, engine as app_engine, get_db
from app.main import app
from app.models import Outfit, VisualDescription, WardrobeItem
from app.schemas import ItemUpdate, OutfitCreate
from app.api.v1 import create_outfit, delete_outfit, get_item, get_outfit, list_items, list_outfits, require_api_access, update_item
from app.services import photo_service
from app.services.photo_service import store_photo
from app.services import archive_service, export_service
from app.services.import_service import import_catalog


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)

        def override_get_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        app_engine.dispose()

    def make_csv(self, path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_import_is_idempotent_and_keeps_user_notes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            catalog = root / "catalog.csv"
            visual = root / "visual.csv"
            self.make_csv(catalog, ["id", "category", "notes", "image_url"], [
                {"id": "W001", "category": "top", "notes": "source note", "image_url": "https://example.invalid/W001.webp"},
            ])
            self.make_csv(visual, ["id", "visual_description", "critical_details", "uncertainties"], [
                {"id": "W001", "visual_description": "White tee", "critical_details": "V-neck", "uncertainties": "Fit unknown"},
            ])
            with self.Session() as db:
                first = import_catalog(db, catalog, visual)
                item = db.get(WardrobeItem, "W001")
                item.user_notes = "My note"
                db.commit()
                second = import_catalog(db, catalog, visual)
                item = db.get(WardrobeItem, "W001")
                self.assertEqual(first["catalog_added"], 1)
                self.assertEqual(first["visual_added"], 1)
                self.assertEqual(second["catalog_updated"], 1)
                self.assertEqual(second["visual_updated"], 1)
                self.assertEqual(item.user_notes, "My note")
                self.assertEqual(item.id, "W001")
                self.assertEqual(item.catalog_fields["notes"], "source note")
                self.assertEqual(item.visual_description.source_fields["critical_details"], "V-neck")

    def test_import_reports_duplicate_and_bad_ids(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            catalog, visual = root / "catalog.csv", root / "visual.csv"
            self.make_csv(catalog, ["id", "category"], [
                {"id": "W001", "category": "top"},
                {"id": "W001", "category": "bottom"},
                {"id": "bad", "category": "accessory"},
            ])
            self.make_csv(visual, ["id", "visual_description", "critical_details", "uncertainties"], [])
            with self.Session() as db:
                report = import_catalog(db, catalog, visual)
                self.assertEqual(report["catalog_added"], 1)
                self.assertEqual(report["catalog_skipped"], 2)
                self.assertEqual(len(report["errors"]), 2)

    def test_items_search_detail_update_and_immutable_id(self):
        with self.Session() as db:
            db.add(WardrobeItem(id="W001", catalog_fields={"id": "W001", "category": "top", "primary_color": "white"}))
            db.commit()
        with self.Session() as db:
            response = list_items(q="white", category=None, subcategory=None, color=None,
                                  season=None, brand=None, has_photo=None, sort="id", limit=139,
                                  offset=0, db=db)
            self.assertEqual(response[0].id, "W001")
            update = update_item("W001", ItemUpdate(user_notes="Keep this"), db)
            self.assertEqual(update.user_notes, "Keep this")
            with self.assertRaises(HTTPException) as error:
                update_item("W001", ItemUpdate(catalog_fields={"id": "W002"}), db)
            self.assertEqual(error.exception.status_code, 422)
            with self.assertRaises(HTTPException) as not_found:
                get_item("W002", db)
            self.assertEqual(not_found.exception.status_code, 404)

    def test_outfit_crud_and_unknown_id_validation(self):
        with self.Session() as db:
            db.add(WardrobeItem(id="W001", catalog_fields={"id": "W001"}))
            db.commit()
        with self.Session() as db:
            with self.assertRaises(HTTPException) as invalid:
                create_outfit(OutfitCreate(name="Bad", item_ids=["W999"]), db)
            self.assertEqual(invalid.exception.status_code, 422)
            created = create_outfit(OutfitCreate(name="Weekend", item_ids=["W001"], season="spring"), db)
            outfit_id = created.id
            self.assertEqual(get_outfit(outfit_id, db).name, "Weekend")
            self.assertEqual(list_outfits(db)[0].name, "Weekend")
            delete_outfit(outfit_id, db)
            with self.assertRaises(HTTPException) as missing:
                get_outfit(outfit_id, db)
            self.assertEqual(missing.exception.status_code, 404)

    def test_openapi_contains_versioned_routes(self):
        schema = app.openapi()
        self.assertIn("/api/v1/items", schema["paths"])
        self.assertIn("/api/v1/items/{item_id}/photo", schema["paths"])
        self.assertIn("/api/v1/outfits", schema["paths"])
        self.assertIn("/api/v1/exports/zip", schema["paths"])
        self.assertIn("/api/v1/imports/zip", schema["paths"])

    def test_hosted_api_requires_bearer_token(self):
        prior = os.environ.get("WARDROBE_API_TOKEN")
        os.environ["WARDROBE_API_TOKEN"] = "test-secret"
        try:
            with self.assertRaises(HTTPException) as missing:
                require_api_access(None)
            self.assertEqual(missing.exception.status_code, 401)
            require_api_access(HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-secret"))
            with self.assertRaises(HTTPException):
                require_api_access(HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong"))
        finally:
            if prior is None:
                os.environ.pop("WARDROBE_API_TOKEN", None)
            else:
                os.environ["WARDROBE_API_TOKEN"] = prior

    def test_zip_import_rejects_path_traversal(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr("../outside.txt", "should never be extracted")
        with self.Session() as db:
            with self.assertRaisesRegex(ValueError, "Unsafe ZIP path"):
                archive_service.import_archive(db, payload.getvalue())

    def test_manual_photo_upload_validation_and_manifest(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            temp_root = Path(temp)
            image_root = temp_root / "data" / "images"
            manifest = temp_root / "data" / "image_manifest.json"
            old_service_root = photo_service.ROOT
            old_service_image_root, old_service_manifest = photo_service.IMAGE_ROOT, photo_service.MANIFEST
            photo_service.ROOT = temp_root
            photo_service.IMAGE_ROOT, photo_service.MANIFEST = image_root, manifest
            try:
                with self.Session() as db:
                    db.add(WardrobeItem(id="W001", catalog_fields={"id": "W001"}))
                    db.commit()
                    buffer = io.BytesIO()
                    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
                    result = store_photo("W001", buffer.getvalue(), "image/png")
                    self.assertEqual(result["status"], "manual_upload")
                    self.assertEqual(result["mime_type"], "image/png")
                    self.assertTrue((temp_root / result["local_path"]).is_file())
                    saved_manifest = json.loads(manifest.read_text(encoding="utf-8"))
                    self.assertEqual(saved_manifest["items"][0]["id"], "W001")
                    with self.assertRaises(photo_service.InvalidPhoto):
                        store_photo("W002", b"<html>not an image</html>", "image/png")
                    with self.assertRaises(photo_service.PhotoConflict):
                        store_photo("W001", buffer.getvalue(), "image/png")
            finally:
                photo_service.ROOT = old_service_root
                photo_service.IMAGE_ROOT, photo_service.MANIFEST = old_service_image_root, old_service_manifest

    def test_zip_export_import_round_trip_and_conflict_guard(self):
        source_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(source_engine)
        SourceSession = sessionmaker(bind=source_engine, autoflush=False, expire_on_commit=False)
        with SourceSession() as source_db:
            item = WardrobeItem(id="W001", catalog_fields={"id": "W001", "category": "top", "image_url": "https://example.test/W001.webp"}, user_notes="Personal note")
            item.visual_description = VisualDescription(
                item_id="W001", source_fields={"visual_description": "White tee", "critical_details": "V neck", "uncertainties": "Fit"})
            source_db.add(item)
            source_db.flush()
            source_db.add(Outfit(
                id=1, name="Casual", description="Daily", season="spring", occasion="walk", item_ids=["W001"]))
            source_db.commit()
            archive_bytes, filename = export_service.make_zip(source_db)
        self.assertTrue(filename.endswith(".zip"))

        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            temp_root = Path(temp)
            local_image_root = temp_root / "data" / "images"
            local_manifest = temp_root / "data" / "image_manifest.json"
            old_archive_root, old_service_root = archive_service.ROOT, photo_service.ROOT
            old_archive_image_root, old_archive_manifest = archive_service.IMAGE_ROOT, archive_service.MANIFEST
            old_service_image_root, old_service_manifest = photo_service.IMAGE_ROOT, photo_service.MANIFEST
            archive_service.ROOT, photo_service.ROOT = temp_root, temp_root
            archive_service.IMAGE_ROOT, archive_service.MANIFEST = local_image_root, local_manifest
            photo_service.IMAGE_ROOT, photo_service.MANIFEST = local_image_root, local_manifest
            target_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
            Base.metadata.create_all(target_engine)
            TargetSession = sessionmaker(bind=target_engine, autoflush=False, expire_on_commit=False)
            try:
                with TargetSession() as target_db:
                    result = archive_service.import_archive(target_db, archive_bytes)
                    imported = target_db.get(WardrobeItem, "W001")
                    self.assertEqual(result["catalog_added"], 1)
                    self.assertEqual(result["photos_imported"], 1)
                    self.assertEqual(imported.user_notes, "Personal note")
                    self.assertEqual(imported.visual_description.source_fields["critical_details"], "V neck")
                    self.assertEqual(target_db.get(Outfit, 1).item_ids, ["W001"])
                    with self.assertRaises(archive_service.ArchiveConflict):
                        archive_service.import_archive(target_db, archive_bytes)
                    imported.user_notes = "Newer local note"
                    target_db.commit()
                    overwrite = archive_service.import_archive(target_db, archive_bytes, overwrite_conflicts=True)
                    self.assertEqual(overwrite["photos_preserved_existing"], 1)
                    self.assertEqual(target_db.get(WardrobeItem, "W001").user_notes, "Newer local note")
            finally:
                target_engine.dispose()
                source_engine.dispose()
                archive_service.ROOT, photo_service.ROOT = old_archive_root, old_service_root
                archive_service.IMAGE_ROOT, archive_service.MANIFEST = old_archive_image_root, old_archive_manifest
                photo_service.IMAGE_ROOT, photo_service.MANIFEST = old_service_image_root, old_service_manifest


if __name__ == "__main__":
    unittest.main()
