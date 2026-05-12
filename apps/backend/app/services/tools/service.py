import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.api.schemas.tools import (
    ToolItemResponse,
    ToolListResponse,
    ToolRunCreateResponse,
    ToolRunListResponse,
    ToolRunResponse,
    VideoMergeRunCreateRequest,
)
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.db.models.file import File
from app.db.models.tool_run import ToolRun
from app.db.session.session import SessionLocal
from app.repositories.file.repository import FileRepository
from app.repositories.tool_run.repository import ToolRunRepository
from app.services.tools.video_merge import (
    LOG_TAIL_CHARS,
    VideoMergeError,
    VideoMergeResolvedInput,
    VideoMergeRunner,
    choose_non_overwriting_path,
    is_allowed_video_path,
    normalize_output_name,
    validate_output_dir,
)


TOOL_KEY_VIDEO_MERGE = "video_merge"
STALE_RUN_MESSAGE = "Tool run was interrupted because the backend process restarted."


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ToolsService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.tool_run_repository = ToolRunRepository()
        self.video_merge_runner = VideoMergeRunner()
        self._video_merge_semaphore = threading.BoundedSemaphore(1)

    def list_tools(self) -> ToolListResponse:
        return ToolListResponse(
            items=[
                ToolItemResponse(
                    key=TOOL_KEY_VIDEO_MERGE,
                    title_key="features.tools.videoMerge.title",
                    description_key="features.tools.videoMerge.description",
                    category="video",
                )
            ]
        )

    def create_video_merge_run(self, session: Session, payload: VideoMergeRunCreateRequest) -> ToolRunCreateResponse:
        try:
            plan = self._build_video_merge_plan(session, payload)
        except VideoMergeError as error:
            raise BadRequestError("VIDEO_MERGE_INVALID", str(error)) from error

        now = _now()
        run = self.tool_run_repository.create(
            session,
            tool_key=TOOL_KEY_VIDEO_MERGE,
            status="pending",
            input_json=json.dumps(plan["input_snapshot"], ensure_ascii=False),
            now=now,
        )
        session.commit()

        thread = threading.Thread(
            target=self._run_video_merge_worker,
            args=(run.id, plan),
            daemon=True,
            name=f"tool-video-merge-{run.id}",
        )
        thread.start()
        return ToolRunCreateResponse(run_id=run.id, status="pending")

    def get_run(self, session: Session, run_id: int) -> ToolRunResponse:
        run = self.tool_run_repository.get_by_id(session, run_id)
        if run is None:
            raise NotFoundError("TOOL_RUN_NOT_FOUND", "Tool run not found.")
        return self._to_run_response(run)

    def list_runs(self, session: Session, *, page: int, page_size: int) -> ToolRunListResponse:
        runs, total = self.tool_run_repository.list_runs(session, page=page, page_size=page_size)
        return ToolRunListResponse(
            items=[self._to_run_response(run) for run in runs],
            page=page,
            page_size=page_size,
            total=total,
        )

    def mark_stale_runs_failed(self, session: Session) -> int:
        count = self.tool_run_repository.mark_stale_active_runs_failed(session, now=_now(), message=STALE_RUN_MESSAGE)
        session.commit()
        return count

    def _run_video_merge_worker(self, run_id: int, plan: dict[str, Any]) -> None:
        with self._video_merge_semaphore:
            with SessionLocal() as session:
                self.tool_run_repository.mark_running(session, run_id, now=_now())
                session.commit()

            try:
                result = self.video_merge_runner.execute(
                    run_id=run_id,
                    inputs=[
                        VideoMergeResolvedInput(
                            source_kind=item["source_kind"],
                            path=Path(item["path"]),
                            file_id=item.get("file_id"),
                        )
                        for item in plan["resolved_inputs"]
                    ],
                    output_path=Path(plan["output_path"]),
                    mode=plan["mode"],
                )
                output = {
                    "output_path": str(result.output_path),
                    "final_output_name": result.final_output_name,
                    "mode": plan["mode"],
                    "command_kind": "ffmpeg_concat",
                }
                with SessionLocal() as session:
                    self.tool_run_repository.mark_succeeded(
                        session,
                        run_id,
                        output_json=json.dumps(output, ensure_ascii=False),
                        log_text=result.log_text,
                        now=_now(),
                    )
                    session.commit()
            except Exception as error:
                with SessionLocal() as session:
                    self.tool_run_repository.mark_failed(
                        session,
                        run_id,
                        error_message=str(error),
                        log_text=str(error),
                        now=_now(),
                    )
                    session.commit()

    def _build_video_merge_plan(self, session: Session, payload: VideoMergeRunCreateRequest) -> dict[str, Any]:
        resolved_inputs = self._resolve_inputs(session, payload)
        output_name = normalize_output_name(payload.output_name)
        output_dir = Path(payload.output_dir) if payload.output_dir else resolved_inputs[0].path.parent
        validate_output_dir(output_dir)
        output_path = choose_non_overwriting_path(output_dir, output_name)
        return {
            "mode": payload.mode,
            "output_path": str(output_path),
            "resolved_inputs": [
                {
                    "source_kind": item.source_kind,
                    "file_id": item.file_id,
                    "path": str(item.path),
                }
                for item in resolved_inputs
            ],
            "input_snapshot": {
                "inputs": [
                    {
                        "source_kind": item.source_kind,
                        "file_id": item.file_id,
                        "path": str(item.path),
                    }
                    for item in resolved_inputs
                ],
                "output_name": output_name,
                "output_dir": str(output_dir),
                "mode": payload.mode,
                "planned_output_path": str(output_path),
            },
        }

    def _resolve_inputs(self, session: Session, payload: VideoMergeRunCreateRequest) -> list[VideoMergeResolvedInput]:
        resolved: list[VideoMergeResolvedInput] = []
        for item in payload.inputs:
            if item.source_kind == "indexed_file":
                if item.file_id is None:
                    raise VideoMergeError("Indexed file input requires file_id.")
                file = self.file_repository.get_by_id(session, item.file_id)
                if file is None or file.is_deleted:
                    raise VideoMergeError("Input file does not exist or was moved.")
                path = Path(file.path)
                self._validate_video_path(path, file=file)
                resolved.append(VideoMergeResolvedInput(source_kind="indexed_file", path=path, file_id=file.id))
                continue

            if item.path is None:
                raise VideoMergeError("External file input requires path.")
            path = Path(item.path)
            self._validate_video_path(path, file=None)
            resolved.append(VideoMergeResolvedInput(source_kind="external_path", path=path, file_id=None))
        return resolved

    def _validate_video_path(self, path: Path, *, file: File | None) -> None:
        if file is not None and file.file_type != "video":
            raise VideoMergeError("This tool only supports video files.")
        if not is_allowed_video_path(path):
            raise VideoMergeError("This tool only supports video files.")
        if not path.exists() or not path.is_file():
            raise VideoMergeError("Input file does not exist or was moved.")
        try:
            with path.open("rb"):
                pass
        except OSError as error:
            raise VideoMergeError("Cannot read this file.") from error

    def _to_run_response(self, run: ToolRun) -> ToolRunResponse:
        input_payload = json.loads(run.input_json)
        output_payload = json.loads(run.output_json) if run.output_json else None
        return ToolRunResponse(
            id=run.id,
            tool_key=run.tool_key,
            status=run.status,
            input=input_payload,
            output=output_payload,
            output_path=output_payload.get("output_path") if output_payload else None,
            final_output_name=output_payload.get("final_output_name") if output_payload else None,
            log_tail=self._tail(run.log_text, LOG_TAIL_CHARS),
            error_message=run.error_message,
            started_at=run.started_at,
            finished_at=run.finished_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    def _tail(self, value: str | None, limit: int) -> str | None:
        if value is None:
            return None
        if len(value) <= limit:
            return value
        return value[-limit:]
