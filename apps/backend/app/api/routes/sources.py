from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.schemas.common import MessageResponse
from app.api.schemas.source import (
    SourceCreateRequest,
    SourceListResponse,
    SourceResponse,
    SourceUpdateRequest,
    TriggerScanResponse,
)
from app.db.session.session import get_db
from app.services.source_management.service import SourceManagementService


router = APIRouter(prefix="/sources", tags=["sources"])
source_service = SourceManagementService()


@router.get("", response_model=SourceListResponse)
def list_sources(db: Session = Depends(get_db)) -> SourceListResponse:
    return SourceListResponse(items=source_service.list_sources(db))


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreateRequest, db: Session = Depends(get_db)) -> SourceResponse:
    return source_service.create_source(db, payload)


@router.patch("/{source_id}", response_model=SourceResponse)
def update_source(source_id: int, payload: SourceUpdateRequest, db: Session = Depends(get_db)) -> SourceResponse:
    return source_service.update_source(db, source_id, payload)


@router.delete("/{source_id}", response_model=MessageResponse)
def delete_source(source_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    source_service.delete_source(db, source_id)
    return MessageResponse(message="Source deleted.")


@router.post("/{source_id}/scan", response_model=TriggerScanResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_scan(source_id: int, db: Session = Depends(get_db)) -> TriggerScanResponse:
    return source_service.trigger_scan(db, source_id)
