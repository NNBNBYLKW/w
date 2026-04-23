from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.file import ColorTagValue, FileListSortBy, FileRatingValue, SortOrder


MediaViewScope = Literal["all", "image", "video"]


class MediaListQueryParams(BaseModel):
    view_scope: MediaViewScope = "all"
    tag_id: int | None = Field(default=None, ge=1)
    color_tag: ColorTagValue | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    sort_by: FileListSortBy = "modified_at"
    sort_order: SortOrder = "desc"


class MediaListItemResponse(BaseModel):
    id: int
    name: str
    path: str
    file_type: Literal["image", "video"]
    modified_at: datetime
    size_bytes: int | None
    is_favorite: bool
    rating: FileRatingValue | None


class MediaListResponse(BaseModel):
    items: list[MediaListItemResponse]
    page: int
    page_size: int
    total: int
