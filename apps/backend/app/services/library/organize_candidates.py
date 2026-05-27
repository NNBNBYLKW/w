from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.classification import (
    DOCUMENT_EXTENSIONS_DOTTED as DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS_DOTTED as IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS_DOTTED as VIDEO_EXTENSIONS,
)
from app.core.time import utcnow
from app.db.models.file import File
from app.db.models.library_object import LibraryObject
from app.db.models.library_root import LibraryRoot
from app.db.models.organize import OrganizeCandidate, OrganizeSuggestion
from app.repositories.library_organize.repository import CandidateFilters, LibraryOrganizeRepository
from app.repositories.source.repository import SourceRepository
from app.schemas.library_organize import (
    CandidateListResponse,
    CandidateScanResponse,
    GenerateSuggestionsResponse,
    OrganizeCandidateItem,
    OrganizeSuggestionItem,
    OrganizeSuggestionListResponse,
)
from app.services.library.object_parser import SUPPORTED_OBJECT_TYPES
from app.services.library.organize_template_renderer import (
    _safe_title,
    _strip_extension,
    _year_from_text,
    suggested_template_key,
)

_now = utcnow

INBOX_NAMES = {"00_inbox", "_to_sort", "inbox"}


@dataclass(frozen=True)
class CandidateDraft:
    candidate_type: str
    source_kind: str
    source_file_id: int | None
    source_object_id: int | None
    source_path: str
    display_name: str
    detected_type: str
    confidence: str
    reason: str


@dataclass(frozen=True)
class SuggestionDraft:
    suggestion_type: str
    payload: dict
    confidence: float
    reason: str


class RuleBasedOrganizeSuggestionProvider:
    provider = "rule_based"

    def generate(self, candidate: OrganizeCandidate) -> list[SuggestionDraft]:
        title = _safe_title(_strip_extension(candidate.display_name))
        year = _year_from_text(candidate.display_name)
        detected_type = candidate.detected_type if candidate.detected_type in set(SUPPORTED_OBJECT_TYPES.values()) else "clip"
        tags = _suggestion_tags(candidate)
        template_key = suggested_template_key(detected_type)
        asset_yaml = _asset_yaml_draft(candidate, Path(candidate.source_path).name if candidate.source_kind == "file" else None)
        asset_yaml["type"] = detected_type
        asset_yaml["title"] = title
        asset_yaml["year"] = year
        asset_yaml["tags"] = tags
        return [
            SuggestionDraft("title", {"title": title}, 0.72, "Derived from candidate display name."),
            SuggestionDraft("object_type", {"object_type": detected_type}, _confidence_score(candidate.confidence), candidate.reason),
            SuggestionDraft("tags", {"tags": tags}, 0.6 if tags else 0.45, "Extracted from filename and path keywords."),
            SuggestionDraft("template_key", {"template_key": template_key}, 0.65, f"Mapped object type '{detected_type}' to builtin template."),
            SuggestionDraft("asset_yaml", asset_yaml, 0.62, "Built from rule-based title, type, year, and tag suggestions."),
        ]


