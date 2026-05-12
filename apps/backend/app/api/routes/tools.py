from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.schemas.tools import (
    ToolListResponse,
    ToolRunCreateResponse,
    ToolRunListResponse,
    ToolRunResponse,
    VideoMergeRunCreateRequest,
)
from app.db.session.session import get_db
from app.services.tools.service import ToolsService


router = APIRouter(prefix="/tools", tags=["tools"])
tools_service = ToolsService()


@router.get("", response_model=ToolListResponse)
def list_tools() -> ToolListResponse:
    return tools_service.list_tools()


@router.post("/video-merge/runs", response_model=ToolRunCreateResponse)
def create_video_merge_run(
    payload: VideoMergeRunCreateRequest,
    db: Session = Depends(get_db),
) -> ToolRunCreateResponse:
    return tools_service.create_video_merge_run(db, payload)


@router.get("/runs", response_model=ToolRunListResponse)
def list_tool_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ToolRunListResponse:
    return tools_service.list_runs(db, page=page, page_size=page_size)


@router.get("/runs/{run_id}", response_model=ToolRunResponse)
def get_tool_run(
    run_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ToolRunResponse:
    return tools_service.get_run(db, run_id)
