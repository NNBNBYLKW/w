from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.api.schemas.tag import TagItemResponse


FileTypeValue = Literal["image", "video", "document", "archive", "other"]
FileKindValue = Literal[
    "image",
    "video",
    "audio",
    "document",
    "ebook",
    "archive",
    "executable",
    "installer",
    "shortcut",
    "other",
]
PlacementValue = Literal["media", "books", "games", "software", "files_only", "none"]
ManualPlacementValue = Literal["media", "books", "games", "software", "files_only"]
ColorTagValue = Literal["red", "yellow", "green", "blue", "purple"]
FileStatusValue = Literal["playing", "completed", "shelved"]
FileRatingValue = Literal[1, 2, 3, 4, 5]
FileListSortBy = Literal["modified_at", "name", "discovered_at"]
SortOrder = Literal["asc", "desc"]


def normalize_directory_path(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().replace("/", "\\")
    if not normalized:
        return None

    if len(normalized) == 3 and normalized[1] == ":" and normalized[2] == "\\":
        return normalized

    return normalized.rstrip("\\")


class FileListQueryParams(BaseModel):
    source_id: int | None = Field(default=None, ge=1)
    parent_path: str | None = None
    file_kind: FileKindValue | None = None
    tag_id: int | None = Field(default=None, ge=1)
    color_tag: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    sort_by: FileListSortBy = "modified_at"
    sort_order: SortOrder = "desc"

    @field_validator("parent_path", mode="before")
    @classmethod
    def normalize_parent_path(cls, value: str | None) -> str | None:
        return normalize_directory_path(value)

    @field_validator("color_tag", mode="before")
    @classmethod
    def normalize_color_tag(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class FileListItemResponse(BaseModel):
    id: int
    name: str
    path: str
    file_type: FileTypeValue
    file_kind: FileKindValue
    auto_placement: PlacementValue
    manual_placement: ManualPlacementValue | None
    effective_placement: PlacementValue
    modified_at: datetime
    size_bytes: int | None


class FileListResponse(BaseModel):
    items: list[FileListItemResponse]
    page: int
    page_size: int
    total: int


class FileMetadataResponse(BaseModel):
    width: int | None
    height: int | None
    duration_ms: int | None
    page_count: int | None


class FileDetailItemResponse(BaseModel):
    id: int
    name: str
    path: str
    file_type: FileTypeValue
    file_kind: FileKindValue
    auto_placement: PlacementValue
    manual_placement: ManualPlacementValue | None
    effective_placement: PlacementValue
    size_bytes: int | None
    created_at_fs: datetime | None
    modified_at_fs: datetime | None
    discovered_at: datetime
    last_seen_at: datetime
    is_deleted: bool
    source_id: int
    tags: list[TagItemResponse]
    color_tag: ColorTagValue | None
    status: FileStatusValue | None
    is_favorite: bool
    rating: FileRatingValue | None
    notes: str | None = None
    metadata: FileMetadataResponse | None
    storage_state: str | None = None
    original_path: str | None = None
    managed_root_id: int | None = None
    managed_at: datetime | None = None
    inbox_item_id: int | None = None


class FileDetailResponse(BaseModel):
    item: FileDetailItemResponse


class FileVideoPreviewItemResponse(BaseModel):
    id: int
    frame_count: int
    frame_indexes: list[int]


class FileVideoPreviewResponse(BaseModel):
    item: FileVideoPreviewItemResponse


class BatchMetaUpdateRequest(BaseModel):
    file_ids: list[int] = Field(min_length=1)
    is_favorite: bool | None = None
    rating: int | None = None


class ThumbnailWarmupRequest(BaseModel):
    file_ids: list[int] = Field(min_length=1, max_length=100)


class ThumbnailWarmupResponse(BaseModel):
    cached: list[int]
    queued: list[int]
    in_progress: list[int]
    unsupported: list[int]
    missing: list[int]
    failed: list[int]



class ColorTagUpdateRequest(BaseModel):
    color_tag: str | None


class BatchTagAttachRequest(BaseModel):
    file_ids: list[int] = Field(min_length=1)
    name: str


class BatchTagAttachResponse(BaseModel):
    updated_file_ids: list[int]
    updated_count: int
    tag: TagItemResponse


class BatchColorTagUpdateRequest(BaseModel):
    file_ids: list[int] = Field(min_length=1)
    color_tag: str | None


class BatchColorTagUpdateResponse(BaseModel):
    updated_file_ids: list[int]
    updated_count: int
    color_tag: ColorTagValue | None


class BatchMetaUpdateResponse(BaseModel):
    updated_file_ids: list[int]
    updated_count: int
    is_favorite: bool | None
    rating: int | None


class FilePlacementUpdateRequest(BaseModel):
    manual_placement: ManualPlacementValue | None


class FilePlacementItemResponse(BaseModel):
    id: int
    file_kind: FileKindValue
    auto_placement: PlacementValue
    manual_placement: ManualPlacementValue | None
    effective_placement: PlacementValue


class FilePlacementResponse(BaseModel):
    item: FilePlacementItemResponse


class BatchPlacementUpdateRequest(BaseModel):
    file_ids: list[int] = Field(min_length=1)
    manual_placement: ManualPlacementValue | None


class BatchPlacementUpdateResponse(BaseModel):
    updated_file_ids: list[int]
    updated_count: int
    manual_placement: ManualPlacementValue | None


class FileColorTagItemResponse(BaseModel):
    id: int
    color_tag: ColorTagValue | None


class FileColorTagResponse(BaseModel):
    item: FileColorTagItemResponse


class FileStatusUpdateRequest(BaseModel):
    status: str | None


class FileStatusItemResponse(BaseModel):
    id: int
    status: FileStatusValue | None


class FileStatusResponse(BaseModel):
    item: FileStatusItemResponse


class FileUserMetaPatchRequest(BaseModel):
    is_favorite: Any = None
    rating: Any = None
    notes: str | None = None


class FileUserMetaItemResponse(BaseModel):
    id: int
    is_favorite: bool
    rating: FileRatingValue | None
    notes: str | None = None


class FileUserMetaResponse(BaseModel):
    item: FileUserMetaItemResponse
