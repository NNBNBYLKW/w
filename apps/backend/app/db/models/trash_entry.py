from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base


class TrashEntry(Base):
    __tablename__ = "trash_entries"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"))
    original_path: Mapped[str]
    trashed_at: Mapped[datetime]
    expires_at: Mapped[datetime]
