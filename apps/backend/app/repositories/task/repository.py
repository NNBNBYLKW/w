from sqlalchemy.orm import Session

from app.db.models.task import Task


class TaskRepository:
    def add(self, session: Session, task: Task) -> Task:
        session.add(task)
        session.flush()
        return task
