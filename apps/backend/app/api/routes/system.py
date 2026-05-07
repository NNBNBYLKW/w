from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.common import HealthResponse, RuntimeDiagnosticsResponse, SystemStatusResponse
from app.db.session.session import get_db
from app.services.diagnostics.runtime import get_runtime_diagnostics
from app.services.system.service import SystemService


router = APIRouter()
system_service = SystemService()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/debug/runtime", response_model=RuntimeDiagnosticsResponse)
def runtime_diagnostics() -> RuntimeDiagnosticsResponse:
    return RuntimeDiagnosticsResponse(**get_runtime_diagnostics())


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_db)) -> SystemStatusResponse:
    return system_service.get_status(db)
