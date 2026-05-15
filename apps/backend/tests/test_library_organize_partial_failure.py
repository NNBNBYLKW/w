import json
import tempfile
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_object import LibraryObject
from app.db.models.library_root import LibraryRoot
from app.db.models.organize import OrganizeAction
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app
from app.services.library.organize import LibraryOrganizeService


def _dt() -> datetime:
    return datetime(2026, 5, 1, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryOrganizePartialFailureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    # ── Helpers ────────────────────────────────────────────────────────

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
            source = session.query(Source).one()
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
    ) -> int:
        now = _dt()
        with SessionLocal() as session:
            root = LibraryRoot(
                root_path=str(path.resolve()),
                display_name=display_name or path.name,
                root_kind="managed",
                is_enabled=is_enabled,
                is_default=True,
                scan_policy="manual",
                created_at=now,
                updated_at=now,
            )
            session.add(root)
            session.commit()
            return root.id

    def _scan_and_get_candidates(self, client: TestClient) -> list[dict]:
        client.post("/library/organize/candidates/scan")
        return client.get("/library/organize/candidates?page_size=50").json()["items"]

    def _wait_for_plan(self, client: TestClient, plan_id: int, timeout: float = 10.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            resp = client.get(f"/library/organize/plans/{plan_id}")
            data = resp.json()
            status = data["plan"]["status"]
            if status in {"completed", "completed_with_errors", "failed", "cancelled"}:
                return data
            time.sleep(0.2)
        return client.get(f"/library/organize/plans/{plan_id}").json()

    def _generate_and_mark_ready(self, client: TestClient, candidate_ids: list[int], root_id: int) -> int:
        gen = client.post("/library/organize/plans/generate", json={
            "candidate_ids": candidate_ids,
            "target_library_root_id": root_id,
        })
        plan_id = gen.json()["plan_id"]
        client.post(f"/library/organize/plans/{plan_id}/mark-ready")
        return plan_id

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM organize_plan_candidates"))
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

    # ── Unit tests: _check_dependency_failure ───────────────────────────

    def _mk_action(self, **kwargs) -> OrganizeAction:
        defaults = {
            "id": 1,
            "plan_id": 1,
            "action_order": 1,
            "action_type": "mkdir",
            "source_path": None,
            "target_path": None,
            "payload_json": None,
            "status": "ready",
            "conflict_status": "ok",
            "conflict_message": None,
            "reason": None,
            "before_path": None,
            "after_path": None,
            "executed_at": None,
            "finished_at": None,
            "error_message": None,
            "reconcile_status": "not_checked",
            "created_at": _dt(),
            "updated_at": _dt(),
        }
        defaults.update(kwargs)
        return OrganizeAction(**defaults)

    def test_check_dependency_mkdir_block_descendants(self) -> None:
        svc = LibraryOrganizeService()
        failed_mkdir = self._mk_action(
            action_type="mkdir",
            target_path="/lib/Movies/[MOVIE] A (2020)",
        )
        move_into = self._mk_action(
            action_type="move",
            target_path="/lib/Movies/[MOVIE] A (2020)/A.mkv",
        )
        yaml_into = self._mk_action(
            action_type="write_asset_yaml",
            target_path="/lib/Movies/[MOVIE] A (2020)/asset.yaml",
        )

        self.assertEqual(
            (True, "Failed dependency: mkdir '/lib/Movies/[MOVIE] A (2020)' failed, blocking descendant action."),
            svc._check_dependency_failure(move_into, [failed_mkdir]),
        )
        self.assertEqual(
            (True, "Failed dependency: mkdir '/lib/Movies/[MOVIE] A (2020)' failed, blocking descendant action."),
            svc._check_dependency_failure(yaml_into, [failed_mkdir]),
        )

    def test_check_dependency_mkdir_unrelated_not_skipped(self) -> None:
        svc = LibraryOrganizeService()
        failed_mkdir = self._mk_action(
            action_type="mkdir",
            target_path="/lib/Movies/[MOVIE] A (2020)",
        )
        unrelated_move = self._mk_action(
            action_type="move",
            target_path="/lib/Games/[GAME] B/B.exe",
        )
        unrelated_mkdir = self._mk_action(
            action_type="mkdir",
            target_path="/lib/Games/[GAME] B",
        )

        self.assertEqual((False, None), svc._check_dependency_failure(unrelated_move, [failed_mkdir]))
        self.assertEqual((False, None), svc._check_dependency_failure(unrelated_mkdir, [failed_mkdir]))

    def test_check_dependency_move_failure_blocks_same_dir_yaml(self) -> None:
        svc = LibraryOrganizeService()
        failed_move = self._mk_action(
            action_type="move",
            source_path="/src/Inbox/A.mkv",
            target_path="/lib/Movies/[MOVIE] A (2020)/A.mkv",
        )
        same_dir_yaml = self._mk_action(
            action_type="write_asset_yaml",
            target_path="/lib/Movies/[MOVIE] A (2020)/asset.yaml",
        )
        different_dir_yaml = self._mk_action(
            action_type="write_asset_yaml",
            target_path="/lib/Games/[GAME] B/asset.yaml",
        )
        different_dir_move = self._mk_action(
            action_type="move",
            target_path="/lib/Games/[GAME] B/B.exe",
        )

        self.assertEqual(
            (True, f"Failed dependency: move to '{failed_move.target_path}' failed, cannot write asset.yaml in the same directory."),
            svc._check_dependency_failure(same_dir_yaml, [failed_move]),
        )
        self.assertEqual((False, None), svc._check_dependency_failure(different_dir_yaml, [failed_move]))
        self.assertEqual((False, None), svc._check_dependency_failure(different_dir_move, [failed_move]))

    def test_check_dependency_write_asset_yaml_failure_isolated(self) -> None:
        svc = LibraryOrganizeService()
        failed_yaml = self._mk_action(
            action_type="write_asset_yaml",
            target_path="/lib/Movies/[MOVIE] A (2020)/asset.yaml",
        )
        unrelated_move = self._mk_action(
            action_type="move",
            target_path="/lib/Movies/[MOVIE] B/B.mkv",
        )
        unrelated_yaml = self._mk_action(
            action_type="write_asset_yaml",
            target_path="/lib/Movies/[MOVIE] B/asset.yaml",
        )

        self.assertEqual((False, None), svc._check_dependency_failure(unrelated_move, [failed_yaml]))
        self.assertEqual((False, None), svc._check_dependency_failure(unrelated_yaml, [failed_yaml]))

    def test_check_dependency_empty_failed_list(self) -> None:
        svc = LibraryOrganizeService()
        action = self._mk_action(action_type="move", target_path="/lib/X/x.mkv")
        self.assertEqual((False, None), svc._check_dependency_failure(action, []))

    # ── Integration test: write_asset_yaml failure does not skip unrelated moves ──

    def test_write_asset_yaml_failure_does_not_skip_unrelated_moves(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source"
            managed = Path(temp_dir) / "managed"
            managed.mkdir()

            # Candidate A: movie file
            inbox_dir = source / "00_Inbox" / "_to_sort"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            a_file = inbox_dir / "Movie.A.2020.1080p.mkv"
            a_file.write_bytes(b"a")

            # Candidate B: game file
            b_file = inbox_dir / "Game.B.exe"
            b_file.write_bytes(b"b")

            # Candidate C: another movie
            c_file = inbox_dir / "Movie.C.2021.1080p.mkv"
            c_file.write_bytes(b"c")

            self._seed_source(source)
            self._seed_file(a_file, "video")
            self._seed_file(b_file, "game")
            self._seed_file(c_file, "video")
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                candidates = self._scan_and_get_candidates(client)
                candidate_ids = [c["id"] for c in candidates]
                plan_id = self._generate_and_mark_ready(client, candidate_ids, root_id)

                # Preflight must pass
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"], f"Preflight not clean: {pf.json()}")

            # Find which action is write_asset_yaml for candidate A
            with SessionLocal() as session:
                actions = sorted(
                    session.query(OrganizeAction).filter(OrganizeAction.plan_id == plan_id).all(),
                    key=lambda a: a.action_order,
                )
                a_yaml_action = next(
                    (a for a in actions
                     if a.action_type == "write_asset_yaml"
                     and a.target_path and "Movie A" in a.target_path),
                    None,
                )
                self.assertIsNotNone(a_yaml_action, "Could not find write_asset_yaml action for Movie A")
                a_yaml_id = a_yaml_action.id

            # Execute with patched _execute_action to fail only for candidate A's yaml
            original_execute = LibraryOrganizeService._execute_action

            def failing_execute(self, s, action):
                if action.id == a_yaml_id:
                    raise RuntimeError("Simulated write_asset_yaml failure for test.")
                return original_execute(self, s, action)

            with patch.object(LibraryOrganizeService, "_execute_action", failing_execute):
                with TestClient(app) as client:
                    exe = client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                    self.assertEqual(200, exe.status_code)
                    detail = self._wait_for_plan(client, plan_id)

            self.assertEqual("completed_with_errors", detail["plan"]["status"])

            # Count actions by status
            actions_by_status = {"succeeded": 0, "failed": 0, "skipped": 0}
            for action in detail["actions"]:
                actions_by_status[action["status"]] = actions_by_status.get(action["status"], 0) + 1

            # 1 failed = A's yaml.  0 skipped.  8 succeeded (9 actions total - 1 failed)
            self.assertEqual(1, actions_by_status["failed"],
                             f"Expected exactly 1 failed action, got: {actions_by_status}")
            self.assertEqual(0, actions_by_status.get("skipped", 0),
                             f"Expected 0 skipped actions (no global stop), got: {actions_by_status}")
            self.assertGreaterEqual(actions_by_status["succeeded"], 6,
                                    f"Expected most actions to succeed, got: {actions_by_status}")

            # Verify B and C's actions all succeeded (neither skipped nor failed)
            b_actions = [a for a in detail["actions"] if a["target_path"] and "Game B" in a["target_path"]]
            c_actions = [a for a in detail["actions"] if a["target_path"] and "Movie C" in a["target_path"]]
            for a in b_actions + c_actions:
                self.assertEqual("succeeded", a["status"],
                                 f"Unrelated action should have succeeded: {a['action_type']} → {a['target_path']} (status={a['status']})")

    # ── Integration test: mkdir failure only skips descendant actions ──

    def test_mkdir_failure_skips_only_descendant_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source"
            managed = Path(temp_dir) / "managed"
            managed.mkdir()

            inbox_dir = source / "00_Inbox" / "_to_sort"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            a_file = inbox_dir / "A.2020.mkv"
            a_file.write_bytes(b"a")
            b_file = inbox_dir / "B.2020.exe"
            b_file.write_bytes(b"b")

            self._seed_source(source)
            self._seed_file(a_file, "video")
            self._seed_file(b_file, "game")
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                candidates = self._scan_and_get_candidates(client)
                candidate_ids = [c["id"] for c in candidates]
                plan_id = self._generate_and_mark_ready(client, candidate_ids, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"], f"Preflight not clean: {pf.json()}")

            # Find mkdir action for candidate A
            with SessionLocal() as session:
                actions = sorted(
                    session.query(OrganizeAction).filter(OrganizeAction.plan_id == plan_id).all(),
                    key=lambda a: a.action_order,
                )
                a_mkdir = next(
                    (a for a in actions
                     if a.action_type == "mkdir"
                     and a.target_path and "A" in a.target_path and "B" not in a.target_path),
                    None,
                )
                self.assertIsNotNone(a_mkdir, "Could not find mkdir action for A")
                a_mkdir_id = a_mkdir.id

            original_execute = LibraryOrganizeService._execute_action

            def failing_mkdir(self, s, action):
                if action.id == a_mkdir_id:
                    raise RuntimeError("Simulated mkdir failure for test.")
                return original_execute(self, s, action)

            with patch.object(LibraryOrganizeService, "_execute_action", failing_mkdir):
                with TestClient(app) as client:
                    exe = client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                    self.assertEqual(200, exe.status_code)
                    detail = self._wait_for_plan(client, plan_id)

            self.assertEqual("completed_with_errors", detail["plan"]["status"])

            actions_by_status = {"succeeded": 0, "failed": 0, "skipped": 0}
            for action in detail["actions"]:
                actions_by_status[action["status"]] = actions_by_status.get(action["status"], 0) + 1

            # 1 failed = A's mkdir.  A's move + yaml should be skipped (dependency).
            # B's actions should all succeed.
            self.assertEqual(1, actions_by_status["failed"])
            self.assertEqual(2, actions_by_status.get("skipped", 0),
                             f"Expected 2 skipped (A's move + yaml), got: {actions_by_status}")

            # All B actions must succeed
            b_actions = [a for a in detail["actions"] if a["target_path"] and "B" in a["target_path"]]
            for a in b_actions:
                self.assertEqual("succeeded", a["status"],
                                 f"B's action should succeed: {a['action_type']} (status={a['status']})")


if __name__ == "__main__":
    unittest.main()
