"""Phase 8C-4C tests: execute + finalize managed compose object creation plans."""

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


class ManagedComposeExecuteTestCase(unittest.TestCase):
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

    def _create_managed_file(self, name: str) -> int:
        p = self.managed_dir / name
        p.write_bytes(b"managed file")
        ext = p.suffix.lstrip(".") if p.suffix else ""
        kind = "image" if ext in ("jpg", "png") else "video"
        with SessionLocal() as session:
            f = File(
                source_id=1, path=str(p), parent_path=str(self.managed_dir),
                name=p.name, stem=p.stem, extension=ext,
                file_type=kind, file_kind=kind, auto_placement="media",
                storage_state="managed", managed_root_id=self.root_id, managed_at=_dt(),
                size_bytes=100, discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
            )
            session.add(f)
            session.commit()
            return f.id

    def _create_and_preflight_plan(self, file_ids: list[int], obj_name="TestObj", obj_type="imgset") -> int:
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": file_ids, "object_name": obj_name,
            "object_type": obj_type, "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        pid = resp.json()["plan_id"]
        self.client.post(f"/library/organize/plans/{pid}/mark-ready")
        pre = self.client.post(f"/library/organize/plans/{pid}/preflight")
        assert pre.json()["can_execute"]
        return pid

    # ── Tests ─────────────────────────────────────────

    def test_execute_moves_files(self):
        fids = [self._create_managed_file(f"mov{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids)
        resp = self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        assert resp.status_code == 200
        # Wait for execution to complete (executes in background thread)
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            for fid in fids:
                f = s.query(File).filter(File.id == fid).first()
                assert f is not None
                # File should have been moved to object dir
                assert "managed" not in str(Path(f.path).parent.name) or "IMGSET" in f.path or "30_Images" in f.path

    def test_execute_creates_library_object(self):
        fids = [self._create_managed_file(f"lo{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids)
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.library_object import LibraryObject
            objects = s.query(LibraryObject).all()
            assert len(objects) == 1
            assert objects[0].metadata_source == "managed_compose"

    def test_execute_creates_library_object_members(self):
        fids = [self._create_managed_file(f"mbr{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids)
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.library_object import LibraryObjectMember
            members = s.query(LibraryObjectMember).all()
            assert len(members) == 2
            for m in members:
                assert m.object_id is not None
                assert m.file_id is not None

    def test_execute_updates_file_paths(self):
        fids = [self._create_managed_file(f"path{i}.jpg") for i in range(2)]
        with SessionLocal() as s:
            old_paths = {fid: s.query(File).filter(File.id == fid).first().path for fid in fids}
        pid = self._create_and_preflight_plan(fids)
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            for fid in fids:
                f = s.query(File).filter(File.id == fid).first()
                assert f.path != old_paths[fid], f"File {fid} path should have changed"

    def test_execute_writes_file_path_history(self):
        fids = [self._create_managed_file(f"hist{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids)
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.importing import FilePathHistory
            entries = s.query(FilePathHistory).filter(
                FilePathHistory.reason == "managed_compose_finalize"
            ).all()
            assert len(entries) == 2

    def test_execute_writes_operation_journal(self):
        fids = [self._create_managed_file(f"jrnl{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids)
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.importing import OperationJournal
            entries = s.query(OperationJournal).filter(
                OperationJournal.operation_type == "managed_compose_finalize"
            ).all()
            assert len(entries) >= 1

    def test_no_object_before_execute(self):
        fids = [self._create_managed_file(f"pre{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids)
        with SessionLocal() as s:
            from app.db.models.library_object import LibraryObject
            assert s.query(LibraryObject).count() == 0

    def test_execute_plan_status_completed(self):
        fids = [self._create_managed_file(f"stat{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids)
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            plan = s.query(OrganizePlan).filter(OrganizePlan.id == pid).first()
            assert plan.status == "completed"

    def test_moved_files_hidden_from_loose_browse(self):
        fids = [self._create_managed_file(f"hide{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids)
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        resp = self.client.get("/library/browse?domain=media")
        assert resp.status_code == 200
        data = resp.json()
        loose = [i for i in data["items"] if i["card_kind"] == "loose_file"]
        loose_ids = {i["file_id"] for i in loose}
        for fid in fids:
            assert fid not in loose_ids, f"File {fid} should not appear as loose file"

    def test_object_detail_shows_members(self):
        fids = [self._create_managed_file(f"det{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids)
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.library_object import LibraryObject
            lo = s.query(LibraryObject).first()
            assert lo is not None
        resp = self.client.get("/library/browse/object-detail", params={
            "object_source": "library_object", "source_id": lo.id,
        })
        assert resp.status_code == 200
        d = resp.json()
        assert d["member_count"] == 2

    def test_unrelated_files_not_deleted(self):
        unrelated = self._create_managed_file("unrel.jpg")
        fids = [self._create_managed_file(f"rel{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids)
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == unrelated).first()
            assert f is not None
            assert Path(f.path).exists()

    # ── P0-01: type_prefix regression ────────────────────

    def test_type_prefix_maps_correctly_for_imgset(self):
        """_finalize_managed_compose writes correct type_prefix for imgset."""
        fids = [self._create_managed_file(f"tp{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids, obj_type="imgset")
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.library_object import LibraryObject
            obj = s.query(LibraryObject).first()
            assert obj is not None
            assert obj.type_prefix == "IMGSET", f"Expected IMGSET, got {obj.type_prefix}"

    def test_type_prefix_maps_correctly_for_movie(self):
        fids = [self._create_managed_file(f"tp_mov{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids, obj_type="movie")
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.library_object import LibraryObject
            obj = s.query(LibraryObject).first()
            assert obj.type_prefix == "MOVIE", f"Expected MOVIE, got {obj.type_prefix}"

    def test_type_prefix_maps_correctly_for_game(self):
        fids = [self._create_managed_file(f"tp_game{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids, obj_type="game")
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.library_object import LibraryObject
            obj = s.query(LibraryObject).first()
            assert obj.type_prefix == "GAME", f"Expected GAME, got {obj.type_prefix}"

    def test_type_prefix_maps_correctly_for_asset_pack(self):
        fids = [self._create_managed_file(f"tp_ap{i}.jpg") for i in range(2)]
        pid = self._create_and_preflight_plan(fids, obj_type="asset_pack")
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        import time; time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.library_object import LibraryObject
            obj = s.query(LibraryObject).first()
            assert obj.type_prefix == "ASSET", f"Expected ASSET, got {obj.type_prefix}"
