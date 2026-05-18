"""Phase 8D-A1 tests: object member soft status field."""

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_object import LibraryObject, LibraryObjectMember
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class ObjectMemberStatusTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset()
        self._ensure_managed_source()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.managed_dir = self.tmp / "managed"
        self.managed_dir.mkdir()
        self.client = TestClient(app)
        self.root_id = self._seed_root()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()
        self._reset()
        engine.dispose()

    def _reset(self) -> None:
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

    def _seed_managed_file(self, name: str) -> int:
        p = self.managed_dir / name
        p.write_bytes(b"data")
        with SessionLocal() as session:
            f = File(
                source_id=1, path=str(p), parent_path=str(self.managed_dir),
                name=p.name, stem=p.stem, extension=name.split(".")[-1] if "." in name else "",
                file_type="image", file_kind="image", auto_placement="media",
                storage_state="managed", managed_root_id=self.root_id, managed_at=_dt(),
                size_bytes=100, discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
            )
            session.add(f)
            session.commit()
            return f.id

    # ── Tests ─────────────────────────────────────────

    def test_managed_compose_execute_creates_active_members(self):
        fids = [self._seed_managed_file(f"st_a_{i}.jpg") for i in range(2)]
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": fids, "object_name": "StatusTest",
            "object_type": "imgset", "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        pid = resp.json()["plan_id"]
        self.client.post(f"/library/organize/plans/{pid}/mark-ready")
        pre = self.client.post(f"/library/organize/plans/{pid}/preflight")
        assert pre.json()["can_execute"]
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            members = s.query(LibraryObjectMember).all()
            assert len(members) == 2
            for m in members:
                assert m.member_status == "active", f"Member {m.id} should be active"

    def test_browse_excludes_active_members_from_loose(self):
        fids = [self._seed_managed_file(f"hide_{i}.jpg") for i in range(2)]
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": fids, "object_name": "HideTest",
            "object_type": "imgset", "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        pid = resp.json()["plan_id"]
        self.client.post(f"/library/organize/plans/{pid}/mark-ready")
        self.client.post(f"/library/organize/plans/{pid}/preflight")
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        br = self.client.get("/library/browse?domain=media")
        assert br.status_code == 200
        data = br.json()
        loose = [i for i in data["items"] if i["card_kind"] == "loose_file"]
        loose_ids = {i["file_id"] for i in loose}
        for fid in fids:
            assert fid not in loose_ids

    def test_object_detail_counts_active_members(self):
        fids = [self._seed_managed_file(f"cnt_{i}.jpg") for i in range(2)]
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": fids, "object_name": "CountTest",
            "object_type": "imgset", "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        pid = resp.json()["plan_id"]
        self.client.post(f"/library/organize/plans/{pid}/mark-ready")
        self.client.post(f"/library/organize/plans/{pid}/preflight")
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            lo = s.query(LibraryObject).first()
            assert lo is not None
        resp = self.client.get("/library/browse/object-detail", params={
            "object_source": "library_object", "source_id": lo.id,
        })
        assert resp.status_code == 200
        assert resp.json()["member_count"] == 2
