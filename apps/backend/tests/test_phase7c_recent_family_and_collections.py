import unittest
from datetime import UTC, datetime
from unittest.mock import patch

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


def _dt(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, day, hour, minute, tzinfo=UTC).replace(tzinfo=None)


FIXED_NOW = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)


class Phase7CRecentFamilyAndCollectionsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_updates_collection_fields_inline(self) -> None:
        seeded = self._seed_library()

        with TestClient(app) as client:
            created = client.post(
                "/collections",
                json={
                    "name": "Starter",
                    "tag_id": seeded["tag_reference_id"],
                    "color_tag": "blue",
                },
            )
            collection_id = created.json()["id"]
            response = client.patch(
                f"/collections/{collection_id}",
                json={
                    "name": "Updated retrieval",
                    "tag_id": seeded["tag_game_id"],
                    "color_tag": "green",
                    "file_type": "other",
                },
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("Updated retrieval", payload["name"])
        self.assertEqual(seeded["tag_game_id"], payload["tag_id"])
        self.assertEqual("green", payload["color_tag"])
        self.assertEqual("other", payload["file_type"])

    def test_rejects_collection_update_when_parent_path_loses_source(self) -> None:
        seeded = self._seed_library()

        with TestClient(app) as client:
            created = client.post(
                "/collections",
                json={
                    "name": "Source retrieval",
                    "source_id": seeded["source_id"],
                    "parent_path": r"D:\Library\Refs",
                },
            )
            collection_id = created.json()["id"]
            response = client.patch(
                f"/collections/{collection_id}",
                json={
                    "source_id": None,
                },
            )

        self.assertEqual(400, response.status_code)
        self.assertEqual("PARENT_PATH_REQUIRES_SOURCE", response.json()["error"]["code"])

    def test_recent_tagged_returns_latest_tagged_active_files(self) -> None:
        self._seed_library()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                response = client.get("/recent/tagged", params={"range": "7d"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(
            ["Quest Launcher.exe", "Steam Shortcut.lnk", "Reference Sheet.pdf"],
            [item["name"] for item in payload["items"]],
        )
        self.assertEqual("2026-04-22T11:40:00", payload["items"][0]["occurred_at"])

    def test_recent_color_tagged_returns_currently_colored_active_files(self) -> None:
        self._seed_library()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                response = client.get("/recent/color-tagged", params={"range": "7d"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(["Quest Launcher.exe", "Reference Sheet.pdf", "Steam Shortcut.lnk"], [item["name"] for item in payload["items"]])
        self.assertEqual("2026-04-22T11:50:00", payload["items"][0]["occurred_at"])

    def test_games_filters_by_tag_and_color_tag(self) -> None:
        seeded = self._seed_library()

        with TestClient(app) as client:
            tag_response = client.get(
                "/library/games",
                params={"tag_id": seeded["tag_game_id"], "sort_by": "name", "sort_order": "asc"},
            )
            color_response = client.get(
                "/library/games",
                params={"color_tag": "green", "sort_by": "name", "sort_order": "asc"},
            )

        self.assertEqual(["Quest Launcher", "Steam Shortcut"], [item["display_title"] for item in tag_response.json()["items"]])
        self.assertEqual(["Quest Launcher"], [item["display_title"] for item in color_response.json()["items"]])

    def test_games_combines_status_and_tag_without_affecting_status_semantics(self) -> None:
        seeded = self._seed_library()

        with TestClient(app) as client:
            response = client.get(
                "/library/games",
                params={
                    "status": "playing",
                    "tag_id": seeded["tag_game_id"],
                    "sort_by": "name",
                    "sort_order": "asc",
                },
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(["Quest Launcher", "Steam Shortcut"], [item["display_title"] for item in payload["items"]])
        self.assertTrue(all(item["status"] == "playing" for item in payload["items"]))

    def _seed_library(self) -> dict[str, int]:
        with SessionLocal() as session:
            source = Source(
                path=r"D:\Library",
                display_name="Library",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(22, 9),
                last_scan_status="succeeded",
                created_at=_dt(22, 8),
                updated_at=_dt(22, 9),
            )
            session.add(source)
            session.flush()

            reference_tag = Tag(name="Reference", normalized_name="reference", created_at=_dt(22, 8), updated_at=_dt(22, 8))
            game_tag = Tag(name="Games", normalized_name="games", created_at=_dt(22, 8, 10), updated_at=_dt(22, 8, 10))
            session.add_all([reference_tag, game_tag])
            session.flush()

            reference_sheet = File(
                source_id=source.id,
                path=r"D:\Library\Refs\Reference Sheet.pdf",
                parent_path=r"D:\Library\Refs",
                name="Reference Sheet.pdf",
                stem="Reference Sheet",
                extension="pdf",
                file_type="document",
                mime_type=None,
                size_bytes=320,
                created_at_fs=_dt(22, 8, 30),
                modified_at_fs=_dt(22, 9, 0),
                discovered_at=_dt(22, 9, 0),
                last_seen_at=_dt(22, 9, 0),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(22, 9, 0),
            )
            steam_shortcut = File(
                source_id=source.id,
                path=r"D:\Library\Steam\Steam Shortcut.lnk",
                parent_path=r"D:\Library\Steam",
                name="Steam Shortcut.lnk",
                stem="Steam Shortcut",
                extension="lnk",
                file_type="other",
                mime_type=None,
                size_bytes=64,
                created_at_fs=_dt(22, 8, 40),
                modified_at_fs=_dt(22, 9, 10),
                discovered_at=_dt(22, 9, 10),
                last_seen_at=_dt(22, 9, 10),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(22, 9, 10),
            )
            quest_launcher = File(
                source_id=source.id,
                path=r"D:\Library\Games\Quest Launcher.exe",
                parent_path=r"D:\Library\Games",
                name="Quest Launcher.exe",
                stem="Quest Launcher",
                extension="exe",
                file_type="other",
                mime_type=None,
                size_bytes=4096,
                created_at_fs=_dt(22, 8, 50),
                modified_at_fs=_dt(22, 9, 20),
                discovered_at=_dt(22, 9, 20),
                last_seen_at=_dt(22, 9, 20),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(22, 9, 20),
            )
            utility = File(
                source_id=source.id,
                path=r"D:\Library\Tools\Portable Utility.exe",
                parent_path=r"D:\Library\Tools",
                name="Portable Utility.exe",
                stem="Portable Utility",
                extension="exe",
                file_type="other",
                mime_type=None,
                size_bytes=1024,
                created_at_fs=_dt(22, 9, 0),
                modified_at_fs=_dt(22, 9, 30),
                discovered_at=_dt(22, 9, 30),
                last_seen_at=_dt(22, 9, 30),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(22, 9, 30),
            )
            deleted_file = File(
                source_id=source.id,
                path=r"D:\Library\Old\Deleted.pdf",
                parent_path=r"D:\Library\Old",
                name="Deleted.pdf",
                stem="Deleted",
                extension="pdf",
                file_type="document",
                mime_type=None,
                size_bytes=12,
                created_at_fs=_dt(22, 8, 20),
                modified_at_fs=_dt(22, 8, 25),
                discovered_at=_dt(22, 8, 25),
                last_seen_at=_dt(22, 8, 25),
                is_deleted=True,
                checksum_hint=None,
                updated_at=_dt(22, 8, 25),
            )
            session.add_all([reference_sheet, steam_shortcut, quest_launcher, utility, deleted_file])
            session.flush()

            session.add_all(
                [
                    FileTag(file_id=reference_sheet.id, tag_id=reference_tag.id, created_at=_dt(22, 10, 15)),
                    FileTag(file_id=quest_launcher.id, tag_id=game_tag.id, created_at=_dt(22, 11, 40)),
                    FileTag(file_id=steam_shortcut.id, tag_id=game_tag.id, created_at=_dt(22, 11, 0)),
                    FileTag(file_id=deleted_file.id, tag_id=reference_tag.id, created_at=_dt(22, 11, 50)),
                ]
            )
            session.add_all(
                [
                    FileUserMeta(
                        file_id=reference_sheet.id,
                        color_tag="blue",
                        status=None,
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(22, 11, 45),
                    ),
                    FileUserMeta(
                        file_id=steam_shortcut.id,
                        color_tag="purple",
                        status="playing",
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(22, 11, 30),
                    ),
                    FileUserMeta(
                        file_id=quest_launcher.id,
                        color_tag="green",
                        status="playing",
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(22, 11, 50),
                    ),
                    FileUserMeta(
                        file_id=utility.id,
                        color_tag=None,
                        status=None,
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(22, 11, 55),
                    ),
                    FileUserMeta(
                        file_id=deleted_file.id,
                        color_tag="red",
                        status=None,
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(22, 11, 59),
                    ),
                ]
            )
            session.commit()

            return {
                "source_id": int(source.id),
                "tag_reference_id": int(reference_tag.id),
                "tag_game_id": int(game_tag.id),
            }

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM collections"))
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
