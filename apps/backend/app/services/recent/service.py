from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.api.schemas.recent import (
    RecentActivityListItemResponse,
    RecentActivityListResponse,
    RecentListItemResponse,
    RecentListQueryParams,
    RecentListResponse,
)
from app.core.errors.exceptions import BadRequestError
from app.repositories.file.repository import FileRepository


def utc_now() -> datetime:
    return datetime.now(UTC)


class RecentImportsService:
    range_windows = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    def __init__(self) -> None:
        self.file_repository = FileRepository()

    def list_recent_imports(self, session: Session, params: RecentListQueryParams) -> RecentListResponse:
        query_cutoff, query_now = self._build_time_window(params.range)

        files, total = self.file_repository.list_recent_files(
            session,
            cutoff=query_cutoff,
            now=query_now,
            page=params.page,
            page_size=params.page_size,
            sort_order=params.sort_order,
        )
        items = [
            RecentListItemResponse(
                id=file.id,
                name=file.name,
                path=file.path,
                file_type=file.file_type,
                discovered_at=file.discovered_at,
                size_bytes=file.size_bytes,
            )
            for file in files
        ]
        return RecentListResponse(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
        )

    def list_recent_tagged(self, session: Session, params: RecentListQueryParams) -> RecentActivityListResponse:
        query_cutoff, query_now = self._build_time_window(params.range)
        rows, total = self.file_repository.list_recent_tagged_files(
            session,
            cutoff=query_cutoff,
            now=query_now,
            page=params.page,
            page_size=params.page_size,
            sort_order=params.sort_order,
        )
        items = [
            RecentActivityListItemResponse(
                id=file.id,
                name=file.name,
                path=file.path,
                file_type=file.file_type,
                occurred_at=occurred_at,
                size_bytes=file.size_bytes,
            )
            for file, occurred_at in rows
        ]
        return RecentActivityListResponse(items=items, page=params.page, page_size=params.page_size, total=total)

    def list_recent_color_tagged(self, session: Session, params: RecentListQueryParams) -> RecentActivityListResponse:
        query_cutoff, query_now = self._build_time_window(params.range)
        rows, total = self.file_repository.list_recent_color_tagged_files(
            session,
            cutoff=query_cutoff,
            now=query_now,
            page=params.page,
            page_size=params.page_size,
            sort_order=params.sort_order,
        )
        items = [
            RecentActivityListItemResponse(
                id=file.id,
                name=file.name,
                path=file.path,
                file_type=file.file_type,
                occurred_at=occurred_at,
                size_bytes=file.size_bytes,
            )
            for file, occurred_at in rows
        ]
        return RecentActivityListResponse(items=items, page=params.page, page_size=params.page_size, total=total)

    def _normalize_range(self, value: str | None) -> str:
        if value is None:
            return "7d"
        if value == "" or value not in self.range_windows:
            raise BadRequestError(
                "RECENT_RANGE_INVALID",
                "range must be one of: 1d, 7d, 30d.",
            )
        return value

    def _build_time_window(self, range_value: str | None) -> tuple[datetime, datetime]:
        normalized_range = self._normalize_range(range_value)
        aware_now = utc_now()
        aware_cutoff = aware_now - self.range_windows[normalized_range]
        return self._to_naive_utc(aware_cutoff), self._to_naive_utc(aware_now)

    def _to_naive_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)
