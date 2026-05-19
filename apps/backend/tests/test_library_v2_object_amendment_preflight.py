"""Phase 8D-B tests: preflight for object amendment plans (add + remove)."""

import shutil
import tempfile
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


class AmendmentPreflightTestCase(unittest.TestCase):
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
        obj_dir = self.managed_dir / "30_Images" / "Image_Sets" / "[IMGSET] PFObject"
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
                title="PF Object", filesystem_title="PF Object",
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

    def _create_add_plan(self, obj_id: int, add_fid: int):
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [add_fid], "remove_member_ids": [],
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        return resp.json()["plan_id"]

    def _create_remove_plan(self, obj_id: int, remove_mid: int):
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [], "remove_member_ids": [remove_mid],
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        return resp.json()["plan_id"]

    def _mark_ready(self, pid: int):
        return self.client.post(f"/library/organize/plans/{pid}/mark-ready")

    def _preflight(self, pid: int):
        return self.client.post(f"/library/organize/plans/{pid}/preflight")

    # ── Valid flow ──────────────────────────────────────

    def test_preflight_add_member_passes(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("new_add.jpg")
        pid = self._create_add_plan(obj_id, fid)
        r = self._mark_ready(pid)
        assert r.status_code == 200
        r = self._preflight(pid)
        assert r.status_code == 200
        assert r.json()["can_execute"] is True

    def test_preflight_remove_member_passes(self):
        obj_id, mid, _ = self._seed_obj_with_member()
        # Pre-create the 90_Loose dir that the remove target needs
        (self.managed_dir / "90_Loose" / "Removed_[IMGSET] PFObject").mkdir(parents=True)
        pid = self._create_remove_plan(obj_id, mid)
        r = self._mark_ready(pid)
        assert r.status_code == 200, f"mark ready failed: {r.json() if r.status_code != 200 else ''}"
        r = self._preflight(pid)
        assert r.status_code == 200, f"preflight failed: {r.json() if r.status_code != 200 else ''}"
        assert r.json()["can_execute"] is True, f"preflight response: {r.json()}"

    # ── Add member invalid ──────────────────────────────

    def test_add_preflight_stale_file_path(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("stale_add.jpg")
        pid = self._create_add_plan(obj_id, fid)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            f.path = str(Path(f.path).parent / "changed.jpg")
            s.commit()
        # mark_ready should reject stale plan
        r = self._mark_ready(pid)
        assert r.status_code == 400

    def test_add_preflight_file_no_longer_managed(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("unmanaged.jpg")
        pid = self._create_add_plan(obj_id, fid)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            f.storage_state = "external"
            s.commit()
        r = self._mark_ready(pid)
        assert r.status_code == 400

    def test_add_preflight_file_became_member(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("became_member.jpg")
        pid = self._create_add_plan(obj_id, fid)
        with SessionLocal() as s:
            lom = LibraryObjectMember(
                object_id=obj_id, file_id=fid, relative_path="became_member.jpg",
                absolute_path=str(self.managed_dir / "became_member.jpg"),
                member_role="image_member", member_status="active", created_at=_dt(),
            )
            s.add(lom); s.commit()
        r = self._mark_ready(pid)
        assert r.status_code == 400

    def test_add_preflight_target_conflict(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("conflict.jpg")
        pid = self._create_add_plan(obj_id, fid)
        self._mark_ready(pid)
        with SessionLocal() as s:
            action = s.query(OrganizeAction).filter(
                OrganizeAction.plan_id == pid, OrganizeAction.action_type == "move"
            ).first()
            Path(action.target_path).parent.mkdir(parents=True, exist_ok=True)
            Path(action.target_path).write_bytes(b"block")
        r = self._preflight(pid)
        assert r.json()["can_execute"] is False

    # ── Remove member invalid ───────────────────────────

    def test_remove_preflight_member_not_active(self):
        obj_id, mid, _ = self._seed_obj_with_member()
        (self.managed_dir / "90_Loose" / "Removed_[IMGSET] PFObject").mkdir(parents=True)
        pid = self._create_remove_plan(obj_id, mid)
        with SessionLocal() as s:
            m = s.query(LibraryObjectMember).filter(LibraryObjectMember.id == mid).first()
            m.member_status = "removed"
            s.commit()
        r = self._mark_ready(pid)
        assert r.status_code == 400

    def test_remove_preflight_member_from_other_object(self):
        obj_id, mid, _ = self._seed_obj_with_member()
        (self.managed_dir / "90_Loose" / "Removed_[IMGSET] PFObject").mkdir(parents=True)
        pid = self._create_remove_plan(obj_id, mid)
        # Move member to different object
        obj2_dir = self.managed_dir / "[IMGSET] Obj2"
        obj2_dir.mkdir(parents=True)
        with SessionLocal() as s:
            lo2 = LibraryObject(
                object_type="imgset", type_prefix="IMGSET",
                root_path=str(obj2_dir), root_name=obj2_dir.name,
                title="Obj2", filesystem_title="Obj2",
                metadata_source="test", needs_review=False,
                last_scanned_at=_dt(), created_at=_dt(), updated_at=_dt(),
            )
            s.add(lo2); s.flush()
            m = s.query(LibraryObjectMember).filter(LibraryObjectMember.id == mid).first()
            m.object_id = lo2.id
            s.commit()
        r = self._mark_ready(pid)
        assert r.status_code == 400

    # ── Safety ──────────────────────────────────────────

    def test_preflight_does_not_move_files(self):
        obj_id, _, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("no_move.jpg")
        pid = self._create_add_plan(obj_id, fid)
        with SessionLocal() as s:
            orig = s.query(File).filter(File.id == fid).first().path
        self._mark_ready(pid)
        self._preflight(pid)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            assert f.path == orig

    def test_preflight_does_not_change_member_status(self):
        obj_id, mid, _ = self._seed_obj_with_member()
        pid = self._create_remove_plan(obj_id, mid)
        self._mark_ready(pid)
        self._preflight(pid)
        with SessionLocal() as s:
            m = s.query(LibraryObjectMember).filter(LibraryObjectMember.id == mid).first()
            assert m.member_status == "active"

    def test_preflight_does_not_create_or_delete_members(self):
        obj_id, mid, _ = self._seed_obj_with_member()
        fid = self._seed_managed_file("safe_add.jpg")
        pid = self._create_add_plan(obj_id, fid)
        with SessionLocal() as s:
            before = s.query(LibraryObjectMember).count()
        self._mark_ready(pid)
        self._preflight(pid)
        with SessionLocal() as s:
            after = s.query(LibraryObjectMember).count()
            assert after == before
