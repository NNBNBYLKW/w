from dataclasses import dataclass
from hashlib import sha256
import logging
from pathlib import Path
from queue import Full, Queue
import subprocess
import sys
from threading import BoundedSemaphore, Lock, Thread, get_ident
import time
from uuid import uuid4

from app.core.config.settings import settings
from app.core.errors.exceptions import NotFoundError
from app.db.models.file import File
from app.repositories.file_metadata.repository import FileMetadataRepository
from app.repositories.file.repository import FileRepository
from app.services.diagnostics.runtime import get_runtime_diagnostics, get_pypdfium_diagnostics
from app.workers.thumbnails.exe_icon_generator import ExeIconGeneratorWorker
from app.workers.thumbnails.generator import ThumbnailGeneratorWorker
from app.workers.thumbnails.pdf_generator import PdfThumbnailGeneratorWorker
from app.workers.thumbnails.video_generator import VideoThumbnailGenerationError, VideoThumbnailGeneratorWorker


VIDEO_PREVIEW_FRAME_COUNT = 6
VIDEO_PREVIEW_WIDTH = 320
VIDEO_PREVIEW_VERSION = "v2"
EXE_ICON_SIZE = 256
EXE_ICON_VERSION = "v3"
EXE_ICON_MAX_CONCURRENCY = 4
PDF_THUMBNAIL_WIDTH = 384
PDF_THUMBNAIL_VERSION = "v1"
PDF_RENDER_SUBPROCESS_TIMEOUT_SECONDS = 60
PDF_RENDER_STDOUT_TAIL_CHARS = 1000
PDF_RENDER_STDERR_TAIL_CHARS = 4000
THUMBNAIL_WARMUP_QUEUE_SIZE = 500
THUMBNAIL_WARMUP_WORKERS = 6
THUMBNAIL_WARMUP_FAILURE_TTL_SECONDS = 60
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThumbnailResult:
    path: Path
    media_type: str


@dataclass(frozen=True)
class ThumbnailWarmupResult:
    cached: list[int]
    queued: list[int]
    in_progress: list[int]
    unsupported: list[int]
    missing: list[int]
    failed: list[int]


@dataclass(frozen=True)
class ThumbnailFileSnapshot:
    id: int
    name: str
    path: str
    extension: str | None
    file_type: str
    size_bytes: int | None


@dataclass(frozen=True)
class ThumbnailWarmupJob:
    cache_key: str
    cache_path: Path
    file: ThumbnailFileSnapshot
    kind: str


@dataclass(frozen=True)
class ThumbnailWarmupFailure:
    file_id: int
    kind: str
    source_path: str
    cache_path: str
    reason: str
    expires_at: float
    tmp_path: str | None = None
    source_exists: bool | None = None
    source_size: int | None = None
    source_first_bytes_hex: str | None = None
    subprocess_command: list[str] | None = None
    subprocess_cwd: str | None = None
    subprocess_returncode: int | None = None
    subprocess_stdout_tail: str | None = None
    subprocess_stderr_tail: str | None = None
    subprocess_timeout: bool = False


class PdfRenderSubprocessError(RuntimeError):
    def __init__(self, message: str, diagnostics: dict) -> None:
        self.diagnostics = diagnostics
        super().__init__(
            (
                f"{message} "
                f"returncode={diagnostics.get('subprocess_returncode')!r} "
                f"timeout={diagnostics.get('subprocess_timeout')!r} "
                f"cwd={diagnostics.get('subprocess_cwd')!r} "
                f"command={diagnostics.get('subprocess_command')!r} "
                f"stdout_tail={diagnostics.get('subprocess_stdout_tail')!r} "
                f"stderr_tail={diagnostics.get('subprocess_stderr_tail')!r}"
            )
        )


