import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.db.models.task import Task
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 17, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase2DScanRuntimeHardeningTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_rejects_same_source_scan_when_pending_task_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_id = self._create_source(root)
            self._insert_task(source_id=source_id, task_type="scan_source", status="pending", created_at=_dt(9, 0))

            with TestClient(app) as client:
                response = client.post(f"/sources/{source_id}/scan")

        self.assertEqual(409, response.status_code)
        self.assertEqual(
            {"error": {"code": "SCAN_ALREADY_RUNNING", "message": "A scan is already running for this source."}},
            response.json(),
        )
        self.assertEqual(1, self._count_tasks())

    def test_rejects_same_source_scan_when_running_task_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_id = self._create_source(root)
            self._insert_task(
                source_id=source_id,
                task_type="scan_source",
                status="running",
                created_at=_dt(9, 0),
                started_at=_dt(9, 1),
            )

            with TestClient(app) as client:
                response = client.post(f"/sources/{source_id}/scan")

        self.assertEqual(409, response.status_code)
        self.assertEqual("SCAN_ALREADY_RUNNING", response.json()["error"]["code"])
        self.assertEqual(1, self._count_tasks())

    def test_does_not_reject_scan_for_different_source_when_another_source_has_active_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_a_root = root / "a"
            source_b_root = root / "b"
            source_a_root.mkdir()
            source_b_root.mkdir()
            (source_b_root / "sample.txt").write_text("scan me", encoding="utf-8")

            source_a = self._create_source(source_a_root)
            source_b = self._create_source(source_b_root)
            self._insert_task(source_id=source_a, task_type="scan_source", status="running", created_at=_dt(9, 0), started_at=_dt(9, 1))

            with TestClient(app) as client:
                response = client.post(f"/sources/{source_b}/scan")

        self.assertEqual(202, response.status_code)
        self.assertEqual("succeeded", response.json()["status"])
        latest_task = self._latest_task()
        self.assertIsNotNone(latest_task)
        self.assertEqual(source_b, latest_task.source_id)

    def test_trigger_scan_success_response_shape_remains_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "sample.txt").write_text("shape check", encoding="utf-8")
            source_id = self._create_source(root)

            with TestClient(app) as client:
                response = client.post(f"/sources/{source_id}/scan")

        self.assertEqual(202, response.status_code)
        self.assertEqual({"task_id", "status"}, set(response.json().keys()))
        self.assertEqual("succeeded", response.json()["status"])

    def test_list_sources_returns_last_scan_error_message_from_latest_failed_scan_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_id = self._create_source(root)
            self._insert_task(
                source_id=source_id,
                task_type="scan_source",
                status="failed",
                created_at=_dt(10, 0),
                finished_at=_dt(10, 5),
                error_message="Directory became unavailable.",
            )

            with TestClient(app) as client:
                response = client.get("/sources")

        self.assertEqual(200, response.status_code)
        listed_source = next(item for item in response.json()["items"] if item["id"] == source_id)
        self.assertEqual("Directory became unavailable.", listed_source["last_scan_error_message"])

    def test_list_sources_returns_null_error_message_when_latest_scan_task_succeeded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "sample.txt").write_text("ok", encoding="utf-8")
            source_id = self._create_source(root)
            self._insert_task(
                source_id=source_id,
                task_type="scan_source",
                status="failed",
                created_at=_dt(10, 0),
                finished_at=_dt(10, 5),
                error_message="Older failure.",
            )
            self._insert_task(
                source_id=source_id,
                task_type="scan_source",
                status="succeeded",
                created_at=_dt(11, 0),
                started_at=_dt(11, 1),
                finished_at=_dt(11, 2),
            )

            with TestClient(app) as client:
                response = client.get("/sources")

        self.assertEqual(200, response.status_code)
        listed_source = next(item for item in response.json()["items"] if item["id"] == source_id)
        self.assertIsNone(listed_source["last_scan_error_message"])

    def test_successful_rescan_clears_last_scan_error_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "sample.txt").write_text("rescan me", encoding="utf-8")
            source_id = self._create_source(root)
            self._insert_task(
                source_id=source_id,
                task_type="scan_source",
                status="failed",
                created_at=_dt(8, 0),
                finished_at=_dt(8, 5),
                error_message="Older failure.",
            )

            with TestClient(app) as client:
                before = client.get("/sources")
                scan_response = client.post(f"/sources/{source_id}/scan")
                after = client.get("/sources")

        self.assertEqual("Older failure.", next(item for item in before.json()["items"] if item["id"] == source_id)["last_scan_error_message"])
        self.assertEqual(202, scan_response.status_code)
        after_source = next(item for item in after.json()["items"] if item["id"] == source_id)
        self.assertEqual("succeeded", after_source["last_scan_status"])
        self.assertIsNone(after_source["last_scan_error_message"])

    def test_non_scan_tasks_do_not_block_scan_and_do_not_drive_last_scan_error_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "sample.txt").write_text("still scannable", encoding="utf-8")
            source_id = self._create_source(root)
            self._insert_task(
                source_id=source_id,
                task_type="refresh_preview",
                status="running",
                created_at=_dt(9, 0),
                started_at=_dt(9, 1),
            )
            self._insert_task(
                source_id=source_id,
                task_type="refresh_preview",
                status="failed",
                created_at=_dt(10, 0),
                finished_at=_dt(10, 5),
                error_message="Non-scan failure.",
            )

            with TestClient(app) as client:
                scan_response = client.post(f"/sources/{source_id}/scan")
                list_response = client.get("/sources")

        self.assertEqual(202, scan_response.status_code)
        listed_source = next(item for item in list_response.json()["items"] if item["id"] == source_id)
        self.assertIsNone(listed_source["last_scan_error_message"])

    def _create_source(self, root: Path) -> int:
        root.mkdir(parents=True, exist_ok=True)
        with TestClient(app) as client:
            response = client.post("/sources", json={"path": str(root), "display_name": root.name or "Source"})
        self.assertEqual(201, response.status_code)
        return int(response.json()["id"])

    def _insert_task(
        self,
        *,
        source_id: int,
        task_type: str,
        status: str,
        created_at: datetime,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error_message: str | None = None,
    ) -> int:
        with SessionLocal() as session:
            task = Task(
                task_type=task_type,
                status=status,
                source_id=source_id,
                target_file_id=None,
                payload_json=None,
                started_at=started_at,
                finished_at=finished_at,
                error_message=error_message,
                created_at=created_at,
                updated_at=finished_at or started_at or created_at,
            )
            session.add(task)
            session.commit()
            return int(task.id)

    def _latest_task(self) -> Task | None:
        with SessionLocal() as session:
            statement = select(Task).order_by(Task.id.desc())
            return session.scalars(statement).first()

    def _count_tasks(self) -> int:
        with SessionLocal() as session:
            statement = select(Task)
            return len(list(session.scalars(statement)))

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM collections"))
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
