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


class Phase4BFilesBrowseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_filters_by_source_id(self) -> None:
        source_one_id, source_two_id = self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/files", params={"source_id": source_one_id, "sort_by": "name", "sort_order": "asc"})

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            ["RootDoc.txt", "SceneA.png", "SceneB.png"],
            [item["name"] for item in response.json()["items"]],
        )

    def test_filters_by_exact_parent_path(self) -> None:
        source_one_id, _ = self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get(
                "/files",
                params={
                    "source_id": source_one_id,
                    "parent_path": r"D:\Assets\Refs",
                    "sort_by": "name",
                    "sort_order": "asc",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(["SceneA.png", "SceneB.png"], [item["name"] for item in response.json()["items"]])

    def test_combines_source_id_and_parent_path(self) -> None:
        _, source_two_id = self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get(
                "/files",
                params={
                    "source_id": source_two_id,
                    "parent_path": r"D:\Assets\Secondary\Refs",
                    "sort_by": "name",
                    "sort_order": "asc",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(["OtherScene.png"], [item["name"] for item in response.json()["items"]])

    def test_returns_parent_path_requires_source_when_parent_path_is_sent_without_source_id(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/files", params={"parent_path": r"D:\Assets\Refs"})

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"error": {"code": "PARENT_PATH_REQUIRES_SOURCE", "message": "parent_path requires source_id."}},
            response.json(),
        )

    def test_returns_source_not_found_for_unknown_source_id(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/files", params={"source_id": 9999})

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"error": {"code": "SOURCE_NOT_FOUND", "message": "Source not found."}},
            response.json(),
        )

    def test_normalizes_parent_path_and_still_matches_stored_exact_parent_path(self) -> None:
        source_one_id, _ = self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get(
                "/files",
                params={
                    "source_id": source_one_id,
                    "parent_path": r" D:/ASSETS/Refs\ ",
                    "sort_by": "name",
                    "sort_order": "asc",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(["SceneA.png", "SceneB.png"], [item["name"] for item in response.json()["items"]])

    def test_preserves_stable_ordering_with_filters_across_repeated_requests(self) -> None:
        source_one_id, _ = self._seed_sources_and_files()

        with TestClient(app) as client:
            first_response = client.get(
                "/files",
                params={
                    "source_id": source_one_id,
                    "parent_path": r"D:\Assets\Refs",
                    "sort_by": "modified_at",
                    "sort_order": "desc",
                },
            )
            second_response = client.get(
                "/files",
                params={
                    "source_id": source_one_id,
                    "parent_path": r"D:\Assets\Refs",
                    "sort_by": "modified_at",
                    "sort_order": "desc",
                },
            )

        first_items = first_response.json()["items"]
        second_items = second_response.json()["items"]
        self.assertEqual([item["id"] for item in first_items], [item["id"] for item in second_items])
        self.assertEqual(["SceneA.png", "SceneB.png"], [item["name"] for item in first_items])

    def _seed_sources_and_files(self) -> tuple[int, int]:
        with SessionLocal() as session:
            source_one = Source(
                path=r"D:\Assets",
                display_name="Assets",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9),
                last_scan_status="succeeded",
                created_at=_dt(8),
                updated_at=_dt(9),
            )
            source_two = Source(
                path=r"D:\Assets\Secondary",
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
                        path=r"D:\Assets\RootDoc.txt",
                        parent_path=r"D:\Assets",
                        name="RootDoc.txt",
                        stem="RootDoc",
                        extension="txt",
                        file_type="document",
                        mime_type=None,
                        size_bytes=80,
                        created_at_fs=_dt(9, 10),
                        modified_at_fs=_dt(10),
                        discovered_at=_dt(9, 15),
                        last_seen_at=_dt(10),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(10),
                    ),
                    File(
                        source_id=source_one.id,
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
                        source_id=source_one.id,
                        path=r"D:\Assets\Refs\SceneB.png",
                        parent_path=r"D:\Assets\Refs",
                        name="SceneB.png",
                        stem="SceneB",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=140,
                        created_at_fs=_dt(9, 22),
                        modified_at_fs=_dt(11),
                        discovered_at=_dt(9, 28),
                        last_seen_at=_dt(11),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(11),
                    ),
                    File(
                        source_id=source_two.id,
                        path=r"D:\Assets\Secondary\Refs\OtherScene.png",
                        parent_path=r"D:\Assets\Secondary\Refs",
                        name="OtherScene.png",
                        stem="OtherScene",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=160,
                        created_at_fs=_dt(9, 40),
                        modified_at_fs=_dt(12),
                        discovered_at=_dt(9, 45),
                        last_seen_at=_dt(12),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(12),
                    ),
                    File(
                        source_id=source_one.id,
                        path=r"D:\Assets\Refs\deleted-note.txt",
                        parent_path=r"D:\Assets\Refs",
                        name="deleted-note.txt",
                        stem="deleted-note",
                        extension="txt",
                        file_type="document",
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
            return int(source_one.id), int(source_two.id)

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
