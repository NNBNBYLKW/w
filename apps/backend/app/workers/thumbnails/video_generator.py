import logging
import shutil
import subprocess
from pathlib import Path

from app.core.config.settings import settings


logger = logging.getLogger(__name__)
SUBPROCESS_STDERR_TAIL_CHARS = 4000


class VideoThumbnailGenerationError(RuntimeError):
    pass


class VideoThumbnailGeneratorWorker:
    def __init__(self, *, timeout_seconds: int = 15) -> None:
        self.timeout_seconds = timeout_seconds

    def generate_poster(
        self,
        source_path: Path,
        output_path: Path,
        *,
        duration_ms: int | None = None,
        width: int = 320,
    ) -> None:
        temporary_path = output_path.with_name(f".{output_path.stem}.tmp.jpg")
        if temporary_path.exists():
            temporary_path.unlink()

        if duration_ms is not None and duration_ms > 0:
            duration_s = duration_ms / 1000.0
            seek_seconds = self._find_best_poster_time(str(source_path), duration_s)
        else:
            seek_seconds = 1.0

        self._run_ffmpeg_frame_extract(source_path, temporary_path, seek_seconds=seek_seconds, width=width)
        temporary_path.replace(output_path)

    def generate_thumbnail(self, source_path: Path, output_path: Path, *, width: int = 320) -> None:
        temporary_path = output_path.with_name(f".{output_path.stem}.tmp.jpg")
        if temporary_path.exists():
            temporary_path.unlink()

        self._run_ffmpeg_frame_extract(source_path, temporary_path, seek_seconds=3, width=width)
        temporary_path.replace(output_path)

    def generate_preview_frames(
        self,
        source_path: Path,
        output_dir: Path,
        *,
        seek_seconds: list[float],
        width: int = 320,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

        temporary_paths: list[Path] = []
        final_paths: list[Path] = []
        try:
            for index, seek_second in enumerate(seek_seconds, start=1):
                final_path = output_dir / f"{index:04d}.jpg"
                temporary_path = output_dir / f".{index:04d}.tmp.jpg"
                if temporary_path.exists():
                    temporary_path.unlink()

                self._run_ffmpeg_frame_extract(
                    source_path,
                    temporary_path,
                    seek_seconds=seek_second,
                    width=width,
                )
                temporary_paths.append(temporary_path)
                final_paths.append(final_path)

            for temporary_path, final_path in zip(temporary_paths, final_paths):
                temporary_path.replace(final_path)
        except Exception:
            for temporary_path in temporary_paths:
                if temporary_path.exists():
                    temporary_path.unlink()
            raise

    def _run_ffmpeg_frame_extract(
        self,
        source_path: Path,
        output_path: Path,
        *,
        seek_seconds: float,
        width: int,
    ) -> None:
        ffmpeg_path = self._resolve_ffmpeg_path()
        if ffmpeg_path is None:
            raise VideoThumbnailGenerationError("ffmpeg was not found on PATH.")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{seek_seconds:.3f}",
            "-i",
            str(source_path),
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:-2",
            "-q:v",
            "3",
            str(output_path),
        ]

        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                text=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            stderr = self._tail_text(self._decode_subprocess_bytes(error.stderr), SUBPROCESS_STDERR_TAIL_CHARS)
            message = "ffmpeg timed out while generating thumbnail."
            if stderr:
                message = f"{message} stderr_tail={stderr}"
            raise VideoThumbnailGenerationError(message) from error
        except OSError as error:
            raise VideoThumbnailGenerationError("ffmpeg could not be executed.") from error

        if completed.returncode != 0:
            stderr = self._tail_text(self._decode_subprocess_bytes(completed.stderr).strip(), SUBPROCESS_STDERR_TAIL_CHARS)
            logger.info("ffmpeg thumbnail generation failed for %s: %s", source_path, stderr or completed.returncode)
            raise VideoThumbnailGenerationError(stderr or "ffmpeg failed while generating thumbnail.")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise VideoThumbnailGenerationError("ffmpeg did not create a thumbnail output file.")

    def _find_best_poster_time(self, video_path: str, duration_s: float) -> float:
        """Try 15%, 25%, 40% — use first that's not black."""
        for pct in [0.15, 0.25, 0.40]:
            seek_time = duration_s * pct
            cmd = ["ffmpeg", "-ss", str(seek_time), "-i", video_path, "-vframes", "1",
                   "-vf", "signalstats", "-f", "null", "-"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return seek_time
        return duration_s * 0.10  # fallback

    def _resolve_ffmpeg_path(self) -> str | None:
        configured_path = settings.ffmpeg_path
        if configured_path is not None:
            if configured_path.exists():
                return str(configured_path)
            logger.info("Configured ffmpeg path does not exist: %s", configured_path)

        return shutil.which("ffmpeg")

    def _decode_subprocess_bytes(self, value: bytes | str | None) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return value.decode("utf-8", errors="replace")

    def _tail_text(self, value: str, limit: int) -> str:
        return value[-limit:] if len(value) > limit else value

    def is_expected_generation_failure(self, error: Exception) -> bool:
        return isinstance(
            error,
            (
                FileNotFoundError,
                NotADirectoryError,
                PermissionError,
                OSError,
                VideoThumbnailGenerationError,
            ),
        )
