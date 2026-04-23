import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.source import Source
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 21, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase7ABatchOrganizeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_batch_attach_tag_dedupes_ids_and_updates_detail_and_subset_queries(self) -> None:
        seeded = self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.post(
                "/files/batch/tags",
                json={"file_ids": [seeded["book_id"], seeded["software_id"], seeded["software_id"]], "name": "Launch-ready"},
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual([seeded["book_id"], seeded["software_id"]], payload["updated_file_ids"])
            self.assertEqual(2, payload["updated_count"])

            tag_id = payload["tag"]["id"]
            detail = client.get(f"/files/{seeded['book_id']}").json()["item"]
            books = client.get("/library/books", params={"tag_id": tag_id}).json()["items"]
            software = client.get("/library/software", params={"tag_id": tag_id}).json()["items"]

        self.assertEqual(["Launch-ready"], [tag["name"] for tag in detail["tags"]])
        self.assertEqual([seeded["book_id"]], [item["id"] for item in books])
        self.assertEqual([seeded["software_id"]], [item["id"] for item in software])

    def test_batch_update_color_tag_and_clear_reflects_in_detail_and_subset_queries(self) -> None:
        seeded = self._seed_sources_and_files()

        with TestClient(app) as client:
            apply_response = client.patch(
                "/files/batch/color-tag",
                json={"file_ids": [seeded["book_id"], seeded["software_id"], seeded["media_id"]], "color_tag": "blue"},
            )

            self.assertEqual(200, apply_response.status_code)
            self.assertEqual(3, apply_response.json()["updated_count"])

            book_detail = client.get(f"/files/{seeded['book_id']}").json()["item"]
            media = client.get("/library/media", params={"color_tag": "blue"}).json()["items"]
            books = client.get("/library/books", params={"color_tag": "blue"}).json()["items"]
            software = client.get("/library/software", params={"color_tag": "blue"}).json()["items"]

            clear_response = client.patch(
                "/files/batch/color-tag",
                json={"file_ids": [seeded["book_id"], seeded["software_id"]], "color_tag": None},
            )

            self.assertEqual(200, clear_response.status_code)
            cleared_book_detail = client.get(f"/files/{seeded['book_id']}").json()["item"]
            cleared_software_detail = client.get(f"/files/{seeded['software_id']}").json()["item"]

        self.assertEqual("blue", book_detail["color_tag"])
        self.assertEqual([seeded["media_id"]], [item["id"] for item in media])
        self.assertEqual([seeded["book_id"]], [item["id"] for item in books])
        self.assertEqual([seeded["software_id"]], [item["id"] for item in software])
        self.assertIsNone(cleared_book_detail["color_tag"])
        self.assertIsNone(cleared_software_detail["color_tag"])

    def test_batch_endpoints_require_non_empty_file_ids(self) -> None:
        with TestClient(app) as client:
            tag_response = client.post("/files/batch/tags", json={"file_ids": [], "name": "Launch-ready"})
            color_response = client.patch("/files/batch/color-tag", json={"file_ids": [], "color_tag": "blue"})

        self.assertEqual(422, tag_response.status_code)
        self.assertEqual(422, color_response.status_code)

    def test_batch_endpoints_fail_when_any_target_file_is_missing_or_deleted(self) -> None:
        seeded = self._seed_sources_and_files()

        with TestClient(app) as client:
            tag_response = client.post(
                "/files/batch/tags",
                json={"file_ids": [seeded["book_id"], seeded["deleted_id"]], "name": "Launch-ready"},
            )
            color_response = client.patch(
                "/files/batch/color-tag",
                json={"file_ids": [seeded["software_id"], 999999], "color_tag": "green"},
            )

        self.assertEqual(400, tag_response.status_code)
        self.assertEqual("BATCH_FILE_SELECTION_INVALID", tag_response.json()["error"]["code"])
        self.assertEqual(400, color_response.status_code)
        self.assertEqual("BATCH_FILE_SELECTION_INVALID", color_response.json()["error"]["code"])

    def _seed_sources_and_files(self) -> dict[str, int]:
        with SessionLocal() as session:
            source = Source(
                path=r"D:\Batch",
                display_name="Batch",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9),
                last_scan_status="succeeded",
                created_at=_dt(8),
                updated_at=_dt(9),
            )
            session.add(source)
            session.flush()

            book = File(
                source_id=source.id,
                path=r"D:\Batch\Books\Orbit Guide.pdf",
                parent_path=r"D:\Batch\Books",
                name="Orbit Guide.pdf",
                stem="Orbit Guide",
                extension="pdf",
                file_type="document",
                mime_type=None,
                size_bytes=1200,
                created_at_fs=_dt(9, 20),
                modified_at_fs=_dt(10),
                discovered_at=_dt(9, 25),
                last_seen_at=_dt(10),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10),
            )
            software = File(
                source_id=source.id,
                path=r"D:\Batch\Software\PatchRunner.exe",
                parent_path=r"D:\Batch\Software",
                name="PatchRunner.exe",
                stem="PatchRunner",
                extension="exe",
                file_type="other",
                mime_type=None,
                size_bytes=2300,
                created_at_fs=_dt(9, 30),
                modified_at_fs=_dt(10, 5),
                discovered_at=_dt(9, 35),
                last_seen_at=_dt(10, 5),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10, 5),
            )
            media = File(
                source_id=source.id,
                path=r"D:\Batch\Media\Scene.png",
                parent_path=r"D:\Batch\Media",
                name="Scene.png",
                stem="Scene",
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=900,
                created_at_fs=_dt(9, 40),
                modified_at_fs=_dt(10, 10),
                discovered_at=_dt(9, 45),
                last_seen_at=_dt(10, 10),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10, 10),
            )
            deleted = File(
                source_id=source.id,
                path=r"D:\Batch\Software\OldSetup.msi",
                parent_path=r"D:\Batch\Software",
                name="OldSetup.msi",
                stem="OldSetup",
                extension="msi",
                file_type="other",
                mime_type=None,
                size_bytes=700,
                created_at_fs=_dt(8, 40),
                modified_at_fs=_dt(8, 50),
                discovered_at=_dt(8, 55),
                last_seen_at=_dt(8, 50),
                is_deleted=True,
                checksum_hint=None,
                updated_at=_dt(11),
            )

            session.add_all([book, software, media, deleted])
            session.commit()
            return {
                "book_id": book.id,
                "software_id": software.id,
                "media_id": media.id,
                "deleted_id": deleted.id,
            }

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM tasks"))
            session.execute(text("DELETE FROM file_metadata"))
            session.execute(text("DELETE FROM file_tags"))
            session.execute(text("DELETE FROM file_user_meta"))
            session.execute(text("DELETE FROM files"))
            session.execute(text("DELETE FROM source_ignore_rules"))
            session.execute(text("DELETE FROM tags"))
            session.execute(text("DELETE FROM sources"))
            session.commit()


if __name__ == "__main__":
    unittest.main()
