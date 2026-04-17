from typing import Literal

from pydantic import BaseModel, Field


TagFileListSortBy = Literal["modified_at", "name", "discovered_at"]
TagFileListSortOrder = Literal["asc", "desc"]


class TagCreateRequest(BaseModel):
    name: str


class TagItemResponse(BaseModel):
    id: int
    name: str


class TagResponse(BaseModel):
    item: TagItemResponse


class TagListResponse(BaseModel):
    items: list[TagItemResponse]


class TagFileListQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    sort_by: TagFileListSortBy = "modified_at"
    sort_order: TagFileListSortOrder = "desc"
