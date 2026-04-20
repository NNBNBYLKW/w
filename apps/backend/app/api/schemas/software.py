from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.file import FileListSortBy, SortOrder


SoftwareFormatValue = Literal["exe", "msi", "zip"]


class SoftwareListQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    sort_by: FileListSortBy = "modified_at"
    sort_order: SortOrder = "desc"


class SoftwareListItemResponse(BaseModel):
    id: int
    display_title: str
    software_format: SoftwareFormatValue
    path: str
    modified_at: datetime
    size_bytes: int | None


class SoftwareListResponse(BaseModel):
    items: list[SoftwareListItemResponse]
    page: int
    page_size: int
    total: int
