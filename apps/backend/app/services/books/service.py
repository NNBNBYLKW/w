import re

from sqlalchemy.orm import Session

from app.api.schemas.books import BookListItemResponse, BooksListQueryParams, BooksListResponse
from app.repositories.file.repository import FileRepository


class BooksLibraryService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()

    def _build_display_title(self, stem: str | None, name: str) -> str:
        raw_value = stem if stem is not None and stem.strip() else name
        normalized_whitespace = re.sub(r"\s+", " ", raw_value.replace("_", " ").strip())
        return normalized_whitespace or name

    def list_books(self, session: Session, params: BooksListQueryParams) -> BooksListResponse:
        files, total = self.file_repository.list_book_files(
            session,
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        items = [
            BookListItemResponse(
                id=file.id,
                display_title=self._build_display_title(file.stem, file.name),
                book_format=(file.extension or "").lower(),
                path=file.path,
                modified_at=file.modified_at_fs or file.discovered_at,
                size_bytes=file.size_bytes,
            )
            for file in files
        ]
        return BooksListResponse(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
        )
