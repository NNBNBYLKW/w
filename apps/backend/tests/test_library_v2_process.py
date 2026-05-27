import os
import tempfile
import unittest
from pathlib import Path
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db.models.file import File
from app.db.models.importing import ImportBatch, InboxItem
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.session import SessionLocal
from app.main import app


def _dt():
    return datetime.now(UTC).replace(tzinfo=None)


_SEED_COUNTER = 0


class ProcessInboxItemTestCase(unittest.TestCase):
    def setUp(self):
        global _SEED_COUNTER
        _SEED_COUNTER += 1
        with SessionLocal() as s:
            if s.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none() is None:
                s.add(Source(path="__workbench_managed_import__", display_name="MI",
                    is_enabled=True, scan_mode="manual", last_scan_status="na",
                    created_at=_dt(), updated_at=_dt()))
                s.commit()

    def _seed_root(self, path: Path) -> int:
        with SessionLocal() as s:
            root = LibraryRoot(root_path=str(path.resolve()), display_name=path.name,
                root_kind="managed", is_enabled=True, is_default=True,
                scan_policy="manual", created_at=_dt(), updated_at=_dt())
            s.add(root); s.commit()
            return root.id

    def _seed_inbox_item(self, root_id: int, inbox_path: Path) -> int:
        with SessionLocal() as s:
            batch = ImportBatch(source_kind="file_selection", status="completed",
                import_method="copy", created_at=_dt())
            s.add(batch); s.commit()
            si = s.query(Source).filter(Source.path == "__workbench_managed_import__").first()
            f = File(source_id=si.id, path=str(inbox_path), parent_path=str(inbox_path.parent),
                name=inbox_path.name, file_type="document", file_kind="document",
                auto_placement="books", storage_state="inbox",
                managed_root_id=root_id, discovered_at=_dt(),
                last_seen_at=_dt(), updated_at=_dt())
            s.add(f); s.commit()
            item = InboxItem(import_batch_id=batch.id, file_id=f.id,
                source_path=str(inbox_path), inbox_path=str(inbox_path),
                status="imported", detected_object_type="docset",
                detected_file_kind="document", created_at=_dt(), updated_at=_dt())
            s.add(item); s.commit()
            return item.id

    def test_process_creates_candidate_and_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Lib"
            root_dir.mkdir()
            rid = self._seed_root(root_dir)
            inbox_file = Path(td) / f"test_{_SEED_COUNTER}.txt"
            inbox_file.write_text("test content")
            item_id = self._seed_inbox_item(rid, inbox_file)
            with TestClient(app) as c:
                r = c.post(f"/library/import/inbox/items/{item_id}/process",
                    json={"final_object_type": "docset", "target_library_root_id": rid})
                self.assertEqual(200, r.status_code)
                d = r.json()
                self.assertIn("plan_id", d)
                self.assertIn("candidate_id", d)
                self.assertEqual("draft", d["plan_status"])

    def test_process_rejects_empty_type(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Lib"
            root_dir.mkdir()
            rid = self._seed_root(root_dir)
            inbox_file = Path(td) / f"test_{_SEED_COUNTER}.txt"
            inbox_file.write_text("test content")
            item_id = self._seed_inbox_item(rid, inbox_file)
            with TestClient(app) as c:
                r = c.post(f"/library/import/inbox/items/{item_id}/process",
                    json={"final_object_type": "", "target_library_root_id": rid})
                self.assertEqual(400, r.status_code)

    def test_process_returns_400_for_missing_item(self):
        with TestClient(app) as c:
            r = c.post("/library/import/inbox/items/99999/process",
                json={"final_object_type": "docset", "target_library_root_id": 1})
            self.assertEqual(400, r.status_code)


if __name__ == "__main__":
    unittest.main()
