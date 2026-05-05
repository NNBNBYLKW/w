import logging
import shutil
import subprocess
from pathlib import Path

from app.core.config.settings import settings


logger = logging.getLogger(__name__)


class VideoThumbnailGenerationError(RuntimeError):
    pass


class VideoThumbnailGeneratorWorker:
    def __init__(self, *, timeout_seconds: int = 15) -> None:
        self.timeout_seconds = timeout_seconds

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
                capture_output=True,
                check=False,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise VideoThumbnailGenerationError("ffmpeg timed out while generating thumbnail.") from error
        except OSError as error:
            raise VideoThumbnailGenerationError("ffmpeg could not be executed.") from error

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            logger.info("ffmpeg thumbnail generation failed for %s: %s", source_path, stderr or completed.returncode)
            raise VideoThumbnailGenerationError(stderr or "ffmpeg failed while generating thumbnail.")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise VideoThumbnailGenerationError("ffmpeg did not create a thumbnail output file.")

    def _resolve_ffmpeg_path(self) -> str | None:
        configured_path = settings.ffmpeg_path
        if configured_path is not None:
            if configured_path.exists():
                return str(configured_path)
            logger.info("Configured ffmpeg path does not exist: %s", configured_path)

        return shutil.which("ffmpeg")

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