class OrganizeCandidates:
    """Candidate and suggestion management for organize plans."""

    def __init__(
        self,
        repository: LibraryOrganizeRepository | None = None,
        source_repository: SourceRepository | None = None,
    ) -> None:
        self.repository = repository or LibraryOrganizeRepository()
        self.source_repository = source_repository or SourceRepository()

    # ------------------------------------------------------------------
    # Candidate CRUD
    # ------------------------------------------------------------------

    def scan_candidates(self, session: Session) -> CandidateScanResponse:
        now = _now()
        objects, files, member_paths = self.repository.list_candidate_sources(session)
        drafts: list[CandidateDraft] = []
        for library_object in objects:
            drafts.append(self._candidate_from_object(library_object))
        sources = {source.id: Path(source.path).resolve() for source in self.source_repository.list_sources(session) if source.is_enabled}
        for file in files:
            if file.path in member_paths:
                continue
            source_root = sources.get(file.source_id)
            if source_root is None or not self._path_within(file, source_root):
                continue
            if not self._is_candidate_file(file, source_root):
                continue
            drafts.append(self._candidate_from_file(file, source_root))

        created = 0
        updated = 0
        ignored = 0
        needs_review = 0
        for draft in drafts:
            existing = self.repository.find_candidate(
                session,
                source_kind=draft.source_kind,
                source_file_id=draft.source_file_id,
                source_object_id=draft.source_object_id,
                candidate_type=draft.candidate_type,
                source_path=draft.source_path,
            )
            if existing is not None and existing.status == "ignored":
                ignored += 1
                continue
            if existing is None:
                existing = OrganizeCandidate(
                    candidate_type=draft.candidate_type,
                    source_kind=draft.source_kind,
                    source_file_id=draft.source_file_id,
                    source_object_id=draft.source_object_id,
                    source_path=draft.source_path,
                    display_name=draft.display_name,
                    detected_type=draft.detected_type,
                    confidence=draft.confidence,
                    reason=draft.reason,
                    status="pending",
                    ignored_at=None,
                    created_at=now,
                    updated_at=now,
                )
                self.repository.add_candidate(session, existing)
                created += 1
            else:
                existing.display_name = draft.display_name
                existing.detected_type = draft.detected_type
                existing.confidence = draft.confidence
                existing.reason = draft.reason
                existing.updated_at = now
                updated += 1
            if draft.confidence in {"low", "unknown"} or draft.candidate_type != "loose_file":
                needs_review += 1
        session.commit()
        return CandidateScanResponse(
            scanned_count=len(drafts),
            candidates_created=created,
            candidates_updated=updated,
            needs_review_count=needs_review,
            ignored_count=ignored,
        )

    def list_candidates(
        self,
        session: Session,
        *,
        page: int,
        page_size: int,
        candidate_type: str | None,
        status: str | None,
        detected_type: str | None,
        confidence: str | None,
        query: str | None,
    ) -> CandidateListResponse:
        items, total = self.repository.list_candidates(
            session,
            CandidateFilters(
                page=page,
                page_size=page_size,
                candidate_type=candidate_type,
                status=status,
                detected_type=detected_type,
                confidence=confidence,
                query=query,
            ),
        )
        return CandidateListResponse(items=[self._candidate_item(item) for item in items], total=total, page=page, page_size=page_size)

    def get_candidate(self, session: Session, candidate_id: int) -> OrganizeCandidateItem:
        candidate = self.repository.get_candidate(session, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Organize candidate not found.")
        return self._candidate_item(candidate)

    def ignore_candidate(self, session: Session, candidate_id: int) -> OrganizeCandidateItem:
        candidate = self.repository.get_candidate(session, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Organize candidate not found.")
        now = _now()
        candidate.status = "ignored"
        candidate.ignored_at = now
        candidate.updated_at = now
        session.commit()
        return self._candidate_item(candidate)

    # ------------------------------------------------------------------
    # Suggestions
    # ------------------------------------------------------------------

    def generate_candidate_suggestions(self, session: Session, candidate_id: int) -> GenerateSuggestionsResponse:
        candidate = self.repository.get_candidate(session, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Organize candidate not found.")
        provider = RuleBasedOrganizeSuggestionProvider()
        now = _now()
        created: list[OrganizeSuggestion] = []
        for draft in provider.generate(candidate):
            existing = self.repository.find_pending_suggestion(
                session,
                candidate_id=candidate.id,
                suggestion_type=draft.suggestion_type,
                provider=provider.provider,
            )
            if existing is not None:
                created.append(existing)
                continue
            suggestion = OrganizeSuggestion(
                candidate_id=candidate.id,
                plan_id=None,
                action_id=None,
                suggestion_type=draft.suggestion_type,
                payload_json=json.dumps(draft.payload, ensure_ascii=False, indent=2),
                confidence=draft.confidence,
                reason=draft.reason,
                provider=provider.provider,
                status="pending",
                created_at=now,
                accepted_at=None,
                rejected_at=None,
            )
            self.repository.add_suggestion(session, suggestion)
            created.append(suggestion)
        session.commit()
        items = self.repository.list_candidate_suggestions(session, candidate.id)
        return GenerateSuggestionsResponse(
            candidate_id=candidate.id,
            created_count=len(created),
            items=[self._suggestion_item(item) for item in items],
        )

    def list_candidate_suggestions(self, session: Session, candidate_id: int) -> OrganizeSuggestionListResponse:
        candidate = self.repository.get_candidate(session, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Organize candidate not found.")
        items = self.repository.list_candidate_suggestions(session, candidate.id)
        return OrganizeSuggestionListResponse(items=[self._suggestion_item(item) for item in items])

    def accept_suggestion(self, session: Session, suggestion_id: int) -> OrganizeSuggestionItem:
        suggestion = self.repository.get_suggestion(session, suggestion_id)
        if suggestion is None:
            raise HTTPException(status_code=404, detail="Organize suggestion not found.")
        if suggestion.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending suggestions can be accepted.")
        suggestion.status = "accepted"
        suggestion.accepted_at = _now()
        session.commit()
        return self._suggestion_item(suggestion)

    def reject_suggestion(self, session: Session, suggestion_id: int) -> OrganizeSuggestionItem:
        suggestion = self.repository.get_suggestion(session, suggestion_id)
        if suggestion is None:
            raise HTTPException(status_code=404, detail="Organize suggestion not found.")
        if suggestion.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending suggestions can be rejected.")
        suggestion.status = "rejected"
        suggestion.rejected_at = _now()
        session.commit()
        return self._suggestion_item(suggestion)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _path_within(file: File, source_root: Path) -> bool:
        from app.services.library.path_safety import is_path_within
        return is_path_within(Path(file.path), source_root)

    def _candidate_from_object(self, item: LibraryObject) -> CandidateDraft:
        if item.metadata_source == "invalid_asset_yaml":
            candidate_type = "invalid_asset_yaml"
            confidence = "high"
            reason = "asset.yaml could not be parsed and needs a draft repair plan."
        elif item.object_type == "unknown_object":
            candidate_type = "unknown_object"
            confidence = "high"
            reason = "Object root has an unknown [TYPE] prefix."
        else:
            candidate_type = "needs_review_object"
            confidence = "high"
            reason = item.review_reason or "Object scanner marked this object as needs_review."
        return CandidateDraft(
            candidate_type=candidate_type,
            source_kind="object",
            source_file_id=None,
            source_object_id=item.id,
            source_path=item.root_path,
            display_name=item.title or item.filesystem_title or item.root_name,
            detected_type=item.object_type,
            confidence=confidence,
            reason=reason,
        )

    def _candidate_from_file(self, file: File, source_root: Path) -> CandidateDraft:
        detected_type, confidence, reason = _detect_file_type(file)
        candidate_type = "inbox_file" if _is_inbox_path(Path(file.path), source_root) else "loose_file"
        return CandidateDraft(
            candidate_type=candidate_type,
            source_kind="file",
            source_file_id=file.id,
            source_object_id=None,
            source_path=file.path,
            display_name=file.name,
            detected_type=detected_type,
            confidence=confidence,
            reason=reason,
        )

    def _is_candidate_file(self, file: File, source_root: Path) -> bool:
        path = Path(file.path)
        extension = path.suffix.lower()
        if extension in {".zip", ".rar", ".7z"}:
            return False
        if _is_inbox_path(path, source_root):
            return True
        try:
            relative = path.relative_to(source_root)
        except ValueError:
            return False
        return len(relative.parts) <= 2

    def _suggestion_item(self, suggestion: OrganizeSuggestion) -> OrganizeSuggestionItem:
        return OrganizeSuggestionItem(
            id=suggestion.id,
            candidate_id=suggestion.candidate_id,
            plan_id=suggestion.plan_id,
            action_id=suggestion.action_id,
            suggestion_type=suggestion.suggestion_type,
            payload_json=suggestion.payload_json,
            confidence=suggestion.confidence,
            reason=suggestion.reason,
            provider=suggestion.provider,
            status=suggestion.status,
            created_at=suggestion.created_at,
            accepted_at=suggestion.accepted_at,
            rejected_at=suggestion.rejected_at,
        )

    def _candidate_item(self, candidate: OrganizeCandidate) -> OrganizeCandidateItem:
        return OrganizeCandidateItem(
            id=candidate.id,
            candidate_type=candidate.candidate_type,
            source_kind=candidate.source_kind,
            source_file_id=candidate.source_file_id,
            source_object_id=candidate.source_object_id,
            source_path=candidate.source_path,
            display_name=candidate.display_name,
            detected_type=candidate.detected_type,
            confidence=candidate.confidence,
            reason=candidate.reason,
            status=candidate.status,
            ignored_at=candidate.ignored_at,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )


# ------------------------------------------------------------------
# Module-level helpers used by candidate flow
# ------------------------------------------------------------------


def _detect_file_type(file, folder_name=None):
    """Return (type, confidence, reason). Optionally uses folder_name for stronger signals."""
    name = file.name
    extension = Path(file.path).suffix.lower()
    if folder_name:
        from app.core.classification import detect_type_from_folder_name

        ft, fc = detect_type_from_folder_name(folder_name)
        if ft and fc == "high":
            return ft, "high", f"Folder name matches '{ft}' pattern."
    if extension in VIDEO_EXTENSIONS:
        if re.search(r"[Ss]\d{1,2}[Ee]\d{1,3}", name):
            return "course", "medium", "Video filename looks episodic or lesson-like."
        if _year_from_text(name):
            return "movie", "medium", "Video filename includes a year."
        return "clip", "low", "Video file without strong pattern."
    if extension == ".exe":
        return "game", "low", "Executable, may be a game."
    if extension in {".bat", ".cmd", ".ps1", ".sh", ".py", ".rb", ".pl"}:
        return "software", "low", "Script or executable file."
    if extension in IMAGE_EXTENSIONS:
        if re.search(r"^\d{2,4}[.\-_]", name):
            return "comic", "medium", "Numbered image suggests comic."
        return "imgset", "low", "Image may belong to an image set."
    if extension in DOCUMENT_EXTENSIONS:
        return "docset", "low", "Document may belong to a document set."
    if extension in {".flac", ".mp3", ".ogg", ".wav", ".m4a", ".wma"}:
        return "audio", "low", "Audio file."
    return "unknown", "unknown", "No rule matched."


def _suggest_target_root(session, file=None, object_type=None):
    """Suggest target root_id. Priority: path-match > same-type-last > global-last > default > first."""
    from app.db.models.importing import InboxItem

    roots = session.query(LibraryRoot).filter(LibraryRoot.is_enabled == True).all()  # noqa: E712
    if not roots:
        return None
    if file and file.path:
        for root in roots:
            try:
                Path(file.path).resolve().relative_to(Path(root.root_path).resolve())
                return root.id
            except ValueError:
                continue
    if object_type:
        last = session.query(InboxItem).filter(
            InboxItem.final_object_type == object_type,
            InboxItem.target_library_root_id.isnot(None),
        ).order_by(InboxItem.updated_at.desc()).first()
        if last and last.target_library_root_id:
            return last.target_library_root_id
    last_any = session.query(InboxItem).filter(
        InboxItem.target_library_root_id.isnot(None),
    ).order_by(InboxItem.updated_at.desc()).first()
    if last_any and last_any.target_library_root_id:
        return last_any.target_library_root_id
    default = next((r for r in roots if r.is_default), None)
    if default:
        return default.id
    return roots[0].id


def _is_inbox_path(path: Path, source_root: Path) -> bool:
    try:
        relative = path.relative_to(source_root)
    except ValueError:
        return False
    return any(part.lower() in INBOX_NAMES for part in relative.parts[:-1])


def _asset_yaml_draft(candidate: OrganizeCandidate, primary_file: str | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "type": candidate.detected_type,
        "title": _safe_title(_strip_extension(candidate.display_name)),
        "filesystem_title": _safe_title(_strip_extension(candidate.display_name)),
        "aliases": [],
    }
    year = _year_from_text(candidate.display_name)
    if year:
        payload["year"] = year
    if primary_file:
        if candidate.detected_type in {"movie", "clip"}:
            payload["main_video"] = primary_file
        elif candidate.detected_type == "game":
            payload["launch_exe"] = primary_file
        else:
            payload["primary_file"] = primary_file
    return payload


def _confidence_score(value: str | None) -> float:
    return {"high": 0.8, "medium": 0.65, "low": 0.5}.get((value or "").lower(), 0.4)


def _suggestion_tags(candidate: OrganizeCandidate) -> list[str]:
    text = f"{candidate.display_name} {candidate.source_path}".lower()
    tags: list[str] = []
    keyword_map = {
        "1080p": "1080p",
        "2160p": "2160p",
        "hevc": "HEVC",
        "flac": "FLAC",
        "web-dl": "WEB-DL",
        "webdl": "WEB-DL",
        "bluray": "BluRay",
        "blu-ray": "BluRay",
        "windows": "Windows",
        "drmfree": "DRMFree",
        "drm-free": "DRMFree",
        "portable": "Portable",
    }
    if candidate.detected_type and candidate.detected_type not in {"unknown", "unknown_object"}:
        tags.append(candidate.detected_type)
    for needle, tag in keyword_map.items():
        if needle in text and tag not in tags:
            tags.append(tag)
    return tags
