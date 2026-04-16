from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.schemas.common import SystemStatusResponse
from app.db.models.file import File
from app.db.models.source import Source
from app.db.models.task import Task


class SystemService:
    def get_status(self, session: Session) -> SystemStatusResponse:
        session.execute(text("SELECT 1"))
        sources_count = session.scalar(select(func.count(Source.id))) or 0
        tasks_count = session.scalar(select(func.count(Task.id))) or 0
        files_count = session.scalar(select(func.count(File.id))) or 0
        return SystemStatusResponse(
            app="ok",
            database="ok",
            sources_count=int(sources_count),
            tasks_count=int(tasks_count),
            files_count=int(files_count),
        )
