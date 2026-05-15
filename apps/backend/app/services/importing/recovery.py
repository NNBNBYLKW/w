"""Recovery diagnostics — detect only, never auto-fix, delete, or move."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.db.models.importing import (
    ImportBatch,
    ImportObjectCandidate,
    ImportObjectMember,
    InboxItem,
    OperationJournal,
)
from app.db.models.library_root import LibraryRoot


@dataclass
class RecoveryFinding:
    finding_type: str
    severity: str  # info / warning / high
    entity_type: str
    entity_id: int | None
    path: str | None
    message: str
    suggested_action: str


@dataclass
class RecoverySummary:
    orphan_inbox_count: int = 0
    missing_inbox_count: int = 0
    missing_managed_count: int = 0
    failed_import_count: int = 0
    incomplete_batch_count: int = 0
    incomplete_journal_count: int = 0
    high_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)


class ImportRecoveryService:
    """Read-only recovery diagnostics. Never modifies files or DB state."""

    def scan(self, session: Session) -> RecoverySummary:
        summary = RecoverySummary()
        findings: list[RecoveryFinding] = []

        findings.extend(self._detect_orphan_inbox_files(session))
        findings.extend(self._detect_missing_inbox_copies(session))
        findings.extend(self._detect_missing_managed_files(session))
        findings.extend(self._detect_failed_imports(session))
        findings.extend(self._detect_incomplete_batches(session))
        findings.extend(self._detect_incomplete_journals(session))

        for f in findings:
            if f.finding_type == "orphan_inbox_file":
                summary.orphan_inbox_count += 1
            elif f.finding_type == "missing_inbox_copy":
                summary.missing_inbox_count += 1
            elif f.finding_type == "missing_managed_file":
                summary.missing_managed_count += 1
            elif f.finding_type == "failed_import_item":
                summary.failed_import_count += 1
            elif f.finding_type == "incomplete_import_batch":
                summary.incomplete_batch_count += 1
            elif f.finding_type == "incomplete_journal_operation":
                summary.incomplete_journal_count += 1

            if f.severity == "high":
                summary.high_count += 1
            elif f.severity == "warning":
                summary.warning_count += 1
            else:
                summary.info_count += 1

        summary.findings = [
            {
                "finding_type": f.finding_type,
                "severity": f.severity,
                "entity_type": f.entity_type,
                "entity_id": f.entity_id,
                "path": f.path,
                "message": f.message,
                "suggested_action": f.suggested_action,
            }
            for f in findings
        ]
        return summary

    # ── detectors ───────────────────────────────────────

    def _detect_orphan_inbox_files(self, session: Session) -> list[RecoveryFinding]:
        findings: list[RecoveryFinding] = []
        roots = session.query(LibraryRoot).filter(
            LibraryRoot.is_enabled == True
        ).all()

        known_paths: set[str] = set()
        for item in session.query(InboxItem.inbox_path).all():
            known_paths.add(item.inbox_path)
        for oc in session.query(ImportObjectCandidate.inbox_root_path).all():
            known_paths.add(oc.inbox_root_path)

        for root in roots:
            inbox_dir = Path(root.root_path) / "00_Inbox"
            if not inbox_dir.exists():
                continue
            for entry in inbox_dir.rglob("*"):
                if entry.is_file():
                    path_str = str(entry.resolve())
                    if path_str not in known_paths:
                        # check if it's not in any known path (exact match)
                        matched = any(
                            path_str == kp or path_str.startswith(kp)
                            for kp in known_paths
                        )
                        if not matched:
                            findings.append(RecoveryFinding(
                                finding_type="orphan_inbox_file",
                                severity="info",
                                entity_type="file",
                                entity_id=None,
                                path=path_str,
                                message=f"Orphan file in inbox without DB record: {entry.name}",
                                suggested_action="Review manually. Files can be imported as new inbox items or cleaned up later.",
                            ))
        return findings

    def _detect_missing_inbox_copies(self, session: Session) -> list[RecoveryFinding]:
        findings: list[RecoveryFinding] = []
        items = session.query(InboxItem).filter(
            InboxItem.status.in_(["imported", "pending_review", "classified", "planned"])
        ).all()
        for item in items:
            if item.inbox_path and not Path(item.inbox_path).exists():
                findings.append(RecoveryFinding(
                    finding_type="missing_inbox_copy",
                    severity="high",
                    entity_type="inbox_item",
                    entity_id=item.id,
                    path=item.inbox_path,
                    message=f"Inbox copy no longer exists: {item.inbox_path}",
                    suggested_action="Retry import if original source still exists, or reject the inbox item.",
                ))
        return findings

    def _detect_missing_managed_files(self, session: Session) -> list[RecoveryFinding]:
        findings: list[RecoveryFinding] = []
        managed = session.query(File).filter(
            File.storage_state == "managed"
        ).all()
        for f in managed:
            if not Path(f.path).exists():
                findings.append(RecoveryFinding(
                    finding_type="missing_managed_file",
                    severity="high",
                    entity_type="file",
                    entity_id=f.id,
                    path=f.path,
                    message=f"Managed file no longer exists on disk: {f.name}",
                    suggested_action="Locate the file manually or restore from backup. Recovery tools will be available in a future phase.",
                ))

        # check object candidate members
        obj_candidates = session.query(ImportObjectCandidate).filter(
            ImportObjectCandidate.status == "organized"
        ).all()
        for oc in obj_candidates:
            members = session.query(ImportObjectMember).filter(
                ImportObjectMember.import_object_candidate_id == oc.id
            ).all()
            for m in members:
                item = session.get(InboxItem, m.inbox_item_id)
                if item and item.file_id:
                    file = session.get(File, item.file_id)
                    if file and file.storage_state == "managed" and file.path:
                        if not Path(file.path).exists():
                            findings.append(RecoveryFinding(
                                finding_type="missing_managed_file",
                                severity="high",
                                entity_type="import_object_member",
                                entity_id=m.id,
                                path=file.path,
                                message=f"Managed file for object member missing: {file.name} (object #{oc.id})",
                                suggested_action="Locate manually or restore from backup.",
                            ))
        return findings

    def _detect_failed_imports(self, session: Session) -> list[RecoveryFinding]:
        findings: list[RecoveryFinding] = []
        items = session.query(InboxItem).filter(InboxItem.status == "failed").all()
        for item in items:
            findings.append(RecoveryFinding(
                finding_type="failed_import_item",
                severity="warning",
                entity_type="inbox_item",
                entity_id=item.id,
                path=item.source_path,
                message=f"Import failed: {item.error_message or 'unknown error'}",
                suggested_action="Retry import if the source file is available.",
            ))
        return findings

    def _detect_incomplete_batches(self, session: Session) -> list[RecoveryFinding]:
        findings: list[RecoveryFinding] = []
        batches = session.query(ImportBatch).filter(
            ImportBatch.status.in_(["created", "running"])
        ).all()
        for batch in batches:
            findings.append(RecoveryFinding(
                finding_type="incomplete_import_batch",
                severity="warning",
                entity_type="import_batch",
                entity_id=batch.id,
                path=None,
                message=f"Batch #{batch.id} is incomplete (status: {batch.status}).",
                suggested_action="Review batch items. Retry failed items or complete the batch.",
            ))
        return findings

    def _detect_incomplete_journals(self, session: Session) -> list[RecoveryFinding]:
        findings: list[RecoveryFinding] = []
        entries = session.query(OperationJournal).filter(
            OperationJournal.status.in_(["started", "running"]),
            OperationJournal.finished_at == None,
        ).all()
        for entry in entries:
            findings.append(RecoveryFinding(
                finding_type="incomplete_journal_operation",
                severity="warning",
                entity_type="operation_journal",
                entity_id=entry.id,
                path=None,
                message=f"Incomplete journal: {entry.operation_type} on {entry.entity_type}#{entry.entity_id}",
                suggested_action="Investigate the operation. May indicate an interrupted import or execute.",
            ))
        return findings


recovery_service = ImportRecoveryService()
