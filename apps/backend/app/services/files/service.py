from sqlalchemy.orm import Session

from app.api.schemas.file import FileListItemResponse, FileListQueryParams, FileListResponse
from app.core.classification import effective_placement
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.db.models.file import File
from app.repositories.file_user_meta.repository import FileUserMetaRepository
from app.repositories.file.repository import FileRepository
from app.repositories.source.repository import SourceRepository
from app.repositories.tag.repository import TagRepository


ALLOWED_COLOR_TAGS = {"red", "yellow", "green", "blue", "purple"}


class FilesService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.source_repository = SourceRepository()
        self.tag_repository = TagRepository()
        self.file_user_meta_repository = FileUserMetaRepository()

    def get_file(self, session: Session, file_id: int) -> File:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")
        return file

    def list_files(self, session: Session, params: FileListQueryParams) -> FileListResponse:
        if params.parent_path is not None and params.source_id is None:
            raise BadRequestError(
                "PARENT_PATH_REQUIRES_SOURCE",
                "parent_path requires source_id.",
            )

        if params.source_id is not None:
            source = self.source_repository.get_by_id(session, params.source_id)
            if source is None:
                raise NotFoundError("SOURCE_NOT_FOUND", "Source not found.")

        if params.tag_id is not None and self.tag_repository.get_by_id(session, params.tag_id) is None:
            raise NotFoundError("TAG_NOT_FOUND", "Tag not found.")

        normalized_color_tag = self._normalize_color_tag(params.color_tag)

        files, total = self.file_repository.list_indexed_files(
            session,
            file_kind=params.file_kind,
            source_id=params.source_id,
            parent_path=params.parent_path,
            tag_id=params.tag_id,
            color_tag=normalized_color_tag,
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        items = [
            self._to_list_item(session, file)
            for file in files
        ]
        return FileListResponse(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
        )

    def _to_list_item(self, session: Session, file) -> FileListItemResponse:
        file_user_meta = self.file_user_meta_repository.get_by_file_id(session, file.id)
        manual_placement = file_user_meta.manual_placement if file_user_meta is not None else None
        return FileListItemResponse(
            id=file.id,
            name=file.name,
            path=file.path,
            file_type=file.file_type,
            file_kind=file.file_kind,
            auto_placement=file.auto_placement,
            manual_placement=manual_placement,
            effective_placement=effective_placement(file.auto_placement, manual_placement),
            modified_at=file.modified_at_fs or file.discovered_at,
            size_bytes=file.size_bytes,
        )

    def list_files_in_directory(
        self,
        session: Session,
        parent_path: str,
        exclude_file_id: int,
        limit: int = 20,
    ) -> list[dict]:
        files = self.file_repository.list_files_in_directory(
            session,
            parent_path=parent_path,
            exclude_file_id=exclude_file_id,
            limit=limit,
        )
        return [
            {
                "id": f.id,
                "name": f.name,
                "path": f.path,
                "file_type": f.file_type,
                "modified_at": f.modified_at_fs or f.discovered_at,
            }
            for f in files
        ]

    def _normalize_color_tag(self, raw_color_tag: str | None) -> str | None:
        if raw_color_tag is None:
            return None

        normalized = raw_color_tag.strip().lower()
        if not normalized or normalized not in ALLOWED_COLOR_TAGS:
            raise BadRequestError("COLOR_TAG_INVALID", "Color tag is invalid.")
        return normalized
