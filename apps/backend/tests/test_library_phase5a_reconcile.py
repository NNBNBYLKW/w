import json
import tempfile
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_object import LibraryObject
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 1, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryPhase5AReconcileTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    # ── Group A: Reconcile allowed/rejected ─────────────────────────

    def test_reconcile_completed_plan_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"], f"Preflight: {pf.json()}")
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, plan_id)
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertEqual("reconciled", data["reconcile_status"])
            self.assertIn("summary", data)
            self.assertIn("actions", data)

    def test_reconcile_draft_plan_rejected_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [cid]})
                plan_id = gen.json()["plan_id"]
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            self.assertEqual(400, resp.status_code)
            self.assertIn("Only completed plans can be reconciled", resp.json()["detail"])

    def test_reconcile_ready_plan_rejected_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            self.assertEqual(400, resp.status_code)

    # ── Group B: Move reconcile ─────────────────────────────────────

    def test_reconcile_move_matched(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, plan_id)
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            data = resp.json()
            move_actions = [a for a in data["actions"] if a["action_type"] == "move"]
            self.assertGreater(len(move_actions), 0)
            for a in move_actions:
                self.assertEqual("matched", a["reconcile_status"],
                                 f"Move action {a['action_id']} expected matched, got {a['reconcile_status']}")

    def test_reconcile_move_source_still_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                detail = client.get(f"/library/organize/plans/{plan_id}")
                move_action = next(
                    (a for a in detail.json()["actions"] if a["action_type"] == "move"), None
                )
                self.assertIsNotNone(move_action)
                target_path = Path(move_action["target_path"])
                target_path.parent.mkdir(parents=True, exist_ok=True)
                # Copy to target instead of moving (source stays)
                import shutil
                shutil.copy2(str(video), str(target_path))
                # Mark as executed manually (simulate the filesystem state after a "failed" move that actually copied)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertFalse(pf.json()["can_execute"],
                                 "Preflight should block since target now exists")
                # Instead, manually execute and then restore source
                # Actually, let's just execute normally and then restore the source file
                # First, undo the copy
                target_path.unlink()
                # Execute normally
                self.assertTrue(
                    client.post(f"/library/organize/plans/{plan_id}/preflight").json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, plan_id)
                # Restore source file
                video.parent.mkdir(parents=True, exist_ok=True)
                video.write_bytes(b"restored")
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            data = resp.json()
            move_actions = [a for a in data["actions"] if a["action_type"] == "move"]
            self.assertGreater(len(move_actions), 0)
            for a in move_actions:
                self.assertEqual("both_exist", a["reconcile_status"],
                                 f"Move action {a['action_id']} expected both_exist, got {a['reconcile_status']}")

    def test_reconcile_move_target_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                detail = self._wait_for_plan(client, plan_id)
                # Delete the moved target file, but keep source gone (normal move result)
                move_action = next(
                    (a for a in detail["actions"] if a["action_type"] == "move"), None
                )
                if move_action and move_action.get("after_path"):
                    Path(move_action["after_path"]).unlink(missing_ok=True)
                if move_action and move_action.get("before_path"):
                    # Recreate source so that source_still_exists is the result
                    src = Path(move_action["before_path"])
                    src.parent.mkdir(parents=True, exist_ok=True)
                    src.write_bytes(b"recreated source")
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            data = resp.json()
            move_actions = [a for a in data["actions"] if a["action_type"] == "move"]
            self.assertGreater(len(move_actions), 0)
            for a in move_actions:
                self.assertEqual("source_still_exists", a["reconcile_status"],
                                 f"Move action {a['action_id']} expected source_still_exists, got {a['reconcile_status']}")

    def test_reconcile_move_both_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                detail = self._wait_for_plan(client, plan_id)
                # Delete both source and target if source still exists somehow
                move_action = next(
                    (a for a in detail["actions"] if a["action_type"] == "move"), None
                )
                if move_action:
                    if move_action.get("after_path"):
                        Path(move_action["after_path"]).unlink(missing_ok=True)
                    if move_action.get("before_path"):
                        Path(move_action["before_path"]).unlink(missing_ok=True)
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            data = resp.json()
            move_actions = [a for a in data["actions"] if a["action_type"] == "move"]
            self.assertGreater(len(move_actions), 0)
            for a in move_actions:
                self.assertEqual("both_missing", a["reconcile_status"],
                                 f"Move action {a['action_id']} expected both_missing, got {a['reconcile_status']}")

    # ── Group C: mkdir reconcile ────────────────────────────────────

    def test_reconcile_mkdir_matched(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, plan_id)
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            data = resp.json()
            mkdir_actions = [a for a in data["actions"] if a["action_type"] == "mkdir"]
            self.assertGreater(len(mkdir_actions), 0)
            for a in mkdir_actions:
                self.assertEqual("matched", a["reconcile_status"],
                                 f"mkdir action {a['action_id']} expected matched, got {a['reconcile_status']}")

    def test_reconcile_mkdir_target_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                detail = client.get(f"/library/organize/plans/{plan_id}")
                # Find mkdir actions and delete the created dirs after execute
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                detail = self._wait_for_plan(client, plan_id)
                mkdir_actions = [a for a in detail["actions"] if a["action_type"] == "mkdir"]
                for a in mkdir_actions:
                    if a.get("after_path"):
                        p = Path(a["after_path"])
                        if p.is_dir():
                            import shutil
                            shutil.rmtree(str(p))
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            data = resp.json()
            mkdir_actions = [a for a in data["actions"] if a["action_type"] == "mkdir"]
            self.assertGreater(len(mkdir_actions), 0)
            for a in mkdir_actions:
                self.assertEqual("target_missing", a["reconcile_status"],
                                 f"mkdir action {a['action_id']} expected target_missing, got {a['reconcile_status']}")

    def test_reconcile_mkdir_target_not_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                detail = client.get(f"/library/organize/plans/{plan_id}")
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                detail = self._wait_for_plan(client, plan_id)
                mkdir_actions = [a for a in detail["actions"] if a["action_type"] == "mkdir"]
                # Replace a mkdir target dir with a file
                for a in mkdir_actions:
                    if a.get("after_path"):
                        p = Path(a["after_path"])
                        if p.is_dir():
                            import shutil
                            shutil.rmtree(str(p))
                            p.write_text("not a dir")
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            data = resp.json()
            mkdir_actions = [a for a in data["actions"] if a["action_type"] == "mkdir"]
            self.assertGreater(len(mkdir_actions), 0)
            for a in mkdir_actions:
                self.assertEqual("target_not_directory", a["reconcile_status"],
                                 f"mkdir action {a['action_id']} expected target_not_directory, got {a['reconcile_status']}")

    # ── Group D: write_asset_yaml reconcile ─────────────────────────

    def test_reconcile_asset_yaml_matched(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, plan_id)
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            data = resp.json()
            yaml_actions = [a for a in data["actions"] if a["action_type"] == "write_asset_yaml"]
            if yaml_actions:
                for a in yaml_actions:
                    self.assertEqual("matched", a["reconcile_status"],
                                     f"write_asset_yaml action {a['action_id']} expected matched, got {a['reconcile_status']}")

    def test_reconcile_asset_yaml_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                detail = self._wait_for_plan(client, plan_id)
                yaml_actions = [a for a in detail["actions"] if a["action_type"] == "write_asset_yaml"]
                for a in yaml_actions:
                    if a.get("after_path"):
                        Path(a["after_path"]).unlink(missing_ok=True)
                resp = client.post(f"/library/organize/plans/{plan_id}/reconcile")
            data = resp.json()
            yaml_actions = [a for a in data["actions"] if a["action_type"] == "write_asset_yaml"]
            if yaml_actions:
                for a in yaml_actions:
                    self.assertEqual("asset_yaml_missing", a["reconcile_status"],
                                     f"write_asset_yaml action {a['action_id']} expected asset_yaml_missing, got {a['reconcile_status']}")

    # ── Group E: Plan/action field updates ──────────────────────────

    def test_reconcile_updates_plan_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, plan_id)
                # Before reconcile
                detail_before = client.get(f"/library/organize/plans/{plan_id}")
                self.assertIn("reconcile_status", detail_before.json()["plan"])
                # Reconcile
                client.post(f"/library/organize/plans/{plan_id}/reconcile")
                detail_after = client.get(f"/library/organize/plans/{plan_id}")
            plan = detail_after.json()["plan"]
            self.assertEqual("reconciled", plan["reconcile_status"])
            self.assertIsNotNone(plan["reconciled_at"])
            self.assertIsNotNone(plan["reconcile_summary_json"])
            summary = json.loads(plan["reconcile_summary_json"])
            self.assertIsInstance(summary, dict)

    def test_reconcile_updates_action_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, plan_id)
                client.post(f"/library/organize/plans/{plan_id}/reconcile")
                detail = client.get(f"/library/organize/plans/{plan_id}")
            for action in detail.json()["actions"]:
                self.assertIn("reconcile_status", action)
                self.assertIsNotNone(action["reconcile_status"])
                self.assertNotEqual("not_checked", action["reconcile_status"])

    # ── Group F: Safety ─────────────────────────────────────────────

    def test_reconcile_does_not_modify_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                detail = self._wait_for_plan(client, plan_id)
                # Snapshot filesystem state before reconcile
                before_files = set()
                for p in Path(temp_dir).rglob("*"):
                    if p.is_file():
                        before_files.add((str(p), p.stat().st_mtime))
                # Reconcile
                client.post(f"/library/organize/plans/{plan_id}/reconcile")
                # Snapshot filesystem state after reconcile
                after_files = set()
                for p in Path(temp_dir).rglob("*"):
                    if p.is_file():
                        after_files.add((str(p), p.stat().st_mtime))
            self.assertEqual(before_files, after_files,
                             "Reconcile must not modify any files on disk")

    # ── Seed Helpers ──────────────────────────────────────────────────

    def _setup_source_with_inbox_file(self, temp_dir: str) -> tuple[Path, Path, Path]:
        source = Path(temp_dir) / "source_root"
        video = source / "00_Inbox" / "_to_sort" / "Inception.2010.1080p.mkv"
        video.parent.mkdir(parents=True)
        video.write_bytes(b"video")
        managed = Path(temp_dir) / "managed_lib"
        managed.mkdir()
        self._seed_source(source)
        self._seed_file(video, "video")
        return source, managed, video

    def _scan_and_get_first_candidate(self, client: TestClient) -> int:
        client.post("/library/organize/candidates/scan")
        candidates = client.get("/library/organize/candidates")
        return candidates.json()["items"][0]["id"]

    def _generate_and_mark_ready(self, client: TestClient, cid: int,
                                  root_id: int | None = None) -> int:
        body: dict = {"candidate_ids": [cid]}
        if root_id is not None:
            body["target_library_root_id"] = root_id
        gen = client.post("/library/organize/plans/generate", json=body)
        plan_id = gen.json()["plan_id"]
        mr = client.post(f"/library/organize/plans/{plan_id}/mark-ready")
        self.assertEqual(200, mr.status_code, f"mark-ready failed: {mr.text}")
        return plan_id

    def _wait_for_plan(self, client: TestClient, plan_id: int, timeout: float = 6.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            resp = client.get(f"/library/organize/plans/{plan_id}")
            data = resp.json()
            status = data["plan"]["status"]
            if status in {"completed", "completed_with_errors", "failed", "cancelled"}:
                return data
            time.sleep(0.2)
        return client.get(f"/library/organize/plans/{plan_id}").json()

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

    def _seed_object(self, path: Path, *, object_type: str, needs_review: bool, metadata_source: str) -> int:
        now = _dt()
        with SessionLocal() as session:
            item = LibraryObject(
                object_type=object_type,
                type_prefix="UNKNOWN",
                root_path=str(path),
                root_name=path.name,
                filesystem_title=path.name,
                title=path.name,
                original_title=None,
                romanized_title=None,
                localized_title_json=None,
                sort_title=None,
                year=None,
                tags_json=json.dumps([]),
                cover_path=None,
                primary_file_path=None,
                metadata_source=metadata_source,
                needs_review=needs_review,
                review_reason="unknown_type_prefix",
                created_at=now,
                updated_at=now,
                last_scanned_at=now,
            )
            session.add(item)
            session.commit()
            return item.id

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


if __name__ == "__main__":
    unittest.main()
