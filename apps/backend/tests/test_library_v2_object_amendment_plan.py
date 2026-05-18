"""Phase 8D-A2 tests: object amendment draft plan (add-only, remove-only)."""

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


class ObjectAmendmentPlanTestCase(unittest.TestCase):
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

    def _seed_object_with_member(self) -> tuple[int, int, int]:
        """Create object with one member. Returns (object_id, member_id, file_id)."""
        fid = self._seed_managed_file("member_orig.jpg")
        obj_dir = self.managed_dir / "30_Images" / "Image_Sets" / "[IMGSET] TestObj"
        obj_dir.mkdir(parents=True)
        # Physically move the managed file into object dir
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            import shutil
            src = Path(f.path)
            dst = obj_dir / f.name
            shutil.move(str(src), str(dst))
            f.path = str(dst)
            f.parent_path = str(obj_dir)
            s.commit()
        with SessionLocal() as session:
            lo = LibraryObject(
                object_type="imgset", type_prefix="IMGSET",
                root_path=str(obj_dir), root_name=obj_dir.name,
                title="Test Object", filesystem_title="Test Object",
                metadata_source="managed_compose", needs_review=False,
                last_scanned_at=_dt(), created_at=_dt(), updated_at=_dt(),
            )
            session.add(lo); session.flush()
            lom = LibraryObjectMember(
                object_id=lo.id, file_id=fid, relative_path="member_orig.jpg",
                absolute_path=str(obj_dir / "member_orig.jpg"),
                member_role="image_member", member_status="active",
                created_at=_dt(),
            )
            session.add(lom); session.commit()
            return lo.id, lom.id, fid

    # ── Add-only tests ─────────────────────────────────

    def test_creates_add_member_plan(self):
        obj_id, _, _ = self._seed_object_with_member()
        fid = self._seed_managed_file("new_file.jpg")
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [fid], "remove_member_ids": [],
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        d = resp.json()
        assert d["plan_kind"] == "object_amendment"
        assert d["amendment_type"] == "add_members"
        assert d["status"] == "draft"
        assert d["add_count"] == 1

    def test_add_member_payload_has_file_trace(self):
        obj_id, _, _ = self._seed_object_with_member()
        fid = self._seed_managed_file("payload_test.jpg")
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [fid], "remove_member_ids": [],
        })
        assert resp.status_code == 201
        with SessionLocal() as s:
            actions = s.query(OrganizeAction).filter(
                OrganizeAction.plan_id == resp.json()["plan_id"]
            ).all()
            assert len(actions) == 1
            assert "object_amendment_plan" in (actions[0].payload_json or "")
            assert "add_member" in (actions[0].payload_json or "")

    def test_add_member_rejects_invalid_object(self):
        resp = self.client.post("/library/objects/99999/amendment-plans", json={
            "add_file_ids": [1], "remove_member_ids": [],
        })
        assert resp.status_code == 404

    def test_add_member_rejects_external_file(self):
        obj_id, _, _ = self._seed_object_with_member()
        fid = self._seed_managed_file("ext.jpg")
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            f.storage_state = "external"
            s.commit()
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [fid], "remove_member_ids": [],
        })
        assert resp.status_code == 400

    def test_add_member_rejects_file_already_member(self):
        obj_id, _, member_fid = self._seed_object_with_member()
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [member_fid], "remove_member_ids": [],
        })
        assert resp.status_code == 400

    def test_add_member_does_not_move_files(self):
        obj_id, _, _ = self._seed_object_with_member()
        fid = self._seed_managed_file("stay.jpg")
        orig_path = str(self.managed_dir / "stay.jpg")
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [fid], "remove_member_ids": [],
        })
        assert resp.status_code == 201
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            assert f.path == orig_path, "File must not be moved by draft plan"

    def test_add_member_does_not_create_members(self):
        obj_id, mid, _ = self._seed_object_with_member()
        fid = self._seed_managed_file("no_create.jpg")
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [fid], "remove_member_ids": [],
        })
        assert resp.status_code == 201
        with SessionLocal() as s:
            members = s.query(LibraryObjectMember).filter(
                LibraryObjectMember.object_id == obj_id
            ).all()
            assert len(members) == 1  # only original

    # ── Remove-only tests ───────────────────────────────

    def test_creates_remove_member_plan(self):
        obj_id, mid, fid = self._seed_object_with_member()
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [], "remove_member_ids": [mid],
        })
        assert resp.status_code == 201
        d = resp.json()
        assert d["amendment_type"] == "remove_members"
        assert d["remove_count"] == 1

    def test_remove_member_rejects_other_object(self):
        obj_id, mid, _ = self._seed_object_with_member()
        # Create second object
        obj2 = self.managed_dir / "[IMGSET] Obj2"
        obj2.mkdir(parents=True)
        with SessionLocal() as s:
            lo2 = LibraryObject(
                object_type="imgset", type_prefix="IMGSET",
                root_path=str(obj2), root_name=obj2.name,
                title="Obj2", filesystem_title="Obj2",
                metadata_source="test", needs_review=False,
                last_scanned_at=_dt(), created_at=_dt(), updated_at=_dt(),
            )
            s.add(lo2); s.commit()
            o2id = lo2.id
        resp = self.client.post(f"/library/objects/{o2id}/amendment-plans", json={
            "add_file_ids": [], "remove_member_ids": [mid],
        })
        assert resp.status_code == 400

    def test_remove_member_does_not_move_files(self):
        obj_id, mid, fid = self._seed_object_with_member()
        with SessionLocal() as s:
            orig_path = s.query(File).filter(File.id == fid).first().path
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [], "remove_member_ids": [mid],
        })
        assert resp.status_code == 201
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            assert f.path == orig_path

    def test_remove_member_does_not_change_status(self):
        obj_id, mid, fid = self._seed_object_with_member()
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [], "remove_member_ids": [mid],
        })
        assert resp.status_code == 201
        with SessionLocal() as s:
            m = s.query(LibraryObjectMember).filter(LibraryObjectMember.id == mid).first()
            assert m is not None
            assert m.member_status == "active"

    # ── Mixed / validation ──────────────────────────────

    def test_rejects_empty(self):
        obj_id, _, _ = self._seed_object_with_member()
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [], "remove_member_ids": [],
        })
        assert resp.status_code == 400

    def test_rejects_mixed(self):
        obj_id, mid, _ = self._seed_object_with_member()
        fid = self._seed_managed_file("mixed.jpg")
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [fid], "remove_member_ids": [mid],
        })
        assert resp.status_code == 400

    def test_plan_summary_all_or_nothing(self):
        obj_id, _, _ = self._seed_object_with_member()
        fid = self._seed_managed_file("policy.jpg")
        resp = self.client.post(f"/library/objects/{obj_id}/amendment-plans", json={
            "add_file_ids": [fid], "remove_member_ids": [],
        })
        assert resp.status_code == 201
        with SessionLocal() as s:
            plan = s.query(OrganizePlan).filter(
                OrganizePlan.id == resp.json()["plan_id"]
            ).first()
            assert "all_or_nothing" in (plan.summary_json or "")
