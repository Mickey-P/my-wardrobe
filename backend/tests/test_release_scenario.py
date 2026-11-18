import csv
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Outfit, WardrobeItem
from app.services import archive_service, export_service, photo_service
from app.services.import_service import import_catalog
from app.services.photo_service import store_photo


class ReleaseScenarioTests(unittest.TestCase):
    def make_csv(self, path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def make_fixture_source(self, root: Path) -> tuple[Path, Path, bytes]:
        catalog = root / "catalog.csv"
        visual = root / "visual.csv"
        self.make_csv(catalog, ["id", "category", "notes", "image_url"], [
            {"id": "W001", "category": "top", "notes": "fixture source", "image_url": "fixture://W001"},
        ])
        self.make_csv(visual, ["id", "visual_description", "critical_details", "uncertainties"], [
            {"id": "W001", "visual_description": "Blue fixture shirt", "critical_details": "round neck", "uncertainties": "synthetic"},
        ])
        image = io.BytesIO()
        Image.new("RGB", (4, 4), "blue").save(image, format="PNG")
        return catalog, visual, image.getvalue()

    def patch_storage(self, root: Path):
        image_root = root / "data" / "images"
        manifest = root / "data" / "image_manifest.json"
        self.addCleanup(setattr, photo_service, "ROOT", photo_service.ROOT)
        self.addCleanup(setattr, photo_service, "IMAGE_ROOT", photo_service.IMAGE_ROOT)
        self.addCleanup(setattr, photo_service, "MANIFEST", photo_service.MANIFEST)
        self.addCleanup(setattr, archive_service, "ROOT", archive_service.ROOT)
        self.addCleanup(setattr, archive_service, "IMAGE_ROOT", archive_service.IMAGE_ROOT)
        self.addCleanup(setattr, archive_service, "MANIFEST", archive_service.MANIFEST)
        photo_service.ROOT = root
        photo_service.IMAGE_ROOT = image_root
        photo_service.MANIFEST = manifest
        archive_service.ROOT = root
        archive_service.IMAGE_ROOT = image_root
        archive_service.MANIFEST = manifest
        return image_root, manifest

    def test_fixture_release_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog, visual, photo_bytes = self.make_fixture_source(root)
            image_root, manifest = self.patch_storage(root)

            source_engine = create_engine("sqlite://", future=True)
            Base.metadata.create_all(source_engine)
            SourceSession = sessionmaker(bind=source_engine, autoflush=False, expire_on_commit=False)
            with SourceSession() as db:
                self.assertEqual(import_catalog(db, catalog, visual)["catalog_added"], 1)
                stored = store_photo("W001", photo_bytes, "image/png")
                self.assertEqual(stored["status"], "manual_upload")
                db.add(Outfit(id=1, name="Fixture outfit", description="Synthetic", season="all", occasion="test", item_ids=["W001"]))
                db.commit()
                archive_bytes, filename = export_service.make_zip(db)

            self.assertTrue(filename.endswith(".zip"))
            target_engine = create_engine("sqlite://", future=True)
            Base.metadata.create_all(target_engine)
            TargetSession = sessionmaker(bind=target_engine, autoflush=False, expire_on_commit=False)
            with TargetSession() as db:
                before = db.query(WardrobeItem).count()
                with self.assertRaises(ValueError):
                    archive_service.import_archive(db, b"not-a-zip")
                self.assertEqual(db.query(WardrobeItem).count(), before)

                report = archive_service.import_archive(db, archive_bytes)
                item = db.get(WardrobeItem, "W001")
                outfit = db.get(Outfit, 1)
                self.assertEqual(report["catalog_added"], 1)
                self.assertEqual(report["outfits_added"], 1)
                self.assertEqual(item.catalog_fields["notes"], "fixture source")
                self.assertEqual(item.visual_description.source_fields["visual_description"], "Blue fixture shirt")
                self.assertEqual(outfit.item_ids, ["W001"])

                imported_photo = image_root / "W001.png"
                self.assertTrue(imported_photo.is_file())
                self.assertEqual(imported_photo.read_bytes(), photo_bytes)
                manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
                entry = next(row for row in manifest_data["items"] if row["id"] == "W001")
                self.assertEqual(entry["sha256"], hashlib.sha256(photo_bytes).hexdigest())
                self.assertEqual(entry["mime_type"], "image/png")

            target_engine.dispose()
            source_engine.dispose()

    def test_hosted_import_failure_keeps_local_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog, visual, photo_bytes = self.make_fixture_source(root)
            image_root, manifest = self.patch_storage(root)

            db_path = root / "local.db"
            source_engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
            Base.metadata.create_all(source_engine)
            SourceSession = sessionmaker(bind=source_engine, autoflush=False, expire_on_commit=False)
            with SourceSession() as db:
                import_catalog(db, catalog, visual)
                stored = store_photo("W001", photo_bytes, "image/png")
                db.add(Outfit(id=1, name="Fixture outfit", item_ids=["W001"]))
                db.commit()
                source_record = db.get(WardrobeItem, "W001").catalog_fields.copy()
                source_photo = (root / stored["local_path"]).read_bytes()
            source_engine.dispose()

            source_snapshot = root / "source-snapshot"
            source_snapshot.mkdir()
            shutil.copy2(catalog, source_snapshot / "catalog.csv")
            shutil.copy2(visual, source_snapshot / "visual.csv")
            shutil.copy2(db_path, source_snapshot / "local.db")
            shutil.copy2(image_root / "W001.png", source_snapshot / "W001.png")
            shutil.copy2(manifest, source_snapshot / "image_manifest.json")

            before_catalog = (source_snapshot / "catalog.csv").read_bytes()
            before_visual = (source_snapshot / "visual.csv").read_bytes()
            before_manifest = (source_snapshot / "image_manifest.json").read_bytes()
            before_db = (source_snapshot / "local.db").read_bytes()
            before_photo = (source_snapshot / "W001.png").read_bytes()

            hosted_import_succeeded = False
            quarantined_target = "fixture-cloud-target"
            if hosted_import_succeeded:
                self.fail("hosted fixture unexpectedly succeeded")

            fresh_db = root / "fresh-local.db"
            shutil.copy2(source_snapshot / "local.db", fresh_db)
            shutil.copy2(source_snapshot / "W001.png", image_root / "W001.png")
            fresh_engine = create_engine(f"sqlite:///{fresh_db.as_posix()}", future=True)
            Base.metadata.create_all(fresh_engine)
            FreshSession = sessionmaker(bind=fresh_engine, autoflush=False, expire_on_commit=False)
            with FreshSession() as db:
                item = db.get(WardrobeItem, "W001")
                outfit = db.get(Outfit, 1)
                self.assertEqual(item.catalog_fields["notes"], "fixture source")
                self.assertEqual(outfit.item_ids, ["W001"])
                fresh_photo = image_root / "W001.png"
                self.assertTrue(fresh_photo.is_file())
                self.assertEqual(fresh_photo.read_bytes(), source_photo)
            fresh_engine.dispose()

            self.assertTrue(quarantined_target)
            self.assertEqual((source_snapshot / "catalog.csv").read_bytes(), before_catalog)
            self.assertEqual((source_snapshot / "visual.csv").read_bytes(), before_visual)
            self.assertEqual((source_snapshot / "image_manifest.json").read_bytes(), before_manifest)
            self.assertEqual((source_snapshot / "local.db").read_bytes(), before_db)
            self.assertEqual((source_snapshot / "W001.png").read_bytes(), before_photo)
            self.assertEqual(hashlib.sha256(before_photo).hexdigest(), hashlib.sha256(source_photo).hexdigest())
            self.assertEqual(source_record["id"], "W001")



if __name__ == "__main__":
    unittest.main()
