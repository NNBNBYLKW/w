from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.library_root import LibraryRoot


class LibraryRootRepository:
    def list_all(self, session: Session) -> list[LibraryRoot]:
        statement = select(LibraryRoot).order_by(LibraryRoot.created_at.desc())
        return list(session.scalars(statement))

    def list_enabled(self, session: Session) -> list[LibraryRoot]:
        statement = (
            select(LibraryRoot)
            .where(LibraryRoot.is_enabled == True)
            .order_by(LibraryRoot.created_at.desc())
        )
        return list(session.scalars(statement))

    def get_by_id(self, session: Session, root_id: int) -> LibraryRoot | None:
        return session.get(LibraryRoot, root_id)

    def get_by_path(self, session: Session, path: str) -> LibraryRoot | None:
        statement = select(LibraryRoot).where(LibraryRoot.root_path == path)
        return session.scalar(statement)

    def get_default(self, session: Session) -> LibraryRoot | None:
        """Return the default root, or the only root, or None if ambiguous."""
        enabled = self.list_enabled(session)
        if not enabled:
            return None
        for r in enabled:
            if r.is_default:
                return r
        if len(enabled) == 1:
            return enabled[0]
        return None

    def any_root_contains(self, session: Session, path: str) -> LibraryRoot | None:
        """Check if any enabled root's path contains, or is contained by, the given path."""
        resolved = Path(path).resolve()
        for root in self.list_enabled(session):
            root_path = Path(root.root_path).resolve()
            try:
                common = Path(root_path).resolve().relative_to(resolved)
                if common is not None:
                    return root
            except ValueError:
                pass
            try:
                common = resolved.relative_to(root_path)
                if common is not None:
                    return root
            except ValueError:
                pass
        return None

    def count_plans_referencing(self, session: Session, root_id: int) -> int:
        from app.db.models.organize import OrganizePlan

        statement = select(OrganizePlan).where(OrganizePlan.target_library_root_id == root_id)
        return len(session.scalars(statement).all())

    def add(self, session: Session, root: LibraryRoot) -> LibraryRoot:
        session.add(root)
        session.flush()
        return root

    def delete(self, session: Session, root: LibraryRoot) -> None:
        session.delete(root)
