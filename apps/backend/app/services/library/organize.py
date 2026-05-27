from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.core.time import utcnow

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
from app.core.classification import (
    DOCUMENT_EXTENSIONS_DOTTED as DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS_DOTTED as IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS_DOTTED as VIDEO_EXTENSIONS,
)
from app.services.library.object_parser import SUPPORTED_OBJECT_TYPES
from app.services.library.organize_template_renderer import (
    OBJECT_PREFIX,
    _safe_title,
    _strip_extension,
    _year_from_text,
    get_template_by_key,
    get_templates,
    render_organize_template,
    suggested_template_key,
)
from app.services.library.path_safety import is_path_within, path_key


class PlanKind:
    ORGANIZE_INBOX = "organize_inbox"
    FIX_OBJECT_REVIEW = "fix_object_review"
    OBJECT_CREATION_MANAGED_COMPOSE = "object_creation_managed_compose"
    OBJECT_AMENDMENT = "object_amendment"


INBOX_NAMES = {"00_inbox", "_to_sort", "inbox"}
PLAN_TARGET_DIRS = {
    "movie": ("10_Movies_Anime", "Movies"),
    "anime": ("10_Movies_Anime", "Anime"),
    "game": ("20_Games",),
    "software": ("30_Software",),
    "course": ("40_Videos", "Courses"),
    "imgset": ("30_Images", "Image_Sets"),
    "docset": ("80_Documents", "Docsets"),
    "clip": ("40_Videos", "Clips"),
    "video_collection": ("40_Videos", "Collections"),
    "clip_set": ("40_Videos", "Clip_Sets"),
    "movie_collection": ("10_Movies_Anime", "Collections"),
    "photo_event": ("30_Images", "Photo_Events"),
    "web_image_set": ("30_Images", "Web_Images"),
    "comic": ("30_Images", "Comics"),
    "audio": ("50_Audio",),
    "asset_pack": ("60_Assets",),
}
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
            if source_root is None or not is_path_within(Path(file.path), source_root):
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
        return get_templates()

    def _get_template(self, template_key: str) -> dict | None:
        return get_template_by_key(template_key)

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

        non_pending = [c for c in valid_candidates if c.status != "pending"]
        if non_pending:
            raise HTTPException(
                status_code=400,
                detail=f"Candidates not in 'pending' status: {[c.id for c in non_pending]}. Only 'pending' candidates can generate plans.",
            )

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
            plan_kind=PlanKind.ORGANIZE_INBOX if any(item.source_kind == "file" for item in valid_candidates) else PlanKind.FIX_OBJECT_REVIEW,
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
        actions = self.repository.list_plan_actions(session, plan.id)
        candidates = self.repository.list_plan_candidates(session, plan.id)
        counts = self.repository.action_counts(session, [plan.id]).get(plan.id, {})
        return PlanDetailResponse(
            plan=self._plan_item(plan, counts, session),
            candidates=[self._candidate_item(candidate) for candidate in candidates],
            actions=[self._action_item(action) for action in actions],
        )

    def refresh_plan_conflicts(self, session: Session, plan_id: int) -> PlanDetailResponse:
        """Explicitly refresh conflict state for a draft or ready plan."""
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        if plan.status not in {"draft", "ready"}:
            raise HTTPException(status_code=400, detail="Only draft or ready plans can refresh conflicts.")
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

    def prepare_plan(self, session: Session, plan_id: int) -> PreflightResponse:
        """Atomically mark-ready + preflight. Does NOT execute."""
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Organize plan not found.")
        if plan.status not in {"draft", "ready"}:
            raise HTTPException(status_code=400, detail="Only draft or ready plans can be prepared.")
        self._refresh_plan_conflicts(session, plan)
        if plan.status == "draft":
            self.mark_ready(session, plan_id)
        return self.preflight_plan(session, plan_id)

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
        if plan.status not in {"draft", "ready"}:
            raise HTTPException(status_code=400, detail="Only draft or ready plan actions can be edited.")
        if target_path is not None:
            action.target_path = target_path.strip() or None
        if payload_json is not None:
            action.payload_json = payload_json
        if status is not None:
            action.status = status
        if reason is not None:
            action.reason = reason.strip() or None
        action.updated_at = _now()
        if plan.status == "ready":
            plan.status = "draft"
            plan.confirmed_at = None
            plan.updated_at = action.updated_at
        else:
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
        now = _now()
        for candidate in self.repository.list_plan_candidates(session, plan.id):
            if candidate.status == "added_to_plan":
                candidate.status = "pending"
                candidate.updated_at = now
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
                failed_actions: list[OrganizeAction] = []
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

                    dep_failed, dep_reason = self._check_dependency_failure(action, failed_actions)
                    if dep_failed:
                        action.status = "skipped"
                        action.error_message = dep_reason
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
                        failed_actions.append(action)
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

                # Phase 7D: sync import-linked paths after successful moves
                self._sync_import_paths_after_execute(session, plan_id)

                # Phase 8C-4C: Finalize managed compose object creation
                self._finalize_managed_compose(session, plan_id, failed)

                # Phase 8D-C: Finalize object amendment
                self._finalize_object_amendment(session, plan_id, failed)

                plan = self.repository.get_plan(session, plan_id)
                if plan is None:
                    return
                now = _now()
                plan.execution_finished_at = now
                plan.executed_at = now
                plan.status = "completed" if failed == 0 and skipped == 0 else "completed_with_errors"

                if plan.status == "completed":
                    for candidate in self.repository.list_plan_candidates(session, plan.id):
                        candidate.status = "resolved"
                        candidate.updated_at = now

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

    @staticmethod
    def _check_dependency_failure(action: OrganizeAction, failed_actions: list[OrganizeAction]) -> tuple[bool, str | None]:
        """Check if an action depends on any previously failed action.

        Returns (should_skip, reason).  Only actions whose target path falls under
        a failed mkdir directory, or whose target parent matches a failed move's
        target parent, are skipped.  Unrelated candidates continue unaffected.
        """
        if not failed_actions:
            return False, None

        action_target = Path(action.target_path) if action.target_path else None

        for failed in failed_actions:
            failed_target = Path(failed.target_path) if failed.target_path else None

            if failed.action_type == "mkdir" and failed_target is not None and action_target is not None:
                if is_path_within(action_target, failed_target):
                    return True, f"Failed dependency: mkdir '{failed.target_path}' failed, blocking descendant action."

            if failed.action_type in {"move", "rename"} and failed_target is not None and action_target is not None:
                if action.action_type == "write_asset_yaml" and action_target.parent == failed_target.parent:
                    return True, f"Failed dependency: move to '{failed.target_path}' failed, cannot write asset.yaml in the same directory."

            if failed.action_type == "write_asset_yaml" and failed_target is not None and action_target is not None:
                if action.action_type == "write_asset_yaml_update" and action_target == failed_target:
                    return True, f"Failed dependency: asset.yaml write failed, cannot update the same file."

            if failed.action_type == "backup_asset_yaml" and failed_target is not None and action_target is not None:
                if action.action_type == "write_asset_yaml_update" and action_target.parent == failed_target.parent:
                    return True, f"Failed dependency: backup_asset_yaml failed, cannot update the same asset.yaml."

        return False, None

    def _run_preflight(self, session: Session, plan: OrganizePlan) -> list[OrganizeAction]:
        actions = self.repository.list_plan_actions(session, plan.id)
        planned_dirs: set[str] = set()
        for action in actions:
            conflict_status, conflict_message = self._preflight_action(session, action, planned_dirs)
            action.conflict_status = conflict_status
            action.conflict_message = conflict_message
            action.updated_at = _now()
            if action.action_type == "mkdir" and action.target_path and conflict_status in {"ok", "warning"}:
                planned_dirs.add(path_key(Path(action.target_path)))
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

            # Phase 8C-4B: managed compose object creation validation
            oc_result = self._validate_object_creation_move(session, action, plan)
            if oc_result is not None:
                return oc_result

            # Phase 8D-B: object amendment validation
            am_result = self._validate_object_amendment_move(session, action, plan)
            if am_result is not None:
                return am_result

            if plan is not None and plan.target_library_root_id is not None:
                lib_root = self.library_root_repository.get_by_id(session, plan.target_library_root_id)
                if lib_root is None or not lib_root.is_enabled:
                    return "blocked", "Target library root is missing or disabled."
                target_root = Path(lib_root.root_path).resolve()
                if not is_path_within(target, target_root):
                    return "blocked", "Target path is outside the selected managed library root."
            else:
                target_root = self._resolve_root_for_mkdir_or_asset(session, target, plan)
                if target_root is None:
                    return "blocked", "Target path is outside any enabled source or managed library root."
                source_in_lib_root = self._resolve_root_for_mkdir_or_asset(session, source, plan)
                if source_in_lib_root is None:
                    return "blocked", "Source path is outside any enabled source or managed library root."
                target_in_source = self._source_root_for_path_safe(session, target)
                source_in_source = self._source_root_for_path_safe(session, source)
                if target_in_source is not None and source_in_source is not None:
                    if path_key(target_in_source) != path_key(source_in_source):
                        return "blocked", "Source and target must stay inside the same enabled source."
                if not is_path_within(target, target_root):
                    return "blocked", "Target path is outside the enabled source."

            if action.action_type == "rename" and path_key(source.parent) != path_key(target.parent):
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
        return target.parent.exists() or path_key(target.parent) in planned_dirs

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
                # For v2 imports, source is in managed root, not a source
                source_path = Path(candidate.source_path)
                source_root = self._source_root_for_path_safe(session, source_path)
                if source_root is None and plan.target_library_root_id is not None:
                    lib_root = self._resolve_root_for_mkdir_or_asset(session, source_path, plan)
                    source_root = lib_root or source_path.parent
                if source_root is None:
                    source_root = source_path.parent
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
            if is_path_within(path, source_root):
                return source_root
        raise HTTPException(status_code=400, detail="Candidate source path is outside enabled sources.")

    def _source_root_for_path_safe(self, session: Session, path: Path) -> Path | None:
        enabled_sources = [source for source in self.source_repository.list_sources(session) if source.is_enabled]
        for source in enabled_sources:
            source_root = Path(source.path).resolve()
            if is_path_within(path, source_root):
                return source_root
        return None

    def _resolve_root_for_mkdir_or_asset(self, session: Session, path: Path, plan: OrganizePlan | None) -> Path | None:
        if plan is not None and plan.target_library_root_id is not None:
            lib_root = self.library_root_repository.get_by_id(session, plan.target_library_root_id)
            if lib_root and lib_root.is_enabled:
                root_path = Path(lib_root.root_path).resolve()
                if is_path_within(path, root_path):
                    return root_path
            return None
        for source in self.source_repository.list_sources(session):
            if source.is_enabled:
                source_root = Path(source.path).resolve()
                if is_path_within(path, source_root):
                    return source_root
        for lib_root in self.library_root_repository.list_enabled(session):
            root_path = Path(lib_root.root_path).resolve()
            if is_path_within(path, root_path):
                return root_path
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
            if not is_path_within(target, target_root):
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
            if action.action_type in {"move", "rename"}:
                oc_result = self._validate_object_creation_move(session, action, plan)
                if oc_result is not None:
                    action.conflict_status = oc_result[0]
                    action.conflict_message = oc_result[1]
                    return
                am_result = self._validate_object_amendment_move(session, action, plan)
                if am_result is not None:
                    action.conflict_status = am_result[0]
                    action.conflict_message = am_result[1]
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
        plan.reconciled_at = utcnow()
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

    # ── Phase 7D: Library v2 path sync ──────────────────────

    def _sync_import_paths_after_execute(self, session: Session, plan_id: int) -> None:
        """After execute worker finishes actions, sync files.path for v2 import-linked
        succeeded move actions. Only touches actions with inbox_item_id or
        import_object_candidate_id set."""
        from datetime import datetime as dt

        actions = self.repository.list_plan_actions(session, plan_id)
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            return

        managed_root_id = plan.target_library_root_id
        now = utcnow()

        for action in actions:
            if action.status != "succeeded":
                continue
            if action.action_type not in {"move", "rename"}:
                continue
            if action.inbox_item_id is None and action.import_object_candidate_id is None:
                continue

            try:
                if action.inbox_item_id:
                    self._sync_single_inbox_item(
                        session, action, managed_root_id, now
                    )
                elif action.import_object_candidate_id:
                    self._sync_object_candidate_members(
                        session, action, managed_root_id, now
                    )
            except Exception as exc:
                self._log_event(
                    session, plan_id, action.id,
                    "action_failed",
                    f"Path sync failed: {exc}",
                    path_before=action.source_path,
                    path_after=action.target_path,
                    error_message=str(exc),
                )

    def _sync_single_inbox_item(
        self, session: Session, action: OrganizeAction,
        managed_root_id: int | None, now: datetime,
    ) -> None:
        from app.db.models.importing import InboxItem
        from app.repositories.importing.repository import ImportRepository

        item = session.get(InboxItem, action.inbox_item_id)
        if item is None or item.file_id is None:
            return

        file = session.get(File, item.file_id)
        if file is None:
            return

        old_path = file.path
        new_path = action.after_path or action.target_path
        if not new_path:
            return

        # update file record
        file.path = new_path
        file.parent_path = str(Path(new_path).parent)
        file.name = Path(new_path).name
        file.storage_state = "managed"
        file.managed_root_id = managed_root_id
        file.managed_at = now
        file.updated_at = now

        # update inbox item
        import_repo = ImportRepository()
        import_repo.update_inbox_item_status(session, item, "organized")

        # write path history
        journal_id = self._append_path_sync_journal(
            session, action, "path_sync", "file", file.id, old_path, new_path,
        )
        import_repo.append_path_history(
            session,
            file_id=file.id,
            old_path=old_path,
            new_path=new_path,
            reason="library_v2_execute",
            operation_journal_id=journal_id,
        )

        self._log_event(
            session, action.plan_id, action.id, "path_synced",
            f"Library v2: synced file {file.id} from {old_path} to {new_path}.",
            path_before=old_path, path_after=new_path,
        )

    def _sync_object_candidate_members(
        self, session: Session, action: OrganizeAction,
        managed_root_id: int | None, now: datetime,
    ) -> None:
        from app.db.models.importing import ImportObjectCandidate, ImportObjectMember, InboxItem
        from app.repositories.importing.repository import ImportRepository

        oc = session.get(ImportObjectCandidate, action.import_object_candidate_id)
        if oc is None:
            return

        import_repo = ImportRepository()
        members = import_repo.list_object_members(session, oc.id)
        target_root_path = action.after_path or action.target_path
        if not target_root_path:
            return

        old_inbox_root = oc.inbox_root_path

        for member in members:
            item = session.get(InboxItem, member.inbox_item_id)
            if item is None or item.file_id is None:
                continue

            file = session.get(File, item.file_id)
            if file is None:
                continue

            old_path = file.path
            # compute new path: map old_inbox_path relative to old_inbox_root → target_root
            old_inbox = Path(item.inbox_path)
            old_root = Path(old_inbox_root)
            try:
                relative = old_inbox.relative_to(old_root)
            except ValueError:
                relative = Path(old_inbox.name)
            new_path = str(Path(target_root_path) / relative)

            file.path = new_path
            file.parent_path = str(Path(new_path).parent)
            file.name = Path(new_path).name
            file.storage_state = "managed"
            file.managed_root_id = managed_root_id
            file.managed_at = now
            file.updated_at = now

            import_repo.update_inbox_item_status(session, item, "organized")

            journal_id = self._append_path_sync_journal(
                session, action, "path_sync", "file", file.id, old_path, new_path,
            )
            import_repo.append_path_history(
                session,
                file_id=file.id,
                old_path=old_path,
                new_path=new_path,
                reason="library_v2_execute",
                operation_journal_id=journal_id,
            )

        # update object candidate status
        oc.status = "organized"
        oc.updated_at = now

        self._log_event(
            session, action.plan_id, action.id, "path_synced",
            f"Library v2: synced {len(members)} members of object candidate {oc.id}.",
        )

    @staticmethod
    def _append_path_sync_journal(
        session: Session, action: OrganizeAction,
        operation_type: str, entity_type: str, entity_id: int,
        old_path: str, new_path: str,
    ) -> int | None:
        from app.repositories.importing.repository import ImportRepository
        import uuid as _uuid

        repo = ImportRepository()
        entry = repo.append_journal_entry(
            session,
            operation_id=str(_uuid.uuid4()),
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            status="succeeded",
            before_json=json.dumps({"path": old_path}),
            after_json=json.dumps({"path": new_path, "action_id": action.id}),
        )
        return entry.id

    # ── Phase 8C-4A: Managed Compose Creation Plan ───────────

    def create_managed_compose_plan(
        self,
        session: Session,
        *,
        file_ids: list[int],
        object_name: str,
        object_type: str,
        target_library_root_id: int | None = None,
    ) -> dict[str, Any]:
        """Create a draft object creation plan for managed loose files.

        Only validates and creates the plan — no preflight, execute, or file ops.
        """
        import re as _re

        if not file_ids:
            raise HTTPException(status_code=400, detail="At least one file is required.")

        # Validate object type
        if object_type not in PLAN_TARGET_DIRS:
            raise HTTPException(status_code=400, detail=f"Unknown object_type: {object_type}")

        # Sanitize name
        object_name = _re.sub(r'[\\/:*?"<>|]', " ", object_name)
        object_name = _re.sub(r"\s+", " ", object_name).strip()
        if not object_name:
            raise HTTPException(status_code=400, detail="Object name is required.")

        # Load and validate files
        files: list[File] = []
        managed_root_id: int | None = None

        # Collect member file_ids to reject already-composed files
        member_file_ids: set[int] = set()
        from app.db.models.library_object import LibraryObjectMember as LOM
        lom_rows = session.query(LOM.file_id).filter(
            LOM.file_id.isnot(None),
            LOM.member_status == "active",
        ).all()
        member_file_ids.update(r[0] for r in lom_rows if r[0] is not None)
        from app.db.models.importing import ImportObjectMember as IOM, ImportObjectCandidate as IOC, InboxItem as II
        iom_ii = session.query(IOM.inbox_item_id).join(IOC, IOM.import_object_candidate_id == IOC.id).filter(IOC.status.in_(["pending_review", "confirmed"])).all()
        iom_ii_ids = [r[0] for r in iom_ii if r[0] is not None]
        if iom_ii_ids:
            iom_fids = session.query(II.file_id).filter(II.id.in_(iom_ii_ids)).all()
            member_file_ids.update(r[0] for r in iom_fids if r[0] is not None)

        for fid in file_ids:
            f = session.query(File).filter(File.id == fid).first()
            if f is None:
                raise HTTPException(status_code=404, detail=f"File not found: {fid}")
            if f.storage_state != "managed":
                raise HTTPException(status_code=400, detail=f"File {fid} must be storage_state=managed, got {f.storage_state}")
            if fid in member_file_ids:
                raise HTTPException(status_code=400, detail=f"File {fid} is already a member of an object.")
            src = Path(f.path)
            if not src.is_file():
                raise HTTPException(status_code=400, detail=f"Source file does not exist: {f.path}")
            if managed_root_id is None:
                managed_root_id = f.managed_root_id
            elif f.managed_root_id != managed_root_id:
                raise HTTPException(status_code=400, detail="Cross-managed-root compose is not supported in Phase 8C-4A.")
            files.append(f)

        # Validate / resolve target root
        if target_library_root_id is not None:
            lib_root = self.library_root_repository.get_by_id(session, target_library_root_id)
            if lib_root is None or not lib_root.is_enabled:
                raise HTTPException(status_code=400, detail="Target library root not found or disabled.")
            base_root = Path(lib_root.root_path).resolve()
        else:
            if managed_root_id:
                lib_root = self.library_root_repository.get_by_id(session, managed_root_id)
                base_root = Path(lib_root.root_path).resolve() if lib_root else Path(files[0].path).parent
                target_library_root_id = managed_root_id
            else:
                base_root = Path(files[0].path).parent
                target_library_root_id = None

        # Render target object directory
        prefix = OBJECT_PREFIX.get(object_type, "OBJ")
        safe_title = _safe_title(_strip_extension(object_name))
        year = _year_from_text(object_name)
        suffix = f" ({year})" if year else ""
        folder_name = f"[{prefix}] {safe_title}{suffix}"

        target_dirs = PLAN_TARGET_DIRS[object_type]
        target_object_dir = base_root.joinpath(*target_dirs, folder_name)

        # Build actions
        now = _now()
        plan_title = f"Object creation: {object_name}"
        plan = OrganizePlan(
            title=plan_title,
            status="draft",
            plan_kind=PlanKind.OBJECT_CREATION_MANAGED_COMPOSE,
            summary=f"Draft object creation plan for {object_name}. No files have been moved.",
            target_library_root_id=target_library_root_id,
            created_at=now,
            updated_at=now,
        )
        self.repository.add_plan(session, plan)

        planned_members: list[dict[str, Any]] = []
        actions: list[OrganizeAction] = []
        order = 1

        # mkdir action
        actions.append(OrganizeAction(
            plan_id=plan.id, action_order=order, action_type="mkdir",
            source_path=None, target_path=str(target_object_dir), payload_json=None,
            status="draft", conflict_status="unchecked",
            reason=f"Create object directory for {object_name}",
            import_object_candidate_id=None, inbox_item_id=None,
            created_at=now, updated_at=now,
        ))
        order += 1

        # move actions — one per file
        for f in files:
            source_path = Path(f.path)
            safe_fname = _re.sub(r'[<>:"/\\|?*]', " ", f.name).strip()
            target_file = target_object_dir / safe_fname
            payload = {
                "file_id": f.id,
                "member_role": "unknown_child",
                "selected_relative_path": safe_fname,
                "object_creation_plan": True,
            }
            if f.file_kind == "image":
                payload["member_role"] = "image_member"
            elif f.file_kind == "video":
                payload["member_role"] = "main_video"
            elif f.file_kind == "document":
                payload["member_role"] = "document_attachment"
            elif f.file_kind in ("executable",):
                payload["member_role"] = "launch_exe"

            actions.append(OrganizeAction(
                plan_id=plan.id, action_order=order, action_type="move",
                source_path=str(source_path), target_path=str(target_file),
                payload_json=json.dumps(payload, ensure_ascii=False),
                status="draft", conflict_status="unchecked",
                reason=f"Move managed loose file into object directory",
                import_object_candidate_id=None, inbox_item_id=None,
                created_at=now, updated_at=now,
            ))
            planned_members.append({
                "file_id": f.id,
                "role": payload["member_role"],
                "relative_path": safe_fname,
                "source_path": str(source_path),
                "target_path": str(target_file),
            })
            order += 1

        self.repository.add_actions(session, actions)

        # summary_json
        plan.summary_json = json.dumps({
            "plan_type": "object_creation",
            "object_name": object_name,
            "object_type": object_type,
            "target_object_dir": str(target_object_dir),
            "selected_file_ids": [f.id for f in files],
            "planned_members": [{k: v for k, v in m.items() if k != "source_path"} for m in planned_members],
            "finalize_policy": "all_or_nothing_object_creation",
        }, ensure_ascii=False)

        session.flush()
        session.commit()

        return {
            "plan_id": plan.id,
            "status": plan.status,
            "plan_kind": plan.plan_kind,
            "actions_count": len(actions),
            "target_library_root_id": target_library_root_id,
            "target_root_path": str(base_root),
            "target_object_dir": str(target_object_dir),
            "planned_members": planned_members,
            "notes": [
                "Draft plan only — no files have been moved.",
                "Mark ready, preflight, then execute to create the object.",
                "Object creation only after full successful execute.",
            ],
        }

    # ── Phase 8C-4B: Managed compose preflight validation ─────

    def _validate_object_creation_move(
        self, session: Session, action: OrganizeAction, plan: OrganizePlan | None,
    ) -> tuple[str, str] | None:
        """Validate move actions for object_creation_managed_compose plans.

        Returns (conflict_status, conflict_message) or None if not applicable.
        """
        if plan is None or plan.plan_kind != PlanKind.OBJECT_CREATION_MANAGED_COMPOSE:
            return None
        if action.action_type != "move":
            return None

        # Parse payload
        payload: dict[str, Any] = {}
        if action.payload_json:
            try:
                payload = json.loads(action.payload_json)
            except json.JSONDecodeError:
                return "blocked", "Action payload is not valid JSON."
        if not payload.get("object_creation_plan"):
            return None

        file_id = payload.get("file_id")
        member_role = payload.get("member_role")
        if file_id is None or not member_role:
            return "blocked", "Move action is missing file_id or member_role in payload."

        # Verify file exists in DB
        file = session.query(File).filter(File.id == file_id).first()
        if file is None:
            return "stale", f"Object creation target file {file_id} no longer exists in the database."

        # Verify storage_state
        if file.storage_state != "managed":
            return "blocked", f"File {file_id} is no longer managed (current: {file.storage_state})."

        # Verify not already a formal member
        from app.db.models.library_object import LibraryObjectMember as LOM
        lom = session.query(LOM).filter(
            LOM.file_id == file_id,
            LOM.member_status == "active",
        ).first()
        if lom is not None:
            return "blocked", f"File {file_id} is already a member of library object {lom.object_id}."

        # Verify not an active import member
        from app.db.models.importing import ImportObjectMember as IOM, ImportObjectCandidate as IOC
        iom = session.query(IOM).join(IOC, IOM.import_object_candidate_id == IOC.id).filter(
            IOM.inbox_item_id.isnot(None)
        ).filter(IOC.status.in_(["pending_review", "confirmed"])).first()
        if iom is not None:
            # Check if any of our import inbox item is also a member
            # Since we don't have inbox_item_id, check if file_id appears via inbox
            from app.db.models.importing import InboxItem as II
            ii = session.query(II).filter(II.file_id == file_id).first()
            if ii:
                iom_check = session.query(IOM).filter(IOM.inbox_item_id == ii.id).join(
                    IOC, IOM.import_object_candidate_id == IOC.id
                ).filter(IOC.status.in_(["pending_review", "confirmed"])).first()
                if iom_check is not None:
                    return "blocked", f"File {file_id} is already an active import object member."

        # Verify source path matches DB
        if action.source_path and file.path != action.source_path:
            return "stale", f"File {file_id} path changed since plan creation."

        return None

    # ── Phase 8D-B: Object amendment preflight ─────────────────

    def _validate_object_amendment_move(
        self, session: Session, action: OrganizeAction, plan: OrganizePlan | None,
    ) -> tuple[str, str] | None:
        """Validate move actions for object_amendment plans.

        Returns (conflict_status, conflict_message) or None if not applicable.
        """
        if plan is None or plan.plan_kind != PlanKind.OBJECT_AMENDMENT:
            return None
        if action.action_type != "move":
            return None

        payload: dict[str, Any] = {}
        if action.payload_json:
            try:
                payload = json.loads(action.payload_json)
            except json.JSONDecodeError:
                return "blocked", "Action payload is not valid JSON."
        if not payload.get("object_amendment_plan"):
            return None

        amendment_action = payload.get("amendment_action", "")
        object_id = payload.get("object_id")

        if not object_id:
            return "blocked", "Amendment action missing object_id in payload."

        # Verify object exists
        lo = session.query(LibraryObject).filter(LibraryObject.id == object_id).first()
        if lo is None:
            return "stale", f"Object {object_id} no longer exists."

        if amendment_action == "add_member":
            return self._validate_amendment_add_member(session, action, payload, lo)
        elif amendment_action == "remove_member":
            return self._validate_amendment_remove_member(session, action, payload, lo)
        else:
            return "blocked", f"Unknown amendment_action: {amendment_action}"

    def _validate_amendment_add_member(
        self, session: Session, action: OrganizeAction,
        payload: dict[str, Any], lo: LibraryObject,
    ) -> tuple[str, str] | None:
        file_id = payload.get("file_id")
        member_role = payload.get("member_role")
        if file_id is None or not member_role:
            return "blocked", "Move action is missing file_id or member_role in payload."

        file = session.query(File).filter(File.id == file_id).first()
        if file is None:
            return "stale", f"Amendment target file {file_id} no longer exists in the database."

        if file.storage_state != "managed":
            return "blocked", f"File {file_id} is no longer managed (current: {file.storage_state})."

        # Not already a formal member
        from app.db.models.library_object import LibraryObjectMember as LOM
        lom = session.query(LOM).filter(LOM.file_id == file_id, LOM.member_status == "active").first()
        if lom is not None:
            return "blocked", f"File {file_id} is already an active member of library object {lom.object_id}."

        # Not an active import member
        from app.db.models.importing import ImportObjectMember as IOM, ImportObjectCandidate as IOC, InboxItem as II
        ii = session.query(II).filter(II.file_id == file_id).first()
        if ii:
            iom_check = session.query(IOM).filter(IOM.inbox_item_id == ii.id).join(
                IOC, IOM.import_object_candidate_id == IOC.id
            ).filter(IOC.status.in_(["pending_review", "confirmed"])).first()
            if iom_check is not None:
                return "blocked", f"File {file_id} is already an active import object member."

        # Path not stale
        if action.source_path and file.path != action.source_path:
            return "stale", f"File {file_id} path changed since plan creation."

        # Target within object root
        if action.target_path:
            obj_root = Path(lo.root_path)
            if not is_path_within(Path(action.target_path), obj_root):
                return "blocked", f"Add target path is outside object root: {lo.root_path}"

        return None

    def _validate_amendment_remove_member(
        self, session: Session, action: OrganizeAction,
        payload: dict[str, Any], lo: LibraryObject,
    ) -> tuple[str, str] | None:
        member_id = payload.get("member_id")
        file_id = payload.get("file_id")
        if member_id is None or file_id is None:
            return "blocked", "Remove action is missing member_id or file_id in payload."

        from app.db.models.library_object import LibraryObjectMember as LOM
        member = session.query(LOM).filter(LOM.id == member_id).first()
        if member is None:
            return "stale", f"Member {member_id} no longer exists."

        if member.object_id != lo.id:
            return "blocked", f"Member {member_id} no longer belongs to object {lo.id}."

        if member.member_status != "active":
            return "blocked", f"Member {member_id} is no longer active (current: {member.member_status})."

        file = session.query(File).filter(File.id == file_id).first()
        if file is None:
            return "stale", f"Remove target file {file_id} no longer exists."

        if file.storage_state != "managed":
            return "blocked", f"File {file_id} is no longer managed."

        if action.source_path and file.path != action.source_path:
            return "stale", f"File {file_id} path changed since plan creation."

        remove_policy = payload.get("remove_target_policy")
        if remove_policy and remove_policy not in ("managed_loose_area",):
            return "blocked", f"Unsupported remove_target_policy: {remove_policy}"

        return None

    # ── Phase 8D-C: Object amendment finalization ─────────────

    @staticmethod
    def _is_action_success_status(status: str | None) -> bool:
        return status in {"succeeded", "completed"}

    def _all_required_amendment_move_actions_succeeded(
        self, actions: list[OrganizeAction], amendment_type: str,
    ) -> bool:
        expected_action = {
            "add_members": "add_member",
            "remove_members": "remove_member",
        }.get(amendment_type)
        if expected_action is None:
            return False

        required_actions: list[OrganizeAction] = []
        for action in actions:
            if action.action_type != "move":
                continue
            payload: dict[str, Any] = {}
            if action.payload_json:
                try:
                    payload = json.loads(action.payload_json)
                except json.JSONDecodeError:
                    return False
            if (
                payload.get("object_amendment_plan")
                and payload.get("amendment_action") == expected_action
            ):
                required_actions.append(action)

        if not required_actions:
            return False
        return all(self._is_action_success_status(action.status) for action in required_actions)

    def _finalize_object_amendment(
        self, session: Session, plan_id: int, failed_count: int,
    ) -> None:
        """After successful execute, finalize object amendment (add/remove members).

        Only runs when plan_kind == object_amendment and all required move
        actions succeeded. Creates/deactivates LibraryObjectMember rows,
        updates file paths, writes history and journal.
        """
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            return
        if plan.plan_kind != PlanKind.OBJECT_AMENDMENT:
            return
        if failed_count > 0:
            return

        summary: dict[str, Any] = {}
        if plan.summary_json:
            try:
                summary = json.loads(plan.summary_json)
            except json.JSONDecodeError:
                return
        if summary.get("plan_type") != PlanKind.OBJECT_AMENDMENT:
            return
        if summary.get("finalize_policy") != "all_or_nothing_object_amendment":
            return
        if summary.get("finalized"):
            return

        amendment_type = summary.get("amendment_type", "")
        object_id = summary.get("object_id")
        if not object_id:
            return

        actions = self.repository.list_plan_actions(session, plan_id)
        if not self._all_required_amendment_move_actions_succeeded(actions, amendment_type):
            return

        lo = session.query(LibraryObject).filter(LibraryObject.id == object_id).first()
        if lo is None:
            return

        now = _now()

        if amendment_type == "add_members":
            self._finalize_add_members(session, plan, actions, lo, now)
        elif amendment_type == "remove_members":
            self._finalize_remove_members(session, plan, actions, lo, now)

    def _finalize_add_members(
        self, session: Session, plan: OrganizePlan,
        actions: list[OrganizeAction], lo: LibraryObject, now: datetime,
    ) -> None:
        from app.db.models.library_object import LibraryObjectMember as LOM
        from app.repositories.importing.repository import ImportRepository
        import uuid as _uuid

        added = 0
        for a in actions:
            if a.action_type != "move" or a.status != "succeeded":
                continue
            payload: dict[str, Any] = {}
            if a.payload_json:
                try:
                    payload = json.loads(a.payload_json)
                except json.JSONDecodeError:
                    continue
            if payload.get("amendment_action") != "add_member":
                continue

            file_id = payload.get("file_id")
            role = payload.get("member_role", "unknown_child")
            rel_path = payload.get("member_relative_path", "")
            if not file_id or not role:
                continue

            file = session.query(File).filter(File.id == file_id).first()
            if file is None:
                continue
            if not a.target_path or not Path(a.target_path).exists():
                continue

            old_path = a.source_path or file.path
            new_path = a.target_path

            # Update file
            file.path = new_path
            file.name = Path(new_path).name
            file.parent_path = str(Path(new_path).parent)
            file.storage_state = "managed"
            if plan.target_library_root_id:
                file.managed_root_id = plan.target_library_root_id
            file.updated_at = now

            # Create active member
            member = LOM(
                object_id=lo.id, file_id=file_id,
                member_role=role, relative_path=rel_path,
                absolute_path=new_path,
                extension=Path(new_path).suffix.lstrip("."),
                member_status="active", created_at=now,
            )
            session.add(member)

            # Path history
            journal_id = self._append_path_sync_journal(
                session, a, "object_amendment_add", "file", file_id, old_path, new_path,
            )
            ImportRepository().append_path_history(
                session, file_id=file_id, old_path=old_path, new_path=new_path,
                reason="object_amendment_add_member", operation_journal_id=journal_id,
            )
            added += 1

        # Journal
        from app.repositories.importing.repository import ImportRepository as IR
        repo = IR()
        repo.append_journal_entry(
            session, operation_id=str(_uuid.uuid4()),
            operation_type="object_amendment_finalize",
            entity_type="organize_plan", entity_id=plan.id,
            status="succeeded",
            after_json=json.dumps({
                "amendment_type": "add_members", "object_id": lo.id,
                "added_count": added, "plan_id": plan.id,
            }),
        )

        # Update plan summary
        summary: dict[str, Any] = json.loads(plan.summary_json or "{}")
        summary["finalized"] = True
        summary["finalized_at"] = now.isoformat()
        summary["finalized_add_count"] = added
        plan.summary_json = json.dumps(summary, ensure_ascii=False)

    def _finalize_remove_members(
        self, session: Session, plan: OrganizePlan,
        actions: list[OrganizeAction], lo: LibraryObject, now: datetime,
    ) -> None:
        from app.db.models.library_object import LibraryObjectMember as LOM
        from app.repositories.importing.repository import ImportRepository
        import uuid as _uuid

        removed = 0
        for a in actions:
            if a.action_type != "move" or a.status != "succeeded":
                continue
            payload: dict[str, Any] = {}
            if a.payload_json:
                try:
                    payload = json.loads(a.payload_json)
                except json.JSONDecodeError:
                    continue
            if payload.get("amendment_action") != "remove_member":
                continue

            member_id = payload.get("member_id")
            file_id = payload.get("file_id")
            if not member_id or not file_id:
                continue

            member = session.query(LOM).filter(LOM.id == member_id).first()
            if member is None:
                continue
            if member.member_status != "active":
                continue
            if member.object_id != lo.id:
                continue

            file = session.query(File).filter(File.id == file_id).first()
            if file is None:
                continue
            if not a.target_path or not Path(a.target_path).exists():
                continue

            old_path = a.source_path or file.path
            new_path = a.target_path

            # Move file to loose area
            file.path = new_path
            file.name = Path(new_path).name
            file.parent_path = str(Path(new_path).parent)
            file.storage_state = "managed"
            file.updated_at = now

            # Soft-deactivate member
            member.member_status = "removed"

            # Path history
            journal_id = self._append_path_sync_journal(
                session, a, "object_amendment_remove", "file", file_id, old_path, new_path,
            )
            ImportRepository().append_path_history(
                session, file_id=file_id, old_path=old_path, new_path=new_path,
                reason="object_amendment_remove_member", operation_journal_id=journal_id,
            )
            removed += 1

        # Journal
        from app.repositories.importing.repository import ImportRepository as IR
        repo = IR()
        repo.append_journal_entry(
            session, operation_id=str(_uuid.uuid4()),
            operation_type="object_amendment_finalize",
            entity_type="organize_plan", entity_id=plan.id,
            status="succeeded",
            after_json=json.dumps({
                "amendment_type": "remove_members", "object_id": lo.id,
                "removed_count": removed, "plan_id": plan.id,
            }),
        )

        # Update plan summary
        summary: dict[str, Any] = json.loads(plan.summary_json or "{}")
        summary["finalized"] = True
        summary["finalized_at"] = now.isoformat()
        summary["finalized_remove_count"] = removed
        plan.summary_json = json.dumps(summary, ensure_ascii=False)

    # ── Phase 8C-4C: Managed compose finalization ─────────────

    def _finalize_managed_compose(
        self, session: Session, plan_id: int, failed_count: int,
    ) -> None:
        """After successful execute, finalize object creation for managed compose plans.

        Only runs when plan_kind == object_creation_managed_compose and all required
        move actions succeeded. Creates LibraryObject + LibraryObjectMember rows,
        updates file paths, writes history and journal.
        """
        plan = self.repository.get_plan(session, plan_id)
        if plan is None:
            return
        if plan.plan_kind != PlanKind.OBJECT_CREATION_MANAGED_COMPOSE:
            return
        if failed_count > 0:
            # completed_with_errors — do not create partial object
            return

        # Parse summary_json
        summary: dict[str, Any] = {}
        if plan.summary_json:
            try:
                summary = json.loads(plan.summary_json)
            except json.JSONDecodeError:
                return
        if summary.get("plan_type") != "object_creation":
            return
        if summary.get("finalize_policy") != "all_or_nothing_object_creation":
            return

        object_name = summary.get("object_name", "")
        object_type = summary.get("object_type", "")
        target_object_dir = summary.get("target_object_dir", "")
        if not object_name or not object_type or not target_object_dir:
            return

        # Verify all required move actions succeeded
        actions = self.repository.list_plan_actions(session, plan_id)
        created_file_ids: list[int] = []
        planned_members: list[dict[str, Any]] = []
        for a in actions:
            if a.action_type != "move":
                continue
            if a.status != "succeeded":
                # A required move failed or was skipped — do not finalize
                return
            payload: dict[str, Any] = {}
            if a.payload_json:
                try:
                    payload = json.loads(a.payload_json)
                except json.JSONDecodeError:
                    payload = {}
            if not payload.get("object_creation_plan"):
                continue
            fid = payload.get("file_id")
            role = payload.get("member_role", "unknown_child")
            rel = payload.get("selected_relative_path", "")
            if fid is None:
                return  # missing file_id — cannot finalize
            created_file_ids.append(fid)
            planned_members.append({
                "file_id": fid, "role": role, "relative_path": rel,
            })

        if not created_file_ids:
            return
        if len(created_file_ids) != len(summary.get("selected_file_ids", [])):
            return  # mismatch — abort

        type_prefix = OBJECT_PREFIX.get(object_type, "OBJ")

        now = _now()
        from pathlib import Path

        # Create LibraryObject
        lib_obj = LibraryObject(
            object_type=object_type,
            type_prefix=type_prefix,
            root_path=target_object_dir,
            root_name=Path(target_object_dir).name,
            title=object_name,
            filesystem_title=object_name,
            metadata_source="managed_compose",
            needs_review=False,
            last_scanned_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(lib_obj)

        # Create LibraryObjectMember for each moved file
        from app.db.models.library_object import LibraryObjectMember as LOM
        for pm in planned_members:
            fid = pm["file_id"]
            file = session.query(File).filter(File.id == fid).first()
            if file is None:
                continue
            # Update file paths (already moved by execute action)
            old_path = file.path
            move_action = next(
                (a for a in actions if a.action_type == "move" and a.status == "succeeded"
                 and a.payload_json and str(fid) in (a.payload_json or "")),
                None,
            )
            if move_action and move_action.target_path:
                new_path = move_action.target_path
                file.path = new_path
                file.name = Path(new_path).name
                file.parent_path = str(Path(new_path).parent)
            file.storage_state = "managed"
            if plan.target_library_root_id:
                file.managed_root_id = plan.target_library_root_id
            file.managed_at = now
            file.updated_at = now

            # Write path history
            if move_action and move_action.target_path:
                journal_id = self._append_path_sync_journal(
                    session, move_action, "managed_compose", "file", fid,
                    old_path, file.path,
                )
                from app.repositories.importing.repository import ImportRepository
                ImportRepository().append_path_history(
                    session, file_id=fid, old_path=old_path,
                    new_path=file.path, reason="managed_compose_finalize",
                    operation_journal_id=journal_id,
                )

            # Create member
            rel_path = pm["relative_path"]
            member = LOM(
                object_id=lib_obj.id,
                file_id=fid,
                member_role=pm["role"],
                relative_path=rel_path,
                absolute_path=file.path,
                extension=Path(file.path).suffix.lstrip(".") if file.path else "",
                member_status="active",
                created_at=now,
            )
            session.add(member)

        # Update summary_json with finalization info
        summary["finalized"] = True
        summary["library_object_id"] = lib_obj.id
        summary["finalized_at"] = now.isoformat()
        summary["finalized_member_count"] = len(planned_members)
        plan.summary_json = json.dumps(summary, ensure_ascii=False)
        plan.updated_at = now

        # Write operation journal
        from app.repositories.importing.repository import ImportRepository
        import uuid as _uuid
        repo = ImportRepository()
        repo.append_journal_entry(
            session,
            operation_id=str(_uuid.uuid4()),
            operation_type="managed_compose_finalize",
            entity_type="organize_plan",
            entity_id=plan.id,
            status="succeeded",
            after_json=json.dumps({
                "library_object_id": lib_obj.id,
                "object_type": object_type,
                "object_name": object_name,
                "member_count": len(planned_members),
                "file_ids": created_file_ids,
                "target_object_dir": target_object_dir,
            }),
        )

        self._log_event(
            session, plan.id, None, "managed_compose_finalized",
            f"Object creation finalized: library_object {lib_obj.id} "
            f"with {len(planned_members)} members.",
        )

    # ── Phase 8D-A2: Object Amendment Draft Plan ──────────────

    def create_amendment_plan(
        self,
        session: Session,
        *,
        object_id: int,
        add_file_ids: list[int],
        remove_member_ids: list[int],
        target_library_root_id: int | None = None,
        remove_target_policy: str = "managed_loose_area",
    ) -> dict[str, Any]:
        """Create a draft amendment plan for an existing library_object.

        Supports add-only and remove-only. Mixed deferred. No file move. No member mutation.
        """
        import re as _re

        # Validate: at least one add or remove, not both
        has_add = len(add_file_ids) > 0
        has_remove = len(remove_member_ids) > 0
        if not has_add and not has_remove:
            raise HTTPException(status_code=400, detail="At least one of add_file_ids or remove_member_ids is required.")
        if has_add and has_remove:
            raise HTTPException(status_code=400, detail="Mixed add+remove amendment plans are not supported in Phase 8D-A2.")

        amendment_type = "add_members" if has_add else "remove_members"

        # Validate object exists
        lo = session.query(LibraryObject).filter(LibraryObject.id == object_id).first()
        if lo is None:
            raise HTTPException(status_code=404, detail="Library object not found.")

        object_root = Path(lo.root_path)

        # Resolve target root
        base_root: Path
        if target_library_root_id is not None:
            lib_root = self.library_root_repository.get_by_id(session, target_library_root_id)
            if lib_root is None or not lib_root.is_enabled:
                raise HTTPException(status_code=400, detail="Target library root not found or disabled.")
            base_root = Path(lib_root.root_path).resolve()
        else:
            base_root = object_root.parent if object_root.parent != object_root else object_root
            for lib_root in self.library_root_repository.list_enabled(session):
                root_path = Path(lib_root.root_path).resolve()
                if is_path_within(object_root, root_path):
                    base_root = root_path
                    target_library_root_id = lib_root.id
                    break

        # Gather member file_ids
        member_file_ids: set[int] = set()
        from app.db.models.library_object import LibraryObjectMember as LOM
        lom_rows = session.query(LOM.file_id).filter(
            LOM.file_id.isnot(None), LOM.member_status == "active"
        ).all()
        member_file_ids.update(r[0] for r in lom_rows if r[0] is not None)

        from app.db.models.importing import ImportObjectMember as IOM, ImportObjectCandidate as IOC, InboxItem as II
        iom_rows = session.query(IOM.inbox_item_id).join(
            IOC, IOM.import_object_candidate_id == IOC.id
        ).filter(IOC.status.in_(["pending_review", "confirmed"])).all()
        iom_ii_ids = [r[0] for r in iom_rows if r[0] is not None]
        if iom_ii_ids:
            iom_fids = session.query(II.file_id).filter(II.id.in_(iom_ii_ids)).all()
            member_file_ids.update(r[0] for r in iom_fids if r[0] is not None)

        planned_actions: list[dict[str, Any]] = []
        now = _now()
        plan_title = f"Amendment: {lo.title or lo.root_name}"

        if has_add:
            # ── Add-only amendment ─────────────────────────
            files: list[File] = []
            for fid in add_file_ids:
                f = session.query(File).filter(File.id == fid).first()
                if f is None:
                    raise HTTPException(status_code=400, detail=f"File not found: {fid}")
                if f.storage_state != "managed":
                    raise HTTPException(status_code=400, detail=f"File {fid} must be managed, got {f.storage_state}")
                if fid in member_file_ids:
                    raise HTTPException(status_code=400, detail=f"File {fid} is already an object member.")
                if not Path(f.path).is_file():
                    raise HTTPException(status_code=400, detail=f"File {fid} source path does not exist on disk.")
                files.append(f)

            add_members_meta: list[dict[str, Any]] = []
            actions: list[OrganizeAction] = []
            order = 1
            for f in files:
                safe_name = _re.sub(r'[<>:"/\\|?*]', " ", f.name).strip()
                target_file = self._no_overwrite_target(object_root / safe_name)
                role = "unknown_child"
                if f.file_kind:
                    if f.file_kind == "image":
                        role = "image_member"
                    elif f.file_kind == "video":
                        role = "main_video"
                    elif f.file_kind in ("document", "ebook"):
                        role = "document_attachment"
                    elif f.file_kind in ("executable",):
                        role = "launch_exe"
                add_members_meta.append({"file_id": f.id, "role": role, "relative_path": safe_name})
                actions.append(OrganizeAction(
                    plan_id=0, action_order=order, action_type="move",
                    source_path=f.path, target_path=str(target_file),
                    payload_json=json.dumps({
                        "object_amendment_plan": True, "amendment_action": "add_member",
                        "object_id": object_id, "file_id": f.id,
                        "member_role": role, "member_relative_path": safe_name,
                    }, ensure_ascii=False),
                    status="draft", conflict_status="unchecked",
                    reason=f"Add managed loose file to object",
                    created_at=now, updated_at=now,
                ))
                planned_actions.append({
                    "action_type": "move", "source_path": f.path,
                    "target_path": str(target_file), "file_id": f.id,
                    "member_role": role, "amendment_action": "add_member",
                })
                order += 1

            plan = OrganizePlan(
                title=plan_title, status="draft", plan_kind=PlanKind.OBJECT_AMENDMENT,
                summary="Draft amendment plan to add members. No files have been moved.",
                summary_json=json.dumps({
                    "plan_type": PlanKind.OBJECT_AMENDMENT, "amendment_type": "add_members",
                    "object_id": object_id, "object_root_path": str(object_root),
                    "add_file_ids": add_file_ids, "remove_member_ids": [],
                    "planned_add_members": add_members_meta,
                    "finalize_policy": "all_or_nothing_object_amendment",
                    "mixed_amendment_allowed": False,
                }, ensure_ascii=False),
                target_library_root_id=target_library_root_id,
                created_at=now, updated_at=now,
            )
            self.repository.add_plan(session, plan)
            for a in actions:
                a.plan_id = plan.id
            self.repository.add_actions(session, actions)
            session.commit()
            return {
                "plan_id": plan.id, "plan_kind": plan.plan_kind,
                "object_id": object_id, "amendment_type": "add_members",
                "status": "draft", "add_count": len(files), "remove_count": 0,
                "planned_actions": planned_actions,
                "notes": ["Draft amendment plan only. No files were moved and object members were not changed."],
            }

        else:
            # ── Remove-only amendment ──────────────────────
            members: list[LOM] = []
            for mid in remove_member_ids:
                m = session.query(LOM).filter(LOM.id == mid).first()
                if m is None:
                    raise HTTPException(status_code=400, detail=f"Member not found: {mid}")
                if m.object_id != object_id:
                    raise HTTPException(status_code=400, detail=f"Member {mid} does not belong to object {object_id}")
                if m.member_status != "active":
                    raise HTTPException(status_code=400, detail=f"Member {mid} is not active (current: {m.member_status})")
                f = session.query(File).filter(File.id == m.file_id).first() if m.file_id else None
                if f is None:
                    raise HTTPException(status_code=400, detail=f"Member {mid} file not found.")
                if not Path(f.path).is_file():
                    raise HTTPException(status_code=400, detail=f"Member {mid} file does not exist on disk.")
                members.append(m)

            remove_target_dir = base_root / "90_Loose" / f"Removed_{lo.root_name}"
            if not is_path_within(remove_target_dir, base_root):
                raise HTTPException(status_code=400, detail="Remove target directory must stay inside the managed root.")
            remove_members_meta: list[dict[str, Any]] = []
            actions: list[OrganizeAction] = []
            order = 1
            actions.append(OrganizeAction(
                plan_id=0, action_order=order, action_type="mkdir",
                source_path=None, target_path=str(remove_target_dir),
                payload_json=json.dumps({
                    "object_amendment_plan": True,
                    "amendment_action": "remove_target_dir",
                    "object_id": object_id,
                    "remove_target_policy": remove_target_policy,
                }, ensure_ascii=False),
                status="draft", conflict_status="unchecked",
                reason="Create removed-member loose target directory",
                created_at=now, updated_at=now,
            ))
            planned_actions.append({
                "action_type": "mkdir", "source_path": None,
                "target_path": str(remove_target_dir),
                "amendment_action": "remove_target_dir",
            })
            order += 1
            for m in members:
                f = session.query(File).filter(File.id == m.file_id).first()
                safe_name = _re.sub(r'[<>:"/\\|?*]', " ", f.name).strip()
                target_file = self._no_overwrite_target(remove_target_dir / safe_name)
                remove_members_meta.append({
                    "member_id": m.id, "file_id": m.file_id,
                    "previous_role": m.member_role, "relative_path": safe_name,
                })
                actions.append(OrganizeAction(
                    plan_id=0, action_order=order, action_type="move",
                    source_path=f.path, target_path=str(target_file),
                    payload_json=json.dumps({
                        "object_amendment_plan": True, "amendment_action": "remove_member",
                        "object_id": object_id, "member_id": m.id,
                        "file_id": m.file_id or 0, "previous_member_role": m.member_role,
                        "remove_target_policy": remove_target_policy,
                    }, ensure_ascii=False),
                    status="draft", conflict_status="unchecked",
                    reason=f"Remove member from object",
                    created_at=now, updated_at=now,
                ))
                planned_actions.append({
                    "action_type": "move", "source_path": f.path,
                    "target_path": str(target_file), "file_id": m.file_id,
                    "amendment_action": "remove_member",
                })
                order += 1

            plan = OrganizePlan(
                title=plan_title, status="draft", plan_kind=PlanKind.OBJECT_AMENDMENT,
                summary="Draft amendment plan to remove members. No files have been moved.",
                summary_json=json.dumps({
                    "plan_type": PlanKind.OBJECT_AMENDMENT, "amendment_type": "remove_members",
                    "object_id": object_id, "object_root_path": str(object_root),
                    "add_file_ids": [], "remove_member_ids": remove_member_ids,
                    "planned_remove_members": remove_members_meta,
                    "remove_target_policy": remove_target_policy,
                    "remove_target_dir": str(remove_target_dir),
                    "finalize_policy": "all_or_nothing_object_amendment",
                    "mixed_amendment_allowed": False,
                }, ensure_ascii=False),
                target_library_root_id=target_library_root_id,
                created_at=now, updated_at=now,
            )
            self.repository.add_plan(session, plan)
            for a in actions:
                a.plan_id = plan.id
            self.repository.add_actions(session, actions)
            session.commit()
            return {
                "plan_id": plan.id, "plan_kind": plan.plan_kind,
                "object_id": object_id, "amendment_type": "remove_members",
                "status": "draft", "add_count": 0, "remove_count": len(members),
                "planned_actions": planned_actions,
                "notes": ["Draft amendment plan only. No files were moved and object members were not changed."],
            }

    @staticmethod
    def _no_overwrite_target(target: Path) -> Path:
        if not target.exists():
            return target
        stem, suffix = target.stem, target.suffix
        parent = target.parent
        counter = 1
        while (parent / f"{stem} ({counter}){suffix}").exists():
            counter += 1
        return parent / f"{stem} ({counter}){suffix}"


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
    if extension in {".bat", ".cmd", ".ps1", ".sh", ".py", ".rb", ".pl"}:
        return "software", "low", "Detected as script or executable file."
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



_now = utcnow
