from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session
import yaml

from app.db.models.file import File
from app.db.models.library_object import LibraryObject
from app.db.models.organize import OrganizeAction, OrganizeActionLog, OrganizeCandidate, OrganizePlan, OrganizeSuggestion
from app.db.session.session import SessionLocal
from app.repositories.library_organize.repository import CandidateFilters, LibraryOrganizeRepository, PlanFilters
from app.repositories.library_roots.repository import LibraryRootRepository
from app.repositories.source.repository import SourceRepository
from app.schemas.library_organize import (
    CandidateListResponse,
    CandidateScanResponse,
    CopyFailedActionsResponse,
    ExecutePlanResponse,
    FieldDiffItem,
    GenerateAssetYamlMergeResponse,
    GenerateRollbackResponse,
    GenerateSuggestionsResponse,
    RollbackBlockedActionItem,
    GeneratePlanResponse,
    OrganizeActionItem,
    OrganizeActionLogItem,
    OrganizeCandidateItem,
    OrganizePlanItem,
    OrganizeStatsResponse,
    OrganizeSuggestionItem,
    OrganizeSuggestionListResponse,
    PlanLogsResponse,
    PlanDetailResponse,
    PlanListResponse,
    PreflightResponse,
    ReconcileActionItem,
    ReconcilePlanResponse,
)
from app.services.library.object_parser import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, SUPPORTED_OBJECT_TYPES, VIDEO_EXTENSIONS


