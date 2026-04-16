import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.db.models.file import File
from app.db.models.source import Source
from app.db.models.task import Task
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


class Phase1AScanningTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()

    def test_scan_persists_discovered_files_and_preserves_discovered_at(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested_dir = root / "nested"
            nested_dir.mkdir()
            (root / "cover.png").write_bytes(b"png")
            (root / "clip.mp4").write_bytes(b"video")
            (root / "notes.pdf").write_text("doc", encoding="utf-8")
            (root / "bundle.zip").write_bytes(b"archive")
            (nested_dir / "unknown.bin").write_bytes(b"other")

            with TestClient(app) as client:
                create_response = client.post(
                    "/sources",
                    json={"path": str(root), "display_name": "Phase 1A Source"},
                )
                self.assertEqual(201, create_response.status_code)
                source_id = create_response.json()["id"]

                first_scan = client.post(f"/sources/{source_id}/scan")
                self.assertEqual(202, first_scan.status_code)
                self.assertEqual("succeeded", first_scan.json()["status"])

                first_rows = self._fetch_files_for_source(source_id)
                self.assertEqual(5, len(first_rows))

                by_name = {row.name: row for row in first_rows}
                self.assertEqual("image", by_name["cover.png"].file_type)
                self.assertEqual("video", by_name["clip.mp4"].file_type)
                self.assertEqual("document", by_name["notes.pdf"].file_type)
                self.assertEqual("archive", by_name["bundle.zip"].file_type)
                self.assertEqual("other", by_name["unknown.bin"].file_type)
                self.assertEqual(str(root), by_name["cover.png"].parent_path)
                self.assertEqual(str(nested_dir), by_name["unknown.bin"].parent_path)
                self.assertEqual("png", by_name["cover.png"].extension)
                self.assertFalse(any(row.is_deleted for row in first_rows))

                first_discovered_at = by_name["cover.png"].discovered_at
                first_last_seen_at = by_name["cover.png"].last_seen_at

                time.sleep(0.02)
                second_scan = client.post(f"/sources/{source_id}/scan")
                self.assertEqual(202, second_scan.status_code)
                self.assertEqual("succeeded", second_scan.json()["status"])

            second_rows = self._fetch_files_for_source(source_id)
            self.assertEqual(5, len(second_rows))
            second_by_name = {row.name: row for row in second_rows}

            self.assertEqual(first_discovered_at, second_by_name["cover.png"].discovered_at)
            self.assertGreater(second_by_name["cover.png"].last_seen_at, first_last_seen_at)

            latest_task = self._fetch_latest_task()
            self.assertIsNotNone(latest_task)
            self.assertEqual("succeeded", latest_task.status)
            self.assertIsNotNone(latest_task.started_at)
            self.assertIsNotNone(latest_task.finished_at)

            source = self._fetch_source(source_id)
            self.assertIsNotNone(source)
            self.assertEqual("succeeded", source.last_scan_status)
            self.assertIsNotNone(source.last_scan_at)

        engine.dispose()

    def test_scan_skips_directory_indirections_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real_dir = root / "real"
            real_dir.mkdir()
            (real_dir / "inside.txt").write_text("content", encoding="utf-8")

            link_dir = root / "linked"
            try:
                link_dir.symlink_to(real_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"Directory symlink creation unavailable: {exc}")

            with TestClient(app) as client:
                create_response = client.post(
                    "/sources",
                    json={"path": str(root), "display_name": "Symlink Source"},
                )
                self.assertEqual(201, create_response.status_code)
                source_id = create_response.json()["id"]

                scan_response = client.post(f"/sources/{source_id}/scan")
                self.assertEqual(202, scan_response.status_code)
                self.assertEqual("succeeded", scan_response.json()["status"])

            rows = self._fetch_files_for_source(source_id)
            paths = {row.path for row in rows}
            self.assertEqual(1, len(rows))
            self.assertIn(str((real_dir / "inside.txt").resolve(strict=False)), paths)
            self.assertTrue(all(row.parent_path == str(real_dir.resolve(strict=False)) for row in rows))

        engine.dispose()

    def _fetch_files_for_source(self, source_id: int) -> list[File]:
        with SessionLocal() as session:
            statement = select(File).where(File.source_id == source_id).order_by(File.path.asc())
            return list(session.scalars(statement))

    def _fetch_latest_task(self) -> Task | None:
        with SessionLocal() as session:
            statement = select(Task).order_by(Task.id.desc())
            return session.scalars(statement).first()

    def _fetch_source(self, source_id: int) -> Source | None:
        with SessionLocal() as session:
            return session.get(Source, source_id)

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
