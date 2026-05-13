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
from app.db.models.organize import OrganizeAction, OrganizeCandidate, OrganizePlan
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 1, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryPhase5DAssetYamlMergeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    # ── Group A: Allowed/rejected ─────────────────────────────────────

    def test_generates_merge_draft_from_blocked_write_asset_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, plan_id = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertEqual(plan_id, data["source_plan_id"])
            self.assertEqual(action_id, data["source_action_id"])
            self.assertGreater(data["merge_plan_id"], 0)
            self.assertGreater(data["backup_action_id"], 0)
            self.assertGreater(data["update_action_id"], 0)
            self.assertEqual("asset_yaml_merge", data["plan_origin"])
            self.assertGreater(len(data["field_diff"]), 0)

    def test_rejects_non_write_asset_yaml_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, plan_id = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            with SessionLocal() as session:
                actions = session.query(OrganizeAction).filter(
                    OrganizeAction.plan_id == plan_id,
                    OrganizeAction.action_type != "write_asset_yaml",
                ).all()
            self.assertGreater(len(actions), 0)
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{actions[0].id}/generate-asset-yaml-merge"
                )
            self.assertEqual(400, resp.status_code)

    def test_rejects_target_not_asset_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "src"
            source.mkdir()
            managed = Path(temp_dir) / "managed"
            managed.mkdir()
            self._seed_source(source)
            root_id = self._seed_library_root(managed)
            now = _dt()
            with SessionLocal() as session:
                candidate = OrganizeCandidate(
                    candidate_type="file",
                    source_kind="source",
                    source_path=str(source),
                    display_name="test",
                    detected_type="movie",
                    confidence="high",
                    reason="test",
                    status="added_to_plan",
                    created_at=now,
                    updated_at=now,
                )
                session.add(candidate)
                session.flush()
                plan = OrganizePlan(
                    title="test",
                    status="draft",
                    plan_kind="organize_inbox",
                    target_library_root_id=root_id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(plan)
                session.flush()
                action = OrganizeAction(
                    plan_id=plan.id,
                    action_order=1,
                    action_type="write_asset_yaml",
                    source_path=None,
                    target_path=str(managed / "wrong_name.yaml"),
                    payload_json=json.dumps({"title": "Test"}),
                    status="draft",
                    conflict_status="unchecked",
                    created_at=now,
                    updated_at=now,
                )
                session.add(action)
                session.commit()
                action_id = action.id
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            self.assertEqual(400, resp.status_code)

    def test_rejects_target_asset_yaml_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "src"
            source.mkdir()
            managed = Path(temp_dir) / "managed"
            managed.mkdir()
            self._seed_source(source)
            now = _dt()
            with SessionLocal() as session:
                candidate = OrganizeCandidate(
                    candidate_type="file",
                    source_kind="source",
                    source_path=str(source),
                    display_name="test",
                    detected_type="movie",
                    confidence="high",
                    reason="test",
                    status="added_to_plan",
                    created_at=now,
                    updated_at=now,
                )
                session.add(candidate)
                session.flush()
                plan = OrganizePlan(
                    title="test",
                    status="draft",
                    plan_kind="organize_inbox",
                    target_library_root_id=None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(plan)
                session.flush()
                target = managed / "subdir" / "asset.yaml"
                action = OrganizeAction(
                    plan_id=plan.id,
                    action_order=1,
                    action_type="write_asset_yaml",
                    source_path=None,
                    target_path=str(target),
                    payload_json=json.dumps({"title": "Test", "type": "movie", "schema_version": 1}),
                    status="draft",
                    conflict_status="unchecked",
                    created_at=now,
                    updated_at=now,
                )
                session.add(action)
                session.commit()
                action_id = action.id
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            self.assertEqual(400, resp.status_code)

    def test_action_not_found_404(self) -> None:
        with TestClient(app) as client:
            resp = client.post("/library/organize/actions/99999/generate-asset-yaml-merge")
        self.assertEqual(404, resp.status_code)

    # ── Group B: Merge plan properties ────────────────────────────────

    def test_merge_plan_status_is_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, plan_id = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            merge_id = resp.json()["merge_plan_id"]
            with TestClient(app) as client:
                detail = client.get(f"/library/organize/plans/{merge_id}")
            self.assertEqual("draft", detail.json()["plan"]["status"])

    def test_merge_plan_lineage_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, plan_id = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            merge_id = resp.json()["merge_plan_id"]
            with TestClient(app) as client:
                detail = client.get(f"/library/organize/plans/{merge_id}")
            plan = detail.json()["plan"]
            self.assertEqual(plan_id, plan["parent_plan_id"])
            self.assertEqual("asset_yaml_merge", plan["plan_origin"])

    def test_creates_backup_before_update_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, plan_id = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            merge_id = resp.json()["merge_plan_id"]
            with TestClient(app) as client:
                detail = client.get(f"/library/organize/plans/{merge_id}")
            actions = detail.json()["actions"]
            self.assertEqual(2, len(actions))
            self.assertEqual("backup_asset_yaml", actions[0]["action_type"])
            self.assertEqual(1, actions[0]["action_order"])
            self.assertEqual("write_asset_yaml_update", actions[1]["action_type"])
            self.assertEqual(2, actions[1]["action_order"])

    # ── Group C: Field diff ───────────────────────────────────────────

    def test_field_diff_marks_safe_additions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, _ = self._create_blocked_write_asset_yaml_with_file(
                temp_dir,
                current_yaml={"schema_version": 1, "type": "movie", "title": "Old"},
                proposed_payload={"schema_version": 1, "type": "movie", "title": "Old",
                                  "aliases": ["new_alias"], "tags": ["action"]},
            )
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            field_diff = resp.json()["field_diff"]
            aliases_diff = next(d for d in field_diff if d["field"] == "aliases")
            self.assertEqual("added", aliases_diff["status"])
            tags_diff = next(d for d in field_diff if d["field"] == "tags")
            self.assertEqual("added", tags_diff["status"])

    def test_field_diff_marks_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, _ = self._create_blocked_write_asset_yaml_with_file(
                temp_dir,
                current_yaml={"schema_version": 1, "type": "movie", "title": "Old Title", "year": 2020},
                proposed_payload={"schema_version": 1, "type": "movie", "title": "New Title", "year": 2021},
            )
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            field_diff = resp.json()["field_diff"]
            title_diff = next(d for d in field_diff if d["field"] == "title")
            self.assertEqual("conflict", title_diff["status"])
            self.assertEqual("Old Title", title_diff["merged"])
            year_diff = next(d for d in field_diff if d["field"] == "year")
            self.assertEqual("conflict", year_diff["status"])
            self.assertEqual("2020", year_diff["merged"])

    def test_field_diff_marks_never_modify(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, _ = self._create_blocked_write_asset_yaml_with_file(
                temp_dir,
                current_yaml={"schema_version": 1, "type": "movie", "title": "Test"},
                proposed_payload={"schema_version": 2, "type": "game", "title": "Test"},
            )
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            field_diff = resp.json()["field_diff"]
            sv_diff = next(d for d in field_diff if d["field"] == "schema_version")
            self.assertEqual("kept_current", sv_diff["status"])
            self.assertEqual("1", sv_diff["merged"])
            type_diff = next(d for d in field_diff if d["field"] == "type")
            self.assertEqual("kept_current", type_diff["status"])
            self.assertEqual("movie", type_diff["merged"])

    # ── Group D: Safety ───────────────────────────────────────────────

    def test_source_plan_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, plan_id = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            with TestClient(app) as client:
                before = client.get(f"/library/organize/plans/{plan_id}")
                before_plan = before.json()["plan"]
                before_actions = before.json()["actions"]
                client.post(f"/library/organize/actions/{action_id}/generate-asset-yaml-merge")
                after = client.get(f"/library/organize/plans/{plan_id}")
                after_plan = after.json()["plan"]
                after_actions = after.json()["actions"]
            self.assertEqual(before_plan["status"], after_plan["status"])
            self.assertEqual(before_plan["title"], after_plan["title"])
            self.assertEqual(len(before_actions), len(after_actions))
            for ba, aa in zip(before_actions, after_actions):
                self.assertEqual(ba["status"], aa["status"])

    def test_source_action_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, plan_id = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            with TestClient(app) as client:
                before = client.get(f"/library/organize/plans/{plan_id}")
                before_action = next(a for a in before.json()["actions"] if a["id"] == action_id)
                client.post(f"/library/organize/actions/{action_id}/generate-asset-yaml-merge")
                after = client.get(f"/library/organize/plans/{plan_id}")
                after_action = next(a for a in after.json()["actions"] if a["id"] == action_id)
            self.assertEqual(before_action["status"], after_action["status"])
            self.assertEqual(before_action["conflict_status"], after_action["conflict_status"])

    def test_generate_does_not_modify_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, _ = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            before_files = set()
            for root, dirs, files in Path(temp_dir).walk():
                for f in files:
                    before_files.add(str(Path(root) / f))
            with TestClient(app) as client:
                client.post(f"/library/organize/actions/{action_id}/generate-asset-yaml-merge")
            after_files = set()
            for root, dirs, files in Path(temp_dir).walk():
                for f in files:
                    after_files.add(str(Path(root) / f))
            self.assertEqual(before_files, after_files,
                             "generate-asset-yaml-merge must not modify the filesystem")

    # ── Group E: Preflight ────────────────────────────────────────────

    def test_preflight_backup_blocks_if_backup_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, _ = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            merge_id = resp.json()["merge_plan_id"]
            # Mark ready first (no conflicts yet)
            with TestClient(app) as client:
                client.post(f"/library/organize/plans/{merge_id}/mark-ready")
            # Then create a file at the backup target path to create a conflict
            with TestClient(app) as client:
                detail = client.get(f"/library/organize/plans/{merge_id}")
            backup_action = detail.json()["actions"][0]
            backup_target = json.loads(backup_action["payload_json"])["backup_path"]
            Path(backup_target).parent.mkdir(parents=True, exist_ok=True)
            Path(backup_target).write_text("blocker", encoding="utf-8")
            # Preflight should now detect the backup conflict
            with TestClient(app) as client:
                pf = client.post(f"/library/organize/plans/{merge_id}/preflight")
            blocked_found = any(
                msg == "Backup target path already exists."
                for msg in pf.json()["messages"]
            )
            self.assertTrue(blocked_found, "Backup should be blocked when target exists")

    def test_preflight_update_requires_backup_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, _ = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            merge_id = resp.json()["merge_plan_id"]
            # Remove the backup action to test the dependency
            with SessionLocal() as session:
                backup_action = session.query(OrganizeAction).filter(
                    OrganizeAction.plan_id == merge_id,
                    OrganizeAction.action_type == "backup_asset_yaml",
                ).first()
                if backup_action:
                    session.delete(backup_action)
                    session.commit()
            with TestClient(app) as client:
                client.post(f"/library/organize/plans/{merge_id}/mark-ready")
                pf = client.post(f"/library/organize/plans/{merge_id}/preflight")
            blocked_found = any(
                "preceding backup_asset_yaml" in msg
                for msg in pf.json()["messages"]
            )
            self.assertTrue(blocked_found, "Update should be blocked without preceding backup")

    # ── Group F: Execute ──────────────────────────────────────────────

    def test_execute_backup_creates_backup_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, _ = self._create_blocked_write_asset_yaml_with_file(temp_dir)
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            merge_id = resp.json()["merge_plan_id"]
            backup_action_id = resp.json()["backup_action_id"]
            with TestClient(app) as client:
                client.post(f"/library/organize/plans/{merge_id}/mark-ready")
                pf = client.post(f"/library/organize/plans/{merge_id}/preflight")
            self.assertTrue(pf.json()["can_execute"],
                            f"Preflight should pass for merge plan: {pf.json()['messages']}")
            with TestClient(app) as client:
                client.post(f"/library/organize/plans/{merge_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, merge_id)
            # Verify backup file was created
            with SessionLocal() as session:
                action = session.get(OrganizeAction, backup_action_id)
                self.assertEqual("succeeded", action.status)
                self.assertIsNotNone(action.after_path)
                self.assertTrue(Path(action.after_path).exists())

    def test_execute_update_writes_merged_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            action_id, _ = self._create_blocked_write_asset_yaml_with_file(
                temp_dir,
                current_yaml={"schema_version": 1, "type": "movie", "title": "Old"},
                proposed_payload={"schema_version": 1, "type": "movie", "title": "Old",
                                  "aliases": ["merged_alias"]},
            )
            with TestClient(app) as client:
                resp = client.post(
                    f"/library/organize/actions/{action_id}/generate-asset-yaml-merge"
                )
            merge_id = resp.json()["merge_plan_id"]
            update_action_id = resp.json()["update_action_id"]
            with TestClient(app) as client:
                client.post(f"/library/organize/plans/{merge_id}/mark-ready")
                pf = client.post(f"/library/organize/plans/{merge_id}/preflight")
            self.assertTrue(pf.json()["can_execute"],
                            f"Preflight should pass: {pf.json()['messages']}")
            with TestClient(app) as client:
                client.post(f"/library/organize/plans/{merge_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, merge_id)
            # Verify update succeeded
            with SessionLocal() as session:
                action = session.get(OrganizeAction, update_action_id)
                self.assertEqual("succeeded", action.status)
                self.assertIsNotNone(action.after_path)
            # Verify merged content in asset.yaml
            import yaml
            with TestClient(app) as client:
                update_detail = client.get(f"/library/organize/plans/{merge_id}")
            update_target = update_detail.json()["actions"][1]["target_path"]
            merged_content = yaml.safe_load(Path(update_target).read_text(encoding="utf-8"))
            self.assertIn("merged_alias", merged_content.get("aliases", []))

    # ── Helper methods ────────────────────────────────────────────────

    def _create_blocked_write_asset_yaml_with_file(
        self, temp_dir: str,
        current_yaml: dict | None = None,
        proposed_payload: dict | None = None,
    ) -> tuple[int, int]:
        """Create a write_asset_yaml action blocked by an existing asset.yaml.

        Returns (action_id, plan_id).
        """
        source_root = Path(temp_dir) / "source_root"
        inbox = source_root / "00_Inbox" / "_to_sort"
        video = inbox / "Inception.2010.1080p.mkv"
        video.parent.mkdir(parents=True)
        video.write_bytes(b"video_content_for_test")
        self._seed_source(source_root)
        self._seed_file(video, "video")

        managed = Path(temp_dir) / "managed_lib"
        managed.mkdir()
        root_id = self._seed_library_root(managed)

        with TestClient(app) as client:
            client.post("/library/organize/candidates/scan")
            candidates = client.get("/library/organize/candidates")
            cid = candidates.json()["items"][0]["id"]
            gen = client.post("/library/organize/plans/generate",
                              json={"candidate_ids": [cid], "target_library_root_id": root_id})
            plan_id = gen.json()["plan_id"]

        # Find the write_asset_yaml action
        with SessionLocal() as session:
            action = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id,
                OrganizeAction.action_type == "write_asset_yaml",
            ).first()
            self.assertIsNotNone(action, "Plan must have a write_asset_yaml action")
            action_id = action.id

            # Override payload if provided
            if proposed_payload is not None:
                action.payload_json = json.dumps(proposed_payload)
                session.commit()

            # Create the asset.yaml on disk to block the action
            target_dir = Path(action.target_path).parent
            target_dir.mkdir(parents=True, exist_ok=True)
            yaml_content = current_yaml or {"schema_version": 1, "type": "movie", "title": "Existing"}
            import yaml
            target_path = Path(action.target_path)
            target_path.write_text(
                yaml.safe_dump(yaml_content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

            # Refresh conflicts to set the action as blocked/warning
            action.conflict_status = "blocked"
            action.conflict_message = "Target metadata file exists; this remains a draft preview only."
            session.commit()

        return action_id, plan_id

    # ── Shared helpers (reused from Phase 5C) ─────────────────────────

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
            source = session.query(Source).filter(
                Source.path == str(self._source_root_for(path))
            ).one()
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
