import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models.task import Task
from app.repositories.task.repository import TaskRepository


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TaskService:
    def __init__(self) -> None:
        self.task_repository = TaskRepository()

    def create_pending_scan_task(self, session: Session, source_id: int) -> Task:
        now = _utcnow()
        task = Task(
            task_type="scan_source",
            status="pending",
            source_id=source_id,
            target_file_id=None,
            payload_json=json.dumps({"source_id": source_id}),
            started_at=None,
            finished_at=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        self.task_repository.add(session, task)
        session.commit()
        session.refresh(task)
        return task

    def get_active_scan_task_for_source(self, session: Session, source_id: int) -> Task | None:
        return self.task_repository.get_active_scan_task_for_source(session, source_id)

    def list_latest_scan_tasks_by_source_ids(self, session: Session, source_ids: list[int]) -> dict[int, Task]:
        return self.task_repository.list_latest_scan_tasks_by_source_ids(session, source_ids)

    def mark_running(self, task: Task, started_at: datetime) -> None:
        task.status = "running"
        task.started_at = started_at
        task.finished_at = None
        task.error_message = None
        task.updated_at = started_at

    def mark_succeeded(self, task: Task, finished_at: datetime) -> None:
        task.status = "succeeded"
        task.finished_at = finished_at
        task.error_message = None
        task.updated_at = finished_at
        if task.started_at is None:
            task.started_at = finished_at

    def mark_failed(self, task: Task, error_message: str, finished_at: datetime) -> None:
        task.status = "failed"
        task.finished_at = finished_at
        task.error_message = error_message
        task.updated_at = finished_at
        if task.started_at is None:
            task.started_at = finished_at
