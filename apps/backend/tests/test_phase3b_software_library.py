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
    return datetime(2026, 4, 18, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase3BSoftwareLibraryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_returns_active_exe_msi_and_zip_files_only(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/software")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(6, payload["total"])
        self.assertEqual(
            [
                "Zip Toolkit",
                "Install Wizard",
                "Patch Runner",
                "Portable Setup.exe",
                "Space Utility Installer",
                "Updater Bundle",
            ],
            [item["display_title"] for item in payload["items"]],
        )

    def test_excludes_deleted_and_non_software_rows(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/software", params={"sort_by": "name", "sort_order": "asc"})

        titles = [item["display_title"] for item in response.json()["items"]]
        self.assertNotIn("deleted installer", titles)
        self.assertNotIn("Guide", titles)
        self.assertNotIn("Scene", titles)

    def test_matches_extensions_conservatively_and_maps_format(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/software", params={"sort_by": "name", "sort_order": "asc"})

        by_title = {item["display_title"]: item for item in response.json()["items"]}
        self.assertEqual("exe", by_title["Patch Runner"]["software_format"])
        self.assertEqual("msi", by_title["Space Utility Installer"]["software_format"])
        self.assertEqual("zip", by_title["Updater Bundle"]["software_format"])
        self.assertEqual("2026-04-18T12:00:00", by_title["Install Wizard"]["modified_at"])

    def test_reuses_conservative_display_title_normalization(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/software", params={"sort_by": "name", "sort_order": "asc"})

        titles = [item["display_title"] for item in response.json()["items"]]
        self.assertIn("Space Utility Installer", titles)
        self.assertIn("Portable Setup.exe", titles)
        self.assertIn("Updater Bundle", titles)

    def test_supports_name_and_discovered_at_sorting(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            name_response = client.get("/library/software", params={"sort_by": "name", "sort_order": "asc"})
            discovered_response = client.get("/library/software", params={"sort_by": "discovered_at", "sort_order": "asc"})

        self.assertEqual(
            [
                "Portable Setup.exe",
                "Install Wizard",
                "Patch Runner",
                "Space Utility Installer",
                "Updater Bundle",
                "Zip Toolkit",
            ],
            [item["display_title"] for item in name_response.json()["items"]],
        )
        self.assertEqual(
            [
                "Patch Runner",
                "Portable Setup.exe",
                "Updater Bundle",
                "Space Utility Installer",
                "Install Wizard",
                "Zip Toolkit",
            ],
            [item["display_title"] for item in discovered_response.json()["items"]],
        )

    def test_paginates_and_sorts_stably(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            first_response = client.get(
                "/library/software",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 6},
            )
            repeated_response = client.get(
                "/library/software",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 6},
            )
            page_one = client.get(
                "/library/software",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 3},
            )
            page_two = client.get(
                "/library/software",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 2, "page_size": 3},
            )

        first_items = first_response.json()["items"]
        repeated_items = repeated_response.json()["items"]
        self.assertEqual([item["id"] for item in first_items], [item["id"] for item in repeated_items])
        self.assertEqual(
            [
                "Zip Toolkit",
                "Install Wizard",
                "Patch Runner",
                "Portable Setup.exe",
                "Space Utility Installer",
                "Updater Bundle",
            ],
            [item["display_title"] for item in first_items],
        )
        self.assertEqual(
            ["Zip Toolkit", "Install Wizard", "Patch Runner"],
            [item["display_title"] for item in page_one.json()["items"]],
        )
        self.assertEqual(
            ["Portable Setup.exe", "Space Utility Installer", "Updater Bundle"],
            [item["display_title"] for item in page_two.json()["items"]],
        )

    def test_supports_tag_filtering(self) -> None:
        seeded = self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get(
                "/library/software",
                params={"tag_id": seeded["utility_tag_id"], "sort_by": "name", "sort_order": "asc"},
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(2, payload["total"])
        self.assertEqual(["Patch Runner", "Zip Toolkit"], [item["display_title"] for item in payload["items"]])

    def test_supports_color_tag_filtering(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/software", params={"color_tag": "blue", "sort_by": "name", "sort_order": "asc"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(2, payload["total"])
        self.assertEqual(["Portable Setup.exe", "Zip Toolkit"], [item["display_title"] for item in payload["items"]])

    def test_supports_combined_tag_and_color_filtering(self) -> None:
        seeded = self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get(
                "/library/software",
                params={"tag_id": seeded["utility_tag_id"], "color_tag": "blue", "sort_by": "name", "sort_order": "asc"},
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["total"])
        self.assertEqual(["Zip Toolkit"], [item["display_title"] for item in payload["items"]])

    def _seed_sources_and_files(self) -> dict[str, int]:
        with SessionLocal() as session:
            source = Source(
                path=r"D:\Software",
                display_name="Software",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9),
                last_scan_status="succeeded",
                created_at=_dt(8),
                updated_at=_dt(9),
            )
            session.add(source)
            session.flush()
            tag_utility = Tag(name="Utility", normalized_name="utility", created_at=_dt(8), updated_at=_dt(8))
            tag_setup = Tag(name="Setup", normalized_name="setup", created_at=_dt(8), updated_at=_dt(8))
            session.add_all([tag_utility, tag_setup])
            session.flush()

            patch_runner = File(
                source_id=source.id,
                path=r"D:\Software\Patch_Runner.exe",
                parent_path=r"D:\Software",
                name="Patch_Runner.exe",
                stem="Patch_Runner",
                extension="EXE",
                file_type="other",
                mime_type=None,
                size_bytes=1200,
                created_at_fs=_dt(9, 20),
                modified_at_fs=_dt(11),
                discovered_at=_dt(9, 25),
                last_seen_at=_dt(11),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(11),
            )
            install_wizard = File(
                source_id=source.id,
                path=r"D:\Software\Install_Wizard.msi",
                parent_path=r"D:\Software",
                name="Install_Wizard.msi",
                stem="Install_Wizard",
                extension="Msi",
                file_type="other",
                mime_type=None,
                size_bytes=2100,
                created_at_fs=_dt(11, 30),
                modified_at_fs=None,
                discovered_at=_dt(12),
                last_seen_at=_dt(12),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(12),
            )
            updater_bundle = File(
                source_id=source.id,
                path=r"D:\Software\Updater__Bundle.zip",
                parent_path=r"D:\Software",
                name="Updater__Bundle.zip",
                stem="Updater__Bundle",
                extension=".ZIP",
                file_type="archive",
                mime_type=None,
                size_bytes=None,
                created_at_fs=_dt(9, 22),
                modified_at_fs=_dt(9, 55),
                discovered_at=_dt(9, 40),
                last_seen_at=_dt(9, 55),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(9, 55),
            )
            zip_toolkit = File(
                source_id=source.id,
                path=r"D:\Software\Zip Toolkit.zip",
                parent_path=r"D:\Software",
                name="Zip Toolkit.zip",
                stem="Zip Toolkit",
                extension="zip",
                file_type="archive",
                mime_type=None,
                size_bytes=3400,
                created_at_fs=_dt(12, 15),
                modified_at_fs=_dt(13),
                discovered_at=_dt(12, 20),
                last_seen_at=_dt(13),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(13),
            )
            portable_setup = File(
                source_id=source.id,
                path=r"D:\Software\  Portable__Setup.exe",
                parent_path=r"D:\Software",
                name="  Portable__Setup.exe",
                stem="   ",
                extension="exe",
                file_type="other",
                mime_type=None,
                size_bytes=4100,
                created_at_fs=_dt(10, 5),
                modified_at_fs=_dt(10, 40),
                discovered_at=_dt(9, 30),
                last_seen_at=_dt(10, 40),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10, 40),
            )
            space_utility = File(
                source_id=source.id,
                path=r"D:\Software\Space_Utility__Installer.msi",
                parent_path=r"D:\Software",
                name="Space_Utility__Installer.msi",
                stem="Space_Utility__Installer",
                extension="msi",
                file_type="other",
                mime_type=None,
                size_bytes=1900,
                created_at_fs=_dt(10, 10),
                modified_at_fs=_dt(10, 15),
                discovered_at=_dt(9, 50),
                last_seen_at=_dt(10, 15),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10, 15),
            )
            guide = File(
                source_id=source.id,
                path=r"D:\Software\Guide.pdf",
                parent_path=r"D:\Software",
                name="Guide.pdf",
                stem="Guide",
                extension="pdf",
                file_type="document",
                mime_type=None,
                size_bytes=900,
                created_at_fs=_dt(10),
                modified_at_fs=_dt(10, 30),
                discovered_at=_dt(10, 35),
                last_seen_at=_dt(10, 30),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10, 30),
            )
            scene = File(
                source_id=source.id,
                path=r"D:\Software\Scene.png",
                parent_path=r"D:\Software",
                name="Scene.png",
                stem="Scene",
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=300,
                created_at_fs=_dt(10),
                modified_at_fs=_dt(10, 30),
                discovered_at=_dt(10, 35),
                last_seen_at=_dt(10, 30),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10, 30),
            )
            deleted_installer = File(
                source_id=source.id,
                path=r"D:\Software\deleted_installer.exe",
                parent_path=r"D:\Software",
                name="deleted_installer.exe",
                stem="deleted_installer",
                extension="exe",
                file_type="other",
                mime_type=None,
                size_bytes=80,
                created_at_fs=_dt(8, 45),
                modified_at_fs=_dt(9),
                discovered_at=_dt(9),
                last_seen_at=_dt(9),
                is_deleted=True,
                checksum_hint=None,
                updated_at=_dt(14),
            )

            session.add_all(
                [
                    patch_runner,
                    install_wizard,
                    updater_bundle,
                    zip_toolkit,
                    portable_setup,
                    space_utility,
                    guide,
                    scene,
                    deleted_installer,
                ]
            )
            session.flush()
            session.add_all(
                [
                    FileTag(file_id=patch_runner.id, tag_id=tag_utility.id, created_at=_dt(8)),
                    FileTag(file_id=zip_toolkit.id, tag_id=tag_utility.id, created_at=_dt(8)),
                    FileTag(file_id=install_wizard.id, tag_id=tag_setup.id, created_at=_dt(8)),
                    FileUserMeta(file_id=zip_toolkit.id, color_tag="blue", status=None, updated_at=_dt(8)),
                    FileUserMeta(file_id=portable_setup.id, color_tag="blue", status=None, updated_at=_dt(8)),
                    FileUserMeta(file_id=install_wizard.id, color_tag="green", status=None, updated_at=_dt(8)),
                    FileUserMeta(file_id=guide.id, color_tag="blue", status=None, updated_at=_dt(8)),
                ]
            )
            session.commit()
            return {
                "utility_tag_id": tag_utility.id,
                "setup_tag_id": tag_setup.id,
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
