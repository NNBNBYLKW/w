import tempfile, unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.importing import InboxItem, OperationJournal
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt():
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryV2RecoveryTestCase(unittest.TestCase):
    def setUp(self):
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()

    def tearDown(self):
        self._reset_database()
        engine.dispose()

    def _reset_database(self):
        with SessionLocal() as s:
            for t in ["import_object_members","import_object_candidates","file_path_history","operation_journal","inbox_items","import_batches","organize_plan_candidates","organize_suggestions","organize_action_logs","organize_actions","organize_plans","organize_candidates","asset_metadata_cache","library_object_members","library_objects","tool_runs","tasks","file_metadata","file_tags","file_user_meta","collections","files","source_ignore_rules","tags","library_roots","sources"]:
                s.execute(text(f"DELETE FROM {t}"))
            s.commit()

    def _ensure_managed_source(self):
        with SessionLocal() as s:
            if s.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none() is None:
                s.add(Source(path="__workbench_managed_import__", display_name="MI", is_enabled=True, scan_mode="manual", last_scan_status="na", created_at=_dt(), updated_at=_dt()))
                s.commit()

    def _seed_managed_root(self, path: Path) -> int:
        with SessionLocal() as s:
            root = LibraryRoot(root_path=str(path.resolve()), display_name=path.name, root_kind="managed", is_enabled=True, is_default=True, scan_policy="manual", created_at=_dt(), updated_at=_dt())
            s.add(root)
            s.commit()
            return root.id

    # ── clean ──────────────────────────────────────────────

    def test_recovery_summary_empty_when_clean(self):
        with SessionLocal() as s:
            s.execute(text("DELETE FROM recovery_findings"))
            s.commit()
        with TestClient(app) as c:
            r = c.get("/library/import/recovery/summary")
            self.assertEqual(200, r.status_code)
            d = r.json()
            self.assertEqual(0, d["high_count"])
            self.assertEqual(0, d["orphan_inbox_count"])

    # ── orphan inbox ───────────────────────────────────────

    def test_detect_orphan_inbox_file(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            orphan = root_dir / "00_Inbox" / "orphan.txt"
            orphan.parent.mkdir(parents=True)
            orphan.write_text("orphan", encoding="utf-8")

            with TestClient(app) as c:
                c.post("/library/import/recovery/scan")
                r = c.get("/library/import/recovery/summary")
                self.assertEqual(200, r.status_code)
                self.assertGreater(r.json()["orphan_inbox_count"], 0)

            # orphan must still exist
            self.assertTrue(orphan.exists())

    # ── scan does not delete or move ───────────────────────

    def test_recovery_scan_does_not_delete_or_move_files(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            orphan = root_dir / "00_Inbox" / "safe.txt"
            orphan.parent.mkdir(parents=True)
            orphan.write_text("safe", encoding="utf-8")

            with TestClient(app) as c:
                c.post("/library/import/recovery/scan")

            self.assertTrue(orphan.exists())
            self.assertEqual("safe", orphan.read_text(encoding="utf-8"))

    # ── missing inbox copy ────────────────────────────────

    def test_detect_missing_inbox_copy(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            fake_path = str(root_dir / "00_Inbox" / "1" / "gone.txt")
            with SessionLocal() as s:
                si = s.query(Source).filter(Source.path == "__workbench_managed_import__").first()
                f = File(source_id=si.id, path=fake_path, parent_path=str(Path(fake_path).parent), name="gone.txt", file_type="document", file_kind="document", auto_placement="books", storage_state="inbox", discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt())
                s.add(f); s.commit()
                ii = InboxItem(import_batch_id=1, file_id=f.id, source_path="/orig/gone.txt", inbox_path=fake_path, status="imported", created_at=_dt(), updated_at=_dt())
                s.add(ii); s.commit()

            with TestClient(app) as c:
                c.post("/library/import/recovery/scan")
                r = c.get("/library/import/recovery/summary")
                self.assertGreater(r.json()["missing_inbox_count"], 0)

    # ── missing managed ───────────────────────────────────

    def test_detect_missing_managed_file(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            fake_path = str(root_dir / "managed" / "missing.dat")
            with SessionLocal() as s:
                si = s.query(Source).filter(Source.path == "__workbench_managed_import__").first()
                f = File(source_id=si.id, path=fake_path, parent_path=str(Path(fake_path).parent), name="missing.dat", file_type="other", file_kind="other", auto_placement="none", storage_state="managed", managed_at=_dt(), discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt())
                s.add(f); s.commit()

            with TestClient(app) as c:
                c.post("/library/import/recovery/scan")
                r = c.get("/library/import/recovery/summary")
                self.assertGreater(r.json()["missing_managed_count"], 0)

    # ── failed import ─────────────────────────────────────

    def test_detect_failed_import_item(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            with SessionLocal() as s:
                ii = InboxItem(import_batch_id=1, source_path="/no/such.mp4", inbox_path="/no/inbox.mp4", status="failed", error_message="File not found", created_at=_dt(), updated_at=_dt())
                s.add(ii); s.commit()

            with TestClient(app) as c:
                c.post("/library/import/recovery/scan")
                r = c.get("/library/import/recovery/summary")
                self.assertGreater(r.json()["failed_import_count"], 0)

    # ── incomplete batch ──────────────────────────────────

    def test_detect_incomplete_import_batch(self):
        with SessionLocal() as s:
            from app.db.models.importing import ImportBatch
            s.add(ImportBatch(source_kind="file_selection", status="created", import_method="copy", created_at=_dt()))
            s.commit()

        with TestClient(app) as c:
            c.post("/library/import/recovery/scan")
            r = c.get("/library/import/recovery/summary")
            self.assertGreater(r.json()["incomplete_batch_count"], 0)

    # ── incomplete journal ────────────────────────────────

    def test_detect_incomplete_journal_operation(self):
        with SessionLocal() as s:
            s.add(OperationJournal(operation_id="op-001", operation_type="import_copy", entity_type="inbox_item", status="started", created_at=_dt()))
            s.commit()

        with TestClient(app) as c:
            c.post("/library/import/recovery/scan")
            r = c.get("/library/import/recovery/summary")
            self.assertGreater(r.json()["incomplete_journal_count"], 0)

    # ── retry failed import ───────────────────────────────

    def test_retry_failed_import_preserves_source(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            src = Path(td) / "retry_me.txt"
            src.write_text("retry", encoding="utf-8")

            with TestClient(app) as c:
                batch = c.post("/library/import/batches", json={"import_method": "copy"})
                bid = batch.json()["id"]
                # create a failed item directly via DB
                with SessionLocal() as s:
                    ii = InboxItem(import_batch_id=bid, source_path=str(src), inbox_path=str(src) + ".bad", status="failed", error_message="test", created_at=_dt(), updated_at=_dt())
                    s.add(ii); s.commit()
                    iid = ii.id

                retry = c.post(f"/library/import/inbox/items/{iid}/retry")
                self.assertEqual(200, retry.status_code)

            self.assertTrue(src.exists())
            self.assertEqual("retry", src.read_text(encoding="utf-8"))

    def test_retry_failed_import_copies_to_inbox(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            src = Path(td) / "reimport.txt"
            src.write_text("hello", encoding="utf-8")

            with TestClient(app) as c:
                batch = c.post("/library/import/batches", json={"import_method": "copy"})
                bid = batch.json()["id"]
                with SessionLocal() as s:
                    ii = InboxItem(import_batch_id=bid, source_path=str(src), inbox_path="/bad/path.txt", status="failed", error_message="x", created_at=_dt(), updated_at=_dt())
                    s.add(ii); s.commit()
                    iid = ii.id

                retry = c.post(f"/library/import/inbox/items/{iid}/retry")
                self.assertEqual(200, retry.status_code)
                data = retry.json()
                self.assertTrue(Path(data["inbox_path"]).exists())

    def test_retry_failed_import_updates_status(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            src = Path(td) / "fixme.txt"
            src.write_text("fix", encoding="utf-8")

            with TestClient(app) as c:
                batch = c.post("/library/import/batches", json={"import_method": "copy"})
                bid = batch.json()["id"]
                with SessionLocal() as s:
                    ii = InboxItem(import_batch_id=bid, source_path=str(src), inbox_path="/bad/path.txt", status="failed", error_message="x", created_at=_dt(), updated_at=_dt())
                    s.add(ii); s.commit()
                    iid = ii.id

                retry = c.post(f"/library/import/inbox/items/{iid}/retry")
                self.assertEqual(200, retry.status_code)
                item = c.get(f"/library/import/inbox/items/{iid}")
                self.assertEqual("imported", item.json()["status"])

    def test_retry_failed_import_writes_journal(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            src = Path(td) / "journal_test.txt"
            src.write_text("j", encoding="utf-8")

            with TestClient(app) as c:
                batch = c.post("/library/import/batches", json={"import_method": "copy"})
                bid = batch.json()["id"]
                with SessionLocal() as s:
                    ii = InboxItem(import_batch_id=bid, source_path=str(src), inbox_path="/bad/path.txt", status="failed", error_message="x", created_at=_dt(), updated_at=_dt())
                    s.add(ii); s.commit()
                    iid = ii.id

                c.post(f"/library/import/inbox/items/{iid}/retry")
                with SessionLocal() as s:
                    journals = s.query(OperationJournal).filter(OperationJournal.operation_type == "retry_import").all()
                    self.assertGreater(len(journals), 0)
