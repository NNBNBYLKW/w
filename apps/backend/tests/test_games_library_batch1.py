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


class GamesLibraryBatch1TestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_returns_active_lnk_and_game_path_exe_files_only(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/games")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(5, payload["total"])
        self.assertEqual(
            [
                "EA Sports FC 26",
                "Indie Quest",
                "Itch Shortcut",
                "Steam Shortcut",
                "Vault Hero",
            ],
            [item["display_title"] for item in payload["items"]],
        )

    def test_excludes_deleted_installers_software_and_non_game_shapes(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/games", params={"sort_by": "name", "sort_order": "asc"})

        titles = [item["display_title"] for item in response.json()["items"]]
        self.assertNotIn("Game Setup", titles)
        self.assertNotIn("Launcher Update", titles)
        self.assertNotIn("Portable Tool", titles)
        self.assertNotIn("Retro ROM Pack", titles)
        self.assertNotIn("deleted shortcut", titles)

    def test_matches_mixed_case_extensions_and_maps_format(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/games", params={"sort_by": "name", "sort_order": "asc"})

        by_title = {item["display_title"]: item for item in response.json()["items"]}
        self.assertEqual("exe", by_title["EA Sports FC 26"]["game_format"])
        self.assertEqual("lnk", by_title["Steam Shortcut"]["game_format"])
        self.assertEqual("2026-04-21T12:00:00", by_title["Steam Shortcut"]["modified_at"])

    def test_reuses_conservative_display_title_normalization(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/games", params={"sort_by": "name", "sort_order": "asc"})

        titles = [item["display_title"] for item in response.json()["items"]]
        self.assertIn("Steam Shortcut", titles)
        self.assertIn("Vault Hero", titles)
        self.assertIn("EA Sports FC 26", titles)

    def test_supports_name_and_discovered_at_sorting(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            name_response = client.get("/library/games", params={"sort_by": "name", "sort_order": "asc"})
            discovered_response = client.get("/library/games", params={"sort_by": "discovered_at", "sort_order": "asc"})

        self.assertEqual(
            [
                "EA Sports FC 26",
                "Indie Quest",
                "Itch Shortcut",
                "Steam Shortcut",
                "Vault Hero",
            ],
            [item["display_title"] for item in name_response.json()["items"]],
        )
        self.assertEqual(
            [
                "Vault Hero",
                "Indie Quest",
                "Itch Shortcut",
                "Steam Shortcut",
                "EA Sports FC 26",
            ],
            [item["display_title"] for item in discovered_response.json()["items"]],
        )

    def test_paginates_and_sorts_stably(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            first_response = client.get(
                "/library/games",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 5},
            )
            repeated_response = client.get(
                "/library/games",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 5},
            )
            page_one = client.get(
                "/library/games",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 3},
            )
            page_two = client.get(
                "/library/games",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 2, "page_size": 3},
            )

        first_items = first_response.json()["items"]
        repeated_items = repeated_response.json()["items"]
        self.assertEqual([item["id"] for item in first_items], [item["id"] for item in repeated_items])
        self.assertEqual(
            [
                "EA Sports FC 26",
                "Indie Quest",
                "Itch Shortcut",
                "Steam Shortcut",
                "Vault Hero",
            ],
            [item["display_title"] for item in first_items],
        )
        self.assertEqual(
            ["EA Sports FC 26", "Indie Quest", "Itch Shortcut"],
            [item["display_title"] for item in page_one.json()["items"]],
        )
        self.assertEqual(
            ["Steam Shortcut", "Vault Hero"],
            [item["display_title"] for item in page_two.json()["items"]],
        )

    def _seed_sources_and_files(self) -> None:
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

            session.add_all(
                [
                    File(
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
                    ),
                    File(
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
                    ),
                    File(
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
                    ),
                    File(
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
                    ),
                    File(
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
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Games\Game_Setup.exe",
                        parent_path=r"D:\Library\Games",
                        name="Game_Setup.exe",
                        stem="Game_Setup",
                        extension="exe",
                        file_type="other",
                        mime_type=None,
                        size_bytes=1100,
                        created_at_fs=_dt(10),
                        modified_at_fs=_dt(10, 5),
                        discovered_at=_dt(10, 2),
                        last_seen_at=_dt(10, 5),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(10, 5),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Steam\Launcher_Update.exe",
                        parent_path=r"D:\Library\Steam",
                        name="Launcher_Update.exe",
                        stem="Launcher_Update",
                        extension="exe",
                        file_type="other",
                        mime_type=None,
                        size_bytes=900,
                        created_at_fs=_dt(9, 35),
                        modified_at_fs=_dt(9, 45),
                        discovered_at=_dt(9, 50),
                        last_seen_at=_dt(9, 45),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(9, 45),
                    ),
                    File(
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
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\ROMs\Retro_ROM_Pack.zip",
                        parent_path=r"D:\Library\ROMs",
                        name="Retro_ROM_Pack.zip",
                        stem="Retro_ROM_Pack",
                        extension="zip",
                        file_type="archive",
                        mime_type=None,
                        size_bytes=8600,
                        created_at_fs=_dt(8, 55),
                        modified_at_fs=_dt(9),
                        discovered_at=_dt(9, 5),
                        last_seen_at=_dt(9),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(9),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Games\download.url",
                        parent_path=r"D:\Library\Games",
                        name="download.url",
                        stem="download",
                        extension="url",
                        file_type="other",
                        mime_type=None,
                        size_bytes=2,
                        created_at_fs=_dt(8, 50),
                        modified_at_fs=_dt(8, 51),
                        discovered_at=_dt(8, 52),
                        last_seen_at=_dt(8, 51),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(8, 51),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Games\deleted_shortcut.lnk",
                        parent_path=r"D:\Library\Games",
                        name="deleted_shortcut.lnk",
                        stem="deleted_shortcut",
                        extension="lnk",
                        file_type="other",
                        mime_type=None,
                        size_bytes=4,
                        created_at_fs=_dt(8, 45),
                        modified_at_fs=_dt(8, 46),
                        discovered_at=_dt(8, 47),
                        last_seen_at=_dt(8, 46),
                        is_deleted=True,
                        checksum_hint=None,
                        updated_at=_dt(8, 46),
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
