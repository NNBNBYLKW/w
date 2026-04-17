from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.db.models.file import File


@dataclass(slots=True)
class ExtractedMetadata:
    width: int | None
    height: int | None
    duration_ms: int | None
    page_count: int | None


class MetadataExtractorWorker:
    def extract_for_file(self, file: File) -> ExtractedMetadata | None:
        if file.file_type != "image":
            return None

        file_path = Path(file.path)
        with Image.open(file_path) as image:
            width, height = image.size

        return ExtractedMetadata(
            width=width,
            height=height,
            duration_ms=None,
            page_count=None,
        )

    def is_expected_extraction_failure(self, error: Exception) -> bool:
        return isinstance(
            error,
            (
                FileNotFoundError,
                NotADirectoryError,
                PermissionError,
                OSError,
                UnidentifiedImageError,
            ),
        )
