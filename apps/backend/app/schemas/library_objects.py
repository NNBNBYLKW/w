from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


LibraryObjectSortBy = Literal["last_scanned_at", "updated_at", "title", "object_type", "root_path"]
SortOrder = Literal["asc", "desc"]


class LibraryObjectScanRequest(BaseModel):
    root_path: str | None = None
    source_id: int | None = None
    dry_run: bool = False


class LibraryObjectScanResponse(BaseModel):
    scanned_roots: int
    objects_found: int
    objects_created: int
    objects_updated: int
    needs_review: int
    errors: list[str] = Field(default_factory=list)


class LibraryObjectListItem(BaseModel):
    id: int
    object_type: str
    type_prefix: str
    title: str | None
    display_title: str
    year: int | None
    tags: list[str]
    root_path: str
    cover_path: str | None
    primary_file_path: str | None
    metadata_source: str
    needs_review: bool
    review_reason: str | None
    last_scanned_at: datetime
    members_count: int


class LibraryObjectListResponse(BaseModel):
    items: list[LibraryObjectListItem]
    total: int
    page: int
    page_size: int


class AssetMetadataSummary(BaseModel):
    yaml_path: str | None
    schema_version: int | None
    parse_status: str
    parse_error: str | None


class LibraryObjectMemberItem(BaseModel):
    id: int
    object_id: int
    file_id: int | None
    relative_path: str
    absolute_path: str
    member_role: str
    sort_index: int | None
    hidden_from_global: bool
    extension: str | None
    size_bytes: int | None
    modified_at: datetime | None


class LibraryObjectDetailResponse(BaseModel):
    object: LibraryObjectListItem
    asset_metadata: AssetMetadataSummary | None
    members: list[LibraryObjectMemberItem]
    members_total: int
    members_page: int
    members_page_size: int


class LibraryObjectMembersResponse(BaseModel):
    items: list[LibraryObjectMemberItem]
    total: int
    page: int
    page_size: int


class LibraryOverviewStatsResponse(BaseModel):
    total_objects: int
    needs_review_count: int
    object_type_counts: dict[str, int]
    asset_yaml_ok_count: int
    asset_yaml_invalid_count: int
    unknown_object_count: int
    last_object_scan_at: datetime | None
