from datetime import datetime

from pydantic import BaseModel, Field


class CreateLibraryRootRequest(BaseModel):
    root_path: str = Field(min_length=1)
    display_name: str | None = None


class UpdateLibraryRootRequest(BaseModel):
    display_name: str | None = None
    is_enabled: bool | None = None
    scan_policy: str | None = None


class LibraryRootItem(BaseModel):
    id: int
    root_path: str
    display_name: str | None
    root_kind: str
    is_enabled: bool
    is_default: bool
    scan_policy: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LibraryRootListResponse(BaseModel):
    items: list[LibraryRootItem]
