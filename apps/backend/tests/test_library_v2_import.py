import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.importing import InboxItem, OperationJournal
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryV2ImportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()

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

    def _seed_managed_root(self, path: Path) -> int:
        now = _dt()
        with SessionLocal() as session:
            root = LibraryRoot(
                root_path=str(path.resolve()),
                display_name=path.name,
                root_kind="managed",
                is_enabled=True,
                is_default=True,
                scan_policy="manual",
                created_at=now,
                updated_at=now,
            )
            session.add(root)
            session.commit()
            return root.id

    def _count_journal_entries(self, operation_id: str) -> int:
        with SessionLocal() as session:
            return len(
                session.query(OperationJournal)
                .filter(OperationJournal.operation_id == operation_id)
                .all()
            )

    # ── 1. create import batch (copy only) ──────────────────

    def test_create_import_batch_copy_only(self) -> None:
        with TestClient(app) as client:
            resp = client.post(
                "/library/import/batches",
                json={"import_method": "copy"},
            )
        self.assertEqual(201, resp.status_code)
        data = resp.json()
        self.assertEqual("created", data["status"])
        self.assertEqual("copy", data["import_method"])
        self.assertIn("id", data)

    # ── 2. reject move import method ────────────────────────

    def test_create_import_batch_rejects_move(self) -> None:
        with TestClient(app) as client:
            resp = client.post(
                "/library/import/batches",
                json={"import_method": "move"},
            )
        self.assertEqual(400, resp.status_code)

    # ── 3. copy preserves source file ───────────────────────

    def test_copy_import_preserves_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_file = Path(temp_dir) / "test_video.mp4"
            source_file.write_bytes(b"original video content")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]

                import_resp = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )
                self.assertEqual(200, import_resp.status_code)
                result = import_resp.json()
                self.assertEqual(1, len(result["created_items"]))
                self.assertEqual(0, len(result["failed_items"]))

            # source file must still exist with original content
            self.assertTrue(source_file.exists())
            self.assertEqual(b"original video content", source_file.read_bytes())

            # inbox copy must exist
            inbox_file = (
                root_dir / "00_Inbox" / str(batch_id) / source_file.name
            )
            self.assertTrue(inbox_file.exists())
            self.assertEqual(b"original video content", inbox_file.read_bytes())

    # ── 4. copy creates inbox file ──────────────────────────

    def test_copy_import_creates_inbox_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_file = Path(temp_dir) / "notes.txt"
            source_file.write_text("hello world", encoding="utf-8")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]

                client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )

            inbox_file = (
                root_dir / "00_Inbox" / str(batch_id) / source_file.name
            )
            self.assertTrue(inbox_file.exists())
            self.assertEqual("hello world", inbox_file.read_text(encoding="utf-8"))

    # ── 5. copy creates file record ─────────────────────────

    def test_copy_import_creates_file_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_file = Path(temp_dir) / "readme.md"
            source_file.write_text("# Test", encoding="utf-8")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]

                import_resp = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )
                file_id = import_resp.json()["created_items"][0]["file_id"]

            with SessionLocal() as session:
                file = session.get(File, file_id)
                self.assertIsNotNone(file)
                inbox_file = (
                    root_dir / "00_Inbox" / str(batch_id) / source_file.name
                )
                self.assertEqual(str(inbox_file), file.path)

    # ── 6. storage_state = inbox ────────────────────────────

    def test_copy_import_sets_storage_state_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_file = Path(temp_dir) / "song.mp3"
            source_file.write_bytes(b"audio")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]
                import_resp = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )
                file_id = import_resp.json()["created_items"][0]["file_id"]

            with SessionLocal() as session:
                file = session.get(File, file_id)
                self.assertEqual("inbox", file.storage_state)

    # ── 7. records original_path ────────────────────────────

    def test_copy_import_records_original_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_file = Path(temp_dir) / "image.png"
            source_file.write_bytes(b"png data")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]
                import_resp = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )
                file_id = import_resp.json()["created_items"][0]["file_id"]

            with SessionLocal() as session:
                file = session.get(File, file_id)
                self.assertEqual(str(source_file), file.original_path)

    # ── 8. creates inbox item ───────────────────────────────

    def test_copy_import_creates_inbox_item(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_file = Path(temp_dir) / "movie.mp4"
            source_file.write_bytes(b"movie data")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]
                import_resp = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )
                item_id = import_resp.json()["created_items"][0]["inbox_item_id"]

            with SessionLocal() as session:
                item = session.get(InboxItem, item_id)
                self.assertIsNotNone(item)
                self.assertEqual(batch_id, item.import_batch_id)
                self.assertEqual("imported", item.status)
                self.assertEqual(str(source_file), item.source_path)

    # ── 9. writes operation journal ─────────────────────────

    def test_copy_import_writes_operation_journal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_file = Path(temp_dir) / "doc.pdf"
            source_file.write_bytes(b"pdf content")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]
                import_resp = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )
                self.assertEqual(200, import_resp.status_code)

            with SessionLocal() as session:
                total = session.query(OperationJournal).count()
                self.assertGreaterEqual(total, 3)  # at least: import_copy started, import_copy succeeded, file_record_create, inbox_status_change

    # ── 10. target conflict adds suffix ─────────────────────

    def test_copy_import_target_conflict_adds_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_file = Path(temp_dir) / "file.txt"
            source_file.write_text("first", encoding="utf-8")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]

                # first import
                r1 = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )
                self.assertEqual(1, len(r1.json()["created_items"]))

                # second import of same file — should get suffix
                r2 = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )
                self.assertEqual(1, len(r2.json()["created_items"]))
                inbox_path2 = r2.json()["created_items"][0]["inbox_path"]
                self.assertIn("(1)", inbox_path2)

            # verify both files exist in inbox
            inbox_dir = root_dir / "00_Inbox" / str(batch_id)
            files = list(inbox_dir.glob("file*"))
            self.assertEqual(2, len(files))

    # ── 11. never overwrites ────────────────────────────────

    def test_copy_import_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_file = Path(temp_dir) / "data.bin"
            source_file.write_bytes(b"first import content")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]

                client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )

                # change source content and import again
                source_file.write_bytes(b"second import - different content")

                r2 = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )

            inbox_dir = root_dir / "00_Inbox" / str(batch_id)
            original = inbox_dir / "data.bin"
            suffixed = inbox_dir / "data (1).bin"
            self.assertTrue(original.exists())
            self.assertTrue(suffixed.exists())
            # original must still have first content (not overwritten)
            self.assertEqual(b"first import content", original.read_bytes())

    # ── 12. missing source marks failed ─────────────────────

    def test_copy_import_missing_source_marks_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            nonexistent = Path(temp_dir) / "does_not_exist.mp4"

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]

                resp = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(nonexistent)]},
                )
                self.assertEqual(200, resp.status_code)  # API responds ok, but item is failed
                result = resp.json()
                self.assertEqual(1, len(result["failed_items"]))
                self.assertEqual(0, len(result["created_items"]))

            # verify batch status is "failed"
            with TestClient(app) as client:
                batch_detail = client.get(f"/library/import/batches/{batch_id}")
                self.assertEqual("failed", batch_detail.json()["status"])

    # ── 13. batch completed_with_errors ─────────────────────

    def test_import_batch_completed_with_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            good_file = Path(temp_dir) / "good.txt"
            good_file.write_text("ok", encoding="utf-8")
            bad_file = Path(temp_dir) / "nonexistent.txt"

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]

                resp = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(good_file), str(bad_file)]},
                )
                result = resp.json()
                self.assertEqual(1, len(result["created_items"]))
                self.assertEqual(1, len(result["failed_items"]))

                batch_detail = client.get(f"/library/import/batches/{batch_id}")
                self.assertEqual("completed_with_errors", batch_detail.json()["status"])
                self.assertEqual(2, batch_detail.json()["file_count"])
                self.assertEqual(1, batch_detail.json()["completed_count"])
                self.assertEqual(1, batch_detail.json()["failed_count"])

    # ── 14. list batches ────────────────────────────────────

    def test_list_import_batches(self) -> None:
        with TestClient(app) as client:
            # create two batches
            client.post("/library/import/batches", json={"import_method": "copy"})
            client.post("/library/import/batches", json={"import_method": "copy"})

            list_resp = client.get("/library/import/batches")
            self.assertEqual(200, list_resp.status_code)
            data = list_resp.json()
            self.assertEqual(2, data["total"])
            self.assertEqual(2, len(data["items"]))

    # ── 15. list inbox items ────────────────────────────────

    def test_list_inbox_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_a = Path(temp_dir) / "a.txt"
            source_a.write_text("a", encoding="utf-8")
            source_b = Path(temp_dir) / "b.txt"
            source_b.write_text("b", encoding="utf-8")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]
                client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_a), str(source_b)]},
                )

                items_resp = client.get("/library/import/inbox/items")
                self.assertEqual(200, items_resp.status_code)
                data = items_resp.json()
                self.assertEqual(2, data["total"])

                # filter by batch_id
                filtered = client.get(
                    f"/library/import/inbox/items?batch_id={batch_id}"
                )
                self.assertEqual(2, filtered.json()["total"])

    # ── 16. does not move/delete source ─────────────────────

    def test_phase7b_does_not_move_or_delete_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "ManagedLib"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            source_file = Path(temp_dir) / "keeper.dat"
            source_content = b"must stay forever"
            source_file.write_bytes(source_content)
            original_stat = source_file.stat()

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]
                client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )

            # source must still exist with same content and inode
            self.assertTrue(source_file.exists())
            self.assertEqual(source_content, source_file.read_bytes())
            self.assertEqual(original_stat.st_ino, source_file.stat().st_ino)

    # ── 17. requires enabled managed root ───────────────────

    def test_import_requires_enabled_managed_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_file = Path(temp_dir) / "orphan.txt"
            source_file.write_text("no root", encoding="utf-8")

            with TestClient(app) as client:
                batch = client.post(
                    "/library/import/batches", json={"import_method": "copy"}
                )
                batch_id = batch.json()["id"]

                resp = client.post(
                    f"/library/import/batches/{batch_id}/files",
                    json={"paths": [str(source_file)]},
                )
                self.assertEqual(400, resp.status_code)

    # ── 18. batch detail 404 ────────────────────────────────

    def test_get_import_batch_404(self) -> None:
        with TestClient(app) as client:
            resp = client.get("/library/import/batches/99999")
            self.assertEqual(404, resp.status_code)

    # ── 19. inbox item detail 404 ───────────────────────────

    def test_get_inbox_item_404(self) -> None:
        with TestClient(app) as client:
            resp = client.get("/library/import/inbox/items/99999")
            self.assertEqual(404, resp.status_code)

    # ── 20. empty paths rejected ────────────────────────────

    def test_import_empty_paths_rejected(self) -> None:
        with TestClient(app) as client:
            batch = client.post(
                "/library/import/batches", json={"import_method": "copy"}
            )
            batch_id = batch.json()["id"]
            resp = client.post(
                f"/library/import/batches/{batch_id}/files",
                json={"paths": []},
            )
            self.assertEqual(400, resp.status_code)
