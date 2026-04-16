import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session.session import SessionLocal
from app.db.session.engine import engine
from app.main import app


class Phase0SmokeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()

    def test_phase0_smoke_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            (source_dir / "sample.txt").write_text("phase 0 smoke file", encoding="utf-8")

            with TestClient(app) as client:
                health_response = client.get("/health")
                self.assertEqual(200, health_response.status_code)
                self.assertEqual({"status": "ok"}, health_response.json())

                status_response = client.get("/system/status")
                self.assertEqual(200, status_response.status_code)
                status_payload = status_response.json()
                self.assertEqual("ok", status_payload["app"])
                self.assertEqual("ok", status_payload["database"])

                create_response = client.post(
                    "/sources",
                    json={"path": str(source_dir), "display_name": "Smoke Source"},
                )
                self.assertEqual(201, create_response.status_code)
                created_source = create_response.json()
                self.assertEqual(str(source_dir), created_source["path"])

                list_response = client.get("/sources")
                self.assertEqual(200, list_response.status_code)
                listed_sources = list_response.json()["items"]
                self.assertTrue(any(item["id"] == created_source["id"] for item in listed_sources))

                scan_response = client.post(f"/sources/{created_source['id']}/scan")
                self.assertEqual(202, scan_response.status_code)
                scan_payload = scan_response.json()
                self.assertIn("task_id", scan_payload)
                self.assertEqual("succeeded", scan_payload["status"])

        engine.dispose()

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM tasks"))
            session.execute(text("DELETE FROM file_metadata"))
            session.execute(text("DELETE FROM file_tags"))
            session.execute(text("DELETE FROM file_user_meta"))
            session.execute(text("DELETE FROM files"))
            session.execute(text("DELETE FROM source_ignore_rules"))
            session.execute(text("DELETE FROM tags"))
            session.execute(text("DELETE FROM sources"))
            session.commit()


if __name__ == "__main__":
    unittest.main()
