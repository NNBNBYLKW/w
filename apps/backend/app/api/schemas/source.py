from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceCreateRequest(BaseModel):
    path: str = Field(min_length=1)
    display_name: str | None = None


class SourceUpdateRequest(BaseModel):
    display_name: str | None = None
    is_enabled: bool | None = None


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    display_name: str | None
    is_enabled: bool
    scan_mode: str
    last_scan_at: datetime | None
    last_scan_status: str | None
    last_scan_error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class SourceListResponse(BaseModel):
    items: list[SourceResponse]


class TriggerScanResponse(BaseModel):
    task_id: int
    status: str