class ThumbnailService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.file_metadata_repository = FileMetadataRepository()
        self.generator = ThumbnailGeneratorWorker()
        self.video_generator = VideoThumbnailGeneratorWorker()
        self.exe_icon_generator = ExeIconGeneratorWorker()
        self.pdf_generator = PdfThumbnailGeneratorWorker()
        self._video_preview_locks: dict[str, Lock] = {}
        self._video_preview_locks_guard = Lock()
        self._thumbnail_generation_locks: dict[str, Lock] = {}
        self._thumbnail_generation_locks_guard = Lock()
        self._exe_icon_semaphore = BoundedSemaphore(EXE_ICON_MAX_CONCURRENCY)
        # PDFium/pypdfium2 rendering is intentionally serialized on Windows:
        # batch warmup workers may run in parallel, but only one PDF render enters PDFium at a time.
        self._pdf_thumbnail_lock = Lock()
        self._warmup_queue: Queue[ThumbnailWarmupJob] = Queue(maxsize=THUMBNAIL_WARMUP_QUEUE_SIZE)
        self._warmup_status_by_cache_key: dict[str, str] = {}
        self._warmup_failures_by_cache_key: dict[str, ThumbnailWarmupFailure] = {}
        self._warmup_guard = Lock()
        self._start_warmup_workers()

    def get_thumbnail(self, session, file_id: int) -> ThumbnailResult:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")

        if file.file_type == "image":
            return ThumbnailResult(path=self._get_image_thumbnail_path(file), media_type="image/jpeg")
        if file.file_type == "video":
            return ThumbnailResult(path=self._get_video_thumbnail_path(file), media_type="image/jpeg")
        if self._is_pdf_file(file):
            runtime = get_runtime_diagnostics()
            logger.info(
                (
                    "PDF thumbnail requested file_id=%s name=%s path=%s extension=%s file_type=%s "
                    "source_exists=%s data_dir=%s database_path=%s sys_executable=%s cwd=%s "
                    "pypdfium2_import=%s pypdfium2_version=%s packaged_backend=%s"
                ),
                file.id,
                file.name,
                file.path,
                file.extension,
                file.file_type,
                Path(file.path).exists(),
                runtime["data_dir"],
                runtime["database_path"],
                runtime["sys_executable"],
                runtime["cwd"],
                runtime["pypdfium2_import"],
                runtime["pypdfium2_version"],
                runtime["packaged_backend"],
            )
            return ThumbnailResult(path=self._get_pdf_thumbnail_path(file), media_type="image/png")
        if self._is_exe_file(file):
            return ThumbnailResult(path=self._get_exe_icon_path(file), media_type="image/png")

        raise NotFoundError("THUMBNAIL_NOT_AVAILABLE", "Thumbnail is not available for this file.")

    def warmup_thumbnails(self, session, file_ids: list[int]) -> ThumbnailWarmupResult:
        unique_file_ids = list(dict.fromkeys(file_ids))
        logger.info("Thumbnail warmup requested file_ids=%s", unique_file_ids)
        result = ThumbnailWarmupResult(
            cached=[],
            queued=[],
            in_progress=[],
            unsupported=[],
            missing=[],
            failed=[],
        )
        files = self.file_repository.list_active_files_by_ids(session, unique_file_ids)
        files_by_id = {file.id: file for file in files}

        for file_id in unique_file_ids:
            file = files_by_id.get(file_id)
            if file is None:
                logger.info("Thumbnail warmup missing file_id=%s reason=file_not_found", file_id)
                result.missing.append(file_id)
                continue

            status = self._warmup_file(file)
            getattr(result, status).append(file_id)

        return result

    def get_warmup_debug_snapshot(self) -> dict:
        implementation = self._get_implementation_fingerprint()
        with self._warmup_guard:
            self._prune_expired_warmup_failures()
            status_counts: dict[str, int] = {}
            for status in self._warmup_status_by_cache_key.values():
                status_counts[status] = status_counts.get(status, 0) + 1
            recent_failures = [
                self._format_warmup_failure_for_debug(failure)
                for failure in self._warmup_failures_by_cache_key.values()
            ][:20]
            failure_count = len(self._warmup_failures_by_cache_key)

        return {
            "implementation": implementation,
            "queue_size": self._warmup_queue.qsize(),
            "status_counts": status_counts,
            "in_progress_count": status_counts.get("in_progress", 0),
            "failure_count": failure_count,
            "recent_failures": recent_failures,
        }

    def get_warmup_debug_for_file(self, session, file_id: int) -> dict:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            return {
                "implementation": self._get_implementation_fingerprint(),
                "file_id": file_id,
                "found": False,
                "kind": None,
                "source_exists": False,
                "cache_path": None,
                "cache_exists": False,
                "active_status": None,
                "failure_reason": None,
            }

        kind = self._get_thumbnail_kind(file)
        cache_path = self._build_thumbnail_path_for_kind(file, kind) if kind is not None else None
        cache_key = f"{kind}:{cache_path}" if kind is not None and cache_path is not None else None
        active_status = None
        failure_debug = None
        if cache_key is not None:
            with self._warmup_guard:
                self._prune_expired_warmup_failures()
                active_status = self._warmup_status_by_cache_key.get(cache_key)
                failure = self._warmup_failures_by_cache_key.get(cache_key)
                failure_debug = self._format_warmup_failure_for_debug(failure) if failure is not None else None

        source_path = Path(file.path)
        try:
            source_size = source_path.stat().st_size if source_path.exists() else None
        except OSError:
            source_size = None

        return {
            "implementation": self._get_implementation_fingerprint(),
            "file_id": file.id,
            "found": True,
            "name": file.name,
            "path": file.path,
            "extension": file.extension,
            "file_type": file.file_type,
            "kind": kind,
            "source_exists": source_path.exists(),
            "source_size": source_size,
            "source_first_bytes_hex": self._read_source_first_bytes_hex(source_path),
            "cache_path": str(cache_path) if cache_path is not None else None,
            "cache_exists": cache_path.exists() if cache_path is not None else False,
            "active_status": active_status,
            "failure_reason": failure_debug["reason"] if failure_debug is not None else None,
            "failure": failure_debug,
        }

    def get_video_preview(self, session, file_id: int) -> dict:
        file = self._get_video_file(session, file_id)
        if not self._build_video_thumbnail_path(file).exists():
            raise NotFoundError("VIDEO_PREVIEW_NOT_AVAILABLE", "Video preview is not available for this file.")

        preview_dir = self._build_video_preview_dir(file)
        frame_indexes = self._get_video_preview_frame_indexes()
        if self._has_complete_video_preview(preview_dir):
            return {
                "id": file.id,
                "frame_count": VIDEO_PREVIEW_FRAME_COUNT,
                "frame_indexes": frame_indexes,
            }

        cache_key = preview_dir.name
        lock = self._get_video_preview_lock(cache_key)
        with lock:
            if self._has_complete_video_preview(preview_dir):
                return {
                    "id": file.id,
                    "frame_count": VIDEO_PREVIEW_FRAME_COUNT,
                    "frame_indexes": frame_indexes,
                }

            metadata = self.file_metadata_repository.get_by_file_id(session, file.id)
            seek_seconds = self._build_video_preview_seek_seconds(metadata.duration_ms if metadata is not None else None)
            try:
                self.video_generator.generate_preview_frames(
                    Path(file.path),
                    preview_dir,
                    seek_seconds=seek_seconds,
                    width=VIDEO_PREVIEW_WIDTH,
                )
            except Exception as error:
                if self.video_generator.is_expected_generation_failure(error):
                    raise NotFoundError(
                        "VIDEO_PREVIEW_NOT_AVAILABLE",
                        "Video preview is not available for this file.",
                    ) from error
                raise

            if not self._has_complete_video_preview(preview_dir):
                raise NotFoundError("VIDEO_PREVIEW_NOT_AVAILABLE", "Video preview is not available for this file.")

        return {
            "id": file.id,
            "frame_count": VIDEO_PREVIEW_FRAME_COUNT,
            "frame_indexes": frame_indexes,
        }

    def get_video_preview_frame_path(self, session, file_id: int, frame_index: int) -> Path:
        file = self._get_video_file(session, file_id)
        if frame_index not in self._get_video_preview_frame_indexes():
            raise NotFoundError("VIDEO_PREVIEW_NOT_AVAILABLE", "Video preview is not available for this file.")

        preview_dir = self._build_video_preview_dir(file)
        frame_path = preview_dir / f"{frame_index:04d}.jpg"
        if not frame_path.exists():
            raise NotFoundError("VIDEO_PREVIEW_NOT_AVAILABLE", "Video preview is not available for this file.")

        return frame_path

    def _get_video_file(self, session, file_id: int) -> File:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")
        if file.file_type != "video":
            raise NotFoundError("VIDEO_PREVIEW_NOT_AVAILABLE", "Video preview is not available for this file.")
        return file

    def _get_image_thumbnail_path(self, file: File) -> Path:
        thumbnail_path = self._build_image_thumbnail_path(file)
        if thumbnail_path.exists():
            return thumbnail_path

        try:
            self.generator.generate_thumbnail(Path(file.path), thumbnail_path)
        except Exception as error:
            if self.generator.is_expected_generation_failure(error):
                raise NotFoundError("THUMBNAIL_NOT_AVAILABLE", "Thumbnail is not available for this file.") from error
            raise

        return thumbnail_path

    def _get_video_thumbnail_path(self, file: File) -> Path:
        thumbnail_path = self._build_video_thumbnail_path(file)
        if thumbnail_path.exists():
            return thumbnail_path

        try:
            self.video_generator.generate_thumbnail(Path(file.path), thumbnail_path)
        except Exception as error:
            if self.video_generator.is_expected_generation_failure(error):
                raise NotFoundError("THUMBNAIL_NOT_AVAILABLE", "Thumbnail is not available for this file.") from error
            raise

        return thumbnail_path

    def _get_exe_icon_path(self, file: File) -> Path:
        icon_path = self._build_exe_icon_path(file)
        if icon_path.exists():
            logger.info("EXE icon cache hit file_id=%s path=%s cache_path=%s", file.id, file.path, icon_path)
            return icon_path

        status = self._warmup_file(file)
        logger.info("EXE icon pending file_id=%s path=%s cache_path=%s warmup_status=%s", file.id, file.path, icon_path, status)
        if status == "failed":
            raise NotFoundError("THUMBNAIL_NOT_AVAILABLE", "Thumbnail is not available for this file.")
        if status == "missing":
            raise NotFoundError("THUMBNAIL_NOT_AVAILABLE", "Thumbnail is not available for this file.")
        raise NotFoundError("THUMBNAIL_PENDING", "Thumbnail generation is pending.")

    def _get_pdf_thumbnail_path(self, file: File) -> Path:
        thumbnail_path = self._build_pdf_thumbnail_path(file)
        if thumbnail_path.exists():
            logger.info("PDF thumbnail cache hit file_id=%s path=%s cache_path=%s", file.id, file.path, thumbnail_path)
            return thumbnail_path

        pypdfium = get_pypdfium_diagnostics()
        logger.info(
            "PDF thumbnail cache miss file_id=%s path=%s cache_path=%s pypdfium2_import=%s pypdfium2_version=%s pypdfium2_error=%s",
            file.id,
            file.path,
            thumbnail_path,
            pypdfium["import"],
            pypdfium["version"],
            pypdfium["error"],
        )
        status = self._warmup_file(file)
        logger.info("PDF thumbnail pending file_id=%s path=%s cache_path=%s warmup_status=%s", file.id, file.path, thumbnail_path, status)
        if status == "failed":
            raise NotFoundError("THUMBNAIL_NOT_AVAILABLE", "Thumbnail is not available for this file.")
        if status == "missing":
            raise NotFoundError("THUMBNAIL_NOT_AVAILABLE", "Thumbnail is not available for this file.")
        raise NotFoundError("THUMBNAIL_PENDING", "Thumbnail generation is pending.")

    def _warmup_file(self, file: File) -> str:
        kind = self._get_thumbnail_kind(file)
        if kind is None:
            logger.info(
                "Thumbnail warmup unsupported file_id=%s path=%s extension=%s file_type=%s",
                file.id,
                file.path,
                file.extension,
                file.file_type,
            )
            return "unsupported"

        cache_path = self._build_thumbnail_path_for_kind(file, kind)
        if cache_path.exists():
            logger.info("Thumbnail warmup cache hit file_id=%s kind=%s cache_path=%s", file.id, kind, cache_path)
            return "cached"

        if not Path(file.path).exists():
            logger.info("Thumbnail warmup source missing file_id=%s kind=%s path=%s", file.id, kind, file.path)
            return "missing"

        job = ThumbnailWarmupJob(
            cache_key=f"{kind}:{cache_path}",
            cache_path=cache_path,
            file=ThumbnailFileSnapshot(
                id=file.id,
                name=file.name,
                path=file.path,
                extension=file.extension,
                file_type=file.file_type,
                size_bytes=file.size_bytes,
            ),
            kind=kind,
        )
        return self._enqueue_warmup_job(job)

    def _enqueue_warmup_job(self, job: ThumbnailWarmupJob) -> str:
        with self._warmup_guard:
            if job.cache_path.exists():
                return "cached"

            failure = self._get_active_warmup_failure(job.cache_key)
            if failure is not None:
                logger.info(
                    "Thumbnail warmup failure ttl active file_id=%s kind=%s cache_path=%s reason=%s",
                    job.file.id,
                    job.kind,
                    job.cache_path,
                    failure,
                )
                return "failed"

            status = self._warmup_status_by_cache_key.get(job.cache_key)
            if status is not None:
                logger.info(
                    "Thumbnail warmup already %s file_id=%s kind=%s cache_path=%s",
                    status,
                    job.file.id,
                    job.kind,
                    job.cache_path,
                )
                return "in_progress"

            try:
                self._warmup_queue.put_nowait(job)
            except Full:
                logger.info("Thumbnail warmup queue full file_id=%s kind=%s cache_path=%s", job.file.id, job.kind, job.cache_path)
                return "failed"

            self._warmup_status_by_cache_key[job.cache_key] = "queued"
            logger.info("Thumbnail warmup queued file_id=%s kind=%s cache_path=%s", job.file.id, job.kind, job.cache_path)
            return "queued"

    def _start_warmup_workers(self) -> None:
        for index in range(THUMBNAIL_WARMUP_WORKERS):
            worker = Thread(target=self._warmup_worker, name=f"thumbnail-warmup-{index + 1}", daemon=True)
            worker.start()

    def _warmup_worker(self) -> None:
        while True:
            job = self._warmup_queue.get()
            temporary_path = self._build_warmup_temporary_path(job.cache_path)
            try:
                with self._warmup_guard:
                    self._warmup_status_by_cache_key[job.cache_key] = "in_progress"
                logger.info("Thumbnail warmup generation started file_id=%s kind=%s cache_path=%s", job.file.id, job.kind, job.cache_path)
                self._run_warmup_job(job, temporary_path)
                self._clear_warmup_failure(job.cache_key)
                logger.info("Thumbnail warmup generation success file_id=%s kind=%s cache_path=%s", job.file.id, job.kind, job.cache_path)
            except Exception as error:
                reason = self._format_warmup_failure_reason(error)
                if self._is_expected_warmup_failure(job, error):
                    logger.warning(
                        (
                            "Thumbnail warmup expected generation failure file_id=%s kind=%s source_path=%s "
                            "cache_path=%s tmp_path=%s exception_type=%s reason=%s"
                        ),
                        job.file.id,
                        job.kind,
                        job.file.path,
                        job.cache_path,
                        temporary_path,
                        type(error).__name__,
                        reason,
                    )
                else:
                    logger.exception(
                        (
                            "Thumbnail warmup generation failed file_id=%s kind=%s source_path=%s "
                            "cache_path=%s tmp_path=%s exception_type=%s message=%s"
                        ),
                        job.file.id,
                        job.kind,
                        job.file.path,
                        job.cache_path,
                        temporary_path,
                        type(error).__name__,
                        error,
                    )
                self._record_warmup_failure(job, reason, error=error, temporary_path=temporary_path)
            finally:
                if temporary_path.exists():
                    try:
                        temporary_path.unlink()
                    except OSError:
                        logger.exception(
                            "Thumbnail warmup temporary cleanup failed file_id=%s kind=%s tmp_path=%s",
                            job.file.id,
                            job.kind,
                            temporary_path,
                        )
                with self._warmup_guard:
                    self._warmup_status_by_cache_key.pop(job.cache_key, None)
                self._warmup_queue.task_done()

    def _run_warmup_job(self, job: ThumbnailWarmupJob, temporary_path: Path) -> None:
        if job.cache_path.exists():
            return

        job.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if temporary_path.exists():
            temporary_path.unlink()

        if job.kind == "pdf":
            with self._pdf_thumbnail_lock:
                logger.info(
                    "Thumbnail warmup PDF generation acquired lock file_id=%s cache_path=%s",
                    job.file.id,
                    job.cache_path,
                )
                self._render_pdf_thumbnail_subprocess(Path(job.file.path), temporary_path, width=PDF_THUMBNAIL_WIDTH)
        elif job.kind == "exe":
            with self._exe_icon_semaphore:
                self.exe_icon_generator.generate_icon(Path(job.file.path), temporary_path, size=EXE_ICON_SIZE)
        elif job.kind == "image":
            self.generator.generate_thumbnail(Path(job.file.path), temporary_path)
        elif job.kind == "video":
            self.video_generator.generate_thumbnail(Path(job.file.path), temporary_path)
        else:
            raise ValueError(f"Unsupported thumbnail kind: {job.kind}")

        if not temporary_path.exists() or temporary_path.stat().st_size <= 0:
            raise RuntimeError("Thumbnail generator did not create an output file.")

        temporary_path.replace(job.cache_path)

    def _render_pdf_thumbnail_subprocess(self, source_path: Path, output_path: Path, *, width: int) -> None:
        command = self._build_pdf_render_command(source_path, output_path, width=width)
        backend_dir = self._get_backend_root()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                cwd=backend_dir,
                shell=False,
                text=True,
                timeout=PDF_RENDER_SUBPROCESS_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as error:
            stdout_tail = self._tail_text(error.stdout, PDF_RENDER_STDOUT_TAIL_CHARS)
            stderr_tail = self._tail_text(error.stderr, PDF_RENDER_STDERR_TAIL_CHARS)
            diagnostics = self._build_pdf_subprocess_diagnostics(
                command=command,
                cwd=backend_dir,
                returncode=None,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                timeout=True,
            )
            raise PdfRenderSubprocessError(
                f"PDF render subprocess timed out after {PDF_RENDER_SUBPROCESS_TIMEOUT_SECONDS}s.",
                diagnostics,
            ) from error

        if completed.returncode != 0:
            stdout_tail = self._tail_text(completed.stdout, PDF_RENDER_STDOUT_TAIL_CHARS)
            stderr_tail = self._tail_text(completed.stderr, PDF_RENDER_STDERR_TAIL_CHARS)
            diagnostics = self._build_pdf_subprocess_diagnostics(
                command=command,
                cwd=backend_dir,
                returncode=completed.returncode,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                timeout=False,
            )
            raise PdfRenderSubprocessError(
                f"PDF render subprocess failed returncode={completed.returncode}.",
                diagnostics,
            )

    def _build_pdf_subprocess_diagnostics(
        self,
        *,
        command: list[str],
        cwd: Path,
        returncode: int | None,
        stdout_tail: str,
        stderr_tail: str,
        timeout: bool,
    ) -> dict:
        return {
            "subprocess_command": command,
            "subprocess_cwd": str(cwd),
            "subprocess_returncode": returncode,
            "subprocess_stdout_tail": stdout_tail,
            "subprocess_stderr_tail": stderr_tail,
            "subprocess_timeout": timeout,
        }

    def _build_pdf_render_command(self, source_path: Path, output_path: Path, *, width: int) -> list[str]:
        if getattr(sys, "frozen", False):
            return [
                sys.executable,
                "--pdf-render-worker",
                "--source",
                str(source_path),
                "--output",
                str(output_path),
                "--width",
                str(width),
            ]
        return [
            sys.executable,
            "-m",
            "app.workers.thumbnails.pdf_render_cli",
            "--source",
            str(source_path),
            "--output",
            str(output_path),
            "--width",
            str(width),
        ]

    def _tail_text(self, value: str | bytes | None, limit: int) -> str:
        if value is None:
            return ""
        text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
        return text[-limit:]

    def _get_backend_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    def _build_warmup_temporary_path(self, cache_path: Path) -> Path:
        return cache_path.with_name(f".{cache_path.stem}.tmp-{get_ident()}-{uuid4().hex}{cache_path.suffix}")

    def _format_warmup_failure_reason(self, error: Exception) -> str:
        return f"{type(error).__name__}: {error}"

    def _is_expected_warmup_failure(self, job: ThumbnailWarmupJob, error: Exception) -> bool:
        return job.kind == "video" and isinstance(error, VideoThumbnailGenerationError)

    def _record_warmup_failure(
        self,
        job: ThumbnailWarmupJob,
        reason: str,
        *,
        error: Exception,
        temporary_path: Path,
    ) -> None:
        source_path = Path(job.file.path)
        try:
            source_exists = source_path.exists()
            source_size = source_path.stat().st_size if source_exists else None
        except OSError:
            source_exists = False
            source_size = None
        subprocess_diagnostics = error.diagnostics if isinstance(error, PdfRenderSubprocessError) else {}
        with self._warmup_guard:
            self._warmup_failures_by_cache_key[job.cache_key] = ThumbnailWarmupFailure(
                file_id=job.file.id,
                kind=job.kind,
                source_path=job.file.path,
                cache_path=str(job.cache_path),
                reason=reason,
                expires_at=time.monotonic() + THUMBNAIL_WARMUP_FAILURE_TTL_SECONDS,
                tmp_path=str(temporary_path),
                source_exists=source_exists,
                source_size=source_size,
                source_first_bytes_hex=self._read_source_first_bytes_hex(source_path),
                subprocess_command=subprocess_diagnostics.get("subprocess_command"),
                subprocess_cwd=subprocess_diagnostics.get("subprocess_cwd"),
                subprocess_returncode=subprocess_diagnostics.get("subprocess_returncode"),
                subprocess_stdout_tail=subprocess_diagnostics.get("subprocess_stdout_tail"),
                subprocess_stderr_tail=subprocess_diagnostics.get("subprocess_stderr_tail"),
                subprocess_timeout=bool(subprocess_diagnostics.get("subprocess_timeout", False)),
            )

    def _get_active_warmup_failure(self, cache_key: str) -> str | None:
        failure = self._warmup_failures_by_cache_key.get(cache_key)
        if failure is None:
            return None

        if time.monotonic() >= failure.expires_at:
            self._warmup_failures_by_cache_key.pop(cache_key, None)
            return None
        return failure.reason

    def _clear_warmup_failure(self, cache_key: str) -> None:
        with self._warmup_guard:
            self._warmup_failures_by_cache_key.pop(cache_key, None)

    def _prune_expired_warmup_failures(self) -> None:
        now = time.monotonic()
        expired_cache_keys = [
            cache_key
            for cache_key, failure in self._warmup_failures_by_cache_key.items()
            if now >= failure.expires_at
        ]
        for cache_key in expired_cache_keys:
            self._warmup_failures_by_cache_key.pop(cache_key, None)

    def _format_warmup_failure_for_debug(self, failure: ThumbnailWarmupFailure) -> dict:
        return {
            "file_id": failure.file_id,
            "kind": failure.kind,
            "source_path": failure.source_path,
            "cache_path": failure.cache_path,
            "tmp_path": failure.tmp_path,
            "reason": failure.reason,
            "expires_in_seconds": max(0, round(failure.expires_at - time.monotonic(), 3)),
            "source_exists": failure.source_exists,
            "source_size": failure.source_size,
            "source_first_bytes_hex": failure.source_first_bytes_hex,
            "subprocess_command": failure.subprocess_command,
            "subprocess_cwd": failure.subprocess_cwd,
            "subprocess_returncode": failure.subprocess_returncode,
            "subprocess_stdout_tail": failure.subprocess_stdout_tail,
            "subprocess_stderr_tail": failure.subprocess_stderr_tail,
            "subprocess_timeout": failure.subprocess_timeout,
        }

    def _get_implementation_fingerprint(self) -> dict:
        runtime = get_runtime_diagnostics()
        module_path = Path(__file__).resolve()
        try:
            module_mtime = module_path.stat().st_mtime
        except OSError:
            module_mtime = None
        return {
            "process_id": runtime["process_id"],
            "process_start_time": runtime["process_start_time"],
            "service_module_path": str(module_path),
            "service_module_mtime": module_mtime,
            "pdf_render_mode": "subprocess-v1",
            "pdf_render_command_kind": self._get_pdf_render_command_kind(),
        }

    def _get_pdf_render_command_kind(self) -> str:
        return "frozen-worker" if getattr(sys, "frozen", False) else "dev-module"

    def _read_source_first_bytes_hex(self, source_path: Path, *, limit: int = 64) -> str | None:
        try:
            if not source_path.exists():
                return None
            with source_path.open("rb") as source_file:
                return source_file.read(limit).hex()
        except OSError:
            return None

    def _build_image_thumbnail_path(self, file: File) -> Path:
        modified_source = file.modified_at_fs or file.discovered_at
        modified_marker = modified_source.strftime("%Y%m%d%H%M%S%f")
        size_marker = file.size_bytes if file.size_bytes is not None else 0
        filename = f"thumb_{file.id}_{size_marker}_{modified_marker}.jpg"
        return self._get_thumbnail_cache_dir() / filename

    def _build_video_thumbnail_path(self, file: File) -> Path:
        modified_source = file.modified_at_fs or file.discovered_at
        modified_marker = modified_source.strftime("%Y%m%d%H%M%S%f")
        size_marker = file.size_bytes if file.size_bytes is not None else 0
        cache_key = sha256(f"{file.path}|{size_marker}|{modified_marker}".encode("utf-8")).hexdigest()[:16]
        filename = f"video_{file.id}_{cache_key}.jpg"
        return self._get_video_thumbnail_cache_dir() / filename

    def _build_video_preview_dir(self, file: File) -> Path:
        modified_source = file.modified_at_fs or file.discovered_at
        modified_marker = modified_source.strftime("%Y%m%d%H%M%S%f")
        size_marker = file.size_bytes if file.size_bytes is not None else 0
        cache_key = sha256(
            "|".join(
                [
                    file.path,
                    str(size_marker),
                    modified_marker,
                    VIDEO_PREVIEW_VERSION,
                    str(VIDEO_PREVIEW_FRAME_COUNT),
                    str(VIDEO_PREVIEW_WIDTH),
                ]
            ).encode("utf-8")
        ).hexdigest()[:24]
        return self._get_video_preview_cache_dir() / cache_key

    def _build_exe_icon_path(self, file: File) -> Path:
        path = Path(file.path)
        try:
            stat_result = path.stat()
            modified_marker = str(stat_result.st_mtime_ns)
            size_marker = stat_result.st_size
        except OSError:
            modified_source = file.modified_at_fs or file.discovered_at
            modified_marker = modified_source.strftime("%Y%m%d%H%M%S%f")
            size_marker = file.size_bytes if file.size_bytes is not None else 0
        cache_key = sha256(
            "|".join(
                [
                    file.path,
                    str(size_marker),
                    modified_marker,
                    EXE_ICON_VERSION,
                    str(EXE_ICON_SIZE),
                ]
            ).encode("utf-8")
        ).hexdigest()[:16]
        filename = f"exe_{file.id}_{cache_key}.png"
        return self._get_exe_icon_cache_dir() / filename

    def _build_pdf_thumbnail_path(self, file: File) -> Path:
        path = Path(file.path)
        try:
            stat_result = path.stat()
            modified_marker = str(stat_result.st_mtime_ns)
            size_marker = stat_result.st_size
        except OSError:
            modified_source = file.modified_at_fs or file.discovered_at
            modified_marker = modified_source.strftime("%Y%m%d%H%M%S%f")
            size_marker = file.size_bytes if file.size_bytes is not None else 0
        cache_key = sha256(
            "|".join(
                [
                    file.path,
                    str(size_marker),
                    modified_marker,
                    PDF_THUMBNAIL_VERSION,
                    str(PDF_THUMBNAIL_WIDTH),
                ]
            ).encode("utf-8")
        ).hexdigest()[:16]
        filename = f"pdf_{file.id}_{cache_key}.png"
        return self._get_pdf_thumbnail_cache_dir() / filename

    def _get_thumbnail_kind(self, file: File) -> str | None:
        if file.file_type == "image":
            return "image"
        if file.file_type == "video":
            return "video"
        if self._is_pdf_file(file):
            return "pdf"
        if self._is_exe_file(file):
            return "exe"
        return None

    def _build_thumbnail_path_for_kind(self, file: File, kind: str) -> Path:
        if kind == "image":
            return self._build_image_thumbnail_path(file)
        if kind == "video":
            return self._build_video_thumbnail_path(file)
        if kind == "pdf":
            return self._build_pdf_thumbnail_path(file)
        if kind == "exe":
            return self._build_exe_icon_path(file)
        raise ValueError(f"Unsupported thumbnail kind: {kind}")

    def _is_exe_file(self, file: File) -> bool:
        extension = file.extension or Path(file.path).suffix
        if extension and not extension.startswith("."):
            extension = f".{extension}"
        return extension.lower() == ".exe"

    def _is_pdf_file(self, file: File) -> bool:
        extension = file.extension or Path(file.path).suffix
        if extension and not extension.startswith("."):
            extension = f".{extension}"
        return extension.lower() == ".pdf"

    def _has_complete_video_preview(self, preview_dir: Path) -> bool:
        return all(
            (preview_dir / f"{frame_index:04d}.jpg").exists()
            for frame_index in self._get_video_preview_frame_indexes()
        )

    def _get_video_preview_frame_indexes(self) -> list[int]:
        return list(range(1, VIDEO_PREVIEW_FRAME_COUNT + 1))

    def _build_video_preview_seek_seconds(self, duration_ms: int | None) -> list[float]:
        if duration_ms is None or duration_ms <= 0:
            return [0.5 * index for index in self._get_video_preview_frame_indexes()]

        duration_seconds = duration_ms / 1000
        safe_margin = min(0.5, duration_seconds * 0.1)
        safe_start = safe_margin
        safe_end = max(safe_start, duration_seconds - safe_margin)
        return [
            safe_start + (safe_end - safe_start) * (index + 1) / (VIDEO_PREVIEW_FRAME_COUNT + 1)
            for index in range(VIDEO_PREVIEW_FRAME_COUNT)
        ]

    def _get_video_preview_lock(self, cache_key: str) -> Lock:
        with self._video_preview_locks_guard:
            lock = self._video_preview_locks.get(cache_key)
            if lock is None:
                lock = Lock()
                self._video_preview_locks[cache_key] = lock
            return lock

    def _get_thumbnail_generation_lock(self, cache_key: str) -> Lock:
        with self._thumbnail_generation_locks_guard:
            lock = self._thumbnail_generation_locks.get(cache_key)
            if lock is None:
                lock = Lock()
                self._thumbnail_generation_locks[cache_key] = lock
            return lock

    def _get_thumbnail_cache_dir(self) -> Path:
        return settings.data_dir / "thumbnails"

    def _get_video_thumbnail_cache_dir(self) -> Path:
        return self._get_thumbnail_cache_dir() / "video"

    def _get_video_preview_cache_dir(self) -> Path:
        return self._get_thumbnail_cache_dir() / "video_preview"

    def _get_exe_icon_cache_dir(self) -> Path:
        return self._get_thumbnail_cache_dir() / "exe_icons"

    def _get_pdf_thumbnail_cache_dir(self) -> Path:
        return self._get_thumbnail_cache_dir() / "pdf"
