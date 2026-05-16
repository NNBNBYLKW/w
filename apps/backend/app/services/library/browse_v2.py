"""Phase 8A: Browse v2 read model adapter.

Pure read-only — no DB writes, no file operations, no schema changes.
"""

from __future__ import annotations

from pathlib import Path
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.db.models.importing import ImportObjectCandidate, ImportObjectMember
from app.db.models.library_object import LibraryObject, LibraryObjectMember
from app.schemas.browse_v2 import (
    BrowseV2LooseFileCard,
    ObjectDetailMember,
    ObjectDetailResponse,
    BrowseV2ObjectCard,
    BrowseV2Response,
    BrowseV2Summary,
)


DOMAIN_TYPE_MAP: dict[str, set[str]] = {
    "media": {"movie", "anime", "course", "video_collection", "clip", "clip_set",
               "imgset", "photo_event", "web_image_set", "comic", "audio"},
    "documents": {"docset"},
    "apps": {"software", "game"},
    "assets": {"asset_pack"},
}

# category query group → individual backend values
CATEGORY_VALUES: dict[str, set[str]] = {
    "movie": {"movie"},
    "series_anime": {"anime"},
    "course": {"course"},
    "video_collection": {"video_collection"},
    "video_clip": {"clip", "clip_set"},
    "image_album": {"imgset", "photo_event", "web_image_set"},
    "comic": {"comic"},
    "audio": {"audio"},
    "docset": {"docset"},
    "software": {"software"},
    "game": {"game"},
    "asset_pack": {"asset_pack"},
}


def _storage_state_from_path(file_path: str | None, file_storage_state: str | None) -> str:
    """Derive a storage_state label for display. Uses file.storage_state if available."""
    if file_storage_state:
        return file_storage_state
    if file_path and "00_Inbox" in file_path.replace("\\", "/"):
        return "inbox"
    return "external"


def _badges_for_object(
    object_source: str, storage_state: str | None, needs_review: bool,
) -> list[str]:
    badges: list[str] = []
    if object_source == "import_object_candidate":
        badges.append("import")
    else:
        badges.append("object")
    if storage_state:
        badges.append(storage_state)
    if needs_review:
        badges.append("needs_review")
    return badges


def _badges_for_loose_file(file_kind: str | None, storage_state: str | None) -> list[str]:
    badges: list[str] = ["file"]
    if file_kind:
        badges.append(file_kind)
    if storage_state:
        badges.append(storage_state)
    return badges


