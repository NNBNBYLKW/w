from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.schemas.common import SystemStatusResponse
from app.core.config.settings import settings
from app.db.models.file import File
from app.db.models.source import Source
from app.db.models.task import Task
from app.services.importing.service import import_service


class SystemService:
    def get_status(self, session: Session) -> SystemStatusResponse:
        session.execute(text("SELECT 1"))
        sources_count = session.scalar(select(func.count(Source.id))) or 0
        tasks_count = session.scalar(select(func.count(Task.id))) or 0
        files_count = session.scalar(select(func.count(File.id))) or 0
        capability = import_service.get_capability()

        last_backup_at: str | None = None
        backup_dir = settings.data_dir / "backups"
        if backup_dir.is_dir():
            backups = sorted(backup_dir.glob("workbench_*.db"), key=lambda p: p.stat().st_mtime)
            if backups:
                last_backup_at = str(backups[-1].stat().st_mtime)

        return SystemStatusResponse(
            app="ok",
            database="ok",
            sources_count=int(sources_count),
            tasks_count=int(tasks_count),
            files_count=int(files_count),
            library_v2_status=capability.status,
            last_backup_at=last_backup_at,
        )
