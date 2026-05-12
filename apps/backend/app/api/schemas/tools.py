from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


ToolRunStatus = Literal["pending", "running", "succeeded", "failed", "cancelled"]
VideoMergeMode = Literal["copy", "reencode"]
VideoMergeSourceKind = Literal["indexed_file", "external_path"]


class ToolItemResponse(BaseModel):
    key: str
    title_key: str
    description_key: str
    category: str


class ToolListResponse(BaseModel):
    items: list[ToolItemResponse]


class VideoMergeInputItem(BaseModel):
    source_kind: VideoMergeSourceKind
    file_id: int | None = Field(default=None, ge=1)
    path: str | None = None

    @field_validator("path", mode="before")
    @classmethod
    def normalize_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class VideoMergeRunCreateRequest(BaseModel):
    inputs: list[VideoMergeInputItem] = Field(min_length=2, max_length=100)
    output_name: str = Field(min_length=1)
    output_dir: str | None = None
    mode: VideoMergeMode

    @field_validator("output_name", "output_dir", mode="before")
    @classmethod
    def trim_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ToolRunCreateResponse(BaseModel):
    run_id: int
    status: ToolRunStatus


class ToolRunResponse(BaseModel):
    id: int
    tool_key: str
    status: ToolRunStatus
    input: dict
    output: dict | None
    output_path: str | None
    final_output_name: str | None
    log_tail: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ToolRunListResponse(BaseModel):
    items: list[ToolRunResponse]
    page: int
    page_size: int
    total: int
