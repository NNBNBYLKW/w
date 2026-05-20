"""P1 fix: auto-repair managed import source sentinel on first access."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.importing import ImportBatch, InboxItem
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app
from app.services.importing.service import ImportService


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class ManagedImportSourceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
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

    def _seed_source(self) -> int:
        with SessionLocal() as session:
            source = Source(
                path="__workbench_managed_import__", display_name="Managed Import",
                is_enabled=True, scan_mode="manual", last_scan_status="not_applicable",
                created_at=_dt(), updated_at=_dt(),
            )
            session.add(source)
            session.commit()
            return source.id

    def _count_sentinels(self) -> int:
        with SessionLocal() as session:
            return session.query(Source).filter(
                Source.path == "__workbench_managed_import__"
            ).count()

    # ── tests ──────────────────────────────────────────────

    def test_get_managed_source_returns_existing_sentinel(self):
        """When sentinel already exists, _get_managed_source returns it."""
        sid = self._seed_source()
        service = ImportService()
        with SessionLocal() as session:
            source = service._get_managed_source(session)
            self.assertEqual(source.id, sid)
            self.assertEqual(source.path, "__workbench_managed_import__")
            self.assertEqual(source.display_name, "Managed Import")
            self.assertEqual(source.scan_mode, "manual")
            self.assertEqual(source.last_scan_status, "not_applicable")
            self.assertTrue(source.is_enabled)

    def test_get_managed_source_auto_repairs_missing_sentinel(self):
        """When sentinel is missing, _get_managed_source creates it."""
        self.assertEqual(self._count_sentinels(), 0)
        service = ImportService()
        with SessionLocal() as session:
            source = service._get_managed_source(session)
            session.commit()
        self.assertIsNotNone(source.id)
        self.assertEqual(source.path, "__workbench_managed_import__")
        self.assertEqual(self._count_sentinels(), 1)

    def test_auto_repaired_sentinel_has_expected_fields(self):
        """Auto-created sentinel matches engine _ensure_library_v2_source fields."""
        self.assertEqual(self._count_sentinels(), 0)
        service = ImportService()
        with SessionLocal() as session:
            source = service._get_managed_source(session)
            session.commit()
        self.assertEqual(source.path, "__workbench_managed_import__")
        self.assertEqual(source.display_name, "Managed Import")
        self.assertTrue(source.is_enabled)
        self.assertEqual(source.scan_mode, "manual")
        self.assertEqual(source.last_scan_status, "not_applicable")

    def test_auto_repair_does_not_create_duplicate_sentinel(self):
        """Two consecutive calls produce exactly one sentinel."""
        self.assertEqual(self._count_sentinels(), 0)
        service = ImportService()
        with SessionLocal() as session:
            source1 = service._get_managed_source(session)
            source2 = service._get_managed_source(session)
            session.commit()
        self.assertEqual(source1.id, source2.id)
        self.assertEqual(self._count_sentinels(), 1)

    def test_import_batch_succeeds_when_sentinel_missing(self):
        """Creating an import batch works even when sentinel is missing."""
        self.assertEqual(self._count_sentinels(), 0)
        resp = self.client.post("/library/import/batches", json={"import_method": "copy"})
        self.assertEqual(resp.status_code, 201, msg=f"Response: {resp.text}")
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "created")

    def test_import_file_succeeds_when_sentinel_missing_but_root_exists(self):
        """Full import works: sentinel auto-created, file copied, source preserved."""
        self.assertEqual(self._count_sentinels(), 0)
        # Create a source file
        src_file = self.tmp / "test_photo.jpg"
        src_file.write_bytes(b"fake-jpeg-content")

        # Create batch
        resp = self.client.post("/library/import/batches", json={"import_method": "copy"})
        self.assertEqual(resp.status_code, 201)
        batch_id = resp.json()["id"]

        # Import file
        resp = self.client.post(
            f"/library/import/batches/{batch_id}/files",
            json={"paths": [str(src_file)]},
        )
        self.assertEqual(resp.status_code, 200, msg=f"Response: {resp.text}")
        data = resp.json()
        self.assertEqual(len(data["created_items"]), 1)
        self.assertEqual(len(data["failed_items"]), 0)

        # Sentinel was auto-created
        self.assertEqual(self._count_sentinels(), 1)

        # Verify the file record has source_id pointing to the sentinel
        created = data["created_items"][0]
        file_id = created["file_id"]
        with SessionLocal() as session:
            f = session.query(File).filter(File.id == file_id).first()
            self.assertIsNotNone(f)
            sentinel = session.query(Source).filter(
                Source.path == "__workbench_managed_import__"
            ).first()
            self.assertEqual(f.source_id, sentinel.id)
            self.assertEqual(f.storage_state, "inbox")

        # Source file preserved (copy-only)
        self.assertTrue(src_file.exists())
        self.assertEqual(src_file.read_bytes(), b"fake-jpeg-content")
