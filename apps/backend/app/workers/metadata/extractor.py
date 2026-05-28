from dataclasses import dataclass
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.core.config.settings import settings
from app.db.models.file import File


try:
    import pypdfium2 as pdfium
    HAS_PYPDFIUM2 = True
except ImportError:
    HAS_PYPDFIUM2 = False

FFPROBE_TIMEOUT_SECONDS = 10
SUBPROCESS_STDERR_TAIL_CHARS = 4000


@dataclass(slots=True)
class ExtractedMetadata:
    width: int | None
    height: int | None
    duration_ms: int | None
    page_count: int | None
    codec: str | None = None
    bitrate: int | None = None
    stream_count: int | None = None
    author: str | None = None
    title: str | None = None


class MetadataExtractorWorker:
    def extract_for_file(self, file: File) -> ExtractedMetadata | None:
        if file.file_type == "image":
            return self._extract_image_metadata(Path(file.path))
        if file.file_type == "video":
            return self._extract_video_metadata(Path(file.path))
        if file.file_type == "document" and HAS_PYPDFIUM2:
            return self._extract_pdf_metadata(Path(file.path))
        return None

    def _extract_image_metadata(self, file_path: Path) -> ExtractedMetadata:
        with Image.open(file_path) as image:
            width, height = image.size

        return ExtractedMetadata(
            width=width,
            height=height,
            duration_ms=None,
            page_count=None,
        )

    def _extract_video_metadata(self, file_path: Path) -> ExtractedMetadata:
        ffprobe_path = self._resolve_ffprobe_path()
        if ffprobe_path is None:
            raise FileNotFoundError("ffprobe was not found.")

        command = [
            ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ]
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                text=False,
                timeout=FFPROBE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as error:
            stderr = self._tail_text(self._decode_subprocess_bytes(error.stderr), SUBPROCESS_STDERR_TAIL_CHARS)
            message = f"ffprobe timed out after {FFPROBE_TIMEOUT_SECONDS} seconds."
            if stderr:
                message = f"{message} stderr_tail={stderr}"
            raise OSError(message) from error

        if completed.returncode != 0:
            stderr = self._tail_text(self._decode_subprocess_bytes(completed.stderr).strip(), SUBPROCESS_STDERR_TAIL_CHARS)
            raise OSError(stderr or "ffprobe failed.")

        payload = json.loads(self._decode_subprocess_bytes(completed.stdout))
        streams = payload.get("streams") if isinstance(payload, dict) else None
        video_stream = next(
            (
                stream
                for stream in streams or []
                if isinstance(stream, dict) and stream.get("codec_type") == "video"
            ),
            {},
        )
        format_block = payload.get("format") if isinstance(payload, dict) else None
        if not isinstance(format_block, dict):
            format_block = {}

        width = self._parse_positive_int(video_stream.get("width"))
        height = self._parse_positive_int(video_stream.get("height"))
        duration_seconds = self._parse_positive_float(video_stream.get("duration"))
        if duration_seconds is None:
            duration_seconds = self._parse_positive_float(format_block.get("duration"))

        codec = video_stream.get("codec_name") if isinstance(video_stream, dict) else None
        bitrate = self._parse_positive_int(format_block.get("bit_rate"))
        video_stream_count = sum(
            1 for stream in streams or []
            if isinstance(stream, dict) and stream.get("codec_type") == "video"
        ) if streams else None

        return ExtractedMetadata(
            width=width,
            height=height,
            duration_ms=round(duration_seconds * 1000) if duration_seconds is not None else None,
            page_count=None,
            codec=codec,
            bitrate=bitrate,
            stream_count=video_stream_count,
        )

    def _extract_pdf_metadata(self, file_path: Path) -> ExtractedMetadata | None:
        try:
            pdf = pdfium.PdfDocument(str(file_path))
            page_count = len(pdf)
            metadata = pdf.get_metadata_dict()
            pdf.close()
            return ExtractedMetadata(
                width=None,
                height=None,
                duration_ms=None,
                page_count=page_count,
                author=metadata.get("author"),
                title=metadata.get("title"),
            )
        except Exception:
            return None

    def _resolve_ffprobe_path(self) -> str | None:
        configured_path = settings.ffmpeg_path
        if configured_path is not None:
            candidate_name = "ffprobe.exe" if configured_path.suffix.lower() == ".exe" else "ffprobe"
            sibling_path = configured_path.with_name(candidate_name)
            if sibling_path.exists():
                return str(sibling_path)

        return shutil.which("ffprobe")

    def _parse_positive_float(self, value: object) -> float | None:
        try:
            parsed_value = float(value)
        except (TypeError, ValueError):
            return None
        return parsed_value if parsed_value > 0 else None

    def _parse_positive_int(self, value: object) -> int | None:
        try:
            parsed_value = int(value)
        except (TypeError, ValueError):
            return None
        return parsed_value if parsed_value > 0 else None

    def _decode_subprocess_bytes(self, value: bytes | str | None) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return value.decode("utf-8", errors="replace")

    def _tail_text(self, value: str, limit: int) -> str:
        return value[-limit:] if len(value) > limit else value

    def is_expected_extraction_failure(self, error: Exception) -> bool:
        return isinstance(
            error,
            (
                FileNotFoundError,
                NotADirectoryError,
                PermissionError,
                OSError,
                json.JSONDecodeError,
                subprocess.TimeoutExpired,
                UnidentifiedImageError,
            ),
        )
