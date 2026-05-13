from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.library_object import AssetMetadataCache, LibraryObject, LibraryObjectMember
from app.repositories.library_objects.repository import LibraryObjectListFilters, LibraryObjectRepository
from app.repositories.source.repository import SourceRepository
from app.schemas.library_objects import (
    AssetMetadataSummary,
    LibraryObjectDetailResponse,
    LibraryObjectListItem,
    LibraryObjectListResponse,
    LibraryObjectMemberItem,
    LibraryObjectMembersResponse,
    LibraryObjectScanResponse,
    LibraryOverviewStatsResponse,
)
from app.services.library.object_parser import (
    ScannedMember,
    parse_object_folder_name,
    parse_scanned_object,
    parsed_json_for_cache,
)


@dataclass(frozen=True)
class ScanRoot:
    path: Path
    source_id: int | None = None


class LibraryObjectScannerService:
    def __init__(
        self,
        object_repository: LibraryObjectRepository | None = None,
        source_repository: SourceRepository | None = None,
    ) -> None:
        self.object_repository = object_repository or LibraryObjectRepository()
        self.source_repository = source_repository or SourceRepository()

    def scan_objects(
        self,
        session: Session,
        *,
        root_path: str | None = None,
        source_id: int | None = None,
        dry_run: bool = False,
    ) -> LibraryObjectScanResponse:
        roots = self._resolve_scan_roots(session, root_path=root_path, source_id=source_id)
        now = datetime.now(UTC).replace(tzinfo=None)
        objects_found = 0
        objects_created = 0
        objects_updated = 0
        needs_review = 0
        errors: list[str] = []

        for scan_root in roots:
            for object_root in self._iter_object_roots(scan_root.path):
                scanned = parse_scanned_object(object_root)
                if scanned is None:
                    continue
                objects_found += 1
                if scanned.needs_review:
                    needs_review += 1
                if dry_run:
                    continue
                existing = self.object_repository.get_by_root_path(session, scanned.root_path)
                if existing is None:
                    existing = LibraryObject(
                        object_type=scanned.object_type,
                        type_prefix=scanned.type_prefix,
                        root_path=scanned.root_path,
                        root_name=scanned.root_name,
                        filesystem_title=scanned.filesystem_title,
                        title=scanned.title,
                        original_title=scanned.original_title,
                        romanized_title=scanned.romanized_title,
                        localized_title_json=scanned.localized_title_json,
                        sort_title=scanned.sort_title,
                        year=scanned.year,
                        tags_json=scanned.tags_json,
                        cover_path=scanned.cover_path,
                        primary_file_path=scanned.primary_file_path,
                        metadata_source=scanned.metadata_source,
                        needs_review=scanned.needs_review,
                        review_reason=scanned.review_reason,
                        created_at=now,
                        updated_at=now,
                        last_scanned_at=now,
                    )
                    self.object_repository.add(session, existing)
                    objects_created += 1
                else:
                    self._apply_scanned_object(existing, scanned, now)
                    objects_updated += 1

                self.object_repository.delete_members(session, existing.id)
                self.object_repository.add_members(
                    session,
                    [self._to_member_model(session, existing.id, member, now) for member in scanned.members],
                )
                self.object_repository.upsert_asset_metadata(
                    session,
                    AssetMetadataCache(
                        object_id=existing.id,
                        yaml_path=str(scanned.asset_yaml.yaml_path) if scanned.asset_yaml.yaml_path else None,
                        schema_version=scanned.asset_yaml.schema_version,
                        parsed_json=parsed_json_for_cache(scanned.asset_yaml),
                        parse_status=scanned.asset_yaml.parse_status,
                        parse_error=scanned.asset_yaml.parse_error,
                        updated_at=now,
                    ),
                )
        if not dry_run:
            session.commit()
        return LibraryObjectScanResponse(
            scanned_roots=len(roots),
            objects_found=objects_found,
            objects_created=objects_created,
            objects_updated=objects_updated,
            needs_review=needs_review,
            errors=errors,
        )

    def list_objects(
        self,
        session: Session,
        *,
        page: int,
        page_size: int,
        object_type: str | None,
        needs_review: bool | None,
        query: str | None,
        sort_by: str,
        sort_order: str,
    ) -> LibraryObjectListResponse:
        filters = LibraryObjectListFilters(
            page=page,
            page_size=page_size,
            object_type=object_type,
            needs_review=needs_review,
            query=query,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        objects, total = self.object_repository.list_objects(session, filters)
        counts = self.object_repository.member_counts_for_objects(session, [item.id for item in objects])
        return LibraryObjectListResponse(
            items=[self._to_list_item(item, counts.get(item.id, 0)) for item in objects],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_object_detail(
        self,
        session: Session,
        object_id: int,
        *,
        members_page: int = 1,
        members_page_size: int = 50,
    ) -> LibraryObjectDetailResponse:
        library_object = self.object_repository.get_by_id(session, object_id)
        if library_object is None:
            raise HTTPException(status_code=404, detail="Library object not found.")
        members, total = self.object_repository.list_members(
            session,
            object_id,
            page=members_page,
            page_size=members_page_size,
        )
        metadata = self.object_repository.get_asset_metadata(session, object_id)
        return LibraryObjectDetailResponse(
            object=self._to_list_item(library_object, total),
            asset_metadata=self._to_asset_metadata_summary(metadata),
            members=[self._to_member_item(member) for member in members],
            members_total=total,
            members_page=members_page,
            members_page_size=members_page_size,
        )

    def list_members(
        self,
        session: Session,
        object_id: int,
        *,
        page: int,
        page_size: int,
        role: str | None,
    ) -> LibraryObjectMembersResponse:
        if self.object_repository.get_by_id(session, object_id) is None:
            raise HTTPException(status_code=404, detail="Library object not found.")
        members, total = self.object_repository.list_members(
            session,
            object_id,
            page=page,
            page_size=page_size,
            role=role,
        )
        return LibraryObjectMembersResponse(
            items=[self._to_member_item(member) for member in members],
            total=total,
            page=page,
            page_size=page_size,
        )

    def overview_stats(self, session: Session) -> LibraryOverviewStatsResponse:
        counts = self.object_repository.overview_counts(session)
        return LibraryOverviewStatsResponse(**counts)

    def _resolve_scan_roots(
        self,
        session: Session,
        *,
        root_path: str | None,
        source_id: int | None,
    ) -> list[ScanRoot]:
        sources = [source for source in self.source_repository.list_sources(session) if source.is_enabled]
        if source_id is not None:
            sources = [source for source in sources if source.id == source_id]
            if not sources:
                raise HTTPException(status_code=404, detail="Enabled source was not found.")

        if root_path:
            root = Path(root_path).expanduser()
            if not root.exists() or not root.is_dir():
                raise HTTPException(status_code=400, detail="Scan root must exist and be a directory.")
            resolved_root = root.resolve()
            if not any(_is_path_within(resolved_root, Path(source.path).resolve()) for source in sources):
                raise HTTPException(status_code=400, detail="Scan root must be inside an enabled source.")
            return [ScanRoot(path=resolved_root)]

        roots: list[ScanRoot] = []
        for source in sources:
            path = Path(source.path).expanduser()
            if path.exists() and path.is_dir():
                roots.append(ScanRoot(path=path.resolve(), source_id=source.id))
        return roots

    def _iter_object_roots(self, root_path: Path):
        stack = [root_path]
        while stack:
            current = stack.pop()
            try:
                children = sorted(current.iterdir(), key=lambda child: child.name.lower())
            except OSError:
                continue
            for child in children:
                if not child.is_dir() or child.is_symlink():
                    continue
                if parse_object_folder_name(child.name) is not None:
                    yield child.resolve()
                    continue
                stack.append(child)

    def _apply_scanned_object(self, target: LibraryObject, scanned, now: datetime) -> None:
        target.object_type = scanned.object_type
        target.type_prefix = scanned.type_prefix
        target.root_name = scanned.root_name
        target.filesystem_title = scanned.filesystem_title
        target.title = scanned.title
        target.original_title = scanned.original_title
        target.romanized_title = scanned.romanized_title
        target.localized_title_json = scanned.localized_title_json
        target.sort_title = scanned.sort_title
        target.year = scanned.year
        target.tags_json = scanned.tags_json
        target.cover_path = scanned.cover_path
        target.primary_file_path = scanned.primary_file_path
        target.metadata_source = scanned.metadata_source
        target.needs_review = scanned.needs_review
        target.review_reason = scanned.review_reason
        target.updated_at = now
        target.last_scanned_at = now

    def _to_member_model(
        self,
        session: Session,
        object_id: int,
        scanned_member: ScannedMember,
        now: datetime,
    ) -> LibraryObjectMember:
        modified_at = None
        if isinstance(scanned_member.modified_at, (int, float)):
            modified_at = datetime.fromtimestamp(scanned_member.modified_at)
        return LibraryObjectMember(
            object_id=object_id,
            file_id=self.object_repository.get_file_id_by_path(session, scanned_member.absolute_path),
            relative_path=scanned_member.relative_path,
            absolute_path=scanned_member.absolute_path,
            member_role=scanned_member.member_role,
            sort_index=scanned_member.sort_index,
            hidden_from_global=scanned_member.hidden_from_global,
            extension=scanned_member.extension,
            size_bytes=scanned_member.size_bytes,
            modified_at=modified_at,
            created_at=now,
        )

    def _to_list_item(self, item: LibraryObject, members_count: int) -> LibraryObjectListItem:
        tags = _json_list(item.tags_json)
        display_title = item.title or item.filesystem_title or item.root_name
        return LibraryObjectListItem(
            id=item.id,
            object_type=item.object_type,
            type_prefix=item.type_prefix,
            title=item.title,
            display_title=display_title,
            year=item.year,
            tags=tags,
            root_path=item.root_path,
            cover_path=item.cover_path,
            primary_file_path=item.primary_file_path,
            metadata_source=item.metadata_source,
            needs_review=item.needs_review,
            review_reason=item.review_reason,
            last_scanned_at=item.last_scanned_at,
            members_count=members_count,
        )

    def _to_member_item(self, member: LibraryObjectMember) -> LibraryObjectMemberItem:
        return LibraryObjectMemberItem(
            id=member.id,
            object_id=member.object_id,
            file_id=member.file_id,
            relative_path=member.relative_path,
            absolute_path=member.absolute_path,
            member_role=member.member_role,
            sort_index=member.sort_index,
            hidden_from_global=member.hidden_from_global,
            extension=member.extension,
            size_bytes=member.size_bytes,
            modified_at=member.modified_at,
        )

    def _to_asset_metadata_summary(self, metadata: AssetMetadataCache | None) -> AssetMetadataSummary | None:
        if metadata is None:
            return None
        return AssetMetadataSummary(
            yaml_path=metadata.yaml_path,
            schema_version=metadata.schema_version,
            parse_status=metadata.parse_status,
            parse_error=metadata.parse_error,
        )


def _is_path_within(path: Path, root: Path) -> bool:
    normalized_path = os.path.normcase(os.path.abspath(path))
    normalized_root = os.path.normcase(os.path.abspath(root))
    try:
        common = os.path.commonpath([normalized_path, normalized_root])
    except ValueError:
        return False
    return common == normalized_root


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        import json

        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []
