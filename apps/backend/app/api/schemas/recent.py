from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.api.schemas.file import FileTypeValue, SortOrder


class RecentListQueryParams(BaseModel):
    range: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    sort_order: SortOrder = "desc"

    @field_validator("range", mode="before")
    @classmethod
    def normalize_range(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class RecentListItemResponse(BaseModel):
    id: int
    name: str
    path: str
    file_type: FileTypeValue
    discovered_at: datetime
    size_bytes: int | None


class RecentListResponse(BaseModel):
    items: list[RecentListItemResponse]
    page: int
    page_size: int
    total: int


class RecentActivityListItemResponse(BaseModel):
    id: int
    name: str
    path: str
    file_type: FileTypeValue
    occurred_at: datetime
    size_bytes: int | None


class RecentActivityListResponse(BaseModel):
    items: list[RecentActivityListItemResponse]
    page: int
    page_size: int
    total: int
