from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.task import Task


class TaskRepository:
    def add(self, session: Session, task: Task) -> Task:
        session.add(task)
        session.flush()
        return task

    def get_active_scan_task_for_source(self, session: Session, source_id: int) -> Task | None:
        statement = (
            select(Task)
            .where(Task.task_type == "scan_source")
            .where(Task.source_id == source_id)
            .where(Task.status.in_(("pending", "running")))
            .order_by(Task.id.desc())
        )
        return session.scalars(statement).first()

    def list_latest_scan_tasks_by_source_ids(self, session: Session, source_ids: list[int]) -> dict[int, Task]:
        if not source_ids:
            return {}

        latest_task_ids = (
            select(
                Task.source_id.label("source_id"),
                func.max(Task.id).label("task_id"),
            )
            .where(Task.task_type == "scan_source")
            .where(Task.source_id.in_(source_ids))
            .group_by(Task.source_id)
            .subquery()
        )

        statement = (
            select(Task)
            .join(latest_task_ids, Task.id == latest_task_ids.c.task_id)
            .order_by(Task.id.desc())
        )
        latest_tasks = list(session.scalars(statement))
        return {task.source_id: task for task in latest_tasks if task.source_id is not None}
