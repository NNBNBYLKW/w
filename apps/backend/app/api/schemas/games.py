from datetime import datetime
from pydantic import BaseModel, Field

from app.api.schemas.file import ColorTagValue, FileKindValue, FileListSortBy, FileRatingValue, FileStatusValue, ManualPlacementValue, PlacementValue, SortOrder


GameFormatValue = str


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
    file_kind: FileKindValue
    auto_placement: PlacementValue
    manual_placement: ManualPlacementValue | None
    effective_placement: PlacementValue
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
