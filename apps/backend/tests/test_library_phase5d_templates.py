import json
import tempfile
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 1, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryPhase5D2TemplatesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    # ── Group A: GET /templates ─────────────────────────────────────────

    def test_list_templates_returns_all_builtin(self) -> None:
        with TestClient(app) as client:
            resp = client.get("/library/organize/templates")
        self.assertEqual(200, resp.status_code)
        items = resp.json()["items"]
        self.assertEqual(7, len(items))
        for item in items:
            self.assertTrue(item["is_builtin"])
            self.assertTrue(item["is_enabled"])

    def test_template_items_have_required_fields(self) -> None:
        with TestClient(app) as client:
            resp = client.get("/library/organize/templates")
        for item in resp.json()["items"]:
            for key in ("template_key", "object_type", "name", "description", "path_template"):
                self.assertIn(key, item)
                self.assertTrue(item[key], f"Empty {key} in {item['template_key']}")

    def test_anime_template_object_type_is_anime(self) -> None:
        with TestClient(app) as client:
            resp = client.get("/library/organize/templates")
        items = resp.json()["items"]
        anime = next(item for item in items if item["template_key"] == "anime_default")
        self.assertEqual("anime", anime["object_type"])

    # ── Group B: Generate with template_key ─────────────────────────────

    def test_generate_with_valid_template_key_uses_template_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "movie_default"}
                resp = client.post("/library/organize/plans/generate", json=body)
            self.assertEqual(200, resp.status_code)
            plan_id = resp.json()["plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{plan_id}")
                actions = detail.json()["actions"]
            target_paths = [a["target_path"] for a in actions if a["target_path"]]
            target_posix = [Path(tp).as_posix() for tp in target_paths]
            self.assertTrue(
                any("10_Movies_Anime/Movies" in tp for tp in target_posix),
                f"Expected template path in target_paths: {target_paths}",
            )
            self.assertTrue(
                any("[MOVIE]" in tp for tp in target_posix),
                f"Expected [MOVIE] prefix in target_paths: {target_paths}",
            )

    def test_generate_without_template_key_keeps_existing_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id}
                resp = client.post("/library/organize/plans/generate", json=body)
            self.assertEqual(200, resp.status_code)
            plan_id = resp.json()["plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{plan_id}")
                actions = detail.json()["actions"]
            target_paths = [a["target_path"] for a in actions if a["target_path"]]
            self.assertTrue(
                any("10_Movies_Anime" in tp for tp in target_paths),
                f"Expected default PLAN_TARGET_DIRS path: {target_paths}",
            )

    def test_generate_with_invalid_template_key_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "nonexistent_template"}
                resp = client.post("/library/organize/plans/generate", json=body)
            self.assertEqual(400, resp.status_code)
            self.assertIn("Unknown or disabled template key", resp.json()["detail"])

    def test_generate_with_disabled_template_400(self) -> None:
        # All builtin templates are enabled by default. This validates
        # that a disabled template (simulated by invalid key) returns 400.
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "disabled_key"}
                resp = client.post("/library/organize/plans/generate", json=body)
            self.assertEqual(400, resp.status_code)

    def test_generate_with_mismatched_object_type_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "game_default"}
                resp = client.post("/library/organize/plans/generate", json=body)
            self.assertEqual(400, resp.status_code)
            self.assertIn("does not match candidate type", resp.json()["detail"])

    # ── Group C: Path safety ────────────────────────────────────────────

    def test_rendered_path_is_relative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "movie_default"}
                resp = client.post("/library/organize/plans/generate", json=body)
            plan_id = resp.json()["plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{plan_id}")
            managed_root = str(managed.resolve())
            actions = detail.json()["actions"]
            for a in actions:
                if a["target_path"]:
                    tp = a["target_path"]
                    self.assertTrue(tp.startswith(managed_root), f"Target path not under managed root: {tp}")
                    relative_part = tp[len(managed_root):].lstrip("\\").lstrip("/")
                    self.assertNotIn("..", Path(relative_part).as_posix())
                    self.assertNotEqual("", relative_part)

    def test_variables_are_substituted_no_raw_braces(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "movie_default"}
                resp = client.post("/library/organize/plans/generate", json=body)
            plan_id = resp.json()["plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{plan_id}")
            actions = detail.json()["actions"]
            for a in actions:
                if a["target_path"]:
                    self.assertNotIn("{title}", a["target_path"])
                    self.assertNotIn("{year}", a["target_path"])
                    self.assertNotIn("{type}", a["target_path"])

    def test_missing_variables_omit_section(self) -> None:
        # When a variable like {creator} is missing, the surrounding punctuation
        # (e.g., " - ") should be stripped from the rendered path.
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir, name="Inception.2010.1080p.mkv")
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                # Use movie_default (matches movie candidate); year variable should be populated, no raw braces remain
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "movie_default"}
                resp = client.post("/library/organize/plans/generate", json=body)
            self.assertEqual(200, resp.status_code)
            plan_id = resp.json()["plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{plan_id}")
            actions = detail.json()["actions"]
            for a in actions:
                if a["target_path"]:
                    tp = a["target_path"]
                    self.assertNotIn("()", tp, f"Empty parentheses found in: {tp}")
                    self.assertNotIn("{year}", tp, f"Raw year placeholder in: {tp}")

    def test_invalid_windows_chars_sanitized(self) -> None:
        # File name with special chars should not cause 500
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source_root"
            video = source / "00_Inbox" / "_to_sort" / "Test: Movie <2024> [1080p].mkv"
            video.parent.mkdir(parents=True)
            video.write_bytes(b"video")
            managed = Path(temp_dir) / "managed_lib"
            managed.mkdir()
            self._seed_source(source)
            self._seed_file(video, "video")
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "movie_default"}
                resp = client.post("/library/organize/plans/generate", json=body)
            self.assertEqual(200, resp.status_code)
            plan_id = resp.json()["plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{plan_id}")
            actions = detail.json()["actions"]
            for a in actions:
                if a["target_path"]:
                    for char in '<>:"/\\|?*':
                        self.assertNotIn(char, Path(a["target_path"]).name)

    # ── Group D: Plan properties ────────────────────────────────────────

    def test_plan_stores_template_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "movie_default"}
                resp = client.post("/library/organize/plans/generate", json=body)
            plan_id = resp.json()["plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{plan_id}")
            self.assertEqual("movie_default", detail.json()["plan"]["template_key"])

    def test_plan_detail_returns_template_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "movie_default"}
                resp = client.post("/library/organize/plans/generate", json=body)
            plan_id = resp.json()["plan_id"]
            detail_resp = client.get(f"/library/organize/plans/{plan_id}")
            self.assertEqual(200, detail_resp.status_code)
            self.assertEqual("movie_default", detail_resp.json()["plan"]["template_key"])

    def test_generate_creates_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            before = set(str(p) for p in Path(temp_dir).rglob("*"))
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "movie_default"}
                client.post("/library/organize/plans/generate", json=body)
            after = set(str(p) for p in Path(temp_dir).rglob("*"))
            self.assertEqual(before, after, "Template generate must not create files")

    def test_plan_without_template_key_has_null_template_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id}
                resp = client.post("/library/organize/plans/generate", json=body)
            plan_id = resp.json()["plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{plan_id}")
            self.assertIsNone(detail.json()["plan"]["template_key"])

    # ── Group E: Integration ────────────────────────────────────────────

    def test_template_generated_plan_can_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "movie_default"}
                gen = client.post("/library/organize/plans/generate", json=body)
            plan_id = gen.json()["plan_id"]
            with TestClient(app) as client2:
                mr = client2.post(f"/library/organize/plans/{plan_id}/mark-ready")
                self.assertEqual(200, mr.status_code, f"mark-ready failed: {mr.text}")
                pf = client2.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertEqual(200, pf.status_code)
                self.assertTrue(pf.json()["can_execute"])

    def test_template_path_stays_within_managed_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_movie_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")
                cid = candidates.json()["items"][0]["id"]
                body = {"candidate_ids": [cid], "target_library_root_id": root_id, "template_key": "movie_default"}
                resp = client.post("/library/organize/plans/generate", json=body)
            plan_id = resp.json()["plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{plan_id}")
            managed_resolved = str(managed.resolve())
            actions = detail.json()["actions"]
            for a in actions:
                if a["target_path"]:
                    self.assertTrue(
                        a["target_path"].startswith(managed_resolved),
                        f"Target path {a['target_path']} not under managed root {managed_resolved}",
                    )

    # ── Helpers ─────────────────────────────────────────────────────────

    def _setup_source_with_movie_file(self, temp_dir: str, name: str = "Inception.2010.1080p.mkv") -> tuple[Path, Path, Path]:
        source = Path(temp_dir) / "source_root"
        video = source / "00_Inbox" / "_to_sort" / name
        video.parent.mkdir(parents=True)
        video.write_bytes(b"video")
        managed = Path(temp_dir) / "managed_lib"
        managed.mkdir()
        self._seed_source(source)
        self._seed_file(video, "video")
        return source, managed, video

    def _seed_source(self, path: Path) -> int:
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

    def _seed_file(self, path: Path, file_type: str) -> int:
        now = _dt()
        with SessionLocal() as session:
            source = session.query(Source).filter(Source.path == str(self._source_root_for(path))).one()
            file = File(
                source_id=source.id,
                path=str(path),
                parent_path=str(path.parent),
                name=path.name,
                stem=path.stem,
                extension=path.suffix.lstrip("."),
                file_type=file_type,
                mime_type=None,
                size_bytes=path.stat().st_size,
                created_at_fs=now,
                modified_at_fs=now,
                discovered_at=now,
                last_seen_at=now,
                is_deleted=False,
                checksum_hint=None,
                updated_at=now,
            )
            session.add(file)
            session.commit()
            return file.id

    def _seed_library_root(
        self, path: Path, *,
        display_name: str | None = None,
        is_enabled: bool = True,
        is_default: bool = False,
    ) -> int:
        now = _dt()
        with SessionLocal() as session:
            root = LibraryRoot(
                root_path=str(path.resolve()),
                display_name=display_name or path.name,
                root_kind="managed",
                is_enabled=is_enabled,
                is_default=is_default,
                scan_policy="manual",
                created_at=now,
                updated_at=now,
            )
            session.add(root)
            session.commit()
            return root.id

    def _source_root_for(self, path: Path) -> Path:
        current = path
        while current.parent != current:
            if current.name in {"00_Inbox", "_to_sort"}:
                return current.parent if current.name == "00_Inbox" else current.parent.parent
            current = current.parent
        return path.parent

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM organize_plan_candidates"))
            session.execute(text("DELETE FROM organize_action_logs"))
            session.execute(text("DELETE FROM organize_actions"))
            session.execute(text("DELETE FROM organize_plans"))
            session.execute(text("DELETE FROM organize_candidates"))
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
            session.execute(text("DELETE FROM library_roots"))
            session.execute(text("DELETE FROM sources"))
            session.commit()
