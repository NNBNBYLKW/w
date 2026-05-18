"""Phase 8C-4B tests: preflight for managed compose object creation plans."""

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


class ManagedComposePreflightTestCase(unittest.TestCase):
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

    def _create_managed_file(self, name: str, path: Path | None = None) -> int:
        p = path or (self.managed_dir / name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"managed file")
        ext = p.suffix.lstrip(".") if p.suffix else ""
        kind = "image" if ext in ("jpg", "png") else "video"
        with SessionLocal() as session:
            f = File(
                source_id=1, path=str(p), parent_path=str(p.parent),
                name=p.name, stem=p.stem, extension=ext,
                file_type=kind, file_kind=kind, auto_placement="media",
                storage_state="managed", managed_root_id=self.root_id, managed_at=_dt(),
                size_bytes=100, discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
            )
            session.add(f)
            session.commit()
            return f.id

    def _create_compose_plan(self, file_ids: list[int], object_name="TestObj", object_type="imgset") -> int:
        resp = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": file_ids, "object_name": object_name,
            "object_type": object_type, "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        return resp.json()["plan_id"]

    def _mark_ready(self, plan_id: int) -> dict:
        resp = self.client.post(f"/library/organize/plans/{plan_id}/mark-ready")
        return resp.json()

    def _preflight(self, plan_id: int) -> dict:
        resp = self.client.post(f"/library/organize/plans/{plan_id}/preflight")
        return resp.json()

    # ── Tests ─────────────────────────────────────────

    def test_mark_ready_managed_compose_plan(self):
        fids = [self._create_managed_file(f"pft{i}.jpg") for i in range(2)]
        pid = self._create_compose_plan(fids)
        result = self._mark_ready(pid)
        assert result["plan"]["status"] == "ready"

    def test_preflight_passes_valid_plan(self):
        fids = [self._create_managed_file(f"pft{i}.jpg") for i in range(2)]
        pid = self._create_compose_plan(fids)
        self._mark_ready(pid)
        result = self._preflight(pid)
        assert result["can_execute"] is True

    def test_preflight_rejects_missing_source_file(self):
        fid = self._create_managed_file("exists.jpg")
        pid = self._create_compose_plan([fid])
        self._mark_ready(pid)
        # Remove physical file
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            Path(f.path).unlink()
        result = self._preflight(pid)
        assert result["can_execute"] is False

    def test_preflight_rejects_stale_source_path(self):
        fid = self._create_managed_file("original.jpg")
        pid = self._create_compose_plan([fid])
        self._mark_ready(pid)
        # Change file path in DB (simulate path drift)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            f.path = str(Path(f.path).parent / "changed.jpg")
            s.commit()
        result = self._preflight(pid)
        assert result["can_execute"] is False

    def test_preflight_rejects_file_no_longer_managed(self):
        fid = self._create_managed_file("was_mgd.jpg")
        pid = self._create_compose_plan([fid])
        self._mark_ready(pid)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fid).first()
            f.storage_state = "external"
            s.commit()
        result = self._preflight(pid)
        assert result["can_execute"] is False

    def test_preflight_rejects_file_became_library_object_member(self):
        fid = self._create_managed_file("now_member.jpg")
        pid = self._create_compose_plan([fid])
        self._mark_ready(pid)
        # Make it a library object member
        with SessionLocal() as s:
            from app.db.models.library_object import LibraryObject, LibraryObjectMember
            lo = LibraryObject(
                root_path=str(self.managed_dir / "[IMGSET] Test"), root_name="Test",
                object_type="imgset", type_prefix="IMGSET", title="Test",
                filesystem_title="Test", metadata_source="scan", needs_review=False,
                last_scanned_at=_dt(), created_at=_dt(), updated_at=_dt(),
            )
            s.add(lo); s.flush()
            lom = LibraryObjectMember(
                object_id=lo.id, file_id=fid, member_role="image_member",
                relative_path=f"{fid}.jpg", absolute_path="", created_at=_dt(),
            )
            s.add(lom); s.commit()
        result = self._preflight(pid)
        assert result["can_execute"] is False

    def test_preflight_does_not_move_files(self):
        fids = [self._create_managed_file(f"nomove{i}.jpg") for i in range(2)]
        pid = self._create_compose_plan(fids)
        self._mark_ready(pid)
        with SessionLocal() as s:
            orig_paths = {fid: s.query(File).filter(File.id == fid).first().path for fid in fids}
        self._preflight(pid)
        with SessionLocal() as s:
            for fid in fids:
                f = s.query(File).filter(File.id == fid).first()
                assert f.path == orig_paths[fid], "Preflight must not move files"
                assert Path(f.path).exists()

    def test_preflight_does_not_create_library_object(self):
        fids = [self._create_managed_file(f"nolo{i}.jpg") for i in range(2)]
        pid = self._create_compose_plan(fids)
        self._mark_ready(pid)
        self._preflight(pid)
        with SessionLocal() as s:
            from app.db.models.library_object import LibraryObject, LibraryObjectMember
            assert s.query(LibraryObject).count() == 0
            assert s.query(LibraryObjectMember).count() == 0

    def test_mark_ready_rejects_stale_missing_payload(self):
        fid = self._create_managed_file("nopayload.jpg")
        pid = self._create_compose_plan([fid])
        # Corrupt the move action payload
        with SessionLocal() as s:
            actions = s.query(OrganizeAction).filter(
                OrganizeAction.plan_id == pid, OrganizeAction.action_type == "move"
            ).all()
            for a in actions:
                a.payload_json = '{"object_creation_plan": true}'
            s.commit()
        resp = self.client.post(f"/library/organize/plans/{pid}/mark-ready")
        assert resp.status_code == 400

    def test_target_conflict_rejected(self):
        fid = self._create_managed_file("conflict.jpg")
        pid = self._create_compose_plan([fid])
        self._mark_ready(pid)
        # Create a file at the target path
        with SessionLocal() as s:
            action = s.query(OrganizeAction).filter(
                OrganizeAction.plan_id == pid, OrganizeAction.action_type == "move"
            ).first()
            Path(action.target_path).parent.mkdir(parents=True, exist_ok=True)
            Path(action.target_path).write_bytes(b"blocker")
        result = self._preflight(pid)
        assert result["can_execute"] is False
