"""Phase 8C-1 tests: compose inbox loose items into import_object_candidate."""

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


class ComposeInboxTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.managed_dir = self.tmp / "managed"
        self.managed_dir.mkdir()
        self.inbox_dir = self.managed_dir / "00_Inbox" / "1"
        self.inbox_dir.mkdir(parents=True)
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

    def _seed_inbox_items(self, count: int = 3) -> list[int]:
        ids: list[int] = []
        with SessionLocal() as session:
            batch = ImportBatch(source_kind="file_selection", import_method="copy", status="completed",
                               created_at=_dt())
            session.add(batch)
            session.flush()
            for i in range(count):
                fname = f"file{i+1}.mp4" if i < 2 else f"cover{i+1}.jpg"
                finbox = self.inbox_dir / fname
                finbox.write_bytes(b"fake")
                f = File(
                    source_id=1, path=str(finbox), parent_path=str(self.inbox_dir),
                    name=fname, stem=Path(fname).stem, extension=Path(fname).suffix.lstrip("."),
                    file_type="video" if fname.endswith(".mp4") else "image",
                    file_kind="video" if fname.endswith(".mp4") else "image",
                    auto_placement="media", storage_state="inbox", size_bytes=100,
                    discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
                )
                session.add(f)
                session.flush()
                ii = InboxItem(
                    import_batch_id=batch.id, file_id=f.id,
                    source_path=str(self.tmp / "source" / fname),
                    inbox_path=str(finbox), status="imported",
                    detected_file_kind=f.file_kind,
                    created_at=_dt(), updated_at=_dt(),
                )
                session.add(ii)
                session.flush()
                ids.append(ii.id)
            session.commit()
        return ids

    # ── Tests ─────────────────────────────────────────

    def test_compose_creates_object_candidate(self):
        ids = self._seed_inbox_items(3)
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "Test Object",
            "suggested_object_type": "video_collection",
            "target_library_root_id": self.root_id,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["object_candidate_id"] > 0
        assert data["member_count"] == 3
        assert data["object_name"] == "Test Object"

    def test_compose_creates_members(self):
        ids = self._seed_inbox_items(2)
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "Test",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["members"]) == 2

    def test_compose_empty_rejected(self):
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": [],
            "object_name": "Test",
        })
        assert resp.status_code == 400

    def test_compose_invalid_item_404(self):
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": [99999],
            "object_name": "Test",
        })
        assert resp.status_code == 400

    def test_compose_updates_inbox_item_status(self):
        ids = self._seed_inbox_items(2)
        self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "Test",
        })
        with SessionLocal() as session:
            for iid in ids:
                ii = session.query(InboxItem).filter(InboxItem.id == iid).first()
                assert ii is not None
                assert ii.status == "classified", f"Item {iid} status is {ii.status}"

    def test_compose_writes_journal(self):
        ids = self._seed_inbox_items(2)
        self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "Test",
        })
        with SessionLocal() as session:
            from app.db.models.importing import OperationJournal
            entries = session.query(OperationJournal).filter(
                OperationJournal.operation_type == "compose_object"
            ).all()
            assert len(entries) >= 1

    def test_compose_duplicate_member_rejected(self):
        ids = self._seed_inbox_items(2)
        # Compose once
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "First",
        })
        assert resp.status_code == 201
        # Compose again with same items
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "Second",
        })
        assert resp.status_code == 400

    def test_compose_does_not_move_or_delete_files(self):
        ids = self._seed_inbox_items(2)
        # Record original paths
        with SessionLocal() as session:
            orig_paths = {}
            for iid in ids:
                ii = session.query(InboxItem).filter(InboxItem.id == iid).first()
                orig_paths[iid] = ii.inbox_path
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "Test",
        })
        assert resp.status_code == 201
        # Verify files still exist
        for iid, path in orig_paths.items():
            assert Path(path).exists(), f"File {path} should still exist"

    def test_compose_requires_same_batch(self):
        # Create items across two separate batches
        with SessionLocal() as session:
            batch1 = ImportBatch(source_kind="file_selection", import_method="copy", status="completed",
                                created_at=_dt())
            session.add(batch1)
            session.flush()
            batch2 = ImportBatch(source_kind="file_selection", import_method="copy", status="completed",
                                created_at=_dt())
            session.add(batch2)
            session.flush()
            ids = []
            for i, batch in enumerate([batch1, batch2]):
                fname = f"batch{chr(65+i)}_file.mp4"
                fpath = self.inbox_dir / fname
                fpath.write_bytes(b"fake")
                f = File(
                    source_id=1, path=str(fpath), parent_path=str(self.inbox_dir),
                    name=fname, stem=Path(fname).stem, extension="mp4",
                    file_type="video", file_kind="video", auto_placement="media",
                    storage_state="inbox", size_bytes=100,
                    discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
                )
                session.add(f)
                session.flush()
                ii = InboxItem(
                    import_batch_id=batch.id, file_id=f.id,
                    source_path=str(self.tmp / "source" / fname),
                    inbox_path=str(fpath), status="imported",
                    detected_file_kind="video",
                    created_at=_dt(), updated_at=_dt(),
                )
                session.add(ii)
                session.flush()
                ids.append(ii.id)
            session.commit()
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "Test",
        })
        assert resp.status_code == 400
        assert "multiple import batches" in str(resp.json()["detail"]).lower()

    def test_compose_rejects_resolved_item(self):
        ids = self._seed_inbox_items(2)
        # Mark first item as "organized" (resolved)
        with SessionLocal() as session:
            ii = session.query(InboxItem).filter(InboxItem.id == ids[0]).first()
            ii.status = "organized"
            session.commit()
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "Test",
        })
        assert resp.status_code == 400

    def test_compose_does_not_create_organize_plan(self):
        ids = self._seed_inbox_items(2)
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "Test",
        })
        assert resp.status_code == 201
        data = resp.json()
        # Verify no organize candidate, plan, or execute was triggered
        with SessionLocal() as session:
            from app.db.models.organize import OrganizeCandidate, OrganizePlan, OrganizeAction
            oc_count = session.query(OrganizeCandidate).count()
            plan_count = session.query(OrganizePlan).count()
            action_count = session.query(OrganizeAction).count()
            assert oc_count == 0, "compose must not create organize candidate"
            assert plan_count == 0, "compose must not create organize plan"
            assert action_count == 0, "compose must not create organize actions"
        # Verify object candidate status
        from app.db.models.importing import ImportObjectCandidate
        with SessionLocal() as session:
            ioc = session.query(ImportObjectCandidate).filter(
                ImportObjectCandidate.id == data["object_candidate_id"]
            ).first()
            assert ioc is not None
            assert ioc.status == "pending_review"

    def test_compose_no_filesystem_operations(self):
        """Verify compose does not create directories or files on disk."""
        ids = self._seed_inbox_items(2)
        # Record existing directory structure
        before_dirs = set()
        for root, dirs, files in os.walk(str(self.managed_dir)):
            for d in dirs:
                before_dirs.add(os.path.join(root, d))
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": ids,
            "object_name": "TestObject",
        })
        assert resp.status_code == 201
        # Check no new directories were created (besides test fixtures)
        after_dirs = set()
        for root, dirs, files in os.walk(str(self.managed_dir)):
            for d in dirs:
                after_dirs.add(os.path.join(root, d))
        new_dirs = after_dirs - before_dirs
        assert len(new_dirs) == 0, f"compose must not create directories: {new_dirs}"

    def test_compose_is_transactional_on_member_failure(self):
        """If member creation fails, no partial candidate should remain."""
        ids = self._seed_inbox_items(2)
        # Force failure: invalid inbox_item_id with a non-existent one
        resp = self.client.post("/library/import/compose", json={
            "inbox_item_ids": [ids[0], 99999],
            "object_name": "Test",
        })
        assert resp.status_code == 400
        # Verify no candidate or members were created
        with SessionLocal() as session:
            from app.db.models.importing import ImportObjectCandidate as IOC, ImportObjectMember as IOM
            all_candidates = session.query(IOC).count()
            all_members = session.query(IOM).count()
            assert all_candidates == 0, "no candidate should remain on partial failure"
            assert all_members == 0, "no members should remain on partial failure"
