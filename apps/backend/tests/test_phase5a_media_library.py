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


class Phase5AMediaLibraryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_returns_active_media_files_only_for_default_scope(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/media")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(4, payload["total"])
        self.assertEqual(["Loop.mp4", "Trailer.mp4", "SceneA.png", "SceneB.png"], [item["name"] for item in payload["items"]])

    def test_filters_by_view_scope(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            images_response = client.get("/library/media", params={"view_scope": "image", "sort_by": "name", "sort_order": "asc"})
            videos_response = client.get("/library/media", params={"view_scope": "video", "sort_by": "name", "sort_order": "asc"})

        self.assertEqual(["SceneA.png", "SceneB.png"], [item["name"] for item in images_response.json()["items"]])
        self.assertEqual(["Loop.mp4", "Trailer.mp4"], [item["name"] for item in videos_response.json()["items"]])

    def test_excludes_deleted_and_non_media_rows(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/media", params={"sort_by": "name", "sort_order": "asc"})

        names = [item["name"] for item in response.json()["items"]]
        self.assertNotIn("Notes.pdf", names)
        self.assertNotIn("deleted-scene.png", names)

    def test_returns_modified_at_from_coalesce_modified_at_fs_or_discovered_at(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/media", params={"sort_by": "name", "sort_order": "asc"})

        by_name = {item["name"]: item for item in response.json()["items"]}
        self.assertEqual("2026-04-16T11:00:00", by_name["SceneA.png"]["modified_at"])
        self.assertEqual("2026-04-16T12:00:00", by_name["Trailer.mp4"]["modified_at"])

    def test_paginates_and_sorts_stably(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            first_response = client.get(
                "/library/media",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 4},
            )
            repeated_response = client.get(
                "/library/media",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 4},
            )
            page_one = client.get(
                "/library/media",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 2},
            )
            page_two = client.get(
                "/library/media",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 2, "page_size": 2},
            )

        first_items = first_response.json()["items"]
        repeated_items = repeated_response.json()["items"]
        self.assertEqual([item["id"] for item in first_items], [item["id"] for item in repeated_items])
        self.assertEqual(["Loop.mp4", "Trailer.mp4", "SceneA.png", "SceneB.png"], [item["name"] for item in first_items])
        self.assertEqual(["Loop.mp4", "Trailer.mp4"], [item["name"] for item in page_one.json()["items"]])
        self.assertEqual(["SceneA.png", "SceneB.png"], [item["name"] for item in page_two.json()["items"]])

    def _seed_sources_and_files(self) -> None:
        with SessionLocal() as session:
            source = Source(
                path=r"D:\Assets",
                display_name="Assets",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9),
                last_scan_status="succeeded",
                created_at=_dt(8),
                updated_at=_dt(9),
            )
            session.add(source)
            session.flush()

            session.add_all(
                [
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\Refs\SceneA.png",
                        parent_path=r"D:\Assets\Refs",
                        name="SceneA.png",
                        stem="SceneA",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=120,
                        created_at_fs=_dt(9, 20),
                        modified_at_fs=_dt(11),
                        discovered_at=_dt(9, 25),
                        last_seen_at=_dt(11),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(11),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\Refs\SceneB.png",
                        parent_path=r"D:\Assets\Refs",
                        name="SceneB.png",
                        stem="SceneB",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=None,
                        created_at_fs=_dt(9, 22),
                        modified_at_fs=_dt(11),
                        discovered_at=_dt(9, 28),
                        last_seen_at=_dt(11),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(11),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\Videos\Trailer.mp4",
                        parent_path=r"D:\Assets\Videos",
                        name="Trailer.mp4",
                        stem="Trailer",
                        extension="mp4",
                        file_type="video",
                        mime_type=None,
                        size_bytes=500,
                        created_at_fs=_dt(11, 30),
                        modified_at_fs=None,
                        discovered_at=_dt(12),
                        last_seen_at=_dt(12),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(12),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\Videos\Loop.mp4",
                        parent_path=r"D:\Assets\Videos",
                        name="Loop.mp4",
                        stem="Loop",
                        extension="mp4",
                        file_type="video",
                        mime_type=None,
                        size_bytes=700,
                        created_at_fs=_dt(12, 15),
                        modified_at_fs=_dt(13),
                        discovered_at=_dt(12, 20),
                        last_seen_at=_dt(13),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(13),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\Docs\Notes.pdf",
                        parent_path=r"D:\Assets\Docs",
                        name="Notes.pdf",
                        stem="Notes",
                        extension="pdf",
                        file_type="document",
                        mime_type=None,
                        size_bytes=300,
                        created_at_fs=_dt(10),
                        modified_at_fs=_dt(10, 30),
                        discovered_at=_dt(10, 35),
                        last_seen_at=_dt(10, 30),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(10, 30),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\Refs\deleted-scene.png",
                        parent_path=r"D:\Assets\Refs",
                        name="deleted-scene.png",
                        stem="deleted-scene",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=60,
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