INBOX_NAMES = {"00_inbox", "_to_sort", "inbox"}
PLAN_TARGET_DIRS = {
    "movie": ("10_Movies_Anime", "Movies"),
    "anime": ("10_Movies_Anime", "Anime"),
    "game": ("20_Games",),
    "course": ("40_Videos", "Courses"),
    "imgset": ("30_Images", "Image_Sets"),
    "docset": ("80_Documents", "Docsets"),
    "clip": ("40_Videos", "Clips"),
}
OBJECT_PREFIX = {
    "movie": "MOVIE",
    "anime": "ANIME",
    "game": "GAME",
    "course": "COURSE",
    "imgset": "IMGSET",
    "docset": "DOCSET",
    "clip": "CLIP",
}
BUILTIN_TEMPLATES: list[dict] = [
    {
        "template_key": "movie_default",
        "object_type": "movie",
        "name": "Movie default",
        "description": "10_Movies_Anime/Movies/[MOVIE] {title} ({year})",
        "path_template": "10_Movies_Anime/Movies/[MOVIE] {title} ({year})",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "anime_default",
        "object_type": "anime",
        "name": "Anime default",
        "description": "10_Movies_Anime/Anime/[ANIME] {title} ({year}) [S{season}]",
        "path_template": "10_Movies_Anime/Anime/[ANIME] {title} ({year}) [S{season}]",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "game_default",
        "object_type": "game",
        "name": "Game default",
        "description": "20_Games/PC_Portable/[GAME] {title} ({year}) [Windows]",
        "path_template": "20_Games/PC_Portable/[GAME] {title} ({year}) [Windows]",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "course_default",
        "object_type": "course",
        "name": "Course default",
        "description": "40_Videos/Courses/[COURSE] {creator} - {title} ({year})",
        "path_template": "40_Videos/Courses/[COURSE] {creator} - {title} ({year})",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "imgset_default",
        "object_type": "imgset",
        "name": "Image set default",
        "description": "30_Images/Image_Sets/[IMGSET] {creator} - {title}",
        "path_template": "30_Images/Image_Sets/[IMGSET] {creator} - {title}",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "docset_default",
        "object_type": "docset",
        "name": "Document set default",
        "description": "80_Documents/Docsets/[DOCSET] {title} ({year})",
        "path_template": "80_Documents/Docsets/[DOCSET] {title} ({year})",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
    {
        "template_key": "fallback_object_default",
        "object_type": "clip",
        "name": "Fallback default",
        "description": "00_Inbox/_to_sort/[{type}] {title}",
        "path_template": "00_Inbox/_to_sort/[{type}] {title}",
        "filename_template": None,
        "is_builtin": True,
        "is_enabled": True,
    },
]
PATH_LENGTH_WARNING = 240
ORGANIZE_EXECUTION_LOCK = threading.BoundedSemaphore(1)


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
        template_key = _suggested_template_key(detected_type)
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


class LibraryOrganizeService:
    def __init__(
        self,
        repository: LibraryOrganizeRepository | None = None,
        source_repository: SourceRepository | None = None,
        library_root_repository: LibraryRootRepository | None = None,
    ) -> None:
        self.repository = repository or LibraryOrganizeRepository()
        self.source_repository = source_repository or SourceRepository()
        self.library_root_repository = library_root_repository or LibraryRootRepository()

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
            if source_root is None or not _is_path_within(Path(file.path), source_root):
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

    def get_templates(self) -> list[dict]:
        return [t for t in BUILTIN_TEMPLATES if t["is_enabled"]]

    def _get_template(self, template_key: str) -> dict | None:
        for t in BUILTIN_TEMPLATES:
            if t["template_key"] == template_key and t["is_enabled"]:
                return t
        return None

    def generate_plan(
        self,
        session: Session,
        candidate_ids: list[int],
        strategy: str | None = "default",
        target_library_root_id: int | None = None,
        template_key: str | None = None,
    ) -> GeneratePlanResponse:
        candidates = [self.repository.get_candidate(session, candidate_id) for candidate_id in candidate_ids]
        if any(candidate is None for candidate in candidates):
            raise HTTPException(status_code=404, detail="One or more organize candidates were not found.")
        valid_candidates = [candidate for candidate in candidates if candidate is not None]
        if not valid_candidates:
            raise HTTPException(status_code=400, detail="At least one candidate is required.")

        selected_template: dict | None = None
        if template_key:
            selected_template = self._get_template(template_key)
            if selected_template is None:
                raise HTTPException(status_code=400, detail=f"Unknown or disabled template key: {template_key}")
            for candidate in valid_candidates:
                if candidate.detected_type != selected_template["object_type"] and selected_template["object_type"] != "clip":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Template object_type '{selected_template['object_type']}' does not match candidate type '{candidate.detected_type}'.",
                    )

        base_root: Path | None = None
        resolved_root_id: int | None = None
        resolved_root_path: str | None = None

        if target_library_root_id is not None:
            lib_root = self.library_root_repository.get_by_id(session, target_library_root_id)
            if lib_root is None:
                raise HTTPException(status_code=404, detail="Library root not found.")
            if not lib_root.is_enabled:
                raise HTTPException(status_code=400, detail="Library root is disabled.")
            base_root = Path(lib_root.root_path).resolve()
            resolved_root_id = lib_root.id
            resolved_root_path = str(base_root)
        else:
            default_root = self.library_root_repository.get_default(session)
            if default_root is not None:
                base_root = Path(default_root.root_path).resolve()
                resolved_root_id = default_root.id
                resolved_root_path = str(base_root)
            else:
                all_enabled = self.library_root_repository.list_enabled(session)
                if len(all_enabled) > 1:
                    raise HTTPException(
                        status_code=400,
                        detail="Multiple library roots exist but no default is set. "
                        "Specify target_library_root_id or set a default root.",
                    )
                base_root = None
                resolved_root_id = None
                resolved_root_path = None

        now = _now()
        plan = OrganizePlan(
            title=self._plan_title(valid_candidates),
            status="draft",
            plan_kind="organize_inbox" if any(item.source_kind == "file" for item in valid_candidates) else "fix_object_review",
            summary="Draft organize plan. No filesystem operation has been executed.",
            summary_json=json.dumps({"strategy": strategy or "default", "candidate_ids": candidate_ids}, ensure_ascii=False),
            target_library_root_id=resolved_root_id,
            template_key=template_key,
            created_at=now,
            updated_at=now,
            confirmed_at=None,
            executed_at=None,
        )
        self.repository.add_plan(session, plan)
        for candidate in valid_candidates:
            self.repository.add_plan_candidate(session, plan.id, candidate.id)
            if candidate.status == "pending":
                candidate.status = "added_to_plan"
                candidate.updated_at = now

        actions = self._build_actions_for_plan(session, plan, valid_candidates, now, base_root, selected_template)
        self.repository.add_actions(session, actions)
        self._refresh_plan_conflicts(session, plan)
        session.commit()
        counts = self.repository.action_counts(session, [plan.id]).get(plan.id, {"total": 0, "blocked": 0, "warning": 0})
        return GeneratePlanResponse(
            plan_id=plan.id,
            status=plan.status,
            actions_count=counts["total"],
            blocked_count=counts["blocked"],
            warning_count=counts["warning"],
            target_library_root_id=resolved_root_id,
            target_root_path=resolved_root_path,
        )

    def list_plans(
        self,
        session: Session,
        *,
        page: int,
        page_size: int,
        status: str | None,
        plan_kind: str | None,
        query: str | None,
    ) -> PlanListResponse:
        plans, total = self.repository.list_plans(
            session, PlanFilters(page=page, page_size=page_size, status=status, plan_kind=plan_kind, query=query)
        )
        counts = self.repository.action_counts(session, [plan.id for plan in plans])
        return PlanListResponse(
            items=[self._plan_item(plan, counts.get(plan.id, {}), session) for plan in plans],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_plan_detail(self, session: Session, plan_id: int) -> PlanDetailResponse:
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        if plan.status in {"draft", "ready"}:
            self._refresh_plan_conflicts(session, plan)
            session.commit()
        actions = self.repository.list_plan_actions(session, plan.id)
        candidates = self.repository.list_plan_candidates(session, plan.id)
        counts = self.repository.action_counts(session, [plan.id]).get(plan.id, {})
        return PlanDetailResponse(
            plan=self._plan_item(plan, counts, session),
            candidates=[self._candidate_item(candidate) for candidate in candidates],
            actions=[self._action_item(action) for action in actions],
        )

    def preflight_plan(self, session: Session, plan_id: int) -> PreflightResponse:
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        if plan.status != "ready":
            raise HTTPException(status_code=400, detail="Only ready plans can be preflighted.")
        self._log_event(session, plan.id, None, "preflight_started", "Preflight started.")
        actions = self._run_preflight(session, plan)
        blocked_count = sum(1 for action in actions if action.status != "cancelled" and action.conflict_status in {"blocked", "stale"})
        warning_count = sum(1 for action in actions if action.status != "cancelled" and action.conflict_status == "warning")
        messages = [action.conflict_message for action in actions if action.conflict_message]
        event = "preflight_ok" if blocked_count == 0 else "preflight_failed"
        message = "Preflight passed." if blocked_count == 0 else "Preflight found blocked actions."
        self._log_event(session, plan.id, None, event, message)
        session.commit()
        return PreflightResponse(
            plan_id=plan.id,
            can_execute=blocked_count == 0,
            blocked_count=blocked_count,
            warning_count=warning_count,
            actions=[self._action_item(action) for action in actions],
            messages=messages,
        )

    def execute_plan(self, session: Session, plan_id: int, *, confirm: bool) -> ExecutePlanResponse:
        if not confirm:
            raise HTTPException(status_code=400, detail="Execution requires explicit confirmation.")
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        if plan.status != "ready":
            raise HTTPException(status_code=400, detail="Only ready plans can be executed.")

        preflight = self.preflight_plan(session, plan_id)
        if not preflight.can_execute:
            raise HTTPException(status_code=400, detail="Preflight failed. Resolve blocked actions before execution.")
        if not ORGANIZE_EXECUTION_LOCK.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="Another organize plan is already executing.")

        now = _now()
        plan.status = "executing"
        plan.execution_started_at = now
        plan.execution_finished_at = None
        plan.execution_summary_json = None
        plan.updated_at = now
        for action in self.repository.list_plan_actions(session, plan.id):
            if action.status == "ready":
                action.error_message = None
                action.before_path = None
                action.after_path = None
                action.executed_at = None
                action.finished_at = None
                action.updated_at = now
        self._log_event(session, plan.id, None, "execution_started", "Execution worker scheduled.")
        session.commit()

        try:
            thread = threading.Thread(
                target=self._execute_plan_worker,
                args=(plan.id,),
                daemon=True,
                name=f"library-organize-plan-{plan.id}",
            )
            thread.start()
        except Exception:
            ORGANIZE_EXECUTION_LOCK.release()
            raise
        return ExecutePlanResponse(plan_id=plan.id, status="executing")

    def list_plan_logs(self, session: Session, plan_id: int) -> PlanLogsResponse:
        if self.repository.get_plan(session, plan_id) is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        logs = self.repository.list_plan_logs(session, plan_id)
        return PlanLogsResponse(items=[self._log_item(log) for log in logs])

    def update_plan(self, session: Session, plan_id: int, *, title: str | None, summary: str | None) -> PlanDetailResponse:
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        if plan.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft plans can be edited.")
        if title is not None and title.strip():
            plan.title = title.strip()
        if summary is not None:
            plan.summary = summary.strip() or None
        plan.updated_at = _now()
        session.commit()
        return self.get_plan_detail(session, plan_id)

    def update_action(
        self,
        session: Session,
        action_id: int,
        *,
        target_path: str | None,
        payload_json: str | None,
        status: str | None,
        reason: str | None,
    ) -> PlanDetailResponse:
        action = self.repository.get_action(session, action_id)
        if action is None:
            raise HTTPException(status_code=404, detail="Organize action not found.")
        plan = self.repository.get_plan(session, action.plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        if plan.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft plan actions can be edited.")
        if target_path is not None:
            action.target_path = target_path.strip() or None
        if payload_json is not None:
            action.payload_json = payload_json
        if status is not None:
            action.status = status
        if reason is not None:
            action.reason = reason.strip() or None
        action.updated_at = _now()
        plan.updated_at = action.updated_at
        self._refresh_action_conflict(session, action, plan)
        session.commit()
        return self.get_plan_detail(session, plan.id)

    def mark_ready(self, session: Session, plan_id: int) -> PlanDetailResponse:
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        if plan.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft plans can be marked ready.")
        self._refresh_plan_conflicts(session, plan)
        actions = self.repository.list_plan_actions(session, plan.id)
        blocked = [action for action in actions if action.status != "cancelled" and action.conflict_status in {"blocked", "stale"}]
        if blocked:
            session.commit()
            raise HTTPException(status_code=400, detail="Blocked or stale actions must be resolved before marking ready.")
        now = _now()
        plan.status = "ready"
        plan.confirmed_at = now
        plan.updated_at = now
        for action in actions:
            if action.status != "cancelled":
                action.status = "ready"
                action.updated_at = now
        session.commit()
        return self.get_plan_detail(session, plan.id)

    def cancel_plan(self, session: Session, plan_id: int) -> PlanDetailResponse:
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        if plan.status not in {"draft", "ready"}:
            raise HTTPException(status_code=400, detail="Only draft or ready plans can be cancelled.")
        plan.status = "cancelled"
        plan.updated_at = _now()
        session.commit()
        return self.get_plan_detail(session, plan.id)

    def organize_stats(self, session: Session) -> OrganizeStatsResponse:
        return OrganizeStatsResponse(**self.repository.organize_stats(session))

    def mark_stale_executing_plans_failed(self, session: Session) -> int:
        count = self.repository.mark_stale_executing_plans_failed(session, now=_now())
        session.commit()
        return count

    def _execute_plan_worker(self, plan_id: int) -> None:
        try:
            with SessionLocal() as session:
                plan = self.repository.get_plan(session, plan_id)
                if plan is None:
                    return
                self._log_event(session, plan.id, None, "execution_started", "Execution started.")
                session.commit()

                failed = 0
                skipped = 0
                succeeded = 0
                stop_after_failure = False
                for action in self.repository.list_plan_actions(session, plan.id):
                    if action.status == "cancelled":
                        action.status = "skipped"
                        action.error_message = "Action was cancelled before execution."
                        action.finished_at = _now()
                        action.updated_at = action.finished_at
                        skipped += 1
                        self._log_event(session, plan.id, action.id, "action_skipped", action.error_message)
                        session.commit()
                        continue
                    if action.status != "ready":
                        continue
                    if stop_after_failure:
                        action.status = "skipped"
                        action.error_message = "Skipped after a previous action failed."
                        action.finished_at = _now()
                        action.updated_at = action.finished_at
                        skipped += 1
                        self._log_event(session, plan.id, action.id, "action_skipped", action.error_message)
                        session.commit()
                        continue

                    action.status = "executing"
                    action.executed_at = _now()
                    action.updated_at = action.executed_at
                    self._log_event(session, plan.id, action.id, "action_started", f"Executing {action.action_type}.", path_before=action.source_path, path_after=action.target_path)
                    session.commit()
                    try:
                        before_path, after_path = self._execute_action(session, action)
                        action.status = "succeeded"
                        action.before_path = before_path
                        action.after_path = after_path
                        action.error_message = None
                        action.finished_at = _now()
                        action.updated_at = action.finished_at
                        succeeded += 1
                        self._log_event(
                            session,
                            plan.id,
                            action.id,
                            "action_succeeded",
                            f"{action.action_type} succeeded.",
                            path_before=before_path,
                            path_after=after_path,
                        )
                        session.commit()
                    except Exception as error:
                        message = str(error)
                        action.status = "failed"
                        action.error_message = message
                        action.finished_at = _now()
                        action.updated_at = action.finished_at
                        failed += 1
                        stop_after_failure = True
                        self._log_event(
                            session,
                            plan.id,
                            action.id,
                            "action_failed",
                            f"{action.action_type} failed.",
                            path_before=action.source_path,
                            path_after=action.target_path,
                            error_message=message,
                        )
                        session.commit()

                plan = self.repository.get_plan(session, plan_id)
                if plan is None:
                    return
                now = _now()
                plan.execution_finished_at = now
                plan.executed_at = now
                plan.status = "completed" if failed == 0 and skipped == 0 else "completed_with_errors"

                affected_source_ids: list[int] = []
                affected_library_root_ids: list[int] = []
                for action in self.repository.list_plan_actions(session, plan.id):
                    if action.source_path:
                        try:
                            src_root = self._source_root_for_path(session, Path(action.source_path))
                            source = self.source_repository.get_by_path(session, str(src_root))
                            if source and source.id not in affected_source_ids:
                                affected_source_ids.append(source.id)
                        except HTTPException:
                            pass
                    if action.target_path:
                        try:
                            target_root = self._resolve_root_for_mkdir_or_asset(session, Path(action.target_path), plan)
                            if target_root:
                                lib_root = self.library_root_repository.get_by_path(session, str(target_root))
                                if lib_root and lib_root.id not in affected_library_root_ids:
                                    affected_library_root_ids.append(lib_root.id)
                        except HTTPException:
                            pass

                plan.execution_summary_json = json.dumps(
                    {
                        "succeeded": succeeded,
                        "failed": failed,
                        "skipped": skipped,
                        "affected_source_ids": affected_source_ids,
                        "affected_library_root_ids": affected_library_root_ids,
                    },
                    ensure_ascii=False,
                )
                plan.updated_at = now
                event = "execution_completed" if plan.status == "completed" else "execution_completed_with_errors"
                self._log_event(session, plan.id, None, event, f"Execution finished with {succeeded} succeeded, {failed} failed, {skipped} skipped.")
                session.commit()
        except Exception as error:
            with SessionLocal() as session:
                plan = self.repository.get_plan(session, plan_id)
                if plan is not None:
                    now = _now()
                    plan.status = "failed"
                    plan.execution_finished_at = now
                    plan.executed_at = now
                    plan.execution_summary_json = json.dumps({"error": str(error)}, ensure_ascii=False)
                    plan.updated_at = now
                    self._log_event(session, plan.id, None, "execution_failed", "Execution failed before completion.", error_message=str(error))
                    session.commit()
        finally:
            ORGANIZE_EXECUTION_LOCK.release()

    def _run_preflight(self, session: Session, plan: OrganizePlan) -> list[OrganizeAction]:
        actions = self.repository.list_plan_actions(session, plan.id)
        planned_dirs: set[str] = set()
        for action in actions:
            conflict_status, conflict_message = self._preflight_action(session, action, planned_dirs)
            action.conflict_status = conflict_status
            action.conflict_message = conflict_message
            action.updated_at = _now()
            if action.action_type == "mkdir" and action.target_path and conflict_status in {"ok", "warning"}:
                planned_dirs.add(_path_key(Path(action.target_path)))
        plan.updated_at = _now()
        return actions

    def _preflight_action(self, session: Session, action: OrganizeAction, planned_dirs: set[str]) -> tuple[str, str | None]:
        if action.status == "cancelled":
            return "ok", "Action is cancelled."
        if action.action_type == "update_metadata":
            return "blocked", "update_metadata is draft-only and cannot be executed in Phase 4."
        if action.action_type not in {"mkdir", "move", "rename", "write_asset_yaml", "backup_asset_yaml", "write_asset_yaml_update"}:
            return "blocked", f"Unsupported action type: {action.action_type}."

        plan = self.repository.get_plan(session, action.plan_id)

        if action.action_type == "mkdir":
            target = self._required_target(action)
            target_root = self._resolve_root_for_mkdir_or_asset(session, target, plan)
            if target_root is None:
                return "blocked", "Target directory is outside any enabled source or managed library root."
            if target.exists() and not target.is_dir():
                return "blocked", "Target path exists and is not a directory."
            if target.exists():
                return "warning", "Target directory already exists."
            if len(str(target)) >= PATH_LENGTH_WARNING:
                return "warning", "Target path is close to the Windows path length risk threshold."
            return "ok", None

        if action.action_type in {"move", "rename"}:
            source = self._required_source(action)
            target = self._required_target(action)
            if not source.exists():
                return "stale", "Source path no longer exists."

            source_root = self._source_root_for_path(session, source)

            if plan is not None and plan.target_library_root_id is not None:
                lib_root = self.library_root_repository.get_by_id(session, plan.target_library_root_id)
                if lib_root is None or not lib_root.is_enabled:
                    return "blocked", "Target library root is missing or disabled."
                target_root = Path(lib_root.root_path).resolve()
                if not _is_path_within(target, target_root):
                    return "blocked", "Target path is outside the selected managed library root."
            else:
                target_root = self._source_root_for_path(session, target)
                if _path_key(source_root) != _path_key(target_root):
                    return "blocked", "Source and target must stay inside the same enabled source."
                if not _is_path_within(target, target_root):
                    return "blocked", "Target path is outside the enabled source."

            if action.action_type == "rename" and _path_key(source.parent) != _path_key(target.parent):
                return "blocked", "Rename target must stay in the same folder."
            if target.exists():
                return "blocked", "Target path already exists and would be overwritten."
            if not self._parent_available(target, planned_dirs):
                return "blocked", "Target parent directory does not exist."
            if len(str(target)) >= PATH_LENGTH_WARNING:
                return "warning", "Target path is close to the Windows path length risk threshold."
            return "ok", None

        if action.action_type == "backup_asset_yaml":
            source = self._required_source(action)
            target = self._required_target(action)
            if not source.exists():
                return "stale", "Source asset.yaml no longer exists."
            target_root = self._resolve_root_for_mkdir_or_asset(session, target, plan)
            if target_root is None:
                return "blocked", "Backup target is outside any enabled source or managed library root."
            if target.exists():
                return "blocked", "Backup target path already exists."
            if not target.parent.exists():
                return "blocked", "Backup target parent directory does not exist."
            if source.parent.resolve() != target.parent.resolve():
                return "blocked", "Backup must be in the same directory as asset.yaml."
            if len(str(target)) >= PATH_LENGTH_WARNING:
                return "warning", "Backup target path is close to the Windows path length risk threshold."
            return "ok", None

        if action.action_type == "write_asset_yaml_update":
            source = self._required_source(action)
            target = self._required_target(action)
            if not source.exists():
                return "stale", "Source asset.yaml no longer exists."
            if not target.exists():
                return "stale", "Target asset.yaml no longer exists."
            target_root = self._resolve_root_for_mkdir_or_asset(session, target, plan)
            if target_root is None:
                return "blocked", "asset.yaml target is outside any enabled source or managed library root."
            if target.name.lower() != "asset.yaml":
                return "blocked", "write_asset_yaml_update can only update asset.yaml."
            if not action.payload_json:
                return "blocked", "asset.yaml update payload is missing."
            try:
                payload = json.loads(action.payload_json)
            except json.JSONDecodeError:
                return "blocked", "asset.yaml update payload is not valid JSON."
            if not payload.get("merged_yaml"):
                return "blocked", "asset.yaml update payload is missing merged_yaml."
            plan = self.repository.get_plan(session, action.plan_id)
            if plan is None:
                return "blocked", "Plan not found."
            all_actions = self.repository.list_plan_actions(session, action.plan_id)
            backup_actions = [a for a in all_actions if a.action_type == "backup_asset_yaml" and a.action_order < action.action_order]
            if not backup_actions:
                return "blocked", "write_asset_yaml_update requires a preceding backup_asset_yaml action in the same plan."
            if len(str(target)) >= PATH_LENGTH_WARNING:
                return "warning", "Target path is close to the Windows path length risk threshold."
            return "ok", None

        if action.action_type == "write_asset_yaml":
            target = self._required_target(action)
            target_root = self._resolve_root_for_mkdir_or_asset(session, target, plan)
            if target_root is None:
                return "blocked", "asset.yaml target is outside any enabled source or managed library root."
            if target.name.lower() != "asset.yaml":
                return "blocked", "write_asset_yaml can only create asset.yaml."
            if target.exists():
                return "blocked", "asset.yaml already exists and will not be overwritten."
            if not self._parent_available(target, planned_dirs):
                return "blocked", "asset.yaml parent directory does not exist."
            if not action.payload_json:
                return "blocked", "asset.yaml draft payload is missing."
            if len(str(target)) >= PATH_LENGTH_WARNING:
                return "warning", "Target path is close to the Windows path length risk threshold."
            return "ok", None

    def _execute_action(self, session: Session, action: OrganizeAction) -> tuple[str | None, str | None]:
        conflict_status, conflict_message = self._preflight_action(session, action, set())
        if conflict_status in {"blocked", "stale"}:
            raise RuntimeError(conflict_message or "Action failed pre-execution safety check.")
        if action.action_type == "mkdir":
            target = self._required_target(action)
            if target.exists() and target.is_dir():
                return None, str(target)
            target.mkdir(parents=True, exist_ok=False)
            return None, str(target)
        if action.action_type in {"move", "rename"}:
            source = self._required_source(action)
            target = self._required_target(action)
            if target.exists():
                raise RuntimeError("Target path already exists and would be overwritten.")
            shutil.move(str(source), str(target))
            if source.exists() or not target.exists():
                raise RuntimeError("Filesystem move did not finish in the expected state.")
            return str(source), str(target)
        if action.action_type == "write_asset_yaml":
            target = self._required_target(action)
            if target.exists():
                raise RuntimeError("asset.yaml already exists and will not be overwritten.")
            payload = self._render_asset_yaml(action.payload_json)
            tmp_path = target.with_name(f"{target.name}.tmp-{uuid.uuid4().hex}")
            try:
                tmp_path.write_text(payload, encoding="utf-8")
                if target.exists():
                    raise RuntimeError("asset.yaml appeared before final write; refusing to overwrite.")
                os.replace(tmp_path, target)
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
            return None, str(target)
        if action.action_type == "backup_asset_yaml":
            source = self._required_source(action)
            target = self._required_target(action)
            if target.exists():
                raise RuntimeError("Backup target path already exists.")
            shutil.copy2(str(source), str(target))
            return str(source), str(target)
        if action.action_type == "write_asset_yaml_update":
            source = self._required_source(action)
            target = self._required_target(action)
            if not source.exists():
                raise RuntimeError("Source asset.yaml no longer exists.")
            if not target.exists():
                raise RuntimeError("Target asset.yaml no longer exists.")
            payload = json.loads(action.payload_json or "{}")
            merged_yaml = payload.get("merged_yaml")
            if not merged_yaml:
                raise RuntimeError("merged_yaml is missing from payload.")
            plan = self.repository.get_plan(session, action.plan_id)
            if plan is None:
                raise RuntimeError("Plan not found.")
            all_actions = self.repository.list_plan_actions(session, action.plan_id)
            backup_actions = [a for a in all_actions if a.action_type == "backup_asset_yaml" and a.action_order < action.action_order]
            if not backup_actions:
                raise RuntimeError("No preceding backup_asset_yaml action found.")
            backup_succeeded = any(a.status == "succeeded" for a in backup_actions)
            if not backup_succeeded:
                raise RuntimeError("Preceding backup_asset_yaml action has not succeeded.")
            rendered = yaml.safe_dump(merged_yaml, allow_unicode=True, sort_keys=False)
            tmp_path = target.with_name(f"{target.name}.tmp-{uuid.uuid4().hex}")
            try:
                tmp_path.write_text(rendered, encoding="utf-8")
                os.replace(tmp_path, target)
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
            return str(source), str(target)
        raise RuntimeError(f"Unsupported action type: {action.action_type}.")

    def _required_source(self, action: OrganizeAction) -> Path:
        if not action.source_path:
            raise RuntimeError("Action source_path is required.")
        return Path(action.source_path).resolve()

    def _required_target(self, action: OrganizeAction) -> Path:
        if not action.target_path:
            raise RuntimeError("Action target_path is required.")
        return Path(action.target_path).resolve()

    def _parent_available(self, target: Path, planned_dirs: set[str]) -> bool:
        return target.parent.exists() or _path_key(target.parent) in planned_dirs

    def _render_asset_yaml(self, payload_json: str | None) -> str:
        if not payload_json:
            raise RuntimeError("asset.yaml draft payload is missing.")
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError as error:
            raise RuntimeError("asset.yaml draft payload is not valid JSON.") from error
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

    def _log_event(
        self,
        session: Session,
        plan_id: int,
        action_id: int | None,
        event_type: str,
        message: str,
        *,
        path_before: str | None = None,
        path_after: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self.repository.add_log(
            session,
            OrganizeActionLog(
                plan_id=plan_id,
                action_id=action_id,
                event_type=event_type,
                message=message,
                path_before=path_before,
                path_after=path_after,
                error_message=error_message,
                created_at=_now(),
            ),
        )

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

    def _build_actions_for_plan(
        self, session: Session, plan: OrganizePlan, candidates: list[OrganizeCandidate], now: datetime,
        base_root: Path | None = None,
        template: dict | None = None,
    ) -> list[OrganizeAction]:
        actions: list[OrganizeAction] = []
        order = 1
        for candidate in candidates:
            if candidate.source_kind == "file":
                source_root = self._source_root_for_path(session, Path(candidate.source_path))
                target_dir = self._target_dir(base_root, source_root, candidate, template)
                target_file = target_dir / self._target_filename(candidate)
                actions.append(self._make_action(plan.id, order, "mkdir", None, str(target_dir), None, "Create target object directory preview.", now))
                order += 1
                actions.append(
                    self._make_action(
                        plan.id,
                        order,
                        "move",
                        candidate.source_path,
                        str(target_file),
                        None,
                        "Move file into proposed object directory preview.",
                        now,
                    )
                )
                order += 1
                actions.append(
                    self._make_action(
                        plan.id,
                        order,
                        "write_asset_yaml",
                        None,
                        str(target_dir / "asset.yaml"),
                        json.dumps(_asset_yaml_draft(candidate, target_file.name), ensure_ascii=False, indent=2),
                        "Draft portable metadata only; no file is written in Phase 3.",
                        now,
                    )
                )
                order += 1
            else:
                target = Path(candidate.source_path) / "asset.yaml"
                payload = json.dumps(_asset_yaml_draft(candidate, None), ensure_ascii=False, indent=2)
                actions.append(
                    self._make_action(
                        plan.id,
                        order,
                        "write_asset_yaml" if candidate.candidate_type != "invalid_asset_yaml" else "update_metadata",
                        candidate.source_path,
                        str(target),
                        payload,
                        "Draft object metadata repair. Real asset.yaml writes are Phase 4.",
                        now,
                    )
                )
                order += 1
        return actions

    def _target_dir(self, base_root: Path | None, source_root: Path, candidate: OrganizeCandidate, template: dict | None = None) -> Path:
        root = base_root if base_root is not None else source_root
        if template is not None:
            relative = render_organize_template(template, candidate)
            return root.joinpath(relative)
        detected_type = candidate.detected_type if candidate.detected_type in PLAN_TARGET_DIRS else "clip"
        prefix = OBJECT_PREFIX.get(detected_type, "CLIP")
        title = _safe_title(_strip_extension(candidate.display_name))
        year = _year_from_text(candidate.display_name)
        suffix = f" ({year})" if year else ""
        folder_name = f"[{prefix}] {title}{suffix}"
        return root.joinpath(*PLAN_TARGET_DIRS[detected_type], folder_name)

    def _target_filename(self, candidate: OrganizeCandidate) -> str:
        source = Path(candidate.source_path)
        title = _safe_title(_strip_extension(candidate.display_name))
        year = _year_from_text(candidate.display_name)
        stem = f"{title} ({year})" if year else title
        return f"{stem}{source.suffix.lower()}"

    def _source_root_for_path(self, session: Session, path: Path) -> Path:
        enabled_sources = [source for source in self.source_repository.list_sources(session) if source.is_enabled]
        for source in enabled_sources:
            source_root = Path(source.path).resolve()
            if _is_path_within(path, source_root):
                return source_root
        raise HTTPException(status_code=400, detail="Candidate source path is outside enabled sources.")

    def _resolve_root_for_mkdir_or_asset(self, session: Session, path: Path, plan: OrganizePlan | None) -> Path | None:
        if plan is not None and plan.target_library_root_id is not None:
            lib_root = self.library_root_repository.get_by_id(session, plan.target_library_root_id)
            if lib_root and lib_root.is_enabled:
                root_path = Path(lib_root.root_path).resolve()
                if _is_path_within(path, root_path):
                    return root_path
            return None
        for source in self.source_repository.list_sources(session):
            if source.is_enabled:
                source_root = Path(source.path).resolve()
                if _is_path_within(path, source_root):
                    return source_root
        return None

    def _make_action(
        self,
        plan_id: int,
        order: int,
        action_type: str,
        source_path: str | None,
        target_path: str | None,
        payload_json: str | None,
        reason: str,
        now: datetime,
    ) -> OrganizeAction:
        return OrganizeAction(
            plan_id=plan_id,
            action_order=order,
            action_type=action_type,
            source_path=source_path,
            target_path=target_path,
            payload_json=payload_json,
            status="draft",
            conflict_status="unchecked",
            conflict_message=None,
            reason=reason,
            created_at=now,
            updated_at=now,
        )

    def _refresh_plan_conflicts(self, session: Session, plan: OrganizePlan) -> None:
        for action in self.repository.list_plan_actions(session, plan.id):
            self._refresh_action_conflict(session, action, plan)
        plan.updated_at = _now()

    def _refresh_action_conflict(self, session: Session, action: OrganizeAction, plan: OrganizePlan | None = None) -> None:
        if action.status == "cancelled":
            action.conflict_status = "ok"
            action.conflict_message = "Action is cancelled."
            return
        if action.source_path:
            source = Path(action.source_path)
            if not source.exists():
                action.conflict_status = "stale"
                action.conflict_message = "Source path no longer exists."
                return
        if action.target_path:
            target = Path(action.target_path)
            target_root = self._resolve_root_for_mkdir_or_asset(session, target, plan)
            if target_root is None:
                action.conflict_status = "blocked"
                action.conflict_message = "Target path is outside any enabled source or managed library root."
                return
            if not _is_path_within(target, target_root):
                action.conflict_status = "blocked"
                action.conflict_message = "Target path is outside the enabled source."
                return
            if len(str(target)) >= PATH_LENGTH_WARNING:
                action.conflict_status = "warning"
                action.conflict_message = "Target path is close to the Windows path length risk threshold."
                return
            if action.action_type == "mkdir":
                action.conflict_status = "warning" if target.exists() else "ok"
                action.conflict_message = "Target directory already exists." if target.exists() else None
                return
            if action.action_type == "backup_asset_yaml":
                if target.exists():
                    action.conflict_status = "blocked"
                    action.conflict_message = "Backup target path already exists."
                else:
                    action.conflict_status = "ok"
                    action.conflict_message = None
                return
            if action.action_type == "write_asset_yaml_update":
                if not target.exists():
                    action.conflict_status = "stale"
                    action.conflict_message = "Target asset.yaml no longer exists."
                elif action.source_path and not Path(action.source_path).exists():
                    action.conflict_status = "stale"
                    action.conflict_message = "Source asset.yaml no longer exists."
                else:
                    action.conflict_status = "ok"
                    action.conflict_message = None
                return
            if action.action_type in {"move", "rename"} and target.exists():
                action.conflict_status = "blocked"
                action.conflict_message = "Target path already exists and would be overwritten."
                return
            if action.action_type in {"write_asset_yaml", "update_metadata"} and target.exists():
                action.conflict_status = "warning"
                action.conflict_message = "Target metadata file exists; this remains a draft preview only."
                return
        action.conflict_status = "ok"
        action.conflict_message = None

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

    def _plan_item(self, plan: OrganizePlan, counts: dict[str, int], session: Session | None = None) -> OrganizePlanItem:
        target_root_path: str | None = None
        if plan.target_library_root_id is not None and session is not None:
            lib_root = self.library_root_repository.get_by_id(session, plan.target_library_root_id)
            if lib_root is not None:
                target_root_path = lib_root.root_path

        return OrganizePlanItem(
            id=plan.id,
            title=plan.title,
            status=plan.status,
            plan_kind=plan.plan_kind,
            summary=plan.summary,
            summary_json=plan.summary_json,
            target_library_root_id=plan.target_library_root_id,
            target_root_path=target_root_path,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            confirmed_at=plan.confirmed_at,
            executed_at=plan.executed_at,
            execution_started_at=plan.execution_started_at,
            execution_finished_at=plan.execution_finished_at,
            execution_summary_json=plan.execution_summary_json,
            actions_count=counts.get("total", 0),
            blocked_count=counts.get("blocked", 0),
            warning_count=counts.get("warning", 0),
            failed_count=counts.get("failed", 0),
            skipped_count=counts.get("skipped", 0),
            reconcile_status=plan.reconcile_status,
            reconciled_at=plan.reconciled_at,
            reconcile_summary_json=plan.reconcile_summary_json,
            parent_plan_id=plan.parent_plan_id,
            plan_origin=plan.plan_origin,
            template_key=plan.template_key,
        )

    def _action_item(self, action: OrganizeAction) -> OrganizeActionItem:
        return OrganizeActionItem(
            id=action.id,
            plan_id=action.plan_id,
            action_order=action.action_order,
            action_type=action.action_type,
            source_path=action.source_path,
            target_path=action.target_path,
            payload_json=action.payload_json,
            status=action.status,
            conflict_status=action.conflict_status,
            conflict_message=action.conflict_message,
            reason=action.reason,
            before_path=action.before_path,
            after_path=action.after_path,
            executed_at=action.executed_at,
            finished_at=action.finished_at,
            error_message=action.error_message,
            reconcile_status=action.reconcile_status,
            created_at=action.created_at,
            updated_at=action.updated_at,
        )

    def _log_item(self, log: OrganizeActionLog) -> OrganizeActionLogItem:
        return OrganizeActionLogItem(
            id=log.id,
            plan_id=log.plan_id,
            action_id=log.action_id,
            event_type=log.event_type,
            message=log.message,
            path_before=log.path_before,
            path_after=log.path_after,
            error_message=log.error_message,
            created_at=log.created_at,
        )

    def _plan_title(self, candidates: list[OrganizeCandidate]) -> str:
        if len(candidates) == 1:
            return f"Organize {candidates[0].display_name}"
        return f"Organize {len(candidates)} candidates"

    def copy_failed_actions_to_new_plan(self, session: Session, plan_id: int) -> CopyFailedActionsResponse:
        plan = session.get(OrganizePlan, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Plan not found.")
        if plan.status not in ("completed", "completed_with_errors", "failed"):
            raise HTTPException(
                status_code=400,
                detail=f"Only completed, completed_with_errors, or failed plans can copy actions. Current status: {plan.status}",
            )

        actions = self.repository.list_plan_actions(session, plan_id)
        copy_statuses = {"failed", "blocked", "skipped"}
        to_copy = [a for a in actions if a.status in copy_statuses]
        skipped_count = len(actions) - len(to_copy)

        if not to_copy:
            raise HTTPException(
                status_code=400,
                detail="No failed, blocked, or skipped actions to copy.",
            )

        now = _now()
        new_plan = OrganizePlan(
            title=f"Retry failed actions from plan #{plan.id}",
            status="draft",
            plan_kind=plan.plan_kind,
            target_library_root_id=plan.target_library_root_id,
            parent_plan_id=plan.id,
            plan_origin="copied_failed_actions",
            reconcile_status="not_required",
            created_at=now,
            updated_at=now,
        )
        session.add(new_plan)
        session.flush()

        for idx, action in enumerate(to_copy, start=1):
            new_action = OrganizeAction(
                plan_id=new_plan.id,
                action_order=idx,
                action_type=action.action_type,
                source_path=action.source_path,
                target_path=action.target_path,
                payload_json=action.payload_json,
                reason=action.reason,
                status="draft",
                conflict_status="unchecked",
                reconcile_status="not_checked",
                created_at=now,
                updated_at=now,
            )
            session.add(new_action)

        session.flush()
        self._refresh_plan_conflicts(session, new_plan)
        session.commit()

        return CopyFailedActionsResponse(
            source_plan_id=plan.id,
            new_plan_id=new_plan.id,
            copied_actions_count=len(to_copy),
            skipped_actions_count=skipped_count,
            plan_origin="copied_failed_actions",
        )

    def generate_rollback_plan(self, session: Session, plan_id: int) -> GenerateRollbackResponse:
        plan = session.get(OrganizePlan, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Plan not found.")
        if plan.status not in ("completed", "completed_with_errors", "failed"):
            raise HTTPException(
                status_code=400,
                detail=f"Only completed, completed_with_errors, or failed plans can generate rollback. Current status: {plan.status}",
            )

        actions = self.repository.list_plan_actions(session, plan_id)
        rollbackable = [
            a for a in actions
            if a.action_type in ("move", "rename") and a.status == "succeeded"
        ]

        blocked: list[RollbackBlockedActionItem] = []
        rollback_actions: list[OrganizeAction] = []
        now = _now()

        for action in rollbackable:
            reason = self._check_rollback_preconditions(action)
            if reason is not None:
                blocked.append(RollbackBlockedActionItem(source_action_id=action.id, reason=reason))
                continue
            rollback_actions.append(OrganizeAction(
                plan_id=0,  # placeholder, set after new_plan flush
                action_order=0,  # placeholder, re-indexed below
                action_type=action.action_type,
                source_path=action.target_path,
                target_path=action.source_path,
                payload_json=None,
                reason=f"Rollback of action #{action.id}",
                status="draft",
                conflict_status="unchecked",
                reconcile_status="not_checked",
                created_at=now,
                updated_at=now,
            ))

        if not rollback_actions:
            raise HTTPException(
                status_code=400,
                detail="No rollbackable actions found.",
            )

        new_plan = OrganizePlan(
            title=f"Rollback plan #{plan.id}",
            status="draft",
            plan_kind=plan.plan_kind,
            target_library_root_id=None,
            parent_plan_id=plan.id,
            plan_origin="rollback",
            reconcile_status="not_required",
            created_at=now,
            updated_at=now,
        )
        session.add(new_plan)
        session.flush()

        for idx, action in enumerate(rollback_actions, start=1):
            action.plan_id = new_plan.id
            action.action_order = idx
            session.add(action)

        session.flush()
        self._refresh_plan_conflicts(session, new_plan)
        session.commit()

        return GenerateRollbackResponse(
            source_plan_id=plan.id,
            rollback_plan_id=new_plan.id,
            rollback_actions_count=len(rollback_actions),
            blocked_actions_count=len(blocked),
            plan_origin="rollback",
            blocked_actions=blocked,
        )

    def generate_asset_yaml_merge_draft(self, session: Session, action_id: int) -> GenerateAssetYamlMergeResponse:
        action = session.get(OrganizeAction, action_id)
        if action is None:
            raise HTTPException(status_code=404, detail="Action not found.")
        if action.action_type != "write_asset_yaml":
            raise HTTPException(
                status_code=400,
                detail=f"Only write_asset_yaml actions can generate merge drafts. Current type: {action.action_type}",
            )
        if not action.target_path or not action.payload_json:
            raise HTTPException(status_code=400, detail="Action must have target_path and payload_json.")

        target = Path(action.target_path).resolve()
        if target.name.lower() != "asset.yaml":
            raise HTTPException(status_code=400, detail="Target is not an asset.yaml.")
        if not target.exists():
            raise HTTPException(
                status_code=400,
                detail="asset.yaml does not exist; use write_asset_yaml to create a new one.",
            )

        try:
            current_yaml = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as error:
            raise HTTPException(status_code=400, detail="Cannot parse current asset.yaml.") from error

        try:
            proposed_yaml = json.loads(action.payload_json)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=400, detail="Action payload_json is not valid JSON.") from error

        source_plan = session.get(OrganizePlan, action.plan_id)
        if source_plan is None:
            raise HTTPException(status_code=404, detail="Source plan not found.")

        field_diff = self._compute_field_diff(current_yaml, proposed_yaml)
        merged_yaml = self._build_merged_yaml(current_yaml, proposed_yaml, field_diff)

        now = _now()
        new_plan = OrganizePlan(
            title=f"Asset.yaml merge plan #{source_plan.id}",
            status="draft",
            plan_kind=source_plan.plan_kind,
            target_library_root_id=source_plan.target_library_root_id,
            parent_plan_id=source_plan.id,
            plan_origin="asset_yaml_merge",
            reconcile_status="not_required",
            created_at=now,
            updated_at=now,
        )
        session.add(new_plan)
        session.flush()

        backup_target = f"{target}.bak-{now.strftime('%Y%m%d-%H%M%S')}"
        backup_action = OrganizeAction(
            plan_id=new_plan.id,
            action_order=1,
            action_type="backup_asset_yaml",
            source_path=action.target_path,
            target_path=backup_target,
            payload_json=json.dumps({"backup_path": backup_target}),
            reason=f"Backup current asset.yaml before merge update from action #{action.id}",
            status="draft",
            conflict_status="unchecked",
            reconcile_status="not_checked",
            created_at=now,
            updated_at=now,
        )
        session.add(backup_action)

        update_action = OrganizeAction(
            plan_id=new_plan.id,
            action_order=2,
            action_type="write_asset_yaml_update",
            source_path=action.target_path,
            target_path=action.target_path,
            payload_json=json.dumps({
                "merge_kind": "asset_yaml_update",
                "current_yaml": current_yaml,
                "proposed_yaml": proposed_yaml,
                "merged_yaml": merged_yaml,
                "field_diff": field_diff,
            }, default=str),
            reason=f"Update asset.yaml with merged content from action #{action.id}",
            status="draft",
            conflict_status="unchecked",
            reconcile_status="not_checked",
            created_at=now,
            updated_at=now,
        )
        session.add(update_action)

        session.flush()
        self._refresh_plan_conflicts(session, new_plan)
        session.commit()

        return GenerateAssetYamlMergeResponse(
            source_plan_id=source_plan.id,
            source_action_id=action.id,
            merge_plan_id=new_plan.id,
            backup_action_id=backup_action.id,
            update_action_id=update_action.id,
            plan_origin="asset_yaml_merge",
            field_diff=[FieldDiffItem(**d) for d in field_diff],
        )

    _SAFE_ADDITION_FIELDS = {"aliases", "tags", "localized_title", "notes"}
    _CONFIRMATION_FIELDS = {"title", "year", "cover", "launch_exe", "main_video", "creator", "source", "source_url"}
    _NEVER_MODIFY_FIELDS = {"schema_version", "type", "filesystem_title", "original_title"}

    def _compute_field_diff(self, current: dict, proposed: dict) -> list[dict]:
        diffs: list[dict] = []
        for field, proposed_val in proposed.items():
            current_val = current.get(field)
            if field == "schema_version" and isinstance(proposed_val, (int, float)) and isinstance(current_val, (int, float)) and proposed_val < current_val:
                diffs.append({"field": field, "status": "kept_current", "current": str(current_val), "proposed": str(proposed_val), "merged": str(current_val)})
                continue
            if field in self._NEVER_MODIFY_FIELDS:
                if current_val is None or str(current_val) == str(proposed_val):
                    diffs.append({"field": field, "status": "unchanged", "current": _serialize_diff_val(current_val), "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(current_val)})
                else:
                    diffs.append({"field": field, "status": "kept_current", "current": _serialize_diff_val(current_val), "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(current_val)})
            elif field in self._CONFIRMATION_FIELDS:
                if current_val is None:
                    diffs.append({"field": field, "status": "conflict", "current": None, "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(current_val)})
                elif str(current_val) == str(proposed_val):
                    diffs.append({"field": field, "status": "unchanged", "current": _serialize_diff_val(current_val), "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(current_val)})
                else:
                    diffs.append({"field": field, "status": "conflict", "current": _serialize_diff_val(current_val), "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(current_val)})
            elif field in self._SAFE_ADDITION_FIELDS:
                if current_val is None:
                    diffs.append({"field": field, "status": "added", "current": None, "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(proposed_val)})
                elif isinstance(current_val, list) and isinstance(proposed_val, list):
                    merged_list = list(dict.fromkeys(current_val + proposed_val))
                    new_items = [v for v in proposed_val if v not in current_val]
                    diffs.append({"field": field, "status": "added" if new_items else "unchanged", "current": _serialize_diff_val(current_val), "proposed": _serialize_diff_val(new_items or proposed_val), "merged": _serialize_diff_val(merged_list)})
                elif str(current_val) == str(proposed_val):
                    diffs.append({"field": field, "status": "unchanged", "current": _serialize_diff_val(current_val), "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(current_val)})
                else:
                    diffs.append({"field": field, "status": "added", "current": _serialize_diff_val(current_val), "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(proposed_val)})
            else:
                if current_val is None:
                    diffs.append({"field": field, "status": "conflict", "current": None, "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(current_val)})
                elif str(current_val) == str(proposed_val):
                    diffs.append({"field": field, "status": "unchanged", "current": _serialize_diff_val(current_val), "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(current_val)})
                else:
                    diffs.append({"field": field, "status": "conflict", "current": _serialize_diff_val(current_val), "proposed": _serialize_diff_val(proposed_val), "merged": _serialize_diff_val(current_val)})
        for field in current:
            if field not in proposed:
                pass
        return diffs

    def _build_merged_yaml(self, current: dict, proposed: dict, field_diff: list[dict]) -> dict:
        merged = dict(current)
        for diff in field_diff:
            if diff["status"] == "added" and diff["merged"] is not None:
                merged[diff["field"]] = _deserialize_diff_val(diff["merged"])
        return merged

    def _check_rollback_preconditions(self, action: OrganizeAction) -> str | None:
        if not action.target_path or not action.source_path:
            return "Missing source or target path."
        target = Path(action.target_path)
        source = Path(action.source_path)
        if action.action_type == "rename" and source.parent != target.parent:
            return "Rename rollback must stay in same parent directory."
        if not target.exists():
            return "Original target missing."
        if source.exists():
            return "Original source still exists."
        if not source.parent.exists():
            return "Rollback target parent does not exist."
        return None

    def reconcile_plan(self, session: Session, plan_id: int) -> ReconcilePlanResponse:
        plan = session.get(OrganizePlan, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Plan not found.")
        if plan.status not in ("completed", "completed_with_errors"):
            raise HTTPException(
                status_code=400,
                detail=f"Only completed plans can be reconciled. Current status: {plan.status}",
            )

        actions = self.repository.list_plan_actions(session, plan_id)
        summary: dict[str, int] = {}
        action_items: list[ReconcileActionItem] = []

        for action in actions:
            if action.status in ("succeeded", "failed", "skipped"):
                rs = self._reconcile_action(action)
            else:
                rs = "not_checked"
            action.reconcile_status = rs
            summary[rs] = summary.get(rs, 0) + 1
            action_items.append(ReconcileActionItem(
                action_id=action.id,
                action_type=action.action_type,
                source_path=action.source_path,
                target_path=action.target_path,
                reconcile_status=rs,
            ))

        plan.reconcile_status = "reconciled"
        plan.reconciled_at = datetime.now(UTC)
        plan.reconcile_summary_json = json.dumps(summary)
        session.commit()

        return ReconcilePlanResponse(
            plan_id=plan.id,
            reconcile_status="reconciled",
            reconciled_at=plan.reconciled_at,
            summary=summary,
            actions=action_items,
        )

    def _reconcile_action(self, action: OrganizeAction) -> str:
        if action.action_type in ("move", "rename"):
            source_exists = bool(action.source_path and Path(action.source_path).exists())
            target_exists = bool(action.target_path and Path(action.target_path).exists())
            if not source_exists and target_exists:
                return "matched"
            elif source_exists and target_exists:
                return "both_exist"
            elif source_exists and not target_exists:
                return "source_still_exists"
            else:
                return "both_missing"

        if action.action_type == "mkdir":
            if not action.target_path:
                return "target_missing"
            target = Path(action.target_path)
            if target.exists():
                return "matched" if target.is_dir() else "target_not_directory"
            return "target_missing"

        if action.action_type == "write_asset_yaml":
            if not action.target_path:
                return "asset_yaml_missing"
            target = Path(action.target_path)
            if target.exists() and target.name.lower() == "asset.yaml":
                return "matched"
            if target.exists():
                return "matched"
            return "asset_yaml_missing"

        if action.action_type == "backup_asset_yaml":
            if not action.target_path:
                return "target_missing"
            target = Path(action.target_path)
            if target.exists():
                return "matched"
            return "target_missing"

        if action.action_type == "write_asset_yaml_update":
            if not action.target_path:
                return "asset_yaml_missing"
            target = Path(action.target_path)
            if target.exists() and target.name.lower() == "asset.yaml":
                return "matched"
            return "asset_yaml_missing"

        return "unknown"


organize_service = LibraryOrganizeService()

def _serialize_diff_val(val: object) -> str | None:
    if val is None:
        return None
    if isinstance(val, (list, dict)):
        return json.dumps(val, default=str)
    return str(val)


def _deserialize_diff_val(val: str | None) -> object:
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


def _detect_file_type(file: File) -> tuple[str, str, str]:
    name = file.name
    extension = Path(file.path).suffix.lower()
    if extension in VIDEO_EXTENSIONS:
        if re.search(r"[Ss]\d{1,2}[Ee]\d{1,3}", name):
            return "course", "medium", "Video filename looks episodic or lesson-like and needs review."
        if _year_from_text(name):
            return "movie", "medium", "Video filename includes a year-like title pattern."
        return "clip", "low", "Video file does not have a strong object pattern."
    if extension == ".exe":
        return "game", "low", "Executable file may belong to a game object but needs review."
    if extension in IMAGE_EXTENSIONS:
        return "imgset", "low", "Image file may belong to an image set."
    if extension in DOCUMENT_EXTENSIONS:
        return "docset", "low", "Document file may belong to a document set."
    return "unknown", "unknown", "No safe rule matched this file."


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


def _suggested_template_key(detected_type: str) -> str:
    mapping = {
        "movie": "movie_default",
        "anime": "anime_default",
        "game": "game_default",
        "course": "course_default",
        "imgset": "imgset_default",
        "docset": "docset_default",
    }
    key = mapping.get(detected_type, "fallback_object_default")
    enabled_keys = {template["template_key"] for template in BUILTIN_TEMPLATES if template["is_enabled"]}
    return key if key in enabled_keys else "fallback_object_default"


def render_organize_template(template: dict, candidate) -> Path:
    detected_type = candidate.detected_type
    title = _safe_title(_strip_extension(candidate.display_name))
    year_val = _year_from_text(candidate.display_name)
    season = _extract_season(candidate.display_name)
    type_prefix = OBJECT_PREFIX.get(detected_type, detected_type.upper() if detected_type else "CLIP")

    variables: dict[str, str] = {
        "type": detected_type or "clip",
        "title": title,
        "year": str(year_val) if year_val else "",
        "season": season,
        "creator": "",
        "source": "",
        "resolution": "",
        "language": "",
        "platform": "",
        "version": "",
        "date": "",
    }

    rendered = template["path_template"]
    for var_name, value in variables.items():
        placeholder = "{" + var_name + "}"
        if value:
            rendered = rendered.replace(placeholder, value)
        else:
            rendered = _strip_missing_var(rendered, placeholder)


    remaining = re.findall(r"\{(\w+)\}", rendered)
    for var_name in remaining:
        rendered = rendered.replace("{" + var_name + "}", "")
    rendered = re.sub(r"\(\s*\)", "", rendered)
    rendered = re.sub(r"\[\s*\]", "", rendered)
    rendered = re.sub(r"\s{2,}", " ", rendered)

    parts = Path(rendered).parts
    safe_parts: list[str] = []
    for part in parts:
        cleaned = re.sub(r'[<>:"/\\|?*]', " ", part)
        cleaned = " ".join(cleaned.split()).strip()
        if cleaned in ("", ".", ".."):
            continue
        safe_parts.append(cleaned)
    if not safe_parts:
        safe_parts = ["Untitled"]

    rendered_path = Path(*safe_parts)
    if rendered_path.is_absolute():
        raise HTTPException(status_code=400, detail="Template rendered an absolute path.")
    if ".." in str(rendered_path).replace("\\", "/").split("/"):
        raise HTTPException(status_code=400, detail="Template rendered path contains parent traversal.")
    drive_match = re.match(r"^[a-zA-Z]:", str(rendered_path))
    if drive_match:
        raise HTTPException(status_code=400, detail="Template rendered path contains a drive letter.")
    if str(rendered_path).startswith("\\\\"):
        raise HTTPException(status_code=400, detail="Template rendered path is a UNC path.")

    return rendered_path


def _extract_season(value: str) -> str:
    match = re.search(r"S(\d{1,2})", value, re.IGNORECASE)
    return match.group(1) if match else ""


def _strip_missing_var(rendered: str, placeholder: str) -> str:
    result: list[str] = []
    i = 0
    while i < len(rendered):
        idx = rendered.find(placeholder, i)
        if idx == -1:
            result.append(rendered[i:])
            break
        result.append(rendered[i:idx])
        before = rendered[i:idx]
        after_start = idx + len(placeholder)
        j = after_start
        while j < len(rendered) and rendered[j] == " ":
            j += 1
        if j < len(rendered) and rendered[j] == ")":
            j += 1
            while j < len(rendered) and rendered[j] == " ":
                j += 1
        if before.rstrip().endswith("("):
            k = len(before) - 1
            while k >= 0 and before[k] == " ":
                k -= 1
            if k >= 0 and before[k] == "(":
                before = before[:k].rstrip()
        if before.rstrip().endswith(" -"):
            before = before.rstrip()[:-2].rstrip()
        result.append(before)
        i = j
    merged = "".join(result)
    merged = re.sub(r"\s{2,}", " ", merged)
    return merged.strip()


def _safe_title(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]", " ", value)
    cleaned = re.sub(r"[._]+", " ", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned or "Untitled"


def _strip_extension(value: str) -> str:
    return Path(value).stem


def _year_from_text(value: str) -> int | None:
    match = re.search(r"(19\d{2}|20\d{2})", value)
    return int(match.group(1)) if match else None


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def _is_path_within(path: Path, root: Path) -> bool:
    normalized_path = os.path.normcase(os.path.abspath(path))
    normalized_root = os.path.normcase(os.path.abspath(root))
    try:
        common = os.path.commonpath([normalized_path, normalized_root])
    except ValueError:
        return False
    return common == normalized_root


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
