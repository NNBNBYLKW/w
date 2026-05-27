import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.classification import (
    ARCHIVE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    EBOOK_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    classify_file,
)


REPARSE_POINT_ATTRIBUTE = 0x0400

SKIP_METADATA_EXTENSIONS = frozenset({
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
    ".exe", ".dll", ".msi",
    ".iso", ".bin", ".cue", ".img",
    ".lnk", ".url",
})


@dataclass(slots=True)
class DiscoveredFileRecord:
    path: str
    parent_path: str
    name: str
    stem: str | None
    extension: str | None
    file_type: str
    file_kind: str
    auto_placement: str
    mime_type: str | None
    size_bytes: int | None
    created_at_fs: datetime | None
    modified_at_fs: datetime | None
    source_id: int = 0
    skip_metadata: bool = False


class ScannerWorker:
    def scan_source(self, source_path: str) -> list[DiscoveredFileRecord]:
        root = Path(source_path)
        if not root.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")
        if not root.is_dir():
            raise ValueError(f"Source path is not a directory: {source_path}")
        if self._is_path_indirection(root):
            raise ValueError("Source root cannot be a symlink or reparse-point directory in Phase 1A.")

        records: list[DiscoveredFileRecord] = []
        directories: list[Path] = [root.resolve(strict=True)]

        while directories:
            current_dir = directories.pop()
            with os.scandir(current_dir) as entries:
                sorted_entries = sorted(entries, key=lambda entry: entry.name.lower())

            for entry in sorted_entries:
                try:
                    stat_result = entry.stat(follow_symlinks=False)
                except OSError:
                    continue

                if self._should_skip_entry(entry, stat_result):
                    continue

                if entry.is_dir(follow_symlinks=False):
                    directories.append(Path(entry.path))
                    continue

                if not entry.is_file(follow_symlinks=False):
                    continue

                records.append(self._build_record(entry.path, stat_result))

        return records

    def _build_record(self, entry_path: str, stat_result: os.stat_result) -> DiscoveredFileRecord:
        file_path = Path(entry_path).resolve(strict=False)
        suffix = file_path.suffix.lower()
        extension = suffix.removeprefix(".") or None
        classification = classify_file(extension, str(file_path))
        return DiscoveredFileRecord(
            path=str(file_path),
            parent_path=str(file_path.parent),
            name=file_path.name,
            stem=file_path.stem or None,
            extension=extension,
            file_type=self._classify_file_type(extension),
            file_kind=classification.file_kind,
            auto_placement=classification.auto_placement,
            mime_type=None,
            size_bytes=stat_result.st_size,
            created_at_fs=self._from_timestamp(stat_result.st_ctime),
            modified_at_fs=self._from_timestamp(stat_result.st_mtime),
            skip_metadata=bool(suffix and suffix in SKIP_METADATA_EXTENSIONS),
        )

    def _should_skip_entry(self, entry: os.DirEntry[str], stat_result: os.stat_result) -> bool:
        return entry.is_symlink() or self._is_reparse_stat(stat_result)

    def _is_path_indirection(self, path: Path) -> bool:
        try:
            if path.is_symlink():
                return True
            stat_result = path.lstat()
        except OSError:
            return False
        return self._is_reparse_stat(stat_result)

    def _is_reparse_stat(self, stat_result: os.stat_result) -> bool:
        attributes = getattr(stat_result, "st_file_attributes", 0)
        return bool(attributes & REPARSE_POINT_ATTRIBUTE)

    def _classify_file_type(self, extension: str | None) -> str:
        if extension is None:
            return "other"
        if extension in IMAGE_EXTENSIONS:
            return "image"
        if extension in VIDEO_EXTENSIONS:
            return "video"
        if extension in DOCUMENT_EXTENSIONS or extension in EBOOK_EXTENSIONS:
            return "document"
        if extension in ARCHIVE_EXTENSIONS:
            return "archive"
        return "other"

    def _from_timestamp(self, value: float | int) -> datetime:
        return datetime.fromtimestamp(value, UTC).replace(tzinfo=None)
