from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.common import HealthResponse, SystemStatusResponse
from app.db.session.session import get_db
from app.services.system.service import SystemService


router = APIRouter()
system_service = SystemService()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_db)) -> SystemStatusResponse:
    return system_service.get_status(db)
