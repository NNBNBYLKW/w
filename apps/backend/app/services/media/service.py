from sqlalchemy.orm import Session

from app.api.schemas.media import MediaListItemResponse, MediaListQueryParams, MediaListResponse
from app.repositories.file.repository import FileRepository


class MediaLibraryService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()

    def list_media(self, session: Session, params: MediaListQueryParams) -> MediaListResponse:
        files, total = self.file_repository.list_media_files(
            session,
            view_scope=params.view_scope,
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        items = [
            MediaListItemResponse(
                id=file.id,
                name=file.name,
                path=file.path,
                file_type=file.file_type,
                modified_at=file.modified_at_fs or file.discovered_at,
                size_bytes=file.size_bytes,
            )
            for file in files
        ]
        return MediaListResponse(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
        )
