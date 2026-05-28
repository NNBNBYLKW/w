import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models.file import File
from app.db.models.source import Source
from app.db.session.session import SessionLocal
from app.core.time import utcnow
from sqlalchemy import text


class GameSessionTestCase(unittest.TestCase):
    def setUp(self):
        with SessionLocal() as s:
            s.execute(text("DELETE FROM game_sessions")); s.execute(text("DELETE FROM files")); s.execute(text("DELETE FROM sources")); s.commit()
            src = Source(path="D:\\Test", created_at=utcnow(), updated_at=utcnow())
            s.add(src); s.flush()
            f = File(source_id=src.id, path="D:\\Test\\game.exe", parent_path="D:\\Test", name="game.exe", file_type="other", file_kind="executable", auto_placement="none", discovered_at=utcnow(), last_seen_at=utcnow(), updated_at=utcnow())
            s.add(f); s.flush()
            self.file_id = f.id
            s.commit()

    def tearDown(self):
        with SessionLocal() as s:
            s.execute(text("DELETE FROM game_sessions")); s.execute(text("DELETE FROM files")); s.execute(text("DELETE FROM sources")); s.commit()

    def test_start_session(self):
        with TestClient(app) as c:
            r = c.post(f"/files/{self.file_id}/sessions")
        self.assertEqual(200, r.status_code)
        self.assertIn("id", r.json())

    def test_end_session(self):
        with TestClient(app) as c:
            start = c.post(f"/files/{self.file_id}/sessions")
            sid = start.json()["id"]
            end = c.patch(f"/files/{self.file_id}/sessions/{sid}")
        self.assertEqual(200, end.status_code)
        self.assertIsNotNone(end.json()["item"]["duration_seconds"])

    def test_end_nonexistent_session(self):
        with TestClient(app) as c:
            r = c.patch(f"/files/{self.file_id}/sessions/99999")
        self.assertEqual(404, r.status_code)
