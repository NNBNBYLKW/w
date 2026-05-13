from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.db.models.library_object import LibraryObject, LibraryObjectMember
from app.db.models.organize import (
    OrganizeAction,
    OrganizeActionLog,
    OrganizeCandidate,
    OrganizePlan,
    OrganizePlanCandidate,
    OrganizeSuggestion,
)


@dataclass(frozen=True)
class CandidateFilters:
    page: int
    page_size: int
    candidate_type: str | None = None
    status: str | None = None
    detected_type: str | None = None
    confidence: str | None = None
    query: str | None = None


@dataclass(frozen=True)
class PlanFilters:
    page: int
    page_size: int
    status: str | None = None
    plan_kind: str | None = None
    query: str | None = None


class LibraryOrganizeRepository:
    def get_candidate(self, session: Session, candidate_id: int) -> OrganizeCandidate | None:
        return session.get(OrganizeCandidate, candidate_id)

    def get_plan(self, session: Session, plan_id: int) -> OrganizePlan | None:
        return session.get(OrganizePlan, plan_id)

    def get_action(self, session: Session, action_id: int) -> OrganizeAction | None:
        return session.get(OrganizeAction, action_id)

    def get_suggestion(self, session: Session, suggestion_id: int) -> OrganizeSuggestion | None:
        return session.get(OrganizeSuggestion, suggestion_id)

    def add_suggestion(self, session: Session, suggestion: OrganizeSuggestion) -> OrganizeSuggestion:
        session.add(suggestion)
        session.flush()
        return suggestion

    def list_candidate_suggestions(self, session: Session, candidate_id: int) -> list[OrganizeSuggestion]:
        return list(
            session.scalars(
                select(OrganizeSuggestion)
                .where(OrganizeSuggestion.candidate_id == candidate_id)
                .order_by(OrganizeSuggestion.created_at.desc(), OrganizeSuggestion.id.desc())
            )
        )

    def find_pending_suggestion(
        self,
        session: Session,
        *,
        candidate_id: int,
        suggestion_type: str,
        provider: str = "rule_based",
    ) -> OrganizeSuggestion | None:
        return session.scalar(
            select(OrganizeSuggestion).where(
                OrganizeSuggestion.candidate_id == candidate_id,
                OrganizeSuggestion.suggestion_type == suggestion_type,
                OrganizeSuggestion.provider == provider,
                OrganizeSuggestion.status == "pending",
            )
        )

    def find_candidate(
        self,
        session: Session,
        *,
        source_kind: str,
        source_file_id: int | None,
        source_object_id: int | None,
        candidate_type: str,
        source_path: str,
    ) -> OrganizeCandidate | None:
        statement = select(OrganizeCandidate).where(
            OrganizeCandidate.source_kind == source_kind,
            OrganizeCandidate.candidate_type == candidate_type,
            OrganizeCandidate.source_path == source_path,
        )
        if source_file_id is None:
            statement = statement.where(OrganizeCandidate.source_file_id.is_(None))
        else:
            statement = statement.where(OrganizeCandidate.source_file_id == source_file_id)
        if source_object_id is None:
            statement = statement.where(OrganizeCandidate.source_object_id.is_(None))
        else:
            statement = statement.where(OrganizeCandidate.source_object_id == source_object_id)
        return session.scalar(statement)

    def add_candidate(self, session: Session, candidate: OrganizeCandidate) -> OrganizeCandidate:
        session.add(candidate)
        session.flush()
        return candidate

    def list_candidate_sources(self, session: Session) -> tuple[list[LibraryObject], list[File], set[str]]:
        objects = list(
            session.scalars(
                select(LibraryObject).where(
                    or_(
                        LibraryObject.needs_review.is_(True),
                        LibraryObject.object_type == "unknown_object",
                        LibraryObject.metadata_source == "invalid_asset_yaml",
                    )
                )
            )
        )
        member_paths = {
            str(path)
            for path in session.scalars(select(LibraryObjectMember.absolute_path)).all()
            if path is not None
        }
        files = list(
            session.scalars(
                select(File)
                .where(File.is_deleted.is_(False))
                .order_by(File.updated_at.desc(), File.id.desc())
            )
        )
        return objects, files, member_paths

    def list_candidates(self, session: Session, filters: CandidateFilters) -> tuple[list[OrganizeCandidate], int]:
        statement = select(OrganizeCandidate)
        count_statement = select(func.count(OrganizeCandidate.id))
        for builder in (statement, count_statement):
            pass
        statement = self._apply_candidate_filters(statement, filters)
        count_statement = self._apply_candidate_filters(count_statement, filters)
        total = int(session.scalar(count_statement) or 0)
        offset = max(filters.page - 1, 0) * filters.page_size
        items = list(
            session.scalars(
                statement.order_by(OrganizeCandidate.updated_at.desc(), OrganizeCandidate.id.desc())
                .offset(offset)
                .limit(filters.page_size)
            )
        )
        return items, total

    def add_plan(self, session: Session, plan: OrganizePlan) -> OrganizePlan:
        session.add(plan)
        session.flush()
        return plan

    def add_plan_candidate(self, session: Session, plan_id: int, candidate_id: int) -> None:
        session.add(OrganizePlanCandidate(plan_id=plan_id, candidate_id=candidate_id))

    def add_actions(self, session: Session, actions: list[OrganizeAction]) -> None:
        session.add_all(actions)
        session.flush()

    def add_log(self, session: Session, log: OrganizeActionLog) -> OrganizeActionLog:
        session.add(log)
        session.flush()
        return log

    def list_plans(self, session: Session, filters: PlanFilters) -> tuple[list[OrganizePlan], int]:
        statement = select(OrganizePlan)
        count_statement = select(func.count(OrganizePlan.id))
        statement = self._apply_plan_filters(statement, filters)
        count_statement = self._apply_plan_filters(count_statement, filters)
        total = int(session.scalar(count_statement) or 0)
        offset = max(filters.page - 1, 0) * filters.page_size
        items = list(
            session.scalars(
                statement.order_by(OrganizePlan.updated_at.desc(), OrganizePlan.id.desc())
                .offset(offset)
                .limit(filters.page_size)
            )
        )
        return items, total

    def list_plan_actions(self, session: Session, plan_id: int) -> list[OrganizeAction]:
        return list(
            session.scalars(
                select(OrganizeAction)
                .where(OrganizeAction.plan_id == plan_id)
                .order_by(OrganizeAction.action_order.asc(), OrganizeAction.id.asc())
            )
        )

    def list_plan_logs(self, session: Session, plan_id: int, *, limit: int = 200) -> list[OrganizeActionLog]:
        return list(
            session.scalars(
                select(OrganizeActionLog)
                .where(OrganizeActionLog.plan_id == plan_id)
                .order_by(OrganizeActionLog.created_at.asc(), OrganizeActionLog.id.asc())
                .limit(limit)
            )
        )

    def list_plan_candidates(self, session: Session, plan_id: int) -> list[OrganizeCandidate]:
        return list(
            session.scalars(
                select(OrganizeCandidate)
                .join(OrganizePlanCandidate, OrganizePlanCandidate.candidate_id == OrganizeCandidate.id)
                .where(OrganizePlanCandidate.plan_id == plan_id)
                .order_by(OrganizeCandidate.id.asc())
            )
        )

    def action_counts(self, session: Session, plan_ids: list[int]) -> dict[int, dict[str, int]]:
        if not plan_ids:
            return {}
        rows = session.execute(
            select(
                OrganizeAction.plan_id,
                OrganizeAction.conflict_status,
                OrganizeAction.status,
                func.count(OrganizeAction.id),
            )
            .where(OrganizeAction.plan_id.in_(plan_ids))
            .group_by(OrganizeAction.plan_id, OrganizeAction.conflict_status, OrganizeAction.status)
        ).all()
        counts: dict[int, dict[str, int]] = {
            plan_id: {"total": 0, "blocked": 0, "warning": 0, "failed": 0, "skipped": 0} for plan_id in plan_ids
        }
        for plan_id, conflict_status, status, count in rows:
            bucket = counts[int(plan_id)]
            bucket["total"] += int(count)
            if conflict_status in {"blocked", "stale"}:
                bucket["blocked"] += int(count)
            elif conflict_status == "warning":
                bucket["warning"] += int(count)
            if status == "failed":
                bucket["failed"] += int(count)
            elif status == "skipped":
                bucket["skipped"] += int(count)
        return counts

    def organize_stats(self, session: Session) -> dict[str, int]:
        return {
            "pending_candidates": int(
                session.scalar(select(func.count(OrganizeCandidate.id)).where(OrganizeCandidate.status == "pending")) or 0
            ),
            "draft_plans": int(session.scalar(select(func.count(OrganizePlan.id)).where(OrganizePlan.status == "draft")) or 0),
            "ready_plans": int(session.scalar(select(func.count(OrganizePlan.id)).where(OrganizePlan.status == "ready")) or 0),
            "blocked_actions": int(
                session.scalar(
                    select(func.count(OrganizeAction.id)).where(OrganizeAction.conflict_status.in_(["blocked", "stale"]))
                )
                or 0
            ),
        }

    def _apply_candidate_filters(self, statement, filters: CandidateFilters):
        if filters.candidate_type:
            statement = statement.where(OrganizeCandidate.candidate_type == filters.candidate_type)
        if filters.status:
            statement = statement.where(OrganizeCandidate.status == filters.status)
        if filters.detected_type:
            statement = statement.where(OrganizeCandidate.detected_type == filters.detected_type)
        if filters.confidence:
            statement = statement.where(OrganizeCandidate.confidence == filters.confidence)
        if filters.query:
            pattern = f"%{filters.query.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(OrganizeCandidate.display_name).like(pattern),
                    func.lower(OrganizeCandidate.source_path).like(pattern),
                    func.lower(OrganizeCandidate.reason).like(pattern),
                )
            )
        return statement

    def _apply_plan_filters(self, statement, filters: PlanFilters):
        if filters.status:
            statement = statement.where(OrganizePlan.status == filters.status)
        if filters.plan_kind:
            statement = statement.where(OrganizePlan.plan_kind == filters.plan_kind)
        if filters.query:
            pattern = f"%{filters.query.lower()}%"
            statement = statement.where(
                or_(func.lower(OrganizePlan.title).like(pattern), func.lower(OrganizePlan.summary).like(pattern))
            )
        return statement
