from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Path as FastapiPath
from sqlalchemy.orm import Session

from app.db.models.library_root import LibraryRoot
from app.db.session.session import get_db
from app.core.config.settings import settings
from app.repositories.library_roots.repository import LibraryRootRepository
from app.schemas.library_root import (
    CreateLibraryRootRequest,
    LibraryRootItem,
    LibraryRootListResponse,
    UpdateLibraryRootRequest,
)
from app.services.library.root_safety import validate_managed_library_root_path


router = APIRouter(prefix="/library/roots", tags=["library"])
repository = LibraryRootRepository()


def _now() -> datetime:
    return datetime.now(UTC)


def _check_root_path_safety(resolved: Path) -> None:
    try:
        validate_managed_library_root_path(resolved, settings=settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _resolve_path(raw: str) -> Path:
    path = Path(raw).resolve()
    if not path.exists():
        raise HTTPException(status_code=400, detail="Path does not exist.")
    if not path.is_absolute():
        raise HTTPException(status_code=400, detail="Path must be absolute.")
    return path


def _check_overlap(session: Session, path_str: str) -> None:
    resolved = Path(path_str).resolve()
    for root in repository.list_enabled(session):
        root_path = Path(root.root_path).resolve()
        if str(root_path) == str(resolved):
            raise HTTPException(status_code=409, detail="A library root with this path already exists.")
        try:
            root_path.relative_to(resolved)
            raise HTTPException(
                status_code=400,
                detail=f"Path contains an existing enabled library root: {root.root_path}",
            )
        except ValueError:
            pass
        try:
            resolved.relative_to(root_path)
            raise HTTPException(
                status_code=400,
                detail=f"Path is contained by an existing enabled library root: {root.root_path}",
            )
        except ValueError:
            pass


@router.get("", response_model=LibraryRootListResponse)
def list_roots(db: Session = Depends(get_db)) -> LibraryRootListResponse:
    items = repository.list_all(db)
    return LibraryRootListResponse(items=[LibraryRootItem.model_validate(r) for r in items])


@router.post("", response_model=LibraryRootItem, status_code=201)
def create_root(payload: CreateLibraryRootRequest, db: Session = Depends(get_db)) -> LibraryRootItem:
    resolved = _resolve_path(payload.root_path)
    _check_root_path_safety(resolved)
    _check_overlap(db, payload.root_path)

    now = _now()
    root = LibraryRoot(
        root_path=str(Path(payload.root_path).resolve()),
        display_name=payload.display_name,
        root_kind="managed",
        is_enabled=True,
        is_default=False,
        scan_policy="manual",
        created_at=now,
        updated_at=now,
    )
    repository.add(db, root)
    db.commit()
    return LibraryRootItem.model_validate(root)


@router.get("/{root_id}", response_model=LibraryRootItem)
def get_root(root_id: int = FastapiPath(..., ge=1), db: Session = Depends(get_db)) -> LibraryRootItem:
    root = repository.get_by_id(db, root_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Library root not found.")
    return LibraryRootItem.model_validate(root)


@router.patch("/{root_id}", response_model=LibraryRootItem)
def update_root(
    payload: UpdateLibraryRootRequest,
    root_id: int = FastapiPath(..., ge=1),
    db: Session = Depends(get_db),
) -> LibraryRootItem:
    root = repository.get_by_id(db, root_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Library root not found.")

    if payload.display_name is not None:
        root.display_name = payload.display_name
    if payload.is_enabled is not None:
        if payload.is_enabled:
            _check_root_path_safety(Path(root.root_path).resolve())
        root.is_enabled = payload.is_enabled
        if not payload.is_enabled and root.is_default:
            root.is_default = False
    if payload.scan_policy is not None:
        root.scan_policy = payload.scan_policy
    root.updated_at = _now()
    db.commit()
    return LibraryRootItem.model_validate(root)


@router.post("/{root_id}/set-default", response_model=LibraryRootItem)
def set_default_root(root_id: int = FastapiPath(..., ge=1), db: Session = Depends(get_db)) -> LibraryRootItem:
    root = repository.get_by_id(db, root_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Library root not found.")
    _check_root_path_safety(Path(root.root_path).resolve())
    if not root.is_enabled:
        raise HTTPException(status_code=400, detail="Cannot set disabled root as default.")

    for r in repository.list_all(db):
        if r.is_default and r.id != root_id:
            r.is_default = False
            r.updated_at = _now()
    root.is_default = True
    root.updated_at = _now()
    db.commit()
    return LibraryRootItem.model_validate(root)
