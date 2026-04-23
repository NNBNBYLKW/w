from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.file import ColorTagValue, FileListSortBy, FileRatingValue, FileStatusValue, SortOrder


GameFormatValue = Literal["exe", "lnk"]


class GamesListQueryParams(BaseModel):
    status: FileStatusValue | None = None
    tag_id: int | None = Field(default=None, ge=1)
    color_tag: ColorTagValue | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    sort_by: FileListSortBy = "modified_at"
    sort_order: SortOrder = "desc"


class GameListItemResponse(BaseModel):
    id: int
    display_title: str
    game_format: GameFormatValue
    path: str
    modified_at: datetime
    size_bytes: int | None
    status: FileStatusValue | None
    is_favorite: bool
    rating: FileRatingValue | None


class GamesListResponse(BaseModel):
    items: list[GameListItemResponse]
    page: int
    page_size: int
    total: int
