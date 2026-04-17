import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.file_tag import FileTag
from app.db.models.source import Source
from app.db.models.tag import Tag
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 16, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase6BTagFilesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_returns_active_files_for_tag_only(self) -> None:
        tag_id = self._seed_tagged_files()

        with TestClient(app) as client:
            response = client.get(f"/tags/{tag_id}/files")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(4, payload["total"])
        self.assertEqual(
            ["archive.zip", "Alpha Notes.pdf", "Beta Cover.png", "Clip.mp4"],
            [item["name"] for item in payload["items"]],
        )

    def test_excludes_deleted_files_from_tag_file_list(self) -> None:
        tag_id = self._seed_tagged_files()

        with TestClient(app) as client:
            response = client.get(f"/tags/{tag_id}/files")

        self.assertEqual(200, response.status_code)
        self.assertNotIn("deleted-note.txt", [item["name"] for item in response.json()["items"]])

    def test_returns_tag_not_found_for_missing_tag(self) -> None:
        with TestClient(app) as client:
            response = client.get("/tags/9999/files")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"error": {"code": "TAG_NOT_FOUND", "message": "Tag not found."}},
            response.json(),
        )

    def test_supports_modified_at_name_discovered_at_sort(self) -> None:
        tag_id = self._seed_tagged_files()

        with TestClient(app) as client:
            by_name = client.get(f"/tags/{tag_id}/files", params={"sort_by": "name", "sort_order": "asc"})
            by_discovered = client.get(
                f"/tags/{tag_id}/files",
                params={"sort_by": "discovered_at", "sort_order": "desc"},
            )

        self.assertEqual(
            ["Alpha Notes.pdf", "archive.zip", "Beta Cover.png", "Clip.mp4"],
            [item["name"] for item in by_name.json()["items"]],
        )
        self.assertEqual(
            ["archive.zip", "Alpha Notes.pdf", "Clip.mp4", "Beta Cover.png"],
            [item["name"] for item in by_discovered.json()["items"]],
        )

    def test_paginates_tag_file_list(self) -> None:
        tag_id = self._seed_tagged_files()

        with TestClient(app) as client:
            page_one = client.get(
                f"/tags/{tag_id}/files",
                params={"page": 1, "page_size": 2, "sort_by": "modified_at", "sort_order": "desc"},
            )
            page_two = client.get(
                f"/tags/{tag_id}/files",
                params={"page": 2, "page_size": 2, "sort_by": "modified_at", "sort_order": "desc"},
            )

        self.assertEqual(["archive.zip", "Alpha Notes.pdf"], [item["name"] for item in page_one.json()["items"]])
        self.assertEqual(["Beta Cover.png", "Clip.mp4"], [item["name"] for item in page_two.json()["items"]])

    def test_preserves_nullable_size_bytes_in_tag_file_list(self) -> None:
        tag_id = self._seed_tagged_files()

        with TestClient(app) as client:
            response = client.get(f"/tags/{tag_id}/files", params={"sort_by": "name", "sort_order": "asc"})

        first_item = response.json()["items"][0]
        self.assertEqual("Alpha Notes.pdf", first_item["name"])
        self.assertIsNone(first_item["size_bytes"])

    def test_preserves_stable_ordering_across_repeated_requests(self) -> None:
        tag_id = self._seed_tagged_files()

        with TestClient(app) as client:
            first = client.get(
                f"/tags/{tag_id}/files",
                params={"sort_by": "modified_at", "sort_order": "desc", "page_size": 50},
            )
            second = client.get(
                f"/tags/{tag_id}/files",
                params={"sort_by": "modified_at", "sort_order": "desc", "page_size": 50},
            )

        self.assertEqual(
            [item["id"] for item in first.json()["items"]],
            [item["id"] for item in second.json()["items"]],
        )

    def _seed_tagged_files(self) -> int:
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
            session.add_all([source_one, source_two])
            session.flush()

            primary_tag = Tag(
                name="Reference",
                normalized_name="reference",
                created_at=_dt(8),
                updated_at=_dt(8),
            )
            other_tag = Tag(
                name="Ignore",
                normalized_name="ignore",
                created_at=_dt(8, 5),
                updated_at=_dt(8, 5),
            )
            session.add_all([primary_tag, other_tag])
            session.flush()

            beta_cover = File(
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
            )
            clip = File(
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
            )
            alpha_notes = File(
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
            )
            archive = File(
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
            )
            deleted = File(
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
            )
            ignored = File(
                source_id=source_one.id,
                path="D:\\Assets\\Misc\\ignored.txt",
                parent_path="D:\\Assets\\Misc",
                name="ignored.txt",
                stem="ignored",
                extension="txt",
                file_type="document",
                mime_type=None,
                size_bytes=20,
                created_at_fs=_dt(9),
                modified_at_fs=_dt(9, 15),
                discovered_at=_dt(9, 15),
                last_seen_at=_dt(9, 15),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(9, 15),
            )
            session.add_all([beta_cover, clip, alpha_notes, archive, deleted, ignored])
            session.flush()

            session.add_all(
                [
                    FileTag(file_id=beta_cover.id, tag_id=primary_tag.id, created_at=_dt(14)),
                    FileTag(file_id=clip.id, tag_id=primary_tag.id, created_at=_dt(14)),
                    FileTag(file_id=alpha_notes.id, tag_id=primary_tag.id, created_at=_dt(14)),
                    FileTag(file_id=archive.id, tag_id=primary_tag.id, created_at=_dt(14)),
                    FileTag(file_id=deleted.id, tag_id=primary_tag.id, created_at=_dt(14)),
                    FileTag(file_id=ignored.id, tag_id=other_tag.id, created_at=_dt(14)),
                ]
            )
            session.commit()
            return int(primary_tag.id)

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
