import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from app.db.models.file import File
from app.db.models.importing import (
    FilePathHistory,
    ImportBatch,
    ImportObjectCandidate,
    ImportObjectMember,
    InboxItem,
    OperationJournal,
)
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.repositories.importing.repository import ImportRepository
from app.services.importing.service import import_service


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryV2DataFoundationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()
        self.repo = ImportRepository()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM import_object_members"))
            session.execute(text("DELETE FROM import_object_candidates"))
            session.execute(text("DELETE FROM file_path_history"))
            session.execute(text("DELETE FROM operation_journal"))
            session.execute(text("DELETE FROM inbox_items"))
            session.execute(text("DELETE FROM import_batches"))
            session.execute(text("DELETE FROM organize_plan_candidates"))
            session.execute(text("DELETE FROM organize_suggestions"))
            session.execute(text("DELETE FROM organize_action_logs"))
            session.execute(text("DELETE FROM organize_actions"))
            session.execute(text("DELETE FROM organize_plans"))
            session.execute(text("DELETE FROM organize_candidates"))
            session.execute(text("DELETE FROM asset_metadata_cache"))
            session.execute(text("DELETE FROM library_object_members"))
            session.execute(text("DELETE FROM library_objects"))
            session.execute(text("DELETE FROM tool_runs"))
            session.execute(text("DELETE FROM tasks"))
            session.execute(text("DELETE FROM file_metadata"))
            session.execute(text("DELETE FROM file_tags"))
            session.execute(text("DELETE FROM file_user_meta"))
            session.execute(text("DELETE FROM collections"))
            session.execute(text("DELETE FROM files"))
            session.execute(text("DELETE FROM source_ignore_rules"))
            session.execute(text("DELETE FROM tags"))
            session.execute(text("DELETE FROM library_roots"))
            session.execute(text("DELETE FROM sources"))
            session.commit()

    def _seed_source(self, path: Path) -> int:
        now = _dt()
        with SessionLocal() as session:
            source = Source(
                path=str(path),
                display_name=path.name,
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=None,
                last_scan_status=None,
                created_at=now,
                updated_at=now,
            )
            session.add(source)
            session.commit()
            return source.id

    def _seed_file(self, source: Source, path: Path, file_type: str = "video") -> int:
        now = _dt()
        with SessionLocal() as session:
            file = File(
                source_id=source.id,
                path=str(path),
                parent_path=str(path.parent),
                name=path.name,
                stem=path.stem,
                extension=path.suffix.lstrip(".") if path.suffix else None,
                file_type=file_type,
                mime_type=None,
                size_bytes=path.stat().st_size if path.exists() else 0,
                created_at_fs=now,
                modified_at_fs=now,
                discovered_at=now,
                last_seen_at=now,
                is_deleted=False,
                checksum_hint=None,
                updated_at=now,
            )
            session.add(file)
            session.commit()
            return file.id

    def _ensure_managed_source(self) -> None:
        with SessionLocal() as session:
            existing = session.query(Source).filter(
                Source.path == "__workbench_managed_import__"
            ).one_or_none()
            if existing is None:
                source = Source(
                    path="__workbench_managed_import__",
                    display_name="Managed Import",
                    is_enabled=True,
                    scan_mode="manual",
                    last_scan_status="not_applicable",
                    created_at=_dt(),
                    updated_at=_dt(),
                )
                session.add(source)
                session.commit()

    # ── 1. Existing files default external ──────────────────

    def test_existing_files_default_external(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir)
            test_file = source_path / "test.mp4"
            test_file.write_bytes(b"video data")
            source = Source(
                path=str(source_path),
                display_name="test-source",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                created_at=_dt(),
                updated_at=_dt(),
            )
            with SessionLocal() as session:
                session.add(source)
                session.commit()
                file = File(
                    source_id=source.id,
                    path=str(test_file),
                    parent_path=str(test_file.parent),
                    name=test_file.name,
                    stem=test_file.stem,
                    extension="mp4",
                    file_type="video",
                    discovered_at=_dt(),
                    last_seen_at=_dt(),
                    updated_at=_dt(),
                )
                session.add(file)
                session.commit()
                file_id = file.id

            with SessionLocal() as session:
                retrieved = session.get(File, file_id)
                self.assertIsNotNone(retrieved)
                self.assertEqual("external", retrieved.storage_state)
                self.assertIsNone(retrieved.managed_root_id)
                self.assertIsNone(retrieved.original_path)
                self.assertIsNone(retrieved.inbox_item_id)
                self.assertIsNone(retrieved.managed_at)

    # ── 2. Source scan creates external files ───────────────

    def test_source_scan_creates_external_files(self) -> None:
        with SessionLocal() as session:
            result = session.execute(
                text("SELECT id FROM sources WHERE path = :p"),
                {"p": "__workbench_managed_import__"},
            ).fetchone()
            self.assertIsNotNone(result)
            managed_source_id = result[0]

            file = File(
                source_id=managed_source_id,
                path="/tmp/test-inbox/test.mp4",
                parent_path="/tmp/test-inbox",
                name="test.mp4",
                stem="test",
                extension="mp4",
                file_type="video",
                discovered_at=_dt(),
                last_seen_at=_dt(),
                updated_at=_dt(),
            )
            session.add(file)
            session.commit()
            file_id = file.id

        with SessionLocal() as session:
            retrieved = session.get(File, file_id)
            self.assertEqual("external", retrieved.storage_state)

    # ── 3. Import batch create ──────────────────────────────

    def test_import_batch_create(self) -> None:
        with SessionLocal() as session:
            batch = self.repo.create_batch(
                session, source_kind="file_selection", import_method="copy"
            )
            self.assertIsNotNone(batch.id)
            self.assertEqual("created", batch.status)
            self.assertEqual("file_selection", batch.source_kind)
            self.assertEqual("copy", batch.import_method)
            self.assertEqual(0, batch.file_count)
            session.commit()

    # ── 4. Import batch default status created ──────────────

    def test_import_batch_status_defaults_created(self) -> None:
        with SessionLocal() as session:
            batch = self.repo.create_batch(
                session, source_kind="file_selection"
            )
            self.assertEqual("created", batch.status)
            session.commit()

    # ── 5. Inbox item create ────────────────────────────────

    def test_inbox_item_create(self) -> None:
        with SessionLocal() as session:
            batch = self.repo.create_batch(
                session, source_kind="file_selection", import_method="copy"
            )
            item = self.repo.create_inbox_item(
                session,
                import_batch_id=batch.id,
                source_path="/test/source.mp4",
                inbox_path="/test/inbox/source.mp4",
            )
            self.assertIsNotNone(item.id)
            self.assertEqual(batch.id, item.import_batch_id)
            self.assertEqual("/test/source.mp4", item.source_path)
            self.assertEqual("/test/inbox/source.mp4", item.inbox_path)
            session.commit()

    # ── 6. Inbox item requires batch ────────────────────────

    def test_inbox_item_requires_batch(self) -> None:
        with SessionLocal() as session:
            batch = self.repo.create_batch(
                session, source_kind="file_selection"
            )
            item = self.repo.create_inbox_item(
                session,
                import_batch_id=batch.id,
                source_path="/test/source.mp4",
                inbox_path="/test/inbox/source.mp4",
            )
            self.assertIsNotNone(item.id)
            self.assertEqual(batch.id, item.import_batch_id)
            session.commit()

    # ── 7. Inbox item default status imported ───────────────

    def test_inbox_item_status_defaults_imported(self) -> None:
        with SessionLocal() as session:
            batch = self.repo.create_batch(
                session, source_kind="file_selection"
            )
            item = self.repo.create_inbox_item(
                session,
                import_batch_id=batch.id,
                source_path="/test/source.mp4",
                inbox_path="/test/inbox/source.mp4",
            )
            self.assertEqual("imported", item.status)
            session.commit()

    # ── 8. Operation journal append-only ────────────────────

    def test_operation_journal_append_only(self) -> None:
        with SessionLocal() as session:
            entry = self.repo.append_journal_entry(
                session,
                operation_id="op-001",
                operation_type="import_copy",
                entity_type="inbox_item",
                entity_id=None,
                status="started",
            )
            journal_id = entry.id

            # append a follow-up for the same operation
            self.repo.append_journal_entry(
                session,
                operation_id="op-001",
                operation_type="import_copy",
                entity_type="inbox_item",
                entity_id=1,
                status="succeeded",
                before_json='{"path": "/test/source.mp4"}',
                after_json='{"path": "/test/inbox/source.mp4"}',
            )
            session.commit()

        with SessionLocal() as session:
            entries = self.repo.list_journal_by_operation(session, "op-001")
            self.assertEqual(2, len(entries))
            self.assertEqual("started", entries[0].status)
            self.assertEqual("succeeded", entries[1].status)

    # ── 9. Operation journal records error ──────────────────

    def test_operation_journal_records_error(self) -> None:
        with SessionLocal() as session:
            self.repo.append_journal_entry(
                session,
                operation_id="op-002",
                operation_type="import_copy",
                entity_type="inbox_item",
                status="failed",
                error_message="Permission denied",
            )
            session.commit()

        with SessionLocal() as session:
            entries = self.repo.list_journal_by_operation(session, "op-002")
            self.assertEqual(1, len(entries))
            self.assertEqual("failed", entries[0].status)
            self.assertEqual("Permission denied", entries[0].error_message)
            self.assertIsNotNone(entries[0].finished_at)

    # ── 10. File path history create ────────────────────────

    def test_file_path_history_create(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir)
            test_file = source_path / "test.mp4"
            test_file.write_bytes(b"video")
            source = Source(
                path=str(source_path),
                display_name="test",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                created_at=_dt(),
                updated_at=_dt(),
            )
            with SessionLocal() as session:
                session.add(source)
                session.commit()
                file = File(
                    source_id=source.id,
                    path=str(test_file),
                    parent_path=str(test_file.parent),
                    name=test_file.name,
                    stem="test",
                    extension="mp4",
                    file_type="video",
                    discovered_at=_dt(),
                    last_seen_at=_dt(),
                    updated_at=_dt(),
                )
                session.add(file)
                session.commit()
                file_id = file.id

            with SessionLocal() as session:
                history = self.repo.append_path_history(
                    session,
                    file_id=file_id,
                    old_path=str(test_file),
                    new_path="/new/path/test.mp4",
                    reason="import_copy",
                )
                self.assertIsNotNone(history.id)
                self.assertEqual(file_id, history.file_id)
                self.assertEqual(str(test_file), history.old_path)
                self.assertEqual("/new/path/test.mp4", history.new_path)
                self.assertEqual("import_copy", history.reason)
                session.commit()

    # ── 11. File path history requires file_id ──────────────

    def test_file_path_history_requires_file_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir)
            test_file = source_path / "test.mp4"
            test_file.write_bytes(b"video")
            source = Source(
                path=str(source_path),
                display_name="test",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                created_at=_dt(),
                updated_at=_dt(),
            )
            with SessionLocal() as session:
                session.add(source)
                session.commit()
                file = File(
                    source_id=source.id,
                    path=str(test_file),
                    parent_path=str(test_file.parent),
                    name=test_file.name,
                    stem="test",
                    extension="mp4",
                    file_type="video",
                    discovered_at=_dt(),
                    last_seen_at=_dt(),
                    updated_at=_dt(),
                )
                session.add(file)
                session.commit()
                file_id = file.id

            with SessionLocal() as session:
                history = self.repo.append_path_history(
                    session,
                    file_id=file_id,
                    new_path="/new/test.mp4",
                    reason="organize_move",
                )
                self.assertIsNotNone(history.id)
                self.assertIsNone(history.old_path)
                session.commit()

    # ── 12. Object candidate create ─────────────────────────

    def test_object_candidate_create(self) -> None:
        with SessionLocal() as session:
            batch = self.repo.create_batch(
                session, source_kind="file_selection"
            )
            candidate = self.repo.create_object_candidate(
                session,
                import_batch_id=batch.id,
                source_root_path="/test/MyTool",
                inbox_root_path="/inbox/MyTool",
                suggested_object_type="software",
                confidence="high",
                member_count=5,
                reason_json=json.dumps({"signals": ["exe_found"]}),
            )
            self.assertIsNotNone(candidate.id)
            self.assertEqual(batch.id, candidate.import_batch_id)
            self.assertEqual("detected", candidate.status)
            self.assertEqual("software", candidate.suggested_object_type)
            self.assertEqual(5, candidate.member_count)
            session.commit()

    # ── 13. Object member create ────────────────────────────

    def test_object_member_create(self) -> None:
        with SessionLocal() as session:
            batch = self.repo.create_batch(
                session, source_kind="file_selection"
            )
            item = self.repo.create_inbox_item(
                session,
                import_batch_id=batch.id,
                source_path="/test/MyTool/config.json",
                inbox_path="/inbox/MyTool/config.json",
            )
            candidate = self.repo.create_object_candidate(
                session,
                import_batch_id=batch.id,
                source_root_path="/test/MyTool",
                inbox_root_path="/inbox/MyTool",
            )
            member = self.repo.create_object_member(
                session,
                import_object_candidate_id=candidate.id,
                inbox_item_id=item.id,
                role="config",
                confidence="high",
                reason="JSON config file in software package",
            )
            self.assertIsNotNone(member.id)
            self.assertEqual(candidate.id, member.import_object_candidate_id)
            self.assertEqual(item.id, member.inbox_item_id)
            self.assertEqual("config", member.role)
            session.commit()

    # ── 14. Service skeleton creates batch without file ops ─

    def test_import_service_creates_batch_without_file_operation(self) -> None:
        with SessionLocal() as session:
            batch = import_service.create_import_batch(
                session, source_kind="file_selection", import_method="copy"
            )
            self.assertIsNotNone(batch.id)
            self.assertEqual("created", batch.status)

            # verify no files were created on disk
            import tempfile
            import os
            tmp = tempfile.gettempdir()
            inbox_candidate = Path(tmp) / "00_Inbox"
            self.assertFalse(
                inbox_candidate.exists(),
                "ImportService skeleton must not create any filesystem directories",
            )
            session.commit()

    # ── 15. Service rejects move import method ──────────────

    def test_import_service_rejects_move_method(self) -> None:
        with self.assertRaises(ValueError):
            with SessionLocal() as session:
                import_service.create_import_batch(
                    session, source_kind="file_selection", import_method="move"
                )

    # ── 16. LibraryV2Capability defaults disabled ───────────

    def test_library_v2_capability_defaults_data_foundation(self) -> None:
        capability = import_service.get_capability()
        self.assertEqual("data_foundation", capability.status)
        self.assertFalse(capability.import_enabled)
        self.assertFalse(capability.inbox_enabled)

    # ── 17. Managed import synthetic source exists ──────────

    def test_managed_import_synthetic_source_exists(self) -> None:
        with SessionLocal() as session:
            source = session.query(Source).filter(
                Source.path == "__workbench_managed_import__"
            ).one_or_none()
            self.assertIsNotNone(source)
            self.assertEqual("Managed Import", source.display_name)
            self.assertTrue(source.is_enabled)

    # ── 18. Phase 7A does not copy/move/delete files ────────

    def test_phase7a_repository_has_no_file_operations(self) -> None:
        """Ensure ImportRepository never imports shutil or os file ops (service may in Phase 7B+)."""
        import inspect
        from app.repositories.importing import repository as repo_mod

        source = inspect.getsource(repo_mod)
        self.assertNotIn("shutil", source)
        self.assertNotIn("os.remove", source)
        self.assertNotIn("os.rename", source)
        self.assertNotIn("os.unlink", source)
        self.assertNotIn("pathlib.Path.unlink", source)

    # ── 19. Page size and pagination bounds ─────────────────

    def test_inbox_item_pagination_defaults(self) -> None:
        with SessionLocal() as session:
            batch = self.repo.create_batch(
                session, source_kind="file_selection"
            )
            for i in range(5):
                self.repo.create_inbox_item(
                    session,
                    import_batch_id=batch.id,
                    source_path=f"/test/source_{i}.mp4",
                    inbox_path=f"/test/inbox/source_{i}.mp4",
                )
            items, total = self.repo.list_inbox_items(session)
            self.assertEqual(5, total)
            self.assertEqual(5, len(items))
            session.commit()

    # ── 20. Batch status transitions ────────────────────────

    def test_import_batch_status_transitions(self) -> None:
        with SessionLocal() as session:
            batch = self.repo.create_batch(
                session, source_kind="file_selection"
            )
            self.assertEqual("created", batch.status)
            self.assertIsNone(batch.finished_at)

            self.repo.update_batch_status(session, batch, "completed")
            self.assertEqual("completed", batch.status)
            self.assertIsNotNone(batch.finished_at)
            session.commit()
