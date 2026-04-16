import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.db.models.file import File
from app.db.models.source import Source
from app.db.models.task import Task
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


class Phase1BDeleteSyncTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()

    def test_successful_rescan_marks_missing_files_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            file_a = root / "a.txt"
            file_b = root / "b.txt"
            file_a.write_text("a", encoding="utf-8")
            file_b.write_text("b", encoding="utf-8")

            with TestClient(app) as client:
                source_id = self._create_source(client, root)

                first_scan = client.post(f"/sources/{source_id}/scan")
                self.assertEqual(202, first_scan.status_code)
                self.assertEqual("succeeded", first_scan.json()["status"])

                first_rows = self._fetch_files_for_source(source_id)
                first_by_name = {row.name: row for row in first_rows}
                deleted_row_before = first_by_name["b.txt"]
                visible_row_before = first_by_name["a.txt"]

                file_b.unlink()

                second_scan = client.post(f"/sources/{source_id}/scan")
                self.assertEqual(202, second_scan.status_code)
                self.assertEqual("succeeded", second_scan.json()["status"])

            second_rows = self._fetch_files_for_source(source_id)
            second_by_name = {row.name: row for row in second_rows}

            self.assertFalse(second_by_name["a.txt"].is_deleted)
            self.assertTrue(second_by_name["b.txt"].is_deleted)
            self.assertEqual(deleted_row_before.discovered_at, second_by_name["b.txt"].discovered_at)
            self.assertEqual(deleted_row_before.last_seen_at, second_by_name["b.txt"].last_seen_at)
            self.assertGreater(second_by_name["b.txt"].updated_at, deleted_row_before.updated_at)
            self.assertGreater(second_by_name["a.txt"].last_seen_at, visible_row_before.last_seen_at)

        engine.dispose()

    def test_delete_sync_is_source_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as dir_a, tempfile.TemporaryDirectory() as dir_b:
            root_a = Path(dir_a)
            root_b = Path(dir_b)
            (root_a / "only-a.txt").write_text("a", encoding="utf-8")
            (root_b / "only-b.txt").write_text("b", encoding="utf-8")

            with TestClient(app) as client:
                source_a = self._create_source(client, root_a)
                source_b = self._create_source(client, root_b)

                self.assertEqual("succeeded", client.post(f"/sources/{source_a}/scan").json()["status"])
                self.assertEqual("succeeded", client.post(f"/sources/{source_b}/scan").json()["status"])

                rows_b_before = {row.name: row for row in self._fetch_files_for_source(source_b)}
                (root_a / "only-a.txt").unlink()

                second_scan = client.post(f"/sources/{source_a}/scan")
                self.assertEqual(202, second_scan.status_code)
                self.assertEqual("succeeded", second_scan.json()["status"])

            rows_a = {row.name: row for row in self._fetch_files_for_source(source_a)}
            rows_b_after = {row.name: row for row in self._fetch_files_for_source(source_b)}

            self.assertTrue(rows_a["only-a.txt"].is_deleted)
            self.assertFalse(rows_b_after["only-b.txt"].is_deleted)
            self.assertEqual(rows_b_before["only-b.txt"].updated_at, rows_b_after["only-b.txt"].updated_at)
            self.assertEqual(rows_b_before["only-b.txt"].last_seen_at, rows_b_after["only-b.txt"].last_seen_at)

        engine.dispose()

    def test_successful_empty_scan_marks_all_current_source_rows_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "first.txt").write_text("1", encoding="utf-8")
            (root / "second.txt").write_text("2", encoding="utf-8")

            with TestClient(app) as client:
                source_id = self._create_source(client, root)
                self.assertEqual("succeeded", client.post(f"/sources/{source_id}/scan").json()["status"])

                for child in root.iterdir():
                    child.unlink()

                second_scan = client.post(f"/sources/{source_id}/scan")
                self.assertEqual(202, second_scan.status_code)
                self.assertEqual("succeeded", second_scan.json()["status"])

            rows = self._fetch_files_for_source(source_id)
            self.assertTrue(rows)
            self.assertTrue(all(row.is_deleted for row in rows))

        engine.dispose()

    def test_already_deleted_rows_are_not_rewritten_every_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            survivor = root / "survivor.txt"
            missing = root / "missing.txt"
            survivor.write_text("stay", encoding="utf-8")
            missing.write_text("gone", encoding="utf-8")

            with TestClient(app) as client:
                source_id = self._create_source(client, root)
                self.assertEqual("succeeded", client.post(f"/sources/{source_id}/scan").json()["status"])

                missing.unlink()
                self.assertEqual("succeeded", client.post(f"/sources/{source_id}/scan").json()["status"])
                rows_after_delete = {row.name: row for row in self._fetch_files_for_source(source_id)}
                deleted_once = rows_after_delete["missing.txt"]

                self.assertEqual("succeeded", client.post(f"/sources/{source_id}/scan").json()["status"])

            rows_after_repeat = {row.name: row for row in self._fetch_files_for_source(source_id)}
            deleted_twice = rows_after_repeat["missing.txt"]

            self.assertTrue(deleted_once.is_deleted)
            self.assertTrue(deleted_twice.is_deleted)
            self.assertEqual(deleted_once.updated_at, deleted_twice.updated_at)
            self.assertEqual(deleted_once.last_seen_at, deleted_twice.last_seen_at)

        engine.dispose()

    def test_failure_after_seen_upsert_does_not_apply_partial_delete_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            survivor = root / "survivor.txt"
            missing = root / "missing.txt"
            survivor.write_text("stay", encoding="utf-8")
            missing.write_text("gone", encoding="utf-8")

            with TestClient(app) as client:
                source_id = self._create_source(client, root)
                self.assertEqual("succeeded", client.post(f"/sources/{source_id}/scan").json()["status"])

                rows_before_failure = {row.name: row for row in self._fetch_files_for_source(source_id)}
                missing.unlink()

                with patch(
                    "app.repositories.file.repository.FileRepository.mark_unseen_files_deleted",
                    side_effect=RuntimeError("Injected delete-sync failure"),
                ):
                    failed_scan = client.post(f"/sources/{source_id}/scan")

                self.assertEqual(202, failed_scan.status_code)
                self.assertEqual("failed", failed_scan.json()["status"])

            rows_after_failure = {row.name: row for row in self._fetch_files_for_source(source_id)}
            latest_task = self._fetch_latest_task()
            source = self._fetch_source(source_id)

            self.assertEqual("failed", latest_task.status)
            self.assertEqual("failed", source.last_scan_status)
            self.assertFalse(rows_after_failure["missing.txt"].is_deleted)
            self.assertEqual(
                rows_before_failure["missing.txt"].last_seen_at,
                rows_after_failure["missing.txt"].last_seen_at,
            )
            self.assertEqual(
                rows_before_failure["survivor.txt"].last_seen_at,
                rows_after_failure["survivor.txt"].last_seen_at,
            )

        engine.dispose()

    def _create_source(self, client: TestClient, root: Path) -> int:
        response = client.post("/sources", json={"path": str(root), "display_name": root.name})
        self.assertEqual(201, response.status_code)
        return response.json()["id"]

    def _fetch_files_for_source(self, source_id: int) -> list[File]:
        with SessionLocal() as session:
            statement = select(File).where(File.source_id == source_id).order_by(File.path.asc())
            return list(session.scalars(statement))

    def _fetch_latest_task(self) -> Task:
        with SessionLocal() as session:
            statement = select(Task).order_by(Task.id.desc())
            task = session.scalars(statement).first()
            assert task is not None
            return task

    def _fetch_source(self, source_id: int) -> Source:
        with SessionLocal() as session:
            source = session.get(Source, source_id)
            assert source is not None
            return source

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
