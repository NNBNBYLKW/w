"""Phase 8C-3 tests: compose external loose files into Inbox object candidate."""

import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.importing import ImportBatch, ImportObjectCandidate, ImportObjectMember, InboxItem
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class ComposeExternalTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.managed_dir = self.tmp / "managed"
        self.managed_dir.mkdir()
        self.source_dir = self.tmp / "source"
        self.source_dir.mkdir()
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

    def _seed_external_files(self, count: int = 3) -> list[int]:
        ids: list[int] = []
        with SessionLocal() as session:
            for i in range(count):
                ext = "mp4" if i < 2 else "jpg"
                fname = f"ext{i+1}.{ext}"
                fpath = self.source_dir / fname
                fpath.write_bytes(b"fake content")
                f = File(
                    source_id=1, path=str(fpath), parent_path=str(self.source_dir),
                    name=fname, stem=f"ext{i+1}", extension=ext,
                    file_type="video" if ext == "mp4" else "image",
                    file_kind="video" if ext == "mp4" else "image",
                    auto_placement="media", storage_state="external", size_bytes=100,
                    discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
                )
                session.add(f)
                session.flush()
                ids.append(f.id)
            session.commit()
        return ids

    # ── Tests ─────────────────────────────────────────

    def test_compose_external_creates_object_candidate(self):
        fids = self._seed_external_files(3)
        resp = self.client.post("/library/import/compose/external-files", json={
            "file_ids": fids, "object_name": "External Pack",
            "suggested_object_type": "video_collection",
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        d = resp.json()
        assert d["object_candidate_id"] > 0
        assert d["import_batch_id"] > 0
        assert d["member_count"] == 3
        assert d["copied_count"] == 3
        assert d["status"] == "pending_review"

    def test_compose_external_preserves_source(self):
        fids = self._seed_external_files(2)
        with SessionLocal() as s:
            orig_paths = {fid: s.query(File).filter(File.id == fid).first().path for fid in fids}
        resp = self.client.post("/library/import/compose/external-files", json={
            "file_ids": fids, "object_name": "Test",
        })
        assert resp.status_code == 201
        for fid, path in orig_paths.items():
            assert Path(path).exists(), f"Source must be preserved: {path}"

    def test_compose_external_copies_to_inbox(self):
        fids = self._seed_external_files(1)
        resp = self.client.post("/library/import/compose/external-files", json={
            "file_ids": fids, "object_name": "Test",
        })
        assert resp.status_code == 201
        # Verify inbox items created
        with SessionLocal() as s:
            items = s.query(InboxItem).filter(InboxItem.file_id.isnot(None)).all()
            assert len(items) >= 1

    def test_compose_external_rejects_empty(self):
        resp = self.client.post("/library/import/compose/external-files", json={
            "file_ids": [], "object_name": "Test",
        })
        assert resp.status_code == 400

    def test_compose_external_rejects_missing_file(self):
        resp = self.client.post("/library/import/compose/external-files", json={
            "file_ids": [99999], "object_name": "Test",
        })
        assert resp.status_code == 400

    def test_compose_external_rejects_non_external(self):
        fids = self._seed_external_files(1)
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fids[0]).first()
            f.storage_state = "managed"
            s.commit()
        resp = self.client.post("/library/import/compose/external-files", json={
            "file_ids": fids, "object_name": "Test",
        })
        assert resp.status_code == 400

    def test_compose_external_no_organize_plan(self):
        fids = self._seed_external_files(2)
        resp = self.client.post("/library/import/compose/external-files", json={
            "file_ids": fids, "object_name": "Test",
        })
        assert resp.status_code == 201
        with SessionLocal() as s:
            from app.db.models.organize import OrganizeCandidate, OrganizePlan, OrganizeAction
            assert s.query(OrganizeCandidate).count() == 0
            assert s.query(OrganizePlan).count() == 0
            assert s.query(OrganizeAction).count() == 0

    def test_compose_external_no_overwrite_suffix(self):
        # Two files with same name in different dirs
        sub = self.source_dir / "sub"
        sub.mkdir()
        f1 = self.source_dir / "cover.jpg"
        f2 = sub / "cover.jpg"
        f1.write_bytes(b"content1")
        f2.write_bytes(b"content2")
        fid1 = fid2 = None
        with SessionLocal() as s:
            for fp in [f1, f2]:
                f = File(
                    source_id=1, path=str(fp), parent_path=str(fp.parent),
                    name=fp.name, stem=fp.stem, extension="jpg",
                    file_type="image", file_kind="image", auto_placement="media",
                    storage_state="external", size_bytes=100,
                    discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
                )
                s.add(f); s.flush()
                if fp == f1: fid1 = f.id
                else: fid2 = f.id
            s.commit()
        resp = self.client.post("/library/import/compose/external-files", json={
            "file_ids": [fid1, fid2], "object_name": "Test",
        })
        assert resp.status_code == 201
        d = resp.json()
        assert d["member_count"] == 2

    def test_compose_external_rollback_on_failure(self):
        fids = self._seed_external_files(1)
        # Make source file unreadable
        with SessionLocal() as s:
            f = s.query(File).filter(File.id == fids[0]).first()
            Path(f.path).unlink()  # Remove physical file
            s.commit()
        resp = self.client.post("/library/import/compose/external-files", json={
            "file_ids": fids, "object_name": "Test",
        })
        assert resp.status_code == 400
        # Verify no candidate or batch remains
        with SessionLocal() as s:
            assert s.query(ImportObjectCandidate).count() == 0
            assert s.query(ImportObjectMember).count() == 0
