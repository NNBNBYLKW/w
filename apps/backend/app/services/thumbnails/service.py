from hashlib import sha256
from pathlib import Path
from threading import Lock

from app.core.config.settings import settings
from app.core.errors.exceptions import NotFoundError
from app.db.models.file import File
from app.repositories.file_metadata.repository import FileMetadataRepository
from app.repositories.file.repository import FileRepository
from app.workers.thumbnails.generator import ThumbnailGeneratorWorker
from app.workers.thumbnails.video_generator import VideoThumbnailGeneratorWorker


VIDEO_PREVIEW_FRAME_COUNT = 6
VIDEO_PREVIEW_WIDTH = 320
VIDEO_PREVIEW_VERSION = "v1"


class ThumbnailService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.file_metadata_repository = FileMetadataRepository()
        self.generator = ThumbnailGeneratorWorker()
        self.video_generator = VideoThumbnailGeneratorWorker()
        self._video_preview_locks: dict[str, Lock] = {}
        self._video_preview_locks_guard = Lock()

    def get_thumbnail_path(self, session, file_id: int) -> Path:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")

        if file.file_type == "image":
            return self._get_image_thumbnail_path(file)
        if file.file_type == "video":
            return self._get_video_thumbnail_path(file)

        raise NotFoundError("THUMBNAIL_NOT_AVAILABLE", "Thumbnail is not available for this file.")

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

        duration_seconds = max(duration_ms / 1000, 1)
        preview_window_seconds = max(min(duration_seconds * 0.3, duration_seconds - 0.2), 0.6)
        step = preview_window_seconds / (VIDEO_PREVIEW_FRAME_COUNT + 1)
        return [max(step * index, 0.2) for index in self._get_video_preview_frame_indexes()]

    def _get_video_preview_lock(self, cache_key: str) -> Lock:
        with self._video_preview_locks_guard:
            lock = self._video_preview_locks.get(cache_key)
            if lock is None:
                lock = Lock()
                self._video_preview_locks[cache_key] = lock
            return lock

    def _get_thumbnail_cache_dir(self) -> Path:
        return settings.data_dir / "thumbnails"

    def _get_video_thumbnail_cache_dir(self) -> Path:
        return self._get_thumbnail_cache_dir() / "video"

    def _get_video_preview_cache_dir(self) -> Path:
        return self._get_thumbnail_cache_dir() / "video_preview"
