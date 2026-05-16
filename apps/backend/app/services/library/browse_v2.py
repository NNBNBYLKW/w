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

            for f in file_rows:
                card = BrowseV2LooseFileCard(
                    file_id=f.id,
                    name=f.name,
                    file_kind=f.file_kind,
                    path=f.path,
                    storage_state=f.storage_state,
                    size_bytes=f.size_bytes,
                    modified_at=f.modified_at_fs,
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


browse_v2_service = BrowseV2Service()
