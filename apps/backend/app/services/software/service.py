import re

from sqlalchemy.orm import Session

from app.api.schemas.software import SoftwareListItemResponse, SoftwareListQueryParams, SoftwareListResponse
from app.repositories.file.repository import FileRepository


class SoftwareLibraryService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()

    def _build_display_title(self, stem: str | None, name: str) -> str:
        raw_value = stem if stem is not None and stem.strip() else name
        normalized_whitespace = re.sub(r"\s+", " ", raw_value.replace("_", " ").strip())
        return normalized_whitespace or name

    def _normalize_extension(self, extension: str | None) -> str:
        return (extension or "").lstrip(".").lower()

    def list_software(self, session: Session, params: SoftwareListQueryParams) -> SoftwareListResponse:
        rows, total = self.file_repository.list_software_files(
            session,
            tag_id=params.tag_id,
            color_tag=params.color_tag,
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        items = [
            SoftwareListItemResponse(
                id=file.id,
                display_title=self._build_display_title(file.stem, file.name),
                software_format=self._normalize_extension(file.extension),
                path=file.path,
                modified_at=file.modified_at_fs or file.discovered_at,
                size_bytes=file.size_bytes,
                is_favorite=is_favorite,
                rating=rating,
            )
            for file, is_favorite, rating in rows
        ]
        return SoftwareListResponse(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
        )
