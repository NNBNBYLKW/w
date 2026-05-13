import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.source import Source
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app
from app.services.library.object_parser import parse_object_folder_name, parse_scanned_object


def _dt() -> datetime:
    return datetime(2026, 5, 1, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryPhase2ObjectsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_folder_parser_extracts_game_title_year_and_tags(self) -> None:
        parsed = parse_object_folder_name("[GAME] Hollow Knight (2017) [Windows][DRMFree]")

        self.assertIsNotNone(parsed)
        self.assertEqual("game", parsed.object_type)
        self.assertEqual("Hollow Knight", parsed.filesystem_title)
        self.assertEqual(2017, parsed.year)
        self.assertEqual(["Windows", "DRMFree"], parsed.tags)

    def test_folder_parser_marks_unknown_type_for_review(self) -> None:
        parsed = parse_object_folder_name("[WEIRD] Strange Object")

        self.assertIsNotNone(parsed)
        self.assertEqual("unknown_object", parsed.object_type)
        self.assertTrue(parsed.needs_review)
        self.assertEqual("unknown_type_prefix", parsed.review_reason)

    def test_valid_asset_yaml_overrides_title(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "[MOVIE] Folder Title (2020)"
            root.mkdir()
            (root / "asset.yaml").write_text("schema_version: 1\ntitle: YAML Title\nyear: 2021\n", encoding="utf-8")
            (root / "movie.mp4").write_bytes(b"video")

            scanned = parse_scanned_object(root)

        self.assertIsNotNone(scanned)
        self.assertEqual("YAML Title", scanned.title)
        self.assertEqual(2021, scanned.year)
        self.assertEqual("ok", scanned.asset_yaml.parse_status)

    def test_invalid_asset_yaml_marks_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "[GAME] Broken YAML"
            root.mkdir()
            (root / "asset.yaml").write_text("title: [unterminated", encoding="utf-8")

            scanned = parse_scanned_object(root)

        self.assertIsNotNone(scanned)
        self.assertTrue(scanned.needs_review)
        self.assertEqual("invalid_asset_yaml", scanned.review_reason)
        self.assertEqual("invalid_yaml", scanned.asset_yaml.parse_status)

    def test_game_parser_finds_single_launcher_and_ignores_noise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "[GAME] Test Game"
            root.mkdir()
            (root / "Game.exe").write_bytes(b"exe")
            (root / "UnityCrashHandler64.exe").write_bytes(b"noise")
            (root / "setup.exe").write_bytes(b"noise")

            scanned = parse_scanned_object(root)

        launchers = [member for member in scanned.members if member.member_role == "launch_exe"]
        self.assertEqual(1, len(launchers))
        self.assertTrue(scanned.primary_file_path.endswith("Game.exe"))
        self.assertFalse(scanned.needs_review)

    def test_game_parser_marks_multiple_launchers_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "[GAME] Multi Launcher"
            root.mkdir()
            (root / "Game.exe").write_bytes(b"exe")
            (root / "Launcher.exe").write_bytes(b"exe")

            scanned = parse_scanned_object(root)

        self.assertTrue(scanned.needs_review)
        self.assertEqual("multiple_launcher_candidates", scanned.review_reason)

    def test_project_parser_ignores_noisy_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "[PROJECT] Useful Project"
            (root / "node_modules").mkdir(parents=True)
            (root / ".venv").mkdir()
            (root / "README.md").write_text("hello", encoding="utf-8")
            (root / "node_modules" / "package.json").write_text("{}", encoding="utf-8")

            scanned = parse_scanned_object(root)

        self.assertEqual(["README.md"], [member.relative_path for member in scanned.members])

    def test_scan_endpoint_creates_objects_and_overview_stats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            game = source_root / "[GAME] API Game (2024)"
            game.mkdir()
            (game / "Game.exe").write_bytes(b"exe")
            unknown = source_root / "[UNKNOWN] Needs Review"
            unknown.mkdir()
            self._seed_source(source_root)

            with TestClient(app) as client:
                scan_response = client.post("/library/objects/scan", json={})
                list_response = client.get("/library/objects")
                pending_response = client.get("/library/objects?needs_review=true")
                overview_response = client.get("/library/overview")

        self.assertEqual(200, scan_response.status_code)
        self.assertEqual(2, scan_response.json()["objects_found"])
        self.assertEqual(200, list_response.status_code)
        self.assertEqual(2, list_response.json()["total"])
        self.assertEqual(1, pending_response.json()["total"])
        self.assertEqual(2, overview_response.json()["total_objects"])
        self.assertFalse((game / "asset.yaml").exists())

    def test_root_path_must_be_inside_enabled_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outside = Path(temp_dir) / "outside"
            outside.mkdir()
            self._seed_source(Path(temp_dir) / "source")
            with TestClient(app) as client:
                response = client.post("/library/objects/scan", json={"root_path": str(outside)})

        self.assertEqual(400, response.status_code)

    def _seed_source(self, path: Path) -> int:
        path.mkdir(parents=True, exist_ok=True)
        now = _dt()
        with SessionLocal() as session:
            source = Source(
                path=str(path),
                display_name=path.name,
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=None,
                last_scan_status=None,
                created_at=now,
                updated_at=now,
            )
            session.add(source)
            session.commit()
            return source.id

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM asset_metadata_cache"))
            session.execute(text("DELETE FROM library_object_members"))
            session.execute(text("DELETE FROM library_objects"))
            session.execute(text("DELETE FROM tool_runs"))
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
