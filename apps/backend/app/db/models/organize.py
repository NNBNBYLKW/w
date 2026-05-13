from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class OrganizeCandidate(Base):
    __tablename__ = "organize_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_type: Mapped[str] = mapped_column(String, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    source_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    source_object_id: Mapped[int | None] = mapped_column(ForeignKey("library_objects.id", ondelete="SET NULL"), nullable=True)
    source_path: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    detected_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    ignored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class OrganizePlan(Base):
    __tablename__ = "organize_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    plan_kind: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    execution_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    execution_finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    execution_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_library_root_id: Mapped[int | None] = mapped_column(ForeignKey("library_roots.id"), nullable=True)
    reconcile_status: Mapped[str] = mapped_column(String, default="not_required", nullable=False)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reconcile_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_plan_id: Mapped[int | None] = mapped_column(ForeignKey("organize_plans.id"), nullable=True)
    plan_origin: Mapped[str] = mapped_column(String, default="generated_from_candidates", nullable=False)
    template_key: Mapped[str | None] = mapped_column(String, nullable=True)


class OrganizeAction(Base):
    __tablename__ = "organize_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("organize_plans.id", ondelete="CASCADE"), nullable=False)
    action_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    source_path: Mapped[str | None] = mapped_column(String, nullable=True)
    target_path: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    conflict_status: Mapped[str] = mapped_column(String, nullable=False)
    conflict_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_path: Mapped[str | None] = mapped_column(String, nullable=True)
    after_path: Mapped[str | None] = mapped_column(String, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reconcile_status: Mapped[str] = mapped_column(String, default="not_checked", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class OrganizePlanCandidate(Base):
    __tablename__ = "organize_plan_candidates"

    plan_id: Mapped[int] = mapped_column(ForeignKey("organize_plans.id", ondelete="CASCADE"), primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("organize_candidates.id", ondelete="CASCADE"), primary_key=True)


class OrganizeActionLog(Base):
    __tablename__ = "organize_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("organize_plans.id", ondelete="CASCADE"), nullable=False)
    action_id: Mapped[int | None] = mapped_column(ForeignKey("organize_actions.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    path_before: Mapped[str | None] = mapped_column(String, nullable=True)
    path_after: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class OrganizeSuggestion(Base):
    __tablename__ = "organize_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int | None] = mapped_column(ForeignKey("organize_candidates.id", ondelete="SET NULL"), nullable=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("organize_plans.id", ondelete="SET NULL"), nullable=True)
    action_id: Mapped[int | None] = mapped_column(ForeignKey("organize_actions.id", ondelete="SET NULL"), nullable=True)
    suggestion_type: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String, default="rule_based", nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
