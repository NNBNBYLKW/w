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


class LibraryPhase5BCopyFailedActionsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    # ── Group A: Allowed/rejected ─────────────────────────────────────

    def test_copy_from_completed_with_errors(self) -> None:
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
                # Set one action to failed and plan to completed_with_errors
                self._set_action_statuses(plan_id, {"failed"})
                self._update_plan_status(plan_id, "completed_with_errors")
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertEqual(plan_id, data["source_plan_id"])
            self.assertGreater(data["copied_actions_count"], 0)
            self.assertEqual("copied_failed_actions", data["plan_origin"])
            new_plan_id = data["new_plan_id"]
            # Verify new plan exists and is draft
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{new_plan_id}")
                self.assertEqual(200, detail.status_code)
                self.assertEqual("draft", detail.json()["plan"]["status"])

    def test_copy_from_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                # Set all actions to failed and plan to failed (simulate failed execution)
                self._set_action_statuses(plan_id, {"failed"})
                self._update_plan_status(plan_id, "failed")
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertEqual(plan_id, data["source_plan_id"])
            self.assertGreater(data["copied_actions_count"], 0)

    def test_copy_completed_no_failed_400(self) -> None:
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
                # All actions succeeded, plan is completed — no failed/blocked/skipped
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            self.assertEqual(400, resp.status_code)
            self.assertIn("No failed", resp.json()["detail"])

    def test_copy_draft_rejected_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [cid]})
                plan_id = gen.json()["plan_id"]
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            self.assertEqual(400, resp.status_code)
            self.assertIn("completed", resp.json()["detail"])

    def test_copy_ready_rejected_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            self.assertEqual(400, resp.status_code)
            self.assertIn("completed", resp.json()["detail"])

    def test_copy_plan_not_found_404(self) -> None:
        with TestClient(app) as client:
            resp = client.post("/library/organize/plans/99999/copy-failed-actions")
        self.assertEqual(404, resp.status_code)

    # ── Group B: Action selection ─────────────────────────────────────

    def test_only_failed_blocked_skipped_copied(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                # Mix: set some to failed, some blocked, one skipped
                self._set_mixed_action_statuses(plan_id, {"failed", "blocked", "skipped"})
                self._update_plan_status(plan_id, "completed_with_errors")
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            new_plan_id = data["new_plan_id"]
            self.assertGreater(data["copied_actions_count"], 0)
            # Verify new plan only has draft actions
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{new_plan_id}")
                for a in detail.json()["actions"]:
                    self.assertEqual("draft", a["status"])

    def test_succeeded_not_copied(self) -> None:
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
                # Set exactly one action to failed, rest stay succeeded
                self._set_one_action_to_failed(plan_id)
                self._update_plan_status(plan_id, "completed_with_errors")
                # Count succeeded actions in source
                source_detail = client.get(f"/library/organize/plans/{plan_id}")
                succeeded_count = sum(
                    1 for a in source_detail.json()["actions"] if a["status"] == "succeeded"
                )
                self.assertGreater(succeeded_count, 0, "Need at least one succeeded action")
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            data = resp.json()
            new_plan_id = data["new_plan_id"]
            # Verify new plan action count < source action count
            with TestClient(app) as client2:
                new_detail = client2.get(f"/library/organize/plans/{new_plan_id}")
                self.assertLess(
                    len(new_detail.json()["actions"]),
                    len(source_detail.json()["actions"]),
                )

    def test_copy_keeps_action_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                # Set all to failed
                self._set_action_statuses(plan_id, {"failed"})
                self._update_plan_status(plan_id, "failed")
                source_detail = client.get(f"/library/organize/plans/{plan_id}")
                source_actions = source_detail.json()["actions"]
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            data = resp.json()
            new_plan_id = data["new_plan_id"]
            with TestClient(app) as client2:
                new_detail = client2.get(f"/library/organize/plans/{new_plan_id}")
                new_actions = new_detail.json()["actions"]
            self.assertEqual(len(source_actions), len(new_actions))
            for sa, na in zip(source_actions, new_actions):
                self.assertEqual(sa["action_type"], na["action_type"])
                self.assertEqual(sa["source_path"], na["source_path"])
                self.assertEqual(sa["target_path"], na["target_path"])
                self.assertEqual(sa["payload_json"], na["payload_json"])

    # ── Group C: New plan properties ──────────────────────────────────

    def test_new_plan_status_is_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                self._set_action_statuses(plan_id, {"failed"})
                self._update_plan_status(plan_id, "failed")
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            new_plan_id = resp.json()["new_plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{new_plan_id}")
            self.assertEqual("draft", detail.json()["plan"]["status"])

    def test_new_plan_parent_and_origin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                self._set_action_statuses(plan_id, {"failed"})
                self._update_plan_status(plan_id, "failed")
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            new_plan_id = resp.json()["new_plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{new_plan_id}")
            plan = detail.json()["plan"]
            self.assertEqual(plan_id, plan["parent_plan_id"])
            self.assertEqual("copied_failed_actions", plan["plan_origin"])

    def test_new_plan_keeps_target_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                self._set_action_statuses(plan_id, {"failed"})
                self._update_plan_status(plan_id, "failed")
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            new_plan_id = resp.json()["new_plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{new_plan_id}")
            self.assertEqual(root_id, detail.json()["plan"]["target_library_root_id"])

    def test_copied_actions_reset_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                self._set_action_statuses(plan_id, {"failed"})
                self._update_plan_status(plan_id, "failed")
                # Set error_message, before_path, after_path, executed_at on source actions
                self._set_action_execution_fields(plan_id)
                resp = client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
            new_plan_id = resp.json()["new_plan_id"]
            with TestClient(app) as client2:
                detail = client2.get(f"/library/organize/plans/{new_plan_id}")
            for a in detail.json()["actions"]:
                self.assertEqual("draft", a["status"])
                self.assertEqual("ok", a["conflict_status"],
                                 f"Action {a['id']} conflict_status should be ok after _refresh_plan_conflicts")
                self.assertIsNone(a["error_message"],
                                  f"Action {a['id']} error_message should be None")
                self.assertIsNone(a["before_path"])
                self.assertIsNone(a["after_path"])
                self.assertIsNone(a["executed_at"])
                self.assertIsNone(a["finished_at"])
                self.assertEqual("not_checked", a["reconcile_status"])

    # ── Group D: Safety ───────────────────────────────────────────────

    def test_source_plan_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                self._set_action_statuses(plan_id, {"failed"})
                self._update_plan_status(plan_id, "failed")
                before = client.get(f"/library/organize/plans/{plan_id}")
                before_plan = before.json()["plan"]
                before_actions = before.json()["actions"]
                client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
                after = client.get(f"/library/organize/plans/{plan_id}")
                after_plan = after.json()["plan"]
                after_actions = after.json()["actions"]
            self.assertEqual(before_plan["status"], after_plan["status"])
            self.assertEqual(before_plan["title"], after_plan["title"])
            self.assertEqual(len(before_actions), len(after_actions))
            for ba, aa in zip(before_actions, after_actions):
                self.assertEqual(ba["status"], aa["status"])
                self.assertEqual(ba["error_message"], aa["error_message"])

    def test_copy_does_not_modify_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_root, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                self._set_action_statuses(plan_id, {"failed"})
                self._update_plan_status(plan_id, "failed")
                # Snapshot filesystem state
                before_files = set()
                for root, dirs, files in Path(temp_dir).walk():
                    for f in files:
                        before_files.add(str(Path(root) / f))
                client.post(f"/library/organize/plans/{plan_id}/copy-failed-actions")
                after_files = set()
                for root, dirs, files in Path(temp_dir).walk():
                    for f in files:
                        after_files.add(str(Path(root) / f))
            self.assertEqual(before_files, after_files,
                             "copy-failed-actions must not modify the filesystem")

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
        with SessionLocal() as session:
            actions = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).order_by(OrganizeAction.action_order).all()
            for i, action in enumerate(actions):
                action.status = list(statuses)[i % len(statuses)]
            session.commit()

    def _set_mixed_action_statuses(self, plan_id: int, statuses: set[str]) -> None:
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
                OrganizeAction.plan_id == plan_id
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

    def _set_action_execution_fields(self, plan_id: int) -> None:
        now = _dt()
        with SessionLocal() as session:
            for action in session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).all():
                action.error_message = "Simulated error"
                action.before_path = "/some/before/path"
                action.after_path = "/some/after/path"
                action.executed_at = now
                action.finished_at = now
            session.commit()