class BrowseV2Service:
    """Read-only browse v2 read model adapter."""

    def list_cards(
        self,
        session: Session,
        *,
        domain: str = "media",
        category: str | None = None,
        storage_state: str = "all",
        card_kind: str = "all",
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "modified_at",
        sort_order: str = "desc",
    ) -> BrowseV2Response:
        # Resolve domain → allowed types
        domain_types = DOMAIN_TYPE_MAP.get(domain, set())
        category_values = CATEGORY_VALUES.get(category or "", set())

        # If category specified, use those values; otherwise use domain types
        type_filter = category_values if category else domain_types

        include_objects = card_kind in ("all", "object")
        include_loose = card_kind in ("all", "loose_file")

        items: list = []
        summary = BrowseV2Summary()

        # ── Object cards from library_objects ────────────────
        if include_objects and type_filter:
            lo_query = session.query(LibraryObject).filter(
                LibraryObject.object_type.in_(type_filter),
            )
            for lo in lo_query.all():
                if storage_state != "all":
                    # library_objects don't have storage_state yet; skip if filtering
                    # but keep for "managed" since these ARE managed objects
                    if storage_state not in ("managed",):
                        continue

                card = BrowseV2ObjectCard(
                    namespaced_id=f"library_object:{lo.id}",
                    object_source="library_object",
                    source_id=lo.id,
                    object_type=lo.object_type,
                    display_title=lo.title or lo.root_name or lo.root_path,
                    member_count=getattr(lo, "member_count", 0) or 0,
                    storage_state="managed",
                    root_path=lo.root_path,
                    needs_review=bool(lo.needs_review),
                    badges=_badges_for_object("library_object", "managed", bool(lo.needs_review)),
                )
                items.append(card)
                summary.total_objects += 1
                summary.managed_objects += 1

        # ── Object cards from import_object_candidates ──────
        if include_objects and type_filter:
            # Get set of library_object root paths for dedup
            lo_root_paths = {
                (lo.root_path or "").lower()
                for lo in session.query(LibraryObject.root_path).all()
            }

            ioc_query = session.query(ImportObjectCandidate).filter(
                ImportObjectCandidate.suggested_object_type.in_(type_filter),
                ImportObjectCandidate.status.in_(["pending_review", "confirmed"]),
            )
            for ioc in ioc_query.all():
                # Dedup: skip if a library_object already covers this root
                if (ioc.inbox_root_path or "").lower() in lo_root_paths:
                    continue

                ss = _storage_state_from_path(
                    ioc.inbox_root_path, None
                )
                # Derive state from inbox_root_path
                if ss == "external":
                    ss = "inbox"  # import candidates are in inbox

                if storage_state != "all" and storage_state != ss:
                    continue

                card = BrowseV2ObjectCard(
                    namespaced_id=f"import_object_candidate:{ioc.id}",
                    object_source="import_object_candidate",
                    source_id=ioc.id,
                    object_type=ioc.suggested_object_type,
                    display_title=Path(ioc.inbox_root_path or "").name or f"Candidate #{ioc.id}",
                    member_count=ioc.member_count,
                    storage_state=ss,
                    root_path=ioc.inbox_root_path,
                    needs_review=True,
                    confidence=ioc.confidence,
                    badges=_badges_for_object("import_object_candidate", ss, True),
                )
                items.append(card)
                summary.total_objects += 1
                if ss == "inbox":
                    summary.inbox_objects += 1

        # ── Loose file cards ────────────────────────────────
        if include_loose:
            # Collect file_ids that are object members
            member_file_ids: set[int] = set()

            # From library_object_members
            lom_rows = session.query(LibraryObjectMember.file_id).all()
            member_file_ids.update(r[0] for r in lom_rows if r[0] is not None)

            # From active import_object_members
            iom_rows = (
                session.query(ImportObjectMember.inbox_item_id)
                .join(ImportObjectCandidate,
                      ImportObjectMember.import_object_candidate_id == ImportObjectCandidate.id)
                .filter(ImportObjectCandidate.status.in_(["pending_review", "confirmed"]))
                .all()
            )
            # inbox_item_ids → file_ids
            from app.db.models.importing import InboxItem
            iom_inbox_ids = [r[0] for r in iom_rows if r[0] is not None]
            if iom_inbox_ids:
                ii_rows = session.query(InboxItem.file_id).filter(
                    InboxItem.id.in_(iom_inbox_ids)
                ).all()
                member_file_ids.update(r[0] for r in ii_rows if r[0] is not None)

            # Query loose files
            file_query = session.query(File).filter(
                File.is_deleted == False,
                ~File.id.in_(member_file_ids) if member_file_ids else True,
            )

            if storage_state != "all":
                file_query = file_query.filter(File.storage_state == storage_state)

            # Paginate
            total_files = file_query.count()
            offset = (page - 1) * page_size
            file_rows = file_query.order_by(
                File.modified_at_fs.desc() if sort_order == "desc" else File.modified_at_fs.asc()
            ).offset(offset).limit(page_size).all()

            # Pre-load inbox item info for inbox files (Phase 8C-2)
            inbox_file_ids = [f.id for f in file_rows if f.storage_state == "inbox"]
            inbox_info: dict[int, tuple[int, int]] = {}  # file_id -> (inbox_item_id, batch_id)
            if inbox_file_ids:
                from app.db.models.importing import InboxItem as II
                ii_rows = session.query(II).filter(
                    II.file_id.in_(inbox_file_ids)
                ).all()
                inbox_info = {ii.file_id: (ii.id, ii.import_batch_id) for ii in ii_rows if ii.file_id}

            for f in file_rows:
                ii_data = inbox_info.get(f.id) if f.storage_state == "inbox" else None
                card = BrowseV2LooseFileCard(
                    file_id=f.id,
                    name=f.name,
                    file_kind=f.file_kind,
                    path=f.path,
                    storage_state=f.storage_state,
                    size_bytes=f.size_bytes,
                    modified_at=f.modified_at_fs,
                    inbox_item_id=ii_data[0] if ii_data else None,
                    import_batch_id=ii_data[1] if ii_data else None,
                    badges=_badges_for_loose_file(f.file_kind, f.storage_state),
                )
                items.append(card)
                summary.total_loose_files += 1
                if f.storage_state == "external":
                    summary.external_loose += 1

        # ── Sort and paginate combined results ──────────────
        items.sort(key=lambda c: (
            0 if getattr(c, "card_kind", None) == "object" else 1,
            getattr(c, "display_title", "") if hasattr(c, "display_title") else getattr(c, "name", ""),
        ))

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = items[start:end]

        return BrowseV2Response(
            items=paged_items,
            summary=summary,
            total=total,
            page=page,
            page_size=page_size,
        )

    # ── Phase 8B: Object Detail ─────────────────────────────

    def get_object_detail(
        self,
        session: Session,
        *,
        object_source: str,
        source_id: int,
        member_page: int = 1,
        member_page_size: int = 50,
    ) -> ObjectDetailResponse:
        """Read-only object detail with paginated member list."""
        member_page_size = min(max(member_page_size, 1), 100)

        if object_source == "library_object":
            return self._library_object_detail(session, source_id, member_page, member_page_size)
        elif object_source == "import_object_candidate":
            return self._import_candidate_detail(session, source_id, member_page, member_page_size)
        else:
            raise ValueError(f"Unknown object_source: {object_source}")

    def _library_object_detail(
        self, session: Session, source_id: int,
        member_page: int, member_page_size: int,
    ) -> ObjectDetailResponse:
        from app.db.models.importing import InboxItem

        lo = session.query(LibraryObject).filter(LibraryObject.id == source_id).first()
        if lo is None:
            raise ValueError(f"Library object not found: {source_id}")

        # members
        member_query = session.query(LibraryObjectMember).filter(
            LibraryObjectMember.object_id == lo.id
        ).order_by(LibraryObjectMember.sort_index, LibraryObjectMember.id)

        member_total = member_query.count()
        member_rows = member_query.offset(
            (member_page - 1) * member_page_size
        ).limit(member_page_size).all()

        members: list[ObjectDetailMember] = []
        for lom in member_rows:
            f = session.query(File).filter(File.id == lom.file_id).first() if lom.file_id else None
            missing = lom.file_id is not None and f is None
            members.append(ObjectDetailMember(
                member_id=lom.id,
                file_id=lom.file_id,
                role=lom.member_role,
                name=f.name if f else (lom.relative_path or ""),
                path=f.path if f else (lom.absolute_path or ""),
                relative_path=lom.relative_path,
                file_kind=f.file_kind if f else None,
                size_bytes=f.size_bytes if f else (lom.size_bytes or None),
                modified_at=f.modified_at_fs if f else (lom.modified_at or None),
                storage_state=f.storage_state if f else None,
                missing=missing,
            ))

        return ObjectDetailResponse(
            object_id=f"library_object:{lo.id}",
            object_source="library_object",
            source_id=lo.id,
            object_type=lo.object_type,
            display_title=lo.title or lo.root_name or lo.root_path,
            storage_state="managed",
            status="organized",
            member_count=member_total,
            root_path=lo.root_path,
            members=members,
            member_page=member_page,
            member_page_size=member_page_size,
            member_total=member_total,
            needs_review=bool(lo.needs_review),
            notes=["Object detail is read-only in Phase 8B."],
        )

    def _import_candidate_detail(
        self, session: Session, source_id: int,
        member_page: int, member_page_size: int,
    ) -> ObjectDetailResponse:
        from app.db.models.importing import InboxItem

        ioc = session.query(ImportObjectCandidate).filter(
            ImportObjectCandidate.id == source_id
        ).first()
        if ioc is None:
            raise ValueError(f"Import object candidate not found: {source_id}")

        # members
        member_query = session.query(ImportObjectMember).filter(
            ImportObjectMember.import_object_candidate_id == ioc.id
        ).order_by(ImportObjectMember.id)

        member_total = member_query.count()
        member_rows = member_query.offset(
            (member_page - 1) * member_page_size
        ).limit(member_page_size).all()

        members: list[ObjectDetailMember] = []
        for iom in member_rows:
            ii = session.query(InboxItem).filter(InboxItem.id == iom.inbox_item_id).first() if iom.inbox_item_id else None
            f = session.query(File).filter(File.id == ii.file_id).first() if (ii and ii.file_id) else None
            missing = (iom.inbox_item_id is not None) and (ii is None or (ii.file_id is not None and f is None))
            rel_path = None
            if ii and ii.inbox_path and ioc.inbox_root_path:
                try:
                    rel_path = str(Path(ii.inbox_path).relative_to(ioc.inbox_root_path))
                except ValueError:
                    rel_path = Path(ii.inbox_path).name
            elif ii and ii.inbox_path:
                rel_path = Path(ii.inbox_path).name
            members.append(ObjectDetailMember(
                member_id=iom.id,
                file_id=f.id if f else (ii.file_id if ii else None),
                role=iom.role,
                name=f.name if f else (rel_path or ""),
                path=f.path if f else (ii.inbox_path if ii else None),
                relative_path=rel_path,
                file_kind=f.file_kind if f else None,
                size_bytes=f.size_bytes if f else None,
                modified_at=f.modified_at_fs if f else None,
                storage_state=f.storage_state if f else (ii.inbox_path and "inbox" or None),
                missing=missing,
            ))

        ss = "inbox"
        if ioc.status == "organized":
            ss = "managed"

        return ObjectDetailResponse(
            object_id=f"import_object_candidate:{ioc.id}",
            object_source="import_object_candidate",
            source_id=ioc.id,
            object_type=ioc.suggested_object_type or ioc.final_object_type,
            display_title=Path(ioc.inbox_root_path or "").name or f"Candidate #{ioc.id}",
            storage_state=ss,
            status=ioc.status,
            member_count=member_total,
            root_path=ioc.inbox_root_path,
            launch_file_id=ioc.launch_file_id,
            primary_file_id=ioc.primary_file_id,
            confidence=ioc.confidence,
            needs_review=ioc.status == "pending_review",
            members=members,
            member_page=member_page,
            member_page_size=member_page_size,
            member_total=member_total,
            notes=["Object detail is read-only in Phase 8B."],
        )


browse_v2_service = BrowseV2Service()
