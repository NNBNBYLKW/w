from pydantic import BaseModel


class TagCreateRequest(BaseModel):
    name: str


class TagItemResponse(BaseModel):
    id: int
    name: str


class TagResponse(BaseModel):
    item: TagItemResponse


class TagListResponse(BaseModel):
    items: list[TagItemResponse]
