"""Recovery diagnostics — detect only, never auto-fix, delete, or move."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.db.models.importing import (
    ImportBatch,
    ImportObjectCandidate,
    ImportObjectMember,
    InboxItem,
    OperationJournal,
)
from app.db.models.library_object import LibraryObjectMember as LOM
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

    def scan(self, session: Session) -> tuple[RecoverySummary, str]:
        summary = RecoverySummary()
        findings: list[RecoveryFinding] = []
        scan_id = str(uuid.uuid4())

        findings.extend(self._detect_orphan_inbox_files(session))
        findings.extend(self._detect_missing_inbox_copies(session))
        findings.extend(self._detect_missing_managed_files(session))
        findings.extend(self._detect_failed_imports(session))
        findings.extend(self._detect_incomplete_batches(session))
        findings.extend(self._detect_incomplete_journals(session))
        findings.extend(self._detect_member_object_mismatches(session))

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

        # Persist findings for later retrieval
        for f in findings:
            session.execute(
                text(
                    "INSERT INTO recovery_findings (scan_id, finding_type, severity, entity_type, entity_id, path, message, suggested_action) "
                    "VALUES (:scan_id, :finding_type, :severity, :entity_type, :entity_id, :path, :message, :suggested_action)"
                ),
                {
                    "scan_id": scan_id,
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "entity_type": f.entity_type,
                    "entity_id": f.entity_id,
                    "path": f.path,
                    "message": f.message,
                    "suggested_action": f.suggested_action,
                },
            )
        session.commit()

        return summary, scan_id

    def get_latest_scan_id(self, session: Session) -> str | None:
        """Return the most recent scan_id from persisted findings, or None."""
        row = session.execute(
            text("SELECT scan_id FROM recovery_findings ORDER BY rowid DESC LIMIT 1")
        ).fetchone()
        return row[0] if row else None

    def get_latest_summary(self, session: Session) -> dict:
        """Return summary counts from the most recent persisted scan. Read-only — no scan triggered."""
        scan_id = self.get_latest_scan_id(session)
        if scan_id is None:
            return {
                "orphan_inbox_count": 0,
                "missing_inbox_count": 0,
                "missing_managed_count": 0,
                "failed_import_count": 0,
                "incomplete_batch_count": 0,
                "incomplete_journal_count": 0,
                "high_count": 0,
                "warning_count": 0,
                "info_count": 0,
                "stale": True,
                "hint": "No scan has been run yet. Use POST /recovery/scan to run a scan.",
            }
        rows = session.execute(
            text(
                "SELECT severity, COUNT(*) FROM recovery_findings "
                "WHERE scan_id = :scan_id GROUP BY severity"
            ),
            {"scan_id": scan_id},
        ).fetchall()
        severity_counts = {"high": 0, "warning": 0, "info": 0}
        for sev, cnt in rows:
            severity_counts[sev] = cnt

        type_counts = dict(
            session.execute(
                text(
                    "SELECT finding_type, COUNT(*) FROM recovery_findings "
                    "WHERE scan_id = :scan_id GROUP BY finding_type"
                ),
                {"scan_id": scan_id},
            ).fetchall()
        )

        return {
            "orphan_inbox_count": type_counts.get("orphan_inbox_file", 0),
            "missing_inbox_count": type_counts.get("missing_inbox_copy", 0),
            "missing_managed_count": type_counts.get("missing_managed_file", 0),
            "failed_import_count": type_counts.get("failed_import_item", 0),
            "incomplete_batch_count": type_counts.get("incomplete_import_batch", 0),
            "incomplete_journal_count": type_counts.get("incomplete_journal_operation", 0),
            "high_count": severity_counts["high"],
            "warning_count": severity_counts["warning"],
            "info_count": severity_counts["info"],
            "scan_id": scan_id,
            "stale": False,
        }

    def get_latest_findings(
        self,
        session: Session,
        severity: str | None = None,
        finding_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Return paginated findings from the most recent persisted scan. Read-only — no scan triggered."""
        scan_id = self.get_latest_scan_id(session)
        if scan_id is None:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "stale": True,
                "hint": "No scan has been run yet. Use POST /recovery/scan to run a scan.",
            }
        params: dict = {"scan_id": scan_id}
        where = ["scan_id = :scan_id"]
        if severity:
            where.append("severity = :severity")
            params["severity"] = severity
        if finding_type:
            where.append("finding_type = :finding_type")
            params["finding_type"] = finding_type
        where_clause = " AND ".join(where)

        total = session.execute(
            text(f"SELECT COUNT(*) FROM recovery_findings WHERE {where_clause}"),
            params,
        ).scalar() or 0

        offset = (page - 1) * page_size
        rows = session.execute(
            text(
                f"SELECT finding_type, severity, entity_type, entity_id, path, message, suggested_action "
                f"FROM recovery_findings WHERE {where_clause} "
                f"ORDER BY (CASE severity WHEN 'high' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END), rowid "
                f"LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": page_size, "offset": offset},
        ).fetchall()

        return {
            "items": [
                {
                    "finding_type": r[0],
                    "severity": r[1],
                    "entity_type": r[2],
                    "entity_id": r[3],
                    "path": r[4],
                    "message": r[5],
                    "suggested_action": r[6],
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "scan_id": scan_id,
            "stale": False,
        }

    def get_persisted_findings(
        self,
        session: Session,
        *,
        severity: str | None = None,
        scan_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Return paginated findings with optional severity and scan_id filters."""
        where: list[str] = []
        params: dict = {}
        if severity:
            where.append("severity = :severity")
            params["severity"] = severity
        if scan_id:
            where.append("scan_id = :scan_id")
            params["scan_id"] = scan_id
        where_clause = (" AND " + " AND ".join(where)) if where else ""
        total = session.execute(
            text(f"SELECT COUNT(*) FROM recovery_findings{where_clause}"), params
        ).scalar() or 0
        offset = (page - 1) * page_size
        rows = session.execute(
            text(
                f"SELECT scan_id, scanned_at, finding_type, severity, entity_type, entity_id, path, message, suggested_action "
                f"FROM recovery_findings{where_clause} ORDER BY scanned_at DESC LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": page_size, "offset": offset},
        ).fetchall()
        return {
            "items": [dict(r._mapping) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

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

    def _detect_member_object_mismatches(self, session: Session) -> list[RecoveryFinding]:
        """Check active members for path/object-root mismatches."""
        findings: list[RecoveryFinding] = []
        active_members = session.query(LOM).filter(LOM.member_status == "active").all()
        from app.db.models.library_object import LibraryObject

        for lom in active_members:
            lo = session.query(LibraryObject).filter(LibraryObject.id == lom.object_id).first()
            if lo is None:
                findings.append(RecoveryFinding(
                    finding_type="member_orphan_object",
                    severity="high",
                    entity_type="library_object_member",
                    entity_id=lom.id,
                    path=lom.absolute_path,
                    message=f"Member #{lom.id} references missing object #{lom.object_id}",
                    suggested_action="Remove the orphaned member record.",
                ))
                continue

            if lom.absolute_path and lo.root_path:
                obj_root = Path(lo.root_path)
                member_path = Path(lom.absolute_path)
                try:
                    member_path.resolve().relative_to(obj_root.resolve())
                except ValueError:
                    findings.append(RecoveryFinding(
                        finding_type="member_outside_object_root",
                        severity="warning",
                        entity_type="library_object_member",
                        entity_id=lom.id,
                        path=lom.absolute_path,
                        message=f"Member #{lom.id} path is outside object #{lo.id} root",
                        suggested_action="Re-run amendment or manually move the file.",
                    ))

            if lom.file_id:
                f = session.query(File).filter(File.id == lom.file_id).first()
                if f is None:
                    findings.append(RecoveryFinding(
                        finding_type="member_missing_file_record",
                        severity="warning",
                        entity_type="library_object_member",
                        entity_id=lom.id,
                        path=lom.absolute_path,
                        message=f"Member #{lom.id} references missing file #{lom.file_id}",
                        suggested_action="Remove the member if the file no longer exists.",
                    ))
                elif f.storage_state != "managed":
                    findings.append(RecoveryFinding(
                        finding_type="member_file_not_managed",
                        severity="warning",
                        entity_type="library_object_member",
                        entity_id=lom.id,
                        path=f.path,
                        message=f"Member #{lom.id} file has storage_state={f.storage_state}, expected managed",
                        suggested_action="Verify the file was properly organized.",
                    ))

        return findings


recovery_service = ImportRecoveryService()
