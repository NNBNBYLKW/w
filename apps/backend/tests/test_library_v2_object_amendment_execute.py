"""Phase 8D-C tests: execute + finalize object amendment plans (add + remove)."""

import shutil
import tempfile
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_object import LibraryObject, LibraryObjectMember
from app.db.models.library_root import LibraryRoot
from app.db.models.organize import OrganizePlan, OrganizeAction
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class AmendmentExecuteTestCase(unittest.TestCase):
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
                name=p.name, stem=p.stem, extension=p.suffix.lstrip("."),
                file_type="image" if name.endswith(("jpg","png")) else "video",
                file_kind="image" if name.endswith(("jpg","png")) else "video",
                auto_placement="media", storage_state="managed",
                managed_root_id=self.root_id, managed_at=_dt(),
                size_bytes=100, discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
            )
            session.add(f)
            session.commit()
            return f.id

    def _seed_obj_with_member(self) -> tuple[int, int, int]:
        fid = self._seed_managed_file("member.jpg")
        obj_dir = self.managed_dir / "30_Images" / "Image_Sets" / "[IMGSET] EXObject"
        obj_dir.mkdir(parents=True)
        with SessionLocal() as s:
            fobj = s.query(File).filter(File.id == fid).first()
            dst = obj_dir / fobj.name
            shutil.move(str(fobj.path), str(dst))
            fobj.path = str(dst)
            fobj.parent_path = str(obj_dir)
            s.commit()
        with SessionLocal() as session:
            lo = LibraryObject(
                object_type="imgset", type_prefix="IMGSET",
                root_path=str(obj_dir), root_name=obj_dir.name,
                title="EX Object", filesystem_title="EX Object",
                metadata_source="managed_compose", needs_review=False,
                last_scanned_at=_dt(), created_at=_dt(), updated_at=_dt(),
            )
            session.add(lo); session.flush()
            lom = LibraryObjectMember(
                object_id=lo.id, file_id=fid, relative_path="member.jpg",
                absolute_path=str(dst), member_role="image_member",
                member_status="active", created_at=_dt(),
            )
            session.add(lom); session.commit()
            return lo.id, lom.id, fid

    def _create_and_preflight(self, obj_id: int, add_ids=None, remove_ids=None) -> int:
        add = add_ids or []
        rem = remove_ids or []
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": add, "remove_member_ids": rem,
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        pid = resp.json()["plan_id"]
        # Create necessary dirs for remove target
        if rem:
            (self.managed_dir / "90_Loose" / "Removed_[IMGSET] EXObject").mkdir(parents=True)
        self.client.post(f"/library/organize/plans/{pid}/mark-ready")
        pre = self.client.post(f"/library/organize/plans/{pid}/preflight")
        assert pre.json()["can_execute"], f"preflight failed: {pre.json()}"
        return pid

    # ── Add-member tests ─────────────────────────────────

    def test_execute_add_member_moves_file(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("new_add.jpg")
        pid = self._create_and_preflight(obj_id, add_ids=[fid])
        with SessionLocal() as s:
            old_path = s.query(File).filter(File.id == fid).first().path
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            assert f.path != old_path

    def test_execute_add_member_creates_active_member(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("create_member.jpg")
        pid = self._create_and_preflight(obj_id, add_ids=[fid])
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        with SessionLocal() as s:
            members = s.query(LibraryObjectMember).filter(
                LibraryObjectMember.object_id == obj_id
            ).all()
            assert len(members) == 2  # original + new
            new_m = [m for m in members if m.file_id == fid][0]
            assert new_m.member_status == "active"

    def test_execute_add_member_updates_file_path(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("path_update.jpg")
        pid = self._create_and_preflight(obj_id, add_ids=[fid])
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            assert "[IMGSET]" in f.path or "30_Images" in f.path

    def test_execute_add_member_writes_path_history(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("hist_add.jpg")
        pid = self._create_and_preflight(obj_id, add_ids=[fid])
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.importing import FilePathHistory
            entries = s.query(FilePathHistory).filter(
                FilePathHistory.reason == "object_amendment_add_member"
            ).all()
            assert len(entries) >= 1

    def test_execute_add_member_hides_from_loose(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("hide_add.jpg")
        pid = self._create_and_preflight(obj_id, add_ids=[fid])
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        resp = self.client.get("/library/browse?domain=media")
        data = resp.json()
        loose_ids = {i["file_id"] for i in data["items"] if i["card_kind"] == "loose_file"}
        assert fid not in loose_ids

    def test_execute_add_member_no_create_before_execute(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("pre_add.jpg")
        pid = self._create_and_preflight(obj_id, add_ids=[fid])
        with SessionLocal() as s:
            assert s.query(LibraryObjectMember).count() == 1  # only original

    # ── Remove-member tests ──────────────────────────────

    def test_execute_remove_member_moves_file(self):
        obj_id, mid, fid = self._seed_obj_with_member()
        pid = self._create_and_preflight(obj_id, remove_ids=[mid])
        with SessionLocal() as s:
            old_path = s.query(File).filter(File.id == fid).first().path
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            assert f.path != old_path
            assert "90_Loose" in f.path

    def test_execute_remove_member_sets_removed(self):
        obj_id, mid, fid = self._seed_obj_with_member()
        pid = self._create_and_preflight(obj_id, remove_ids=[mid])
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        with SessionLocal() as s:
            m = s.query(LibraryObjectMember).filter(LibraryObjectMember.id == mid).first()
            assert m.member_status == "removed"

    def test_execute_remove_member_not_hard_delete(self):
        obj_id, mid, fid = self._seed_obj_with_member()
        pid = self._create_and_preflight(obj_id, remove_ids=[mid])
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        with SessionLocal() as s:
            m = s.query(LibraryObjectMember).filter(LibraryObjectMember.id == mid).first()
            assert m is not None, "Member must not be hard-deleted"

    def test_execute_remove_file_returns_to_loose(self):
        obj_id, mid, fid = self._seed_obj_with_member()
        pid = self._create_and_preflight(obj_id, remove_ids=[mid])
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        resp = self.client.get("/library/browse?domain=media")
        data = resp.json()
        loose_ids = {i["file_id"] for i in data["items"] if i["card_kind"] == "loose_file"}
        assert fid in loose_ids, "Removed member file should appear as loose"

    def test_execute_remove_member_writes_path_history(self):
        obj_id, mid, fid = self._seed_obj_with_member()
        pid = self._create_and_preflight(obj_id, remove_ids=[mid])
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.importing import FilePathHistory
            entries = s.query(FilePathHistory).filter(
                FilePathHistory.reason == "object_amendment_remove_member"
            ).all()
            assert len(entries) >= 1

    def test_execute_remove_member_writes_journal(self):
        obj_id, mid, fid = self._seed_obj_with_member()
        pid = self._create_and_preflight(obj_id, remove_ids=[mid])
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        with SessionLocal() as s:
            from app.db.models.importing import OperationJournal
            entries = s.query(OperationJournal).filter(
                OperationJournal.operation_type == "object_amendment_finalize"
            ).all()
            assert len(entries) >= 1

    def test_no_delete_unrelated_files(self):
        obj_id, _, _ = self._seed_obj_with_member()
        unrelated = self._seed_managed_file("unrelated.jpg")
        fid = self._seed_managed_file("add_this.jpg")
        pid = self._create_and_preflight(obj_id, add_ids=[fid])
        self.client.post(f"/library/organize/plans/{pid}/execute", json={"confirm": True})
        time.sleep(0.5)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == unrelated).first()
            assert f is not None
            assert Path(f.path).exists()
