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
from app.db.models.organize import OrganizeAction, OrganizePlan
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 1, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryPhase5CGenerateRollbackTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    # ── Group A: Allowed/rejected ─────────────────────────────────────

    def test_completed_plan_generates_rollback(self) -> None:
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
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertEqual(plan_id, data["source_plan_id"])
            self.assertGreater(data["rollback_actions_count"], 0)
            self.assertEqual("rollback", data["plan_origin"])

    def test_completed_with_errors_generates_rollback(self) -> None:
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
                # Add a second valid rollbackable move so there's still one left after setting one to failed
                self._add_clean_rollbackable_move(plan_id, managed)
                self._set_one_action_to_failed(plan_id)
                self._update_plan_status(plan_id, "completed_with_errors")
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertGreater(data["rollback_actions_count"], 0)
            self.assertEqual("rollback", data["plan_origin"])

    def test_failed_plan_generates_rollback_for_succeeded_actions(self) -> None:
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
                self._add_clean_rollbackable_move(plan_id, managed)
                self._set_one_action_to_failed(plan_id)
                self._update_plan_status(plan_id, "failed")
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertGreater(data["rollback_actions_count"], 0)

    def test_draft_rejected_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [cid]})
                plan_id = gen.json()["plan_id"]
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            self.assertEqual(400, resp.status_code)
            self.assertIn("completed", resp.json()["detail"])

    def test_ready_rejected_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            self.assertEqual(400, resp.status_code)

    def test_plan_not_found_404(self) -> None:
        with TestClient(app) as client:
            resp = client.post("/library/organize/plans/99999/generate-rollback")
        self.assertEqual(404, resp.status_code)

    # ── Group B: Rollback action generation ───────────────────────────

    def test_move_succeeded_generates_reverse_move(self) -> None:
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
                source_detail = client.get(f"/library/organize/plans/{plan_id}")
                source_actions = source_detail.json()["actions"]
                move_action = next(a for a in source_actions if a["action_type"] == "move")
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            data = resp.json()
            new_plan_id = data["rollback_plan_id"]
            with TestClient(app) as client2:
                new_detail = client2.get(f"/library/organize/plans/{new_plan_id}")
                new_actions = new_detail.json()["actions"]
            self.assertEqual(1, len(new_actions))
            na = new_actions[0]
            # Rollback source = original target, rollback target = original source
            self.assertEqual(move_action["target_path"], na["source_path"])
            self.assertEqual(move_action["source_path"], na["target_path"])
            self.assertEqual("move", na["action_type"])

    def test_rename_succeeded_generates_reverse_rename(self) -> None:
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
                # Add a valid same-dir rename action (target exists, source doesn't)
                self._add_same_dir_rename_action(plan_id, managed)
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            data = resp.json()
            new_plan_id = data["rollback_plan_id"]
            with TestClient(app) as client2:
                new_detail = client2.get(f"/library/organize/plans/{new_plan_id}")
                new_actions = new_detail.json()["actions"]
            rename_actions = [a for a in new_actions if a["action_type"] == "rename"]
            self.assertGreater(len(rename_actions), 0, f"Expected rename action; got {new_actions}")
            ra = rename_actions[0]
            self.assertEqual(
                Path(ra["source_path"]).parent,
                Path(ra["target_path"]).parent,
                "Rename rollback must have same parent",
            )

    def test_mkdir_not_rollbacked(self) -> None:
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
                # Add a succeeded mkdir action
                self._add_succeeded_mkdir_action(plan_id, managed)
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            data = resp.json()
            new_plan_id = data["rollback_plan_id"]
            with TestClient(app) as client2:
                new_detail = client2.get(f"/library/organize/plans/{new_plan_id}")
                new_actions = new_detail.json()["actions"]
            # No mkdir rollback actions
            for na in new_actions:
                self.assertNotEqual("mkdir", na["action_type"])

    def test_write_asset_yaml_not_rollbacked(self) -> None:
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
                self._add_succeeded_asset_yaml_action(plan_id, managed)
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            data = resp.json()
            new_plan_id = data["rollback_plan_id"]
            with TestClient(app) as client2:
                new_detail = client2.get(f"/library/organize/plans/{new_plan_id}")
                new_actions = new_detail.json()["actions"]
            for na in new_actions:
                self.assertNotEqual("write_asset_yaml", na["action_type"])

    def test_failed_blocked_skipped_not_rollbacked(self) -> None:
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
                self._add_non_succeeded_move_actions(plan_id, managed)
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            data = resp.json()
            new_plan_id = data["rollback_plan_id"]
            with TestClient(app) as client2:
                new_detail = client2.get(f"/library/organize/plans/{new_plan_id}")
                new_actions = new_detail.json()["actions"]
            # Only succeed actions are rollbacked
            for na in new_actions:
                self.assertEqual(
                    "succeeded",
                    self._original_action_status(plan_id, na["reason"]),
                )

    # ── Group C: Blocked conditions ───────────────────────────────────

    def test_target_missing_blocked(self) -> None:
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
                # Add a clean rollbackable move so we get 200 with blocked info
                self._add_clean_rollbackable_move(plan_id, managed)
                # Delete the original moved file target (blocking the executed action)
                for a in client.get(f"/library/organize/plans/{plan_id}").json()["actions"]:
                    if a["action_type"] == "move" and a.get("reason") is None:
                        Path(a["target_path"]).unlink(missing_ok=True)
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertGreater(data["blocked_actions_count"], 0)
            self.assertTrue(
                any("Original target missing" in ba["reason"] for ba in data["blocked_actions"]))

    def test_source_still_exists_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                # Execute normally (file gets moved)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, plan_id)
                # Add a clean rollbackable move so we get 200
                self._add_clean_rollbackable_move(plan_id, managed)
                # Add a blocked move where source still exists
                self._add_move_where_source_still_exists(plan_id, managed)
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertGreater(data["blocked_actions_count"], 0)
            self.assertTrue(
                any("Original source still exists" in ba["reason"] for ba in data["blocked_actions"]),
                f"Blocked actions: {data['blocked_actions']}",
            )

    def test_rollback_target_already_exists_blocked(self) -> None:
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
                # Add a clean rollbackable move so we get 200
                self._add_clean_rollbackable_move(plan_id, managed)
                # Re-create the source file so rollback target already exists (blocks the executed move)
                video.write_bytes(b"blocker")
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertGreater(data["blocked_actions_count"], 0)
            self.assertTrue(
                any("Original source still exists" in ba["reason"] for ba in data["blocked_actions"]),
                f"Blocked actions: {data['blocked_actions']}",
            )

    def test_no_rollbackable_actions_400(self) -> None:
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
                # Delete all moved files so everything is blocked
                detail = client.get(f"/library/organize/plans/{plan_id}")
                for a in detail.json()["actions"]:
                    if a["action_type"] == "move" and a["target_path"]:
                        Path(a["target_path"]).unlink(missing_ok=True)
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            self.assertEqual(400, resp.status_code)
            self.assertIn("No rollbackable", resp.json()["detail"])

    def test_rename_cross_directory_blocked(self) -> None:
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
                # Add a clean rollbackable move so we get 200
                self._add_clean_rollbackable_move(plan_id, managed)
                # Add a rename with cross-directory paths (blocked)
                self._add_cross_dir_rename_action(plan_id)
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertGreater(data["blocked_actions_count"], 0)
            self.assertTrue(
                any("same parent" in ba["reason"] for ba in data["blocked_actions"]),
                f"Blocked actions: {data['blocked_actions']}",
            )

    # ── Group D: New plan properties ──────────────────────────────────

    def test_rollback_plan_status_is_draft(self) -> None:
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
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            new_plan_id = resp.json()["rollback_plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{new_plan_id}")
            self.assertEqual("draft", detail.json()["plan"]["status"])

    def test_rollback_plan_lineage_fields(self) -> None:
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
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            new_plan_id = resp.json()["rollback_plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{new_plan_id}")
            plan = detail.json()["plan"]
            self.assertEqual(plan_id, plan["parent_plan_id"])
            self.assertEqual("rollback", plan["plan_origin"])
            self.assertIsNone(plan["target_library_root_id"])

    def test_rollback_actions_reset_fields(self) -> None:
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
                resp = client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
            new_plan_id = resp.json()["rollback_plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{new_plan_id}")
            for a in detail.json()["actions"]:
                self.assertEqual("draft", a["status"])
                self.assertIsNone(a["error_message"])
                self.assertIsNone(a["before_path"])
                self.assertIsNone(a["after_path"])
                self.assertIsNone(a["executed_at"])
                self.assertIsNone(a["finished_at"])
                self.assertEqual("not_checked", a["reconcile_status"])

    # ── Group E: Safety ───────────────────────────────────────────────

    def test_source_plan_unchanged(self) -> None:
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
                before = client.get(f"/library/organize/plans/{plan_id}")
                before_plan = before.json()["plan"]
                before_actions = before.json()["actions"]
                client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
                after = client.get(f"/library/organize/plans/{plan_id}")
                after_plan = after.json()["plan"]
                after_actions = after.json()["actions"]
            self.assertEqual(before_plan["status"], after_plan["status"])
            self.assertEqual(before_plan["title"], after_plan["title"])
            self.assertEqual(len(before_actions), len(after_actions))
            for ba, aa in zip(before_actions, after_actions):
                self.assertEqual(ba["status"], aa["status"])

    def test_generate_does_not_modify_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_root, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"])
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, plan_id)
                before_files = set()
                for root, dirs, files in Path(temp_dir).walk():
                    for f in files:
                        before_files.add(str(Path(root) / f))
                client.post(f"/library/organize/plans/{plan_id}/generate-rollback")
                after_files = set()
                for root, dirs, files in Path(temp_dir).walk():
                    for f in files:
                        after_files.add(str(Path(root) / f))
            self.assertEqual(before_files, after_files,
                             "generate-rollback must not modify the filesystem")

    # ── Helper methods ────────────────────────────────────────────────

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

    def _set_action_statuses(self, plan_id: int, statuses: set[str]) -> None:
        status_list = list(statuses)
        with SessionLocal() as session:
            actions = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).order_by(OrganizeAction.action_order).all()
            for i, action in enumerate(actions):
                action.status = status_list[i % len(status_list)]
            session.commit()

    def _set_one_action_to_failed(self, plan_id: int) -> None:
        with SessionLocal() as session:
            action = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id,
                OrganizeAction.action_type == "move",
            ).order_by(OrganizeAction.action_order).first()
            if action:
                action.status = "failed"
            session.commit()

    def _update_plan_status(self, plan_id: int, status: str) -> None:
        with SessionLocal() as session:
            plan = session.get(OrganizePlan, plan_id)
            if plan:
                plan.status = status
            session.commit()

    def _add_clean_rollbackable_move(self, plan_id: int, managed_dir: Path) -> None:
        """Add a succeeded move action where rollback preconditions pass."""
        now = _dt()
        src = managed_dir / "clean_source.mkv"
        tgt = managed_dir / "clean_target.mkv"
        tgt.parent.mkdir(parents=True, exist_ok=True)
        tgt.write_bytes(b"clean")
        with SessionLocal() as session:
            max_order = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).count()
            action = OrganizeAction(
                plan_id=plan_id,
                action_order=max_order + 1,
                action_type="move",
                source_path=str(src),
                target_path=str(tgt),
                status="succeeded",
                conflict_status="ok",
                reconcile_status="not_checked",
                created_at=now,
                updated_at=now,
            )
            session.add(action)
            session.commit()

    def _add_move_where_source_still_exists(self, plan_id: int, managed_dir: Path) -> None:
        """Add a succeeded move where the original source still exists (should be blocked)."""
        now = _dt()
        src = managed_dir / "still_exists_source.mkv"
        tgt = managed_dir / "still_exists_target.mkv"
        tgt.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(b"source_still_here")
        tgt.write_bytes(b"target_exists_too")
        with SessionLocal() as session:
            max_order = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).count()
            action = OrganizeAction(
                plan_id=plan_id,
                action_order=max_order + 1,
                action_type="move",
                source_path=str(src),
                target_path=str(tgt),
                status="succeeded",
                conflict_status="ok",
                reconcile_status="not_checked",
                created_at=now,
                updated_at=now,
            )
            session.add(action)
            session.commit()

    def _add_same_dir_rename_action(self, plan_id: int, managed_dir: Path) -> None:
        """Add a valid same-dir rename (target exists, source doesn't)."""
        now = _dt()
        src = managed_dir / "rename_from.mkv"
        tgt = managed_dir / "rename_to.mkv"
        tgt.parent.mkdir(parents=True, exist_ok=True)
        tgt.write_bytes(b"renamed")
        # Source must NOT exist (it was renamed away)
        src.unlink(missing_ok=True)
        with SessionLocal() as session:
            max_order = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).count()
            action = OrganizeAction(
                plan_id=plan_id,
                action_order=max_order + 1,
                action_type="rename",
                source_path=str(src),
                target_path=str(tgt),
                status="succeeded",
                conflict_status="ok",
                reconcile_status="not_checked",
                created_at=now,
                updated_at=now,
            )
            session.add(action)
            session.commit()

    def _add_cross_dir_rename_action(self, plan_id: int) -> None:
        """Add a rename action with different parent dirs (should be blocked)."""
        now = _dt()
        with SessionLocal() as session:
            max_order = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).count()
            action = OrganizeAction(
                plan_id=plan_id,
                action_order=max_order + 1,
                action_type="rename",
                source_path="/dir_a/from.mkv",
                target_path="/dir_b/to.mkv",
                status="succeeded",
                conflict_status="ok",
                reconcile_status="not_checked",
                created_at=now,
                updated_at=now,
            )
            session.add(action)
            session.commit()

    def _add_succeeded_mkdir_action(self, plan_id: int, managed_dir: Path) -> None:
        now = _dt()
        with SessionLocal() as session:
            max_order = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).count()
            action = OrganizeAction(
                plan_id=plan_id,
                action_order=max_order + 1,
                action_type="mkdir",
                target_path=str(managed_dir / "some_created_dir"),
                status="succeeded",
                conflict_status="ok",
                reconcile_status="not_checked",
                created_at=now,
                updated_at=now,
            )
            session.add(action)
            session.commit()

    def _add_succeeded_asset_yaml_action(self, plan_id: int, managed_dir: Path) -> None:
        now = _dt()
        yaml_path = managed_dir / "asset.yaml"
        yaml_path.write_text("schema_version: 1", encoding="utf-8")
        with SessionLocal() as session:
            max_order = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).count()
            action = OrganizeAction(
                plan_id=plan_id,
                action_order=max_order + 1,
                action_type="write_asset_yaml",
                target_path=str(yaml_path),
                status="succeeded",
                conflict_status="ok",
                reconcile_status="not_checked",
                created_at=now,
                updated_at=now,
            )
            session.add(action)
            session.commit()

    def _add_non_succeeded_move_actions(self, plan_id: int, managed_dir: Path) -> None:
        now = _dt()
        statuses = ["failed", "blocked", "skipped"]
        with SessionLocal() as session:
            base_order = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).count()
            for i, status in enumerate(statuses):
                action = OrganizeAction(
                    plan_id=plan_id,
                    action_order=base_order + i + 1,
                    action_type="move",
                    source_path=str(managed_dir / f"src_{status}.mkv"),
                    target_path=str(managed_dir / f"tgt_{status}.mkv"),
                    status=status,
                    conflict_status="ok",
                    reconcile_status="not_checked",
                    created_at=now,
                    updated_at=now,
                )
                session.add(action)
            session.commit()

    def _original_action_status(self, plan_id: int, reason: str) -> str:
        import re
        match = re.search(r"#(\d+)", reason)
        if not match:
            return "unknown"
        action_id = int(match.group(1))
        with SessionLocal() as session:
            action = session.get(OrganizeAction, action_id)
            return action.status if action else "unknown"
