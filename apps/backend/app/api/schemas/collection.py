from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.schemas.file import FileListSortBy, FileTypeValue, SortOrder, normalize_directory_path


class CollectionCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    file_type: FileTypeValue | None = None
    tag_id: int | None = Field(default=None, ge=1)
    color_tag: str | None = None
    source_id: int | None = Field(default=None, ge=1)
    parent_path: str | None = None

    @field_validator("color_tag", mode="before")
    @classmethod
    def normalize_color_tag(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("parent_path", mode="before")
    @classmethod
    def normalize_parent_path(cls, value: str | None) -> str | None:
        return normalize_directory_path(value)


class CollectionUpdateRequest(BaseModel):
    name: str | None = None
    file_type: FileTypeValue | None = None
    tag_id: int | None = Field(default=None, ge=1)
    color_tag: str | None = None
    source_id: int | None = Field(default=None, ge=1)
    parent_path: str | None = None

    @field_validator("color_tag", mode="before")
    @classmethod
    def normalize_color_tag(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("parent_path", mode="before")
    @classmethod
    def normalize_parent_path(cls, value: str | None) -> str | None:
        return normalize_directory_path(value)


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    file_type: FileTypeValue | None
    tag_id: int | None
    color_tag: str | None
    source_id: int | None
    parent_path: str | None
    created_at: datetime
    updated_at: datetime


class CollectionListResponse(BaseModel):
    items: list[CollectionResponse]


class CollectionFilesQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    sort_by: FileListSortBy = "modified_at"
    sort_order: SortOrder = "desc"
