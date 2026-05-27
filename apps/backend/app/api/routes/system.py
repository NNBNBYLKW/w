import shutil
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.common import HealthResponse, MessageResponse, RuntimeDiagnosticsResponse, SystemStatusResponse
from app.core.config.settings import settings
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


@router.post("/debug/thumbnails/clear-cache", response_model=MessageResponse)
def clear_thumbnail_cache() -> MessageResponse:
    """Delete all thumbnail cache files."""
    thumbnail_dir = settings.data_dir / "thumbnails"
    if thumbnail_dir.exists():
        shutil.rmtree(thumbnail_dir)
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
    return MessageResponse(message="Thumbnail cache cleared.")
