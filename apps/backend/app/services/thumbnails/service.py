from pathlib import Path

from app.core.config.settings import settings
from app.core.errors.exceptions import NotFoundError
from app.db.models.file import File
from app.repositories.file.repository import FileRepository
from app.workers.thumbnails.generator import ThumbnailGeneratorWorker


class ThumbnailService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.generator = ThumbnailGeneratorWorker()

    def get_thumbnail_path(self, session, file_id: int) -> Path:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")
        if file.file_type != "image":
            raise NotFoundError("THUMBNAIL_NOT_AVAILABLE", "Thumbnail is not available for this file.")

        thumbnail_path = self._build_thumbnail_path(file)
        if thumbnail_path.exists():
            return thumbnail_path

        try:
            self.generator.generate_thumbnail(Path(file.path), thumbnail_path)
        except Exception as error:
            if self.generator.is_expected_generation_failure(error):
                raise NotFoundError("THUMBNAIL_NOT_AVAILABLE", "Thumbnail is not available for this file.") from error
            raise

        return thumbnail_path

    def _build_thumbnail_path(self, file: File) -> Path:
        modified_source = file.modified_at_fs or file.discovered_at
        modified_marker = modified_source.strftime("%Y%m%d%H%M%S%f")
        size_marker = file.size_bytes if file.size_bytes is not None else 0
        filename = f"thumb_{file.id}_{size_marker}_{modified_marker}.jpg"
        return self._get_thumbnail_cache_dir() / filename

    def _get_thumbnail_cache_dir(self) -> Path:
        return settings.data_dir / "thumbnails"
