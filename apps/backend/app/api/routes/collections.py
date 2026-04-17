from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.collection import CollectionCreateRequest, CollectionFilesQueryParams, CollectionListResponse, CollectionResponse
from app.api.schemas.common import MessageResponse
from app.api.schemas.file import FileListResponse, FileListSortBy, SortOrder
from app.db.session.session import get_db
from app.services.collections.service import CollectionsService


router = APIRouter(prefix="/collections", tags=["collections"])
collections_service = CollectionsService()


@router.get("", response_model=CollectionListResponse)
def list_collections(db: Session = Depends(get_db)) -> CollectionListResponse:
    return collections_service.list_collections(db)


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(payload: CollectionCreateRequest, db: Session = Depends(get_db)) -> CollectionResponse:
    return collections_service.create_collection(db, payload)


@router.delete("/{collection_id}", response_model=MessageResponse)
def delete_collection(
    collection_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> MessageResponse:
    return collections_service.delete_collection(db, collection_id)


@router.get("/{collection_id}/files", response_model=FileListResponse)
def list_collection_files(
    collection_id: int = Path(..., ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> FileListResponse:
    params = CollectionFilesQueryParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return collections_service.list_collection_files(db, collection_id, params)
