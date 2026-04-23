import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.file_user_meta import FileUserMeta
from app.db.models.source import Source
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 22, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class GamesLibraryBatch3TestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_updates_status_and_exposes_it_in_file_details(self) -> None:
        seeded = self._seed_sources_and_files()

        with TestClient(app) as client:
            patch_response = client.patch(f"/files/{seeded['vault_hero_id']}/status", json={"status": "playing"})
            detail_response = client.get(f"/files/{seeded['vault_hero_id']}")

        self.assertEqual(200, patch_response.status_code)
        self.assertEqual("playing", patch_response.json()["item"]["status"])
        self.assertEqual(200, detail_response.status_code)
        self.assertEqual("playing", detail_response.json()["item"]["status"])

    def test_clears_status_with_null_payload(self) -> None:
        seeded = self._seed_sources_and_files()

        with TestClient(app) as client:
            patch_response = client.patch(f"/files/{seeded['steam_shortcut_id']}/status", json={"status": None})
            detail_response = client.get(f"/files/{seeded['steam_shortcut_id']}")

        self.assertEqual(200, patch_response.status_code)
        self.assertIsNone(patch_response.json()["item"]["status"])
        self.assertIsNone(detail_response.json()["item"]["status"])

    def test_rejects_invalid_status_values(self) -> None:
        seeded = self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.patch(f"/files/{seeded['vault_hero_id']}/status", json={"status": "paused"})

        self.assertEqual(400, response.status_code)
        self.assertEqual("FILE_STATUS_INVALID", response.json()["error"]["code"])

    def test_filters_games_by_status(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            playing_response = client.get("/library/games", params={"status": "playing", "sort_by": "name", "sort_order": "asc"})
            completed_response = client.get("/library/games", params={"status": "completed", "sort_by": "name", "sort_order": "asc"})
            shelved_response = client.get("/library/games", params={"status": "shelved", "sort_by": "name", "sort_order": "asc"})

        self.assertEqual(["Steam Shortcut", "Vault Hero"], [item["display_title"] for item in playing_response.json()["items"]])
        self.assertEqual(["EA Sports FC 26"], [item["display_title"] for item in completed_response.json()["items"]])
        self.assertEqual(["Indie Quest"], [item["display_title"] for item in shelved_response.json()["items"]])

    def test_non_game_files_with_status_do_not_enter_games_surface(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/games", params={"status": "playing", "sort_by": "name", "sort_order": "asc"})

        titles = [item["display_title"] for item in response.json()["items"]]
        self.assertNotIn("Portable Tool", titles)

    def test_default_games_listing_still_returns_unfiltered_batch1_results(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/games")

        self.assertEqual(200, response.status_code)
        self.assertEqual(5, response.json()["total"])

    def _seed_sources_and_files(self) -> dict[str, int]:
        with SessionLocal() as session:
            source = Source(
                path=r"D:\Library",
                display_name="Library",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9),
                last_scan_status="succeeded",
                created_at=_dt(8),
                updated_at=_dt(9),
            )
            session.add(source)
            session.flush()

            steam_shortcut = File(
                source_id=source.id,
                path=r"D:\Library\Steam\Steam_Shortcut.lnk",
                parent_path=r"D:\Library\Steam",
                name="Steam_Shortcut.lnk",
                stem="Steam_Shortcut",
                extension="LNK",
                file_type="other",
                mime_type=None,
                size_bytes=12,
                created_at_fs=_dt(9, 20),
                modified_at_fs=None,
                discovered_at=_dt(12),
                last_seen_at=_dt(12),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(12),
            )
            vault_hero = File(
                source_id=source.id,
                path=r"D:\Library\Games\Vault_Hero.exe",
                parent_path=r"D:\Library\Games",
                name="Vault_Hero.exe",
                stem="Vault_Hero",
                extension="EXE",
                file_type="other",
                mime_type=None,
                size_bytes=3200,
                created_at_fs=_dt(10, 10),
                modified_at_fs=_dt(10, 30),
                discovered_at=_dt(9, 15),
                last_seen_at=_dt(10, 30),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10, 30),
            )
            ea_fc = File(
                source_id=source.id,
                path=r"D:\Library\EA Games\EA_Sports_FC_26.exe",
                parent_path=r"D:\Library\EA Games",
                name="EA_Sports_FC_26.exe",
                stem="EA_Sports_FC_26",
                extension=".exe",
                file_type="other",
                mime_type=None,
                size_bytes=5400,
                created_at_fs=_dt(12, 10),
                modified_at_fs=_dt(13),
                discovered_at=_dt(12, 20),
                last_seen_at=_dt(13),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(13),
            )
            indie_quest = File(
                source_id=source.id,
                path=r"D:\Library\itch\Indie_Quest.exe",
                parent_path=r"D:\Library\itch",
                name="Indie_Quest.exe",
                stem="Indie_Quest",
                extension="exe",
                file_type="other",
                mime_type=None,
                size_bytes=2700,
                created_at_fs=_dt(11, 45),
                modified_at_fs=_dt(12, 45),
                discovered_at=_dt(9, 40),
                last_seen_at=_dt(12, 45),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(12, 45),
            )
            itch_shortcut = File(
                source_id=source.id,
                path=r"D:\Library\Itch\Itch Shortcut.lnk",
                parent_path=r"D:\Library\Itch",
                name="Itch Shortcut.lnk",
                stem="Itch Shortcut",
                extension="lnk",
                file_type="other",
                mime_type=None,
                size_bytes=20,
                created_at_fs=_dt(11, 50),
                modified_at_fs=_dt(12, 10),
                discovered_at=_dt(10, 5),
                last_seen_at=_dt(12, 10),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(12, 10),
            )
            portable_tool = File(
                source_id=source.id,
                path=r"D:\Library\Tools\Portable_Tool.exe",
                parent_path=r"D:\Library\Tools",
                name="Portable_Tool.exe",
                stem="Portable_Tool",
                extension="exe",
                file_type="other",
                mime_type=None,
                size_bytes=700,
                created_at_fs=_dt(9, 10),
                modified_at_fs=_dt(9, 20),
                discovered_at=_dt(9, 22),
                last_seen_at=_dt(9, 20),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(9, 20),
            )

            session.add_all([steam_shortcut, vault_hero, ea_fc, indie_quest, itch_shortcut, portable_tool])
            session.flush()

            session.add_all(
                [
                    FileUserMeta(
                        file_id=steam_shortcut.id,
                        color_tag=None,
                        status="playing",
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(12, 5),
                    ),
                    FileUserMeta(
                        file_id=vault_hero.id,
                        color_tag=None,
                        status="playing",
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(12, 6),
                    ),
                    FileUserMeta(
                        file_id=ea_fc.id,
                        color_tag=None,
                        status="completed",
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(12, 7),
                    ),
                    FileUserMeta(
                        file_id=indie_quest.id,
                        color_tag=None,
                        status="shelved",
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(12, 8),
                    ),
                    FileUserMeta(
                        file_id=portable_tool.id,
                        color_tag=None,
                        status="playing",
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(12, 9),
                    ),
                ]
            )
            session.commit()

            return {
                "steam_shortcut_id": steam_shortcut.id,
                "vault_hero_id": vault_hero.id,
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
