from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.schemas.tag import TagCreateRequest, TagListResponse, TagResponse
from app.db.session.session import get_db
from app.services.tags.service import TagsService


router = APIRouter(tags=["tags"])
tags_service = TagsService()


@router.get("/tags", response_model=TagListResponse)
def list_tags(db: Session = Depends(get_db)) -> TagListResponse:
    return tags_service.list_tags(db)


@router.post("/tags", response_model=TagResponse)
def create_tag(
    payload: TagCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TagResponse:
    tag_response, created = tags_service.create_tag(db, payload)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return tag_response
