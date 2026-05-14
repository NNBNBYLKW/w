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


class LibraryRootsAndCrossSourceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    # ── Group A: Library Root CRUD ────────────────────────────────────

    def test_create_root_returns_201(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "managed_lib"
            lib.mkdir()
            with TestClient(app) as client:
                resp = client.post("/library/roots", json={
                    "root_path": str(lib),
                    "display_name": "My Library",
                })
            self.assertEqual(201, resp.status_code)
            data = resp.json()
            self.assertEqual(str(lib), data["root_path"])
            self.assertEqual("My Library", data["display_name"])
            self.assertEqual("managed", data["root_kind"])
            self.assertTrue(data["is_enabled"])
            self.assertFalse(data["is_default"])

    def test_list_roots_returns_all(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_a = Path(temp_dir) / "lib_a"
            lib_b = Path(temp_dir) / "lib_b"
            lib_a.mkdir()
            lib_b.mkdir()
            self._seed_library_root(lib_a, display_name="A")
            self._seed_library_root(lib_b, display_name="B")
            with TestClient(app) as client:
                resp = client.get("/library/roots")
            self.assertEqual(200, resp.status_code)
            items = resp.json()["items"]
            self.assertEqual(2, len(items))

    def test_get_root_by_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "lib"
            lib.mkdir()
            root_id = self._seed_library_root(lib, display_name="Test")
            with TestClient(app) as client:
                resp = client.get(f"/library/roots/{root_id}")
            self.assertEqual(200, resp.status_code)
            self.assertEqual(str(lib), resp.json()["root_path"])

    def test_get_root_nonexistent_404(self) -> None:
        with TestClient(app) as client:
            resp = client.get("/library/roots/99999")
        self.assertEqual(404, resp.status_code)

    def test_update_root_display_name_and_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "lib"
            lib.mkdir()
            root_id = self._seed_library_root(lib, display_name="Original")
            with TestClient(app) as client:
                resp = client.patch(f"/library/roots/{root_id}", json={
                    "display_name": "Renamed",
                    "is_enabled": False,
                    "scan_policy": "full",
                })
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertEqual("Renamed", data["display_name"])
            self.assertFalse(data["is_enabled"])
            self.assertEqual("full", data["scan_policy"])

    def test_update_root_nonexistent_404(self) -> None:
        with TestClient(app) as client:
            resp = client.patch("/library/roots/99999", json={"display_name": "X"})
        self.assertEqual(404, resp.status_code)

    # ── Group B: Default Root Logic ───────────────────────────────────

    def test_set_default_clears_old_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_a = Path(temp_dir) / "lib_a"
            lib_b = Path(temp_dir) / "lib_b"
            lib_a.mkdir()
            lib_b.mkdir()
            id_a = self._seed_library_root(lib_a, is_default=True)
            id_b = self._seed_library_root(lib_b, is_default=False)
            with TestClient(app) as client:
                resp = client.post(f"/library/roots/{id_b}/set-default")
            self.assertEqual(200, resp.status_code)
            self.assertTrue(resp.json()["is_default"])
            # Verify old default cleared
            with SessionLocal() as session:
                a = session.get(LibraryRoot, id_a)
                self.assertFalse(a.is_default)

    def test_set_default_on_disabled_root_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "lib"
            lib.mkdir()
            root_id = self._seed_library_root(lib, is_enabled=False)
            with TestClient(app) as client:
                resp = client.post(f"/library/roots/{root_id}/set-default")
            self.assertEqual(400, resp.status_code)

    def test_get_default_zero_roots_none(self) -> None:
        from app.repositories.library_roots.repository import LibraryRootRepository
        repo = LibraryRootRepository()
        with SessionLocal() as session:
            result = repo.get_default(session)
        self.assertIsNone(result)

    def test_get_default_single_root_auto(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "only"
            lib.mkdir()
            self._seed_library_root(lib)
            from app.repositories.library_roots.repository import LibraryRootRepository
            repo = LibraryRootRepository()
            with SessionLocal() as session:
                result = repo.get_default(session)
            self.assertIsNotNone(result)
            self.assertEqual(str(lib), result.root_path)

    # ── Group C: Duplicate and Overlap ────────────────────────────────

    def test_create_duplicate_path_409(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "lib"
            lib.mkdir()
            self._seed_library_root(lib)
            with TestClient(app) as client:
                resp = client.post("/library/roots", json={"root_path": str(lib)})
            self.assertEqual(409, resp.status_code)

    def test_create_parent_of_existing_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / "parent"
            child = parent / "child"
            child.mkdir(parents=True)
            self._seed_library_root(child)
            with TestClient(app) as client:
                resp = client.post("/library/roots", json={"root_path": str(parent)})
            self.assertEqual(400, resp.status_code)

    def test_create_child_of_existing_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / "parent"
            child = parent / "child"
            parent.mkdir()
            child.mkdir()
            self._seed_library_root(parent)
            with TestClient(app) as client:
                resp = client.post("/library/roots", json={"root_path": str(child)})
            self.assertEqual(400, resp.status_code)

    # ── Group D: generate_plan with target_library_root_id ────────────

    def _setup_source_with_inbox_file(self, temp_dir: str) -> tuple[Path, Path, Path]:
        """Create source + inbox file on disk, seed DB. Returns (source, managed_lib, video)."""
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

    def test_generate_with_target_anchors_to_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [cid],
                    "target_library_root_id": root_id,
                })
                detail = client.get(f"/library/organize/plans/{gen.json()['plan_id']}")

            self.assertEqual(200, detail.status_code)
            managed_str = str(managed.resolve())
            for action in detail.json()["actions"]:
                if action["target_path"]:
                    self.assertTrue(
                        action["target_path"].startswith(managed_str),
                        f"Expected target {action['target_path']} to start with {managed_str}",
                    )
            # File not moved during generate
            self.assertTrue(video.exists())

    def test_generate_saves_target_library_root_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [cid],
                    "target_library_root_id": root_id,
                })
                detail = client.get(f"/library/organize/plans/{gen.json()['plan_id']}")

            self.assertEqual(root_id, detail.json()["plan"]["target_library_root_id"])

    def test_generate_response_has_target_root_info(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [cid],
                    "target_library_root_id": root_id,
                })

            resp = gen.json()
            self.assertEqual(root_id, resp["target_library_root_id"])
            self.assertIsNotNone(resp["target_root_path"])
            self.assertTrue(resp["target_root_path"].startswith(str(managed.resolve())))

    def test_generate_with_disabled_root_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed, is_enabled=False)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                resp = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [cid],
                    "target_library_root_id": root_id,
                })

            self.assertEqual(400, resp.status_code)

    def test_generate_with_nonexistent_root_404(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                resp = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [cid],
                    "target_library_root_id": 99999,
                })
            self.assertEqual(404, resp.status_code)

    # ── Group E: generate_plan auto-select ────────────────────────────

    def test_generate_no_roots_fallback_source_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            # No library roots created

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [cid],
                })
                detail = client.get(f"/library/organize/plans/{gen.json()['plan_id']}")

            self.assertIsNone(detail.json()["plan"]["target_library_root_id"])
            self.assertIsNone(gen.json()["target_library_root_id"])
            # Targets should be anchored to source root
            source_str = str(source.resolve())
            for action in detail.json()["actions"]:
                if action["target_path"]:
                    self.assertTrue(
                        action["target_path"].startswith(source_str),
                        f"Expected target {action['target_path']} to start with source {source_str}",
                    )

    def test_generate_one_root_auto_selects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [cid],
                })

            self.assertEqual(root_id, gen.json()["target_library_root_id"])
            managed_str = str(managed.resolve())
            self.assertTrue(gen.json()["target_root_path"].startswith(managed_str))

    def test_generate_multi_with_default_auto_selects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            other = Path(temp_dir) / "other_lib"
            other.mkdir()
            self._seed_library_root(other, is_default=False)
            default_id = self._seed_library_root(managed, is_default=True)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [cid],
                })

            self.assertEqual(default_id, gen.json()["target_library_root_id"])

    def test_generate_multi_no_default_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            other = Path(temp_dir) / "other_lib"
            other.mkdir()
            self._seed_library_root(managed, is_default=False)
            self._seed_library_root(other, is_default=False)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                resp = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [cid],
                })

            self.assertEqual(400, resp.status_code)
            self.assertIn("Multiple library roots exist", resp.json()["detail"])

    # ── Group F: Preflight ────────────────────────────────────────────

    def _generate_and_mark_ready(self, client: TestClient, cid: int, root_id: int | None = None) -> int:
        payload: dict = {"candidate_ids": [cid]}
        if root_id is not None:
            payload["target_library_root_id"] = root_id
        gen = client.post("/library/organize/plans/generate", json=payload)
        plan_id = gen.json()["plan_id"]
        client.post(f"/library/organize/plans/{plan_id}/mark-ready")
        return plan_id

    def test_preflight_target_inside_root_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")

            self.assertEqual(200, pf.status_code)
            self.assertTrue(pf.json()["can_execute"])

    def test_preflight_target_outside_root_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [cid],
                    "target_library_root_id": root_id,
                })
                plan_id = gen.json()["plan_id"]
                detail = client.get(f"/library/organize/plans/{plan_id}")
                move_action = next(
                    (a for a in detail.json()["actions"] if a["action_type"] == "move"),
                    None,
                )
                self.assertIsNotNone(move_action, "Expected a move action in the plan")
                outside_target = str(Path(temp_dir) / "outside" / "evil.mkv")
                patch_resp = client.patch(f"/library/organize/actions/{move_action['id']}", json={
                    "target_path": outside_target,
                })
                self.assertEqual(200, patch_resp.status_code,
                                 f"PATCH action failed: {patch_resp.text}")
                mr = client.post(f"/library/organize/plans/{plan_id}/mark-ready")
                self.assertEqual(400, mr.status_code,
                                 f"Expected mark-ready to reject outside-root target: {mr.text}")
                self.assertIn("blocked", mr.text.lower())

    def test_preflight_legacy_same_source_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            # No library roots

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")

            self.assertEqual(200, pf.status_code)
            self.assertTrue(pf.json()["can_execute"])

    def test_preflight_legacy_cross_source_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_a = Path(temp_dir) / "source_a"
            source_b = Path(temp_dir) / "source_b"
            video = source_a / "00_Inbox" / "_to_sort" / "movie.mp4"
            video.parent.mkdir(parents=True)
            video.write_bytes(b"video")
            source_b.mkdir(parents=True, exist_ok=True)
            self._seed_source(source_a)
            self._seed_source(source_b)
            self._seed_file(video, "video")

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [cid]})
                plan_id = gen.json()["plan_id"]
                # Patch move action target into source_b
                detail = client.get(f"/library/organize/plans/{plan_id}")
                move_action = next(
                    (a for a in detail.json()["actions"] if a["action_type"] == "move"),
                    None,
                )
                self.assertIsNotNone(move_action, "Expected a move action")
                cross_target = str(source_b / "movie.mkv")
                client.patch(f"/library/organize/actions/{move_action['id']}", json={
                    "target_path": cross_target,
                })
                client.post(f"/library/organize/plans/{plan_id}/mark-ready")
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")

            self.assertFalse(pf.json()["can_execute"])
            self.assertGreater(pf.json()["blocked_count"], 0)

    def test_preflight_disabled_root_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                # Disable the root after plan creation
                client.patch(f"/library/roots/{root_id}", json={"is_enabled": False})
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")

            self.assertFalse(pf.json()["can_execute"])
            self.assertGreater(pf.json()["blocked_count"], 0)

    # ── Group G: Execute ─────────────────────────────────────────────

    def _wait_for_plan(self, client: TestClient, plan_id: int, timeout: float = 6.0) -> dict:
        """Poll plan detail until the plan reaches a terminal status."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            resp = client.get(f"/library/organize/plans/{plan_id}")
            data = resp.json()
            status = data["plan"]["status"]
            if status in {"completed", "completed_with_errors", "failed", "cancelled"}:
                return data
            time.sleep(0.2)
        return client.get(f"/library/organize/plans/{plan_id}").json()

    def test_execute_cross_root_move_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                # Preflight before execute
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"], f"Preflight not ready: {pf.json()}")
                # Execute
                exe = client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self.assertEqual(200, exe.status_code)
                # Poll for completion
                detail = self._wait_for_plan(client, plan_id)

            self.assertIn(detail["plan"]["status"], {"completed", "completed_with_errors"})
            # File should have moved from source to managed root
            self.assertFalse(video.exists(), f"Source file {video} should have been moved")
            # Check file exists somewhere under managed root
            moved_files = list(managed.rglob("*"))
            moved = [f for f in moved_files if f.is_file()]
            self.assertGreater(len(moved), 0, f"No files found under {managed}")

    def test_execute_affected_ids_in_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"], f"Preflight not ready: {pf.json()}")
                exe = client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self.assertEqual(200, exe.status_code)
                # ExecutePlanResponse has affected IDs at top level
                self.assertIn("affected_source_ids", exe.json())
                self.assertIn("affected_library_root_ids", exe.json())
                # Poll and check execution_summary_json on plan detail
                detail = self._wait_for_plan(client, plan_id)
                summary_json = detail["plan"].get("execution_summary_json")
                if summary_json:
                    summary = json.loads(summary_json)
                    self.assertIn("affected_source_ids", summary)
                    self.assertIn("affected_library_root_ids", summary)

    def test_execute_blocked_by_disabled_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                plan_id = self._generate_and_mark_ready(client, cid, root_id)
                # Disable root
                client.patch(f"/library/roots/{root_id}", json={"is_enabled": False})
                # Execute should fail because preflight blocks
                exe = client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})

            self.assertEqual(400, exe.status_code)

    # ── Group H: Safety ───────────────────────────────────────────────

    def test_path_traversal_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [cid]})
                plan_id = gen.json()["plan_id"]
                detail = client.get(f"/library/organize/plans/{plan_id}")
                move_action = next(
                    (a for a in detail.json()["actions"] if a["action_type"] == "move"),
                    None,
                )
                self.assertIsNotNone(move_action, "Expected a move action")
                traversal = "../../../Windows/System32/evil.exe"
                patch_resp = client.patch(f"/library/organize/actions/{move_action['id']}", json={
                    "target_path": traversal,
                })
                self.assertEqual(200, patch_resp.status_code,
                                 f"PATCH action failed: {patch_resp.text}")
                mr = client.post(f"/library/organize/plans/{plan_id}/mark-ready")
                self.assertEqual(400, mr.status_code,
                                 f"Expected mark-ready to reject traversal: {mr.text}")
                self.assertIn("blocked", mr.text.lower())

    def test_target_exists_blocked_in_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [cid]})
                plan_id = gen.json()["plan_id"]
                detail = client.get(f"/library/organize/plans/{plan_id}")
                move_action = next(
                    (a for a in detail.json()["actions"] if a["action_type"] == "move"),
                    None,
                )
                self.assertIsNotNone(move_action, "Expected a move action")
                # Create a conflicting file at the target path
                target = Path(move_action["target_path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"existing")
                mr = client.post(f"/library/organize/plans/{plan_id}/mark-ready")
                self.assertEqual(400, mr.status_code,
                                 f"Expected mark-ready to reject existing target: {mr.text}")
                self.assertIn("blocked", mr.text.lower())

    def test_asset_yaml_create_only_no_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [cid]})
                plan_id = gen.json()["plan_id"]
                detail = client.get(f"/library/organize/plans/{plan_id}")
                yaml_action = next(
                    (a for a in detail.json()["actions"] if a["action_type"] == "write_asset_yaml"),
                    None,
                )
                self.assertIsNotNone(yaml_action, "Expected a write_asset_yaml action")
                # Create asset.yaml at the target path
                target = Path(yaml_action["target_path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("existing: true")
                client.post(f"/library/organize/plans/{plan_id}/mark-ready")
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")

            self.assertFalse(pf.json()["can_execute"])
            self.assertGreater(pf.json()["blocked_count"], 0)

    def test_rename_must_stay_same_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, managed, video = self._setup_source_with_inbox_file(temp_dir)
            with TestClient(app) as client:
                cid = self._scan_and_get_first_candidate(client)
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [cid]})
                plan_id = gen.json()["plan_id"]
                detail = client.get(f"/library/organize/plans/{plan_id}")
                move_action = next(
                    (a for a in detail.json()["actions"] if a["action_type"] == "move"),
                    None,
                )
                self.assertIsNotNone(move_action, "Expected a move action")
                # Change to rename with target in a different parent
                different_parent = str(Path(move_action["target_path"]).parent.parent / "renamed.mkv")
                client.patch(f"/library/organize/actions/{move_action['id']}", json={
                    "action_type": "rename",
                    "target_path": different_parent,
                })
                client.post(f"/library/organize/plans/{plan_id}/mark-ready")
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")

            self.assertFalse(pf.json()["can_execute"])
            self.assertGreater(pf.json()["blocked_count"], 0)

    # ── Group I: System Path Exclusion (H1) ───────────────────────────

    def test_create_root_rejects_drive_root(self) -> None:
        import sys
        if sys.platform != "win32":
            self.skipTest("Windows-specific test")
        with TestClient(app) as client:
            resp = client.post("/library/roots", json={"root_path": "C:\\"})
        self.assertEqual(400, resp.status_code)

    def test_create_root_rejects_windows_system_dir(self) -> None:
        import os
        import sys
        if sys.platform != "win32":
            self.skipTest("Windows-specific test")
        windir = os.environ.get("SystemRoot", "C:\\Windows")
        with TestClient(app) as client:
            resp = client.post("/library/roots", json={"root_path": windir})
        self.assertEqual(400, resp.status_code)

    def test_create_root_rejects_program_files(self) -> None:
        import os
        import sys
        if sys.platform != "win32":
            self.skipTest("Windows-specific test")
        pf = os.environ.get("ProgramFiles", "C:\\Program Files")
        with TestClient(app) as client:
            resp = client.post("/library/roots", json={"root_path": pf})
        self.assertEqual(400, resp.status_code)

    def test_create_root_rejects_backend_base_dir(self) -> None:
        from app.core.config.settings import settings
        with TestClient(app) as client:
            resp = client.post("/library/roots", json={"root_path": str(settings.base_dir)})
        self.assertEqual(400, resp.status_code)

    def test_create_root_rejects_backend_data_dir(self) -> None:
        from app.core.config.settings import settings
        with TestClient(app) as client:
            resp = client.post("/library/roots", json={"root_path": str(settings.data_dir)})
        self.assertEqual(400, resp.status_code)

    def test_create_root_rejects_node_modules_in_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            nm = Path(temp_dir) / "project" / "node_modules" / "somepkg"
            nm.mkdir(parents=True)
            with TestClient(app) as client:
                resp = client.post("/library/roots", json={"root_path": str(nm)})
            self.assertEqual(400, resp.status_code)

    def test_create_root_rejects_dotgit_in_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gitdir = Path(temp_dir) / "repo" / ".git" / "objects"
            gitdir.mkdir(parents=True)
            with TestClient(app) as client:
                resp = client.post("/library/roots", json={"root_path": str(gitdir)})
            self.assertEqual(400, resp.status_code)

    def test_create_root_rejects_dotgit_subpath(self) -> None:
        r"""D:\Repo\.git\objects should be rejected (not just leaf name)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            git_objects = repo / ".git" / "objects"
            git_objects.mkdir(parents=True)
            with TestClient(app) as client:
                resp = client.post("/library/roots", json={"root_path": str(git_objects)})
            self.assertEqual(400, resp.status_code)

    def test_create_root_accepts_normal_user_temp_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "my_media_library"
            lib.mkdir()
            with TestClient(app) as client:
                resp = client.post("/library/roots", json={"root_path": str(lib)})
            self.assertEqual(201, resp.status_code)

    def test_enable_disabled_unsafe_existing_root_rejected(self) -> None:
        from app.core.config.settings import settings
        # Create a root with a temp path first (so it exists), then modify its
        # root_path in DB to point to an unsafe location (simulating pre-H1 root).
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "normal_lib"
            lib.mkdir()
            root_id = self._seed_library_root(lib, is_enabled=False)
            # Manually change root_path to unsafe path in DB
            with SessionLocal() as session:
                root = session.get(LibraryRoot, root_id)
                root.root_path = str(settings.base_dir)
                session.commit()
            with TestClient(app) as client:
                resp = client.patch(f"/library/roots/{root_id}", json={"is_enabled": True})
            self.assertEqual(400, resp.status_code)

    def test_set_default_existing_enabled_unsafe_root_rejected(self) -> None:
        from app.core.config.settings import settings
        # Simulate a pre-H1 enabled unsafe root in the DB.
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "normal_lib"
            lib.mkdir()
            root_id = self._seed_library_root(lib, is_enabled=True)
            with SessionLocal() as session:
                root = session.get(LibraryRoot, root_id)
                root.root_path = str(settings.base_dir)
                session.commit()
            with TestClient(app) as client:
                resp = client.post(f"/library/roots/{root_id}/set-default")
            self.assertEqual(400, resp.status_code)

    def test_disable_root_always_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "disable_test_lib"
            lib.mkdir()
            root_id = self._seed_library_root(lib, is_enabled=True)
            with TestClient(app) as client:
                resp = client.patch(f"/library/roots/{root_id}", json={"is_enabled": False})
            self.assertEqual(200, resp.status_code)
            self.assertFalse(resp.json()["is_enabled"])

    def test_create_duplicate_still_rejected_after_h1(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lib = Path(temp_dir) / "dup_test"
            lib.mkdir()
            self._seed_library_root(lib)
            with TestClient(app) as client:
                resp = client.post("/library/roots", json={"root_path": str(lib)})
            self.assertEqual(409, resp.status_code)

    def test_create_overlap_still_rejected_after_h1(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / "parent_overlap"
            child = parent / "child"
            child.mkdir(parents=True)
            self._seed_library_root(child)
            with TestClient(app) as client:
                resp = client.post("/library/roots", json={"root_path": str(parent)})
            self.assertEqual(400, resp.status_code)

    # ── Seed Helpers ──────────────────────────────────────────────────

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
