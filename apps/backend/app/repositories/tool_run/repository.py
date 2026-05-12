from datetime import datetime

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from app.db.models.tool_run import ToolRun


class ToolRunRepository:
    def create(
        self,
        session: Session,
        *,
        tool_key: str,
        status: str,
        input_json: str,
        now: datetime,
    ) -> ToolRun:
        run = ToolRun(
            tool_key=tool_key,
            status=status,
            input_json=input_json,
            output_json=None,
            log_text=None,
            error_message=None,
            started_at=None,
            finished_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(run)
        session.flush()
        return run

    def get_by_id(self, session: Session, run_id: int) -> ToolRun | None:
        return session.get(ToolRun, run_id)

    def list_runs(self, session: Session, *, page: int, page_size: int) -> tuple[list[ToolRun], int]:
        offset = (page - 1) * page_size
        statement = select(ToolRun).order_by(ToolRun.created_at.desc(), ToolRun.id.desc()).offset(offset).limit(page_size)
        total = int(session.scalar(select(func.count()).select_from(ToolRun)) or 0)
        return list(session.scalars(statement)), total

    def mark_running(self, session: Session, run_id: int, *, now: datetime) -> ToolRun | None:
        run = self.get_by_id(session, run_id)
        if run is None:
            return None
        run.status = "running"
        run.started_at = now
        run.updated_at = now
        session.flush()
        return run

    def mark_succeeded(
        self,
        session: Session,
        run_id: int,
        *,
        output_json: str,
        log_text: str,
        now: datetime,
    ) -> ToolRun | None:
        run = self.get_by_id(session, run_id)
        if run is None:
            return None
        run.status = "succeeded"
        run.output_json = output_json
        run.log_text = log_text
        run.error_message = None
        run.finished_at = now
        run.updated_at = now
        session.flush()
        return run

    def mark_failed(
        self,
        session: Session,
        run_id: int,
        *,
        error_message: str,
        log_text: str | None,
        now: datetime,
    ) -> ToolRun | None:
        run = self.get_by_id(session, run_id)
        if run is None:
            return None
        run.status = "failed"
        run.error_message = error_message
        run.log_text = log_text
        run.finished_at = now
        run.updated_at = now
        session.flush()
        return run

    def mark_stale_active_runs_failed(self, session: Session, *, now: datetime, message: str) -> int:
        statement = (
            update(ToolRun)
            .where(ToolRun.status.in_(["pending", "running"]))
            .values(status="failed", error_message=message, finished_at=now, updated_at=now)
        )
        result = session.execute(statement)
        session.flush()
        return int(result.rowcount or 0)
