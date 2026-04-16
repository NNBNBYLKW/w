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
    return datetime(2026, 4, 16, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase4AFilesListTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_returns_active_indexed_files_only(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/files")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(4, payload["total"])
        self.assertEqual(4, len(payload["items"]))
        self.assertNotIn("deleted-note.txt", [item["name"] for item in payload["items"]])

    def test_excludes_deleted_rows(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/files", params={"page_size": 10})

        self.assertEqual(200, response.status_code)
        self.assertTrue(all(item["name"] != "deleted-note.txt" for item in response.json()["items"]))

    def test_returns_modified_at_from_coalesce_modified_at_fs_or_discovered_at(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/files", params={"sort_by": "name", "sort_order": "asc"})

        self.assertEqual(200, response.status_code)
        by_name = {item["name"]: item for item in response.json()["items"]}
        self.assertEqual("2026-04-16T12:00:00", by_name["Alpha Notes.pdf"]["modified_at"])
        self.assertEqual("2026-04-16T10:00:00", by_name["Beta Cover.png"]["modified_at"])

    def test_paginates_and_sorts_stably(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            full_page_one = client.get(
                "/files",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 4},
            )
            repeated_full_page_one = client.get(
                "/files",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 4},
            )
            page_one = client.get(
                "/files",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 2},
            )
            page_two = client.get(
                "/files",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 2, "page_size": 2},
            )

        full_page_one_items = full_page_one.json()["items"]
        repeated_full_page_one_items = repeated_full_page_one.json()["items"]
        self.assertEqual(
            [item["id"] for item in full_page_one_items],
            [item["id"] for item in repeated_full_page_one_items],
        )
        self.assertEqual(
            ["archive.zip", "Alpha Notes.pdf", "Beta Cover.png", "Clip.mp4"],
            [item["name"] for item in full_page_one_items],
        )
        self.assertEqual(["archive.zip", "Alpha Notes.pdf"], [item["name"] for item in page_one.json()["items"]])
        self.assertEqual(["Beta Cover.png", "Clip.mp4"], [item["name"] for item in page_two.json()["items"]])

    def test_supports_name_sort_and_discovered_at_sort(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            by_name = client.get("/files", params={"sort_by": "name", "sort_order": "asc"})
            by_discovered = client.get("/files", params={"sort_by": "discovered_at", "sort_order": "desc"})

        self.assertEqual(
            ["Alpha Notes.pdf", "archive.zip", "Beta Cover.png", "Clip.mp4"],
            [item["name"] for item in by_name.json()["items"]],
        )
        self.assertEqual(
            ["archive.zip", "Alpha Notes.pdf", "Clip.mp4", "Beta Cover.png"],
            [item["name"] for item in by_discovered.json()["items"]],
        )

    def test_preserves_nullable_size_bytes_in_list_response(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/files", params={"sort_by": "name", "sort_order": "asc"})

        first_item = response.json()["items"][0]
        self.assertEqual("Alpha Notes.pdf", first_item["name"])
        self.assertIsNone(first_item["size_bytes"])

    def _seed_sources_and_files(self) -> None:
        with SessionLocal() as session:
            source_one = Source(
                path="D:\\Assets",
                display_name="Assets",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9),
                last_scan_status="succeeded",
                created_at=_dt(8),
                updated_at=_dt(9),
            )
            source_two = Source(
                path="D:\\Assets\\Secondary",
                display_name="Secondary",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9, 30),
                last_scan_status="succeeded",
                created_at=_dt(8, 30),
                updated_at=_dt(9, 30),
            )
            session.add(source_one)
            session.add(source_two)
            session.flush()

            session.add_all(
                [
                    File(
                        source_id=source_one.id,
                        path="D:\\Assets\\Refs\\Beta Cover.png",
                        parent_path="D:\\Assets\\Refs",
                        name="Beta Cover.png",
                        stem="Beta Cover",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=123,
                        created_at_fs=_dt(9, 30),
                        modified_at_fs=_dt(10),
                        discovered_at=_dt(9, 35),
                        last_seen_at=_dt(10),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(10),
                    ),
                    File(
                        source_id=source_one.id,
                        path="D:\\Assets\\Videos\\Clip.mp4",
                        parent_path="D:\\Assets\\Videos",
                        name="Clip.mp4",
                        stem="Clip",
                        extension="mp4",
                        file_type="video",
                        mime_type=None,
                        size_bytes=456,
                        created_at_fs=_dt(9, 45),
                        modified_at_fs=_dt(10),
                        discovered_at=_dt(11),
                        last_seen_at=_dt(11),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(11),
                    ),
                    File(
                        source_id=source_one.id,
                        path="D:\\Assets\\Docs\\Alpha Notes.pdf",
                        parent_path="D:\\Assets\\Docs",
                        name="Alpha Notes.pdf",
                        stem="Alpha Notes",
                        extension="pdf",
                        file_type="document",
                        mime_type=None,
                        size_bytes=None,
                        created_at_fs=_dt(11, 30),
                        modified_at_fs=None,
                        discovered_at=_dt(12),
                        last_seen_at=_dt(12),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(12),
                    ),
                    File(
                        source_id=source_two.id,
                        path="D:\\Assets\\Secondary\\Bundles\\archive.zip",
                        parent_path="D:\\Assets\\Secondary\\Bundles",
                        name="archive.zip",
                        stem="archive",
                        extension="zip",
                        file_type="archive",
                        mime_type=None,
                        size_bytes=321,
                        created_at_fs=_dt(12, 15),
                        modified_at_fs=_dt(13),
                        discovered_at=_dt(12, 20),
                        last_seen_at=_dt(13),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(13),
                    ),
                    File(
                        source_id=source_one.id,
                        path="D:\\Assets\\Docs\\deleted-note.txt",
                        parent_path="D:\\Assets\\Docs",
                        name="deleted-note.txt",
                        stem="deleted-note",
                        extension="txt",
                        file_type="document",
                        mime_type=None,
                        size_bytes=99,
                        created_at_fs=_dt(8, 45),
                        modified_at_fs=_dt(9),
                        discovered_at=_dt(9),
                        last_seen_at=_dt(9),
                        is_deleted=True,
                        checksum_hint=None,
                        updated_at=_dt(14),
                    ),
                ]
            )
            session.commit()

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
