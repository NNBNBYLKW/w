import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models.source import Source
from app.db.models.task import Task
from app.repositories.file.repository import FileRepository
from app.repositories.source.repository import SourceRepository
from app.services.tasks.service import TaskService
from app.workers.scanning.scanner import ScannerWorker


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ScanningService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.source_repository = SourceRepository()
        self.task_service = TaskService()
        self.worker = ScannerWorker()

    def run_source_scan_inline(self, session: Session, source: Source, task: Task) -> Task:
        started_at = _utcnow()
        self.task_service.mark_running(task, started_at)
        source.last_scan_status = "running"
        source.updated_at = started_at
        session.commit()

        try:
            self._ensure_non_overlapping_roots(session, source)
            scanned_at = self._next_scan_marker(session, source)
            records = self.worker.scan_source(source.path)
            self.file_repository.upsert_discovered_files(session, source.id, records, scanned_at)
            self.file_repository.mark_unseen_files_deleted(session, source.id, scanned_at)

            finished_at = _utcnow()
            self.task_service.mark_succeeded(task, finished_at)
            source.last_scan_status = "succeeded"
            source.last_scan_at = scanned_at
            source.updated_at = finished_at
            session.commit()
            session.refresh(task)
            session.refresh(source)
            return task
        except Exception as exc:
            session.rollback()

            failed_task = session.get(Task, task.id)
            failed_source = self.source_repository.get_by_id(session, source.id)
            if failed_task is None or failed_source is None:
                raise

            finished_at = _utcnow()
            self.task_service.mark_failed(failed_task, str(exc), finished_at)
            failed_source.last_scan_status = "failed"
            failed_source.updated_at = finished_at
            session.commit()
            session.refresh(failed_task)
            return failed_task

    def _ensure_non_overlapping_roots(self, session: Session, source: Source) -> None:
        current_parts = self._normalized_path_parts(source.path)
        for other_source in self.source_repository.list_other_sources(session, source.id):
            other_parts = self._normalized_path_parts(other_source.path)
            if self._parts_overlap(current_parts, other_parts):
                raise ValueError("Overlapping source roots are not supported in Phase 1A.")

    def _normalized_path_parts(self, raw_path: str) -> tuple[str, ...]:
        normalized = os.path.normcase(str(Path(raw_path).resolve(strict=False)))
        return tuple(Path(normalized).parts)

    def _parts_overlap(self, left: tuple[str, ...], right: tuple[str, ...]) -> bool:
        shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
        return shorter == longer[: len(shorter)]

    def _next_scan_marker(self, session: Session, source: Source) -> datetime:
        candidate = _utcnow()
        latest_last_seen = self.file_repository.get_latest_last_seen_at_for_source(session, source.id)
        floors = [value for value in (source.last_scan_at, latest_last_seen) if value is not None]
        if not floors:
            return candidate

        floor = max(floors)
        if candidate <= floor:
            return floor + timedelta(microseconds=1)
        return candidate
