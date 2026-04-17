from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.api.schemas.collection import CollectionCreateRequest, CollectionFilesQueryParams, CollectionListResponse, CollectionResponse
from app.api.schemas.common import MessageResponse
from app.api.schemas.file import FileListItemResponse, FileListResponse
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.db.models.collection import Collection
from app.repositories.collection.repository import CollectionRepository
from app.repositories.file.repository import FileRepository
from app.repositories.source.repository import SourceRepository
from app.repositories.tag.repository import TagRepository


ALLOWED_COLOR_TAGS = {"red", "yellow", "green", "blue", "purple"}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CollectionsService:
    def __init__(self) -> None:
        self.collection_repository = CollectionRepository()
        self.file_repository = FileRepository()
        self.source_repository = SourceRepository()
        self.tag_repository = TagRepository()

    def list_collections(self, session: Session) -> CollectionListResponse:
        collections = self.collection_repository.list_collections(session)
        return CollectionListResponse(items=[CollectionResponse.model_validate(item) for item in collections])

    def create_collection(self, session: Session, payload: CollectionCreateRequest) -> CollectionResponse:
        name = payload.name.strip()
        if not name:
            raise BadRequestError("COLLECTION_NAME_INVALID", "Collection name cannot be empty.")

        if payload.tag_id is not None and self.tag_repository.get_by_id(session, payload.tag_id) is None:
            raise NotFoundError("TAG_NOT_FOUND", "Tag not found.")

        if payload.source_id is not None and self.source_repository.get_by_id(session, payload.source_id) is None:
            raise NotFoundError("SOURCE_NOT_FOUND", "Source not found.")

        color_tag = self._normalize_color_tag(payload.color_tag)
        if payload.parent_path is not None and payload.source_id is None:
            raise BadRequestError("PARENT_PATH_REQUIRES_SOURCE", "Parent path requires a source.")

        now = _utcnow()
        collection = Collection(
            name=name,
            file_type=payload.file_type,
            tag_id=payload.tag_id,
            color_tag=color_tag,
            source_id=payload.source_id,
            parent_path=payload.parent_path,
            created_at=now,
            updated_at=now,
        )
        self.collection_repository.add(session, collection)
        session.commit()
        session.refresh(collection)
        return CollectionResponse.model_validate(collection)

    def delete_collection(self, session: Session, collection_id: int) -> MessageResponse:
        collection = self.collection_repository.get_by_id(session, collection_id)
        if collection is None:
            raise NotFoundError("COLLECTION_NOT_FOUND", "Collection not found.")
        self.collection_repository.delete(session, collection)
        session.commit()
        return MessageResponse(message="Collection deleted.")

    def list_collection_files(
        self,
        session: Session,
        collection_id: int,
        params: CollectionFilesQueryParams,
    ) -> FileListResponse:
        collection = self.collection_repository.get_by_id(session, collection_id)
        if collection is None:
            raise NotFoundError("COLLECTION_NOT_FOUND", "Collection not found.")

        if collection.source_id is not None and self.source_repository.get_by_id(session, collection.source_id) is None:
            return FileListResponse(items=[], page=params.page, page_size=params.page_size, total=0)

        if collection.tag_id is not None and self.tag_repository.get_by_id(session, collection.tag_id) is None:
            return FileListResponse(items=[], page=params.page, page_size=params.page_size, total=0)

        files, total = self.file_repository.list_indexed_files(
            session,
            source_id=collection.source_id,
            parent_path=collection.parent_path,
            tag_id=collection.tag_id,
            color_tag=collection.color_tag,
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            file_type=collection.file_type,
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
        return FileListResponse(items=items, page=params.page, page_size=params.page_size, total=total)

    def _normalize_color_tag(self, raw_color_tag: str | None) -> str | None:
        if raw_color_tag is None:
            return None

        normalized = raw_color_tag.strip().lower()
        if not normalized or normalized not in ALLOWED_COLOR_TAGS:
            raise BadRequestError("COLOR_TAG_INVALID", "Color tag is invalid.")
        return normalized
