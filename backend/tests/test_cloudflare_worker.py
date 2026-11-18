import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from backend.cloudflare.worker import _csv_bytes, _image_type, _item_out, _query, _save_outfit, _valid_id


class FakeStatement:
    def __init__(self, sql):
        self.sql = sql
        self.values = ()

    def bind(self, *values):
        self.values = values
        return self

    async def all(self):
        return SimpleNamespace(results=[{"id": "W001", "category": "top"}])


class FakeDatabase:
    def prepare(self, sql):
        self.statement = FakeStatement(sql)
        return self.statement


def run_immediate(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return completed.value
    raise AssertionError("Test coroutine unexpectedly suspended")


class CloudflareWorkerTests(unittest.TestCase):
    def test_valid_item_ids_are_bounded(self):
        self.assertTrue(_valid_id("W001"))
        self.assertTrue(_valid_id("W139"))
        self.assertFalse(_valid_id("W000"))
        self.assertFalse(_valid_id("W140"))
        self.assertFalse(_valid_id("W01"))

    def test_image_type_uses_file_signature(self):
        self.assertEqual(_image_type(b"\xff\xd8\xffpayload"), (".jpg", "image/jpeg"))
        self.assertEqual(_image_type(b"\x89PNG\r\n\x1a\npayload"), (".png", "image/png"))
        self.assertEqual(_image_type(b"RIFF0000WEBPpayload"), (".webp", "image/webp"))
        with self.assertRaises(ValueError):
            _image_type(b"<html>not an image</html>")

    def test_item_output_preserves_cloud_photo_key_and_status(self):
        item = _item_out({
            "id": "W001", "catalog_fields": '{"category":"top"}', "user_notes": "",
            "source_fields": None, "object_key": "images/W001.webp", "status": "downloaded",
            "mime_type": "image/webp",
        })
        self.assertEqual(item["local_image_path"], "images/W001.webp")
        self.assertEqual(item["image_status"], "downloaded")
        self.assertEqual(item["catalog_fields"]["category"], "top")

    def test_d1_rows_use_bound_parameters(self):
        database = FakeDatabase()
        request = SimpleNamespace(scope={"env": SimpleNamespace(WARDROBE_DB=database)})
        rows = run_immediate(_query(request, "SELECT * FROM wardrobe_items WHERE id = ?", "W001"))
        self.assertEqual(rows, [{"id": "W001", "category": "top"}])
        self.assertEqual(database.statement.values, ("W001",))

    def test_outfit_rejects_duplicate_ids_before_writing(self):
        request = SimpleNamespace(scope={"env": SimpleNamespace()})
        with self.assertRaises(HTTPException) as raised:
            run_immediate(_save_outfit(request, {"name": "Duplicate", "item_ids": ["W001", "W001"]}))
        self.assertEqual(raised.exception.status_code, 422)

    def test_csv_export_keeps_utf8_data(self):
        exported = _csv_bytes([{"id": "W001", "notes": "café"}]).decode("utf-8-sig")
        self.assertIn("W001", exported)
        self.assertIn("café", exported)


if __name__ == "__main__":
    unittest.main()
