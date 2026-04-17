import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.file_tag import FileTag
from app.db.models.file_user_meta import FileUserMeta
from app.db.models.source import Source
from app.db.models.tag import Tag
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 16, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase2CFilesFiltersTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_files_filters_by_tag_id(self) -> None:
        seeded = self._seed_sources_files_and_tags()

        with TestClient(app) as client:
            response = client.get(
                "/files",
                params={
                    "source_id": seeded["source_one_id"],
                    "tag_id": seeded["refs_tag_id"],
                    "sort_by": "name",
                    "sort_order": "asc",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(["Alpha Scene.png", "Bravo Scene.png"], [item["name"] for item in response.json()["items"]])
        self.assertEqual(2, response.json()["total"])

    def test_files_filters_by_color_tag(self) -> None:
        seeded = self._seed_sources_files_and_tags()

        with TestClient(app) as client:
            response = client.get(
                "/files",
                params={
                    "source_id": seeded["source_one_id"],
                    "color_tag": "blue",
                    "sort_by": "name",
                    "sort_order": "asc",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(["Alpha Scene.png", "ColorOnlyRoot.png"], [item["name"] for item in response.json()["items"]])
        self.assertEqual(2, response.json()["total"])

    def test_files_combines_source_parent_path_tag_and_color_with_and_semantics(self) -> None:
        seeded = self._seed_sources_files_and_tags()

        with TestClient(app) as client:
            response = client.get(
                "/files",
                params={
                    "source_id": seeded["source_one_id"],
                    "parent_path": r"D:\Assets\Refs",
                    "tag_id": seeded["refs_tag_id"],
                    "color_tag": "blue",
                    "sort_by": "name",
                    "sort_order": "asc",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(["Alpha Scene.png"], [item["name"] for item in response.json()["items"]])
        self.assertEqual(1, response.json()["total"])

    def test_files_returns_tag_not_found_for_unknown_tag_id(self) -> None:
        seeded = self._seed_sources_files_and_tags()

        with TestClient(app) as client:
            response = client.get("/files", params={"source_id": seeded["source_one_id"], "tag_id": 999999})

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"error": {"code": "TAG_NOT_FOUND", "message": "Tag not found."}},
            response.json(),
        )

    def test_files_returns_color_tag_invalid_for_invalid_color(self) -> None:
        seeded = self._seed_sources_files_and_tags()

        with TestClient(app) as client:
            response = client.get("/files", params={"source_id": seeded["source_one_id"], "color_tag": "orange"})

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"error": {"code": "COLOR_TAG_INVALID", "message": "Color tag is invalid."}},
            response.json(),
        )

    def test_files_preserve_existing_parent_path_requires_source_rule_under_filters(self) -> None:
        seeded = self._seed_sources_files_and_tags()

        with TestClient(app) as client:
            response = client.get(
                "/files",
                params={
                    "parent_path": r"D:\Assets\Refs",
                    "tag_id": seeded["refs_tag_id"],
                    "color_tag": "blue",
                },
            )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"error": {"code": "PARENT_PATH_REQUIRES_SOURCE", "message": "parent_path requires source_id."}},
            response.json(),
        )

    def test_files_preserve_stable_ordering_under_filters(self) -> None:
        seeded = self._seed_sources_files_and_tags()

        with TestClient(app) as client:
            first_response = client.get(
                "/files",
                params={
                    "source_id": seeded["source_one_id"],
                    "tag_id": seeded["refs_tag_id"],
                    "sort_by": "modified_at",
                    "sort_order": "desc",
                },
            )
            second_response = client.get(
                "/files",
                params={
                    "source_id": seeded["source_one_id"],
                    "tag_id": seeded["refs_tag_id"],
                    "sort_by": "modified_at",
                    "sort_order": "desc",
                },
            )

        first_items = first_response.json()["items"]
        second_items = second_response.json()["items"]
        self.assertEqual([item["id"] for item in first_items], [item["id"] for item in second_items])
        self.assertEqual(["Alpha Scene.png", "Bravo Scene.png"], [item["name"] for item in first_items])

    def test_files_total_and_items_do_not_duplicate_under_filters(self) -> None:
        seeded = self._seed_sources_files_and_tags()

        with TestClient(app) as client:
            response = client.get(
                "/files",
                params={
                    "source_id": seeded["source_one_id"],
                    "tag_id": seeded["refs_tag_id"],
                    "color_tag": "blue",
                    "sort_by": "name",
                    "sort_order": "asc",
                },
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["total"])
        self.assertEqual(1, len(payload["items"]))
        self.assertEqual(["Alpha Scene.png"], [item["name"] for item in payload["items"]])

    def _seed_sources_files_and_tags(self) -> dict[str, int]:
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

            refs_tag = Tag(name="Refs", normalized_name="refs", created_at=_dt(8, 5), updated_at=_dt(8, 5))
            docs_tag = Tag(name="Docs", normalized_name="docs", created_at=_dt(8, 10), updated_at=_dt(8, 10))
            session.add_all([refs_tag, docs_tag])
            session.flush()

            alpha_file = File(
                source_id=source_one.id,
                path=r"D:\Assets\Refs\Alpha Scene.png",
                parent_path=r"D:\Assets\Refs",
                name="Alpha Scene.png",
                stem="Alpha Scene",
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=120,
                created_at_fs=_dt(9, 10),
                modified_at_fs=_dt(11),
                discovered_at=_dt(9, 15),
                last_seen_at=_dt(11),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(11),
            )
            bravo_file = File(
                source_id=source_one.id,
                path=r"D:\Assets\Refs\Bravo Scene.png",
                parent_path=r"D:\Assets\Refs",
                name="Bravo Scene.png",
                stem="Bravo Scene",
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=140,
                created_at_fs=_dt(9, 20),
                modified_at_fs=_dt(11),
                discovered_at=_dt(9, 25),
                last_seen_at=_dt(11),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(11),
            )
            color_only_root = File(
                source_id=source_one.id,
                path=r"D:\Assets\ColorOnlyRoot.png",
                parent_path=r"D:\Assets",
                name="ColorOnlyRoot.png",
                stem="ColorOnlyRoot",
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=160,
                created_at_fs=_dt(10, 10),
                modified_at_fs=_dt(12),
                discovered_at=_dt(10, 15),
                last_seen_at=_dt(12),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(12),
            )
            docs_file = File(
                source_id=source_one.id,
                path=r"D:\Assets\Docs\Guide.pdf",
                parent_path=r"D:\Assets\Docs",
                name="Guide.pdf",
                stem="Guide",
                extension="pdf",
                file_type="document",
                mime_type=None,
                size_bytes=180,
                created_at_fs=_dt(10, 20),
                modified_at_fs=_dt(13),
                discovered_at=_dt(10, 25),
                last_seen_at=_dt(13),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(13),
            )
            secondary_file = File(
                source_id=source_two.id,
                path=r"D:\Assets\Secondary\Refs\OtherScene.png",
                parent_path=r"D:\Assets\Secondary\Refs",
                name="OtherScene.png",
                stem="OtherScene",
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=200,
                created_at_fs=_dt(10, 30),
                modified_at_fs=_dt(14),
                discovered_at=_dt(10, 35),
                last_seen_at=_dt(14),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(14),
            )
            session.add_all([alpha_file, bravo_file, color_only_root, docs_file, secondary_file])
            session.flush()

            session.add_all(
                [
                    FileTag(file_id=alpha_file.id, tag_id=refs_tag.id, created_at=_dt(11, 5)),
                    FileTag(file_id=bravo_file.id, tag_id=refs_tag.id, created_at=_dt(11, 6)),
                    FileTag(file_id=docs_file.id, tag_id=docs_tag.id, created_at=_dt(11, 7)),
                    FileTag(file_id=secondary_file.id, tag_id=refs_tag.id, created_at=_dt(11, 8)),
                ]
            )
            session.add_all(
                [
                    FileUserMeta(file_id=alpha_file.id, color_tag="blue", status=None, rating=None, is_favorite=False, updated_at=_dt(11, 10)),
                    FileUserMeta(file_id=color_only_root.id, color_tag="blue", status=None, rating=None, is_favorite=False, updated_at=_dt(12, 10)),
                    FileUserMeta(file_id=docs_file.id, color_tag="red", status=None, rating=None, is_favorite=False, updated_at=_dt(13, 10)),
                    FileUserMeta(file_id=secondary_file.id, color_tag="green", status=None, rating=None, is_favorite=False, updated_at=_dt(14, 10)),
                ]
            )
            session.commit()

            return {
                "source_one_id": int(source_one.id),
                "source_two_id": int(source_two.id),
                "refs_tag_id": int(refs_tag.id),
                "docs_tag_id": int(docs_tag.id),
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
