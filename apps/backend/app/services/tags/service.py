import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.api.schemas.file import FileListItemResponse, FileListResponse
from app.api.schemas.tag import TagCreateRequest, TagFileListQueryParams, TagItemResponse, TagListResponse, TagResponse
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.db.models.tag import Tag
from app.repositories.file.repository import FileRepository
from app.repositories.file_tag.repository import FileTagRepository
from app.repositories.tag.repository import TagRepository


WHITESPACE_PATTERN = re.compile(r"\s+")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TagsService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.file_tag_repository = FileTagRepository()
        self.tag_repository = TagRepository()

    def list_tags(self, session: Session) -> TagListResponse:
        tags = self.tag_repository.list_tags(session)
        return TagListResponse(items=[self._to_tag_item(tag) for tag in tags])

    def create_tag(self, session: Session, payload: TagCreateRequest) -> tuple[TagResponse, bool]:
        cleaned_name, normalized_name = self._normalize_tag_name(payload.name)
        existing_tag = self.tag_repository.get_by_normalized_name(session, normalized_name)
        if existing_tag is not None:
            return TagResponse(item=self._to_tag_item(existing_tag)), False

        now = _utcnow()
        tag = Tag(
            name=cleaned_name,
            normalized_name=normalized_name,
            created_at=now,
            updated_at=now,
        )
        self.tag_repository.add(session, tag)
        session.commit()
        return TagResponse(item=self._to_tag_item(tag)), True

    def attach_tag_to_file(self, session: Session, file_id: int, payload: TagCreateRequest) -> TagListResponse:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")

        cleaned_name, normalized_name = self._normalize_tag_name(payload.name)
        tag = self.tag_repository.get_by_normalized_name(session, normalized_name)
        if tag is None:
            now = _utcnow()
            tag = Tag(
                name=cleaned_name,
                normalized_name=normalized_name,
                created_at=now,
                updated_at=now,
            )
            self.tag_repository.add(session, tag)

        self.file_tag_repository.attach_tag(session, file_id, tag.id, _utcnow())
        session.commit()
        return self._build_file_tag_list(session, file_id)

    def list_files_for_tag(
        self,
        session: Session,
        tag_id: int,
        params: TagFileListQueryParams,
    ) -> FileListResponse:
        tag = self.tag_repository.get_by_id(session, tag_id)
        if tag is None:
            raise NotFoundError("TAG_NOT_FOUND", "Tag not found.")

        files, total = self.file_repository.list_files_for_tag(
            session,
            tag_id=tag_id,
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        items = [
            FileListItemResponse(
                id=file.id,
                name=file.name,
                path=file.path,
                file_type=file.file_type,
                modified_at=file.modified_at_fs or file.discovered_at,
                size_bytes=file.size_bytes,
            )
            for file in files
        ]
        return FileListResponse(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
        )

    def remove_tag_from_file(self, session: Session, file_id: int, tag_id: int) -> TagListResponse:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")

        tag = self.tag_repository.get_by_id(session, tag_id)
        if tag is None:
            raise NotFoundError("TAG_NOT_FOUND", "Tag not found.")

        self.file_tag_repository.detach_tag(session, file_id, tag_id)
        session.commit()
        return self._build_file_tag_list(session, file_id)

    def _build_file_tag_list(self, session: Session, file_id: int) -> TagListResponse:
        tags = self.file_tag_repository.list_tags_for_file(session, file_id)
        return TagListResponse(items=[self._to_tag_item(tag) for tag in tags])

    def _normalize_tag_name(self, raw_name: str) -> tuple[str, str]:
        cleaned_name = WHITESPACE_PATTERN.sub(" ", raw_name.strip())
        if not cleaned_name:
            raise BadRequestError("TAG_NAME_INVALID", "Tag name cannot be empty.")
        return cleaned_name, cleaned_name.casefold()

    def _to_tag_item(self, tag: Tag) -> TagItemResponse:
        return TagItemResponse(id=tag.id, name=tag.name)
