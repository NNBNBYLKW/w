from sqlalchemy.orm import Session

from app.api.schemas.file import FileDetailItemResponse, FileDetailResponse
from app.core.errors.exceptions import NotFoundError
from app.repositories.file.repository import FileRepository
from app.repositories.file_metadata.repository import FileMetadataRepository
from app.repositories.file_tag.repository import FileTagRepository
from app.repositories.file_user_meta.repository import FileUserMetaRepository


class DetailsService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.file_metadata_repository = FileMetadataRepository()
        self.file_tag_repository = FileTagRepository()
        self.file_user_meta_repository = FileUserMetaRepository()

    def get_file_details(self, session: Session, file_id: int) -> FileDetailResponse:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")
        file_metadata = self.file_metadata_repository.get_by_file_id(session, file_id)
        tags = self.file_tag_repository.list_tags_for_file(session, file_id)
        file_user_meta = self.file_user_meta_repository.get_by_file_id(session, file_id)

        return FileDetailResponse(
            item=FileDetailItemResponse(
                id=file.id,
                name=file.name,
                path=file.path,
                file_type=file.file_type,
                size_bytes=file.size_bytes,
                created_at_fs=file.created_at_fs,
                modified_at_fs=file.modified_at_fs,
                discovered_at=file.discovered_at,
                last_seen_at=file.last_seen_at,
                is_deleted=file.is_deleted,
                source_id=file.source_id,
                tags=[{"id": tag.id, "name": tag.name} for tag in tags],
                color_tag=file_user_meta.color_tag if file_user_meta is not None else None,
                metadata=(
                    {
                        "width": file_metadata.width,
                        "height": file_metadata.height,
                        "duration_ms": file_metadata.duration_ms,
                        "page_count": file_metadata.page_count,
                    }
                    if file_metadata is not None
                    else None
                ),
            )
        )
