"""Phase 8C-4A tests: managed compose creation plan (draft only)."""

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_root import LibraryRoot
from app.db.models.organize import OrganizePlan, OrganizeAction
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class ManagedComposePlanTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.managed_dir = self.tmp / "managed"
        self.managed_dir.mkdir()
        self.client = TestClient(app)
        self.root_id = self._seed_root()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()
        self._reset_database()
        engine.dispose()

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            for tbl in [
                "import_object_members", "import_object_candidates",
                "file_path_history", "operation_journal", "inbox_items", "import_batches",
                "organize_plan_candidates", "organize_suggestions", "organize_action_logs",
                "organize_actions", "organize_plans", "organize_candidates",
                "asset_metadata_cache", "library_object_members", "library_objects",
                "tool_runs", "tasks", "file_metadata", "file_tags", "file_user_meta",
                "collections", "files", "source_ignore_rules", "tags",
                "library_roots", "sources",
            ]:
                session.execute(text(f"DELETE FROM {tbl}"))
            session.commit()

    def _ensure_managed_source(self) -> None:
        with SessionLocal() as session:
            if session.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none() is None:
                session.add(Source(
                    path="__workbench_managed_import__", display_name="Managed Import",
                    is_enabled=True, scan_mode="manual", last_scan_status="not_applicable",
                    created_at=_dt(), updated_at=_dt(),
                ))
                session.commit()

    def _seed_root(self) -> int:
        with SessionLocal() as session:
            root = LibraryRoot(
                root_path=str(self.managed_dir.resolve()), display_name="Test Root",
                root_kind="managed", is_enabled=True, is_default=True,
                scan_policy="manual", created_at=_dt(), updated_at=_dt(),
            )
            session.add(root)
            session.commit()
            return root.id

    def _seed_managed_files(self, count: int = 3) -> list[int]:
        ids: list[int] = []
        with SessionLocal() as session:
            for i in range(count):
                ext = "mp4" if i < 2 else "jpg"
                fname = f"managed{i+1}.{ext}"
                fpath = self.managed_dir / fname
                fpath.write_bytes(b"fake managed")
                f = File(
                    source_id=1, path=str(fpath), parent_path=str(self.managed_dir),
                    name=fname, stem=f"managed{i+1}", extension=ext,
                    file_type="video" if ext == "mp4" else "image",
                    file_kind="video" if ext == "mp4" else "image",
                    auto_placement="media", storage_state="managed",
                    managed_root_id=self.root_id, managed_at=_dt(),
                    size_bytes=100, discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
                )
                session.add(f)
                session.flush()
                ids.append(f.id)
            session.commit()
        return ids

    # ── Tests ─────────────────────────────────────────

    def test_creates_draft_plan(self):
        fids = self._seed_managed_files(3)
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": fids, "object_name": "My Object",
            "object_type": "video_collection",
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        d = resp.json()
        assert d["plan_id"] > 0
        assert d["status"] == "draft"
        assert d["plan_kind"] == "object_creation_managed_compose"
        assert d["actions_count"] == 4  # 1 mkdir + 3 moves

    def test_returns_planned_members(self):
        fids = self._seed_managed_files(2)
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": fids, "object_name": "Pics",
            "object_type": "imgset",
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        d = resp.json()
        assert len(d["planned_members"]) == 2
        for m in d["planned_members"]:
            assert "file_id" in m
            assert "role" in m

    def test_rejects_empty(self):
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": [], "object_name": "X", "object_type": "imgset",
        })
        assert resp.status_code == 422

    def test_rejects_non_managed(self):
        fids = self._seed_managed_files(1)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fids[0]).first()
            f.storage_state = "external"
            s.commit()
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": fids, "object_name": "X", "object_type": "imgset",
        })
        assert resp.status_code == 400

    def test_does_not_execute(self):
        fids = self._seed_managed_files(2)
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": fids, "object_name": "NoExec",
            "object_type": "imgset",
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        d = resp.json()
        with SessionLocal() as s:
            plan = s.query(OrganizePlan).filter(OrganizePlan.id == d["plan_id"]).first()
            assert plan.status == "draft"
            assert plan.executed_at is None
            actions = s.query(OrganizeAction).filter(OrganizeAction.plan_id == plan.id).all()
            for a in actions:
                assert a.status == "draft"
                assert a.before_path is None
                assert a.after_path is None

    def test_target_dir_includes_prefix(self):
        fids = self._seed_managed_files(1)
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": fids, "object_name": "My Movie",
            "object_type": "movie",
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        d = resp.json()
        assert "[MOVIE]" in d["target_object_dir"]
        assert "My Movie" in d["target_object_dir"]

    def test_actions_have_move_with_payload(self):
        fids = self._seed_managed_files(1)
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": fids, "object_name": "Single",
            "object_type": "imgset",
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        d = resp.json()
        with SessionLocal() as s:
            actions = s.query(OrganizeAction).filter(OrganizeAction.plan_id == d["plan_id"]).all()
            types = {a.action_type for a in actions}
            assert "mkdir" in types
            assert "move" in types
            move_actions = [a for a in actions if a.action_type == "move"]
            assert len(move_actions) == 1
            assert move_actions[0].payload_json is not None
            assert "file_id" in move_actions[0].payload_json

    def test_rejects_invalid_object_type(self):
        fids = self._seed_managed_files(1)
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": fids, "object_name": "X", "object_type": "nonexistent",
        })
        assert resp.status_code == 400
