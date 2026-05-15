from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ImportBatchCreateRequest(BaseModel):
    import_method: str = "copy"
    target_library_root_id: int | None = None


class ImportBatchResponse(BaseModel):
    id: int
    status: str
    source_kind: str
    import_method: str
    file_count: int
    completed_count: int
    failed_count: int
    created_at: datetime
    finished_at: datetime | None = None
    error_summary: str | None = None

    model_config = {"from_attributes": True}


class ImportFilesRequest(BaseModel):
    paths: list[str]


class ImportFilesResponse(BaseModel):
    batch_id: int
    created_items: list[dict] = []
    failed_items: list[dict] = []


class InboxItemResponse(BaseModel):
    id: int
    import_batch_id: int
    file_id: int | None = None
    source_path: str
    inbox_path: str
    status: str
    detected_file_kind: str | None = None
    detected_placement: str | None = None
    detected_object_type: str | None = None
    final_object_type: str | None = None
    target_library_root_id: int | None = None
    organize_candidate_id: int | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImportBatchListResponse(BaseModel):
    items: list[ImportBatchResponse]
    total: int
    page: int
    page_size: int


class InboxItemListResponse(BaseModel):
    items: list[InboxItemResponse]
    total: int
    page: int
    page_size: int


class ImportFolderRequest(BaseModel):
    paths: list[str]
    mode: str = "object"


class ImportFolderResponse(BaseModel):
    batch_id: int
    object_candidates: list[dict] = []
    created_items: list[dict] = []
    failed_items: list[dict] = []


class ObjectCandidateResponse(BaseModel):
    id: int
    import_batch_id: int
    source_root_path: str
    inbox_root_path: str
    suggested_object_type: str | None = None
    final_object_type: str | None = None
    confidence: str | None = None
    status: str
    primary_file_id: int | None = None
    launch_file_id: int | None = None
    member_count: int
    reason_json: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ObjectCandidateMemberResponse(BaseModel):
    id: int
    inbox_item_id: int
    role: str
    confidence: str | None = None
    reason: str | None = None
    source_path: str | None = None
    inbox_path: str | None = None
    file_id: int | None = None


class ObjectCandidateDetailResponse(BaseModel):
    id: int
    import_batch_id: int
    source_root_path: str
    inbox_root_path: str
    suggested_object_type: str | None = None
    final_object_type: str | None = None
    confidence: str | None = None
    status: str
    launch_file_id: int | None = None
    primary_file_id: int | None = None
    member_count: int
    reason_json: str | None = None
    created_at: str | None = None
    members: list[ObjectCandidateMemberResponse] = []


class ObjectCandidateListResponse(BaseModel):
    items: list[ObjectCandidateResponse]
    total: int
    page: int
    page_size: int


class ObjectCandidateUpdateRequest(BaseModel):
    final_object_type: str | None = None
    launch_file_id: int | None = None


class LibraryV2CapabilityResponse(BaseModel):
    status: str = "data_foundation"
    import_enabled: bool = False
    inbox_enabled: bool = False
