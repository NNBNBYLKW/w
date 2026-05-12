import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.config.settings import settings


ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".ts"}
FFMPEG_TIMEOUT_SECONDS = 60 * 60 * 6
LOG_LIMIT_CHARS = 120_000
LOG_TAIL_CHARS = 20_000
PROCESS_TEXT_TAIL_CHARS = 8_000


class VideoMergeError(RuntimeError):
    pass


@dataclass(frozen=True)
class VideoMergeResolvedInput:
    source_kind: str
    path: Path
    file_id: int | None = None


@dataclass(frozen=True)
class VideoMergeExecutionResult:
    output_path: Path
    final_output_name: str
    log_text: str
    command: list[str]


class VideoMergeRunner:
    def execute(
        self,
        *,
        run_id: int,
        inputs: list[VideoMergeResolvedInput],
        output_path: Path,
        mode: str,
    ) -> VideoMergeExecutionResult:
        ffmpeg_path = self._resolve_ffmpeg_path()
        if ffmpeg_path is None:
            raise VideoMergeError("FFmpeg was not found. Please check FFmpeg configuration.")

        work_dir = settings.data_dir / "tool_runs" / str(run_id)
        work_dir.mkdir(parents=True, exist_ok=True)
        concat_path = work_dir / "concat_list.txt"
        concat_path.write_text(self._build_concat_list(inputs), encoding="utf-8")

        command = self._build_command(ffmpeg_path, concat_path, output_path, mode)
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=FFMPEG_TIMEOUT_SECONDS,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            stderr = _tail_text(_decode_subprocess_bytes(error.stderr), PROCESS_TEXT_TAIL_CHARS)
            message = "FFmpeg timed out while merging videos."
            if stderr:
                message = f"{message} {stderr}"
            raise VideoMergeError(_tail_text(message, PROCESS_TEXT_TAIL_CHARS)) from error
        except OSError as error:
            raise VideoMergeError("FFmpeg could not be executed.") from error

        stdout = _decode_subprocess_bytes(completed.stdout)
        stderr = _decode_subprocess_bytes(completed.stderr)
        log_text = _tail_text(
            "\n".join(
                [
                    f"command={json.dumps(command, ensure_ascii=False)}",
                    f"returncode={completed.returncode}",
                    stdout.strip(),
                    stderr.strip(),
                ]
            ).strip(),
            LOG_LIMIT_CHARS,
        )

        if completed.returncode != 0:
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            reason = _tail_text(stderr.strip() or stdout.strip() or "FFmpeg failed while merging videos.", PROCESS_TEXT_TAIL_CHARS)
            if mode == "copy":
                reason = f"{reason}\nFast merge may fail when input streams or containers are not MP4-compatible. Try Compatible merge."
            raise VideoMergeError(reason)

        if not output_path.exists() or output_path.stat().st_size <= 0:
            raise VideoMergeError("FFmpeg did not create a usable output file.")

        return VideoMergeExecutionResult(
            output_path=output_path,
            final_output_name=output_path.name,
            log_text=log_text,
            command=command,
        )

    def _resolve_ffmpeg_path(self) -> str | None:
        configured_path = settings.ffmpeg_path
        if configured_path is not None and configured_path.exists():
            return str(configured_path)
        return shutil.which("ffmpeg")

    def _build_command(self, ffmpeg_path: str, concat_path: Path, output_path: Path, mode: str) -> list[str]:
        command = [
            ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
        ]
        if mode == "copy":
            command.extend(["-c", "copy"])
        else:
            command.extend(["-c:v", "libx264", "-c:a", "aac"])
        command.append(str(output_path))
        return command

    def _build_concat_list(self, inputs: list[VideoMergeResolvedInput]) -> str:
        return "".join(f"file '{_escape_concat_path(item.path)}'\n" for item in inputs)


def is_allowed_video_path(path: Path) -> bool:
    return path.suffix.lower() in ALLOWED_VIDEO_EXTENSIONS


def normalize_output_name(raw_name: str) -> str:
    name = raw_name.strip()
    if not name:
        raise VideoMergeError("Output filename is required.")
    if re.search(r'[\\/:*?"<>|]', name):
        raise VideoMergeError("Output filename contains invalid characters.")
    if name.endswith("."):
        raise VideoMergeError("Output filename cannot end with a dot.")

    stem = Path(name).stem if Path(name).suffix else name
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if stem.upper() in reserved:
        raise VideoMergeError("Output filename uses a reserved Windows name.")

    if Path(name).suffix == "":
        name = f"{name}.mp4"
    return name


def choose_non_overwriting_path(output_dir: Path, output_name: str) -> Path:
    candidate = output_dir / output_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    for index in range(1, 10_000):
        next_candidate = output_dir / f"{stem}_{index}{suffix}"
        if not next_candidate.exists():
            return next_candidate
    raise VideoMergeError("Could not create a non-overwriting output filename.")


def validate_output_dir(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        raise VideoMergeError("Output directory does not exist.")
    if not os.access(path, os.W_OK):
        raise VideoMergeError("Output directory is not writable.")


def _escape_concat_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "'\\''")


def _decode_subprocess_bytes(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


def _tail_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]
