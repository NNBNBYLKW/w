from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


FileTypeFilter = Literal["image", "video", "document", "archive", "other"]
SearchSortBy = Literal["modified_at", "name", "discovered_at"]
SortOrder = Literal["asc", "desc"]


class SearchQueryParams(BaseModel):
    query: str | None = None
    file_type: FileTypeFilter | None = None
    tag_id: int | None = Field(default=None, ge=1)
    color_tag: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    sort_by: SearchSortBy = "modified_at"
    sort_order: SortOrder = "desc"

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @field_validator("color_tag", mode="before")
    @classmethod
    def normalize_color_tag(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class SearchResultItemResponse(BaseModel):
    id: int
    name: str
    path: str
    file_type: FileTypeFilter
    modified_at: datetime


class SearchResponse(BaseModel):
    items: list[SearchResultItemResponse]
    page: int
    page_size: int
    total: int
