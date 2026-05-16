"""Phase 8A: Browse v2 read model schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# ── Card types ──────────────────────────────────────────

class BrowseV2ObjectCard(BaseModel):
    card_kind: str = "object"
    namespaced_id: str
    object_source: str  # "library_object" | "import_object_candidate"
    source_id: int
    object_type: str | None = None
    display_title: str
    member_count: int = 0
    storage_state: str | None = None
    root_path: str | None = None
    needs_review: bool = False
    confidence: str | None = None
    badges: list[str] = []


class BrowseV2LooseFileCard(BaseModel):
    card_kind: str = "loose_file"
    file_id: int
    name: str
    file_kind: str | None = None
    path: str
    storage_state: str | None = None
    size_bytes: int | None = None
    modified_at: datetime | None = None
    badges: list[str] = []


# ── Response ────────────────────────────────────────────

class BrowseV2Summary(BaseModel):
    total_objects: int = 0
    total_loose_files: int = 0
    managed_objects: int = 0
    inbox_objects: int = 0
    external_loose: int = 0


class BrowseV2Response(BaseModel):
    items: list[BrowseV2ObjectCard | BrowseV2LooseFileCard] = []
    summary: BrowseV2Summary = BrowseV2Summary()
    total: int = 0
    page: int = 1
    page_size: int = 50
