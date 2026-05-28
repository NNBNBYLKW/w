import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models.file import File
from app.db.models.source import Source
from app.db.session.session import SessionLocal
from app.core.time import utcnow
from sqlalchemy import text


class TrashTestCase(unittest.TestCase):
    def setUp(self):
        with SessionLocal() as s:
            self._safe_delete(s, ["files", "sources"])
            src = Source(path="D:\\Test", created_at=utcnow(), updated_at=utcnow())
            s.add(src); s.flush()
            f = File(source_id=src.id, path="D:\\Test\\a.txt", parent_path="D:\\Test", name="a.txt", file_type="other", file_kind="other", auto_placement="none", discovered_at=utcnow(), last_seen_at=utcnow(), updated_at=utcnow())
            s.add(f); s.flush()
            self.file_id = f.id
            s.commit()

    def tearDown(self):
        with SessionLocal() as s:
            self._safe_delete(s, ["trash_entries", "files", "sources"])

    @staticmethod
    def _safe_delete(session, tables: list[str]):
        for table in tables:
            try:
                session.execute(text(f"DELETE FROM {table}"))
            except Exception:
                pass
        session.commit()

    def test_trash_file(self):
        with TestClient(app) as c:
            r = c.post(f"/files/{self.file_id}/trash")
        self.assertEqual(200, r.status_code)

    def test_trash_already_deleted(self):
        with TestClient(app) as c:
            c.post(f"/files/{self.file_id}/trash")
            r2 = c.post(f"/files/{self.file_id}/trash")
        self.assertEqual(400, r2.status_code)

    def test_restore_file(self):
        with TestClient(app) as c:
            c.post(f"/files/{self.file_id}/trash")
            r = c.post(f"/files/{self.file_id}/restore")
        self.assertEqual(200, r.status_code)

    def test_restore_not_trashed(self):
        with TestClient(app) as c:
            r = c.post(f"/files/{self.file_id}/restore")
        self.assertEqual(404, r.status_code)

    def test_list_trash(self):
        with TestClient(app) as c:
            c.post(f"/files/{self.file_id}/trash")
            r = c.get("/trash")
        self.assertEqual(200, r.status_code)
        self.assertGreaterEqual(len(r.json()["items"]), 1)
