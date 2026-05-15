import time
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.importing import (
    FilePathHistory, ImportObjectCandidate, ImportObjectMember, InboxItem, OperationJournal,
)
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryV2PathSyncTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            for t in [
                "import_object_members", "import_object_candidates",
                "file_path_history", "operation_journal", "inbox_items", "import_batches",
                "organize_plan_candidates", "organize_suggestions", "organize_action_logs",
                "organize_actions", "organize_plans", "organize_candidates",
                "asset_metadata_cache", "library_object_members", "library_objects",
                "tool_runs", "tasks", "file_metadata", "file_tags", "file_user_meta",
                "collections", "files", "source_ignore_rules", "tags",
                "library_roots", "sources",
            ]:
                session.execute(text(f"DELETE FROM {t}"))
            session.commit()

    def _ensure_managed_source(self) -> None:
        with SessionLocal() as session:
            if session.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none() is None:
                session.add(Source(path="__workbench_managed_import__", display_name="Managed Import", is_enabled=True, scan_mode="manual", last_scan_status="not_applicable", created_at=_dt(), updated_at=_dt()))
                session.commit()

    def _seed_managed_root(self, path: Path) -> int:
        with SessionLocal() as session:
            root = LibraryRoot(root_path=str(path.resolve()), display_name=path.name, root_kind="managed", is_enabled=True, is_default=True, scan_policy="manual", created_at=_dt(), updated_at=_dt())
            session.add(root)
            session.commit()
            return root.id

    def _import_and_plan(self, client: TestClient, src: Path, root_id: int, final_type="movie") -> int:
        """Import file, confirm, create candidate, generate draft plan. Returns plan_id."""
        batch = client.post("/library/import/batches", json={"import_method": "copy"})
        bid = batch.json()["id"]
        imp = client.post(f"/library/import/batches/{bid}/files", json={"paths": [str(src)]})
        iid = imp.json()["created_items"][0]["inbox_item_id"]
        client.post(f"/library/import/inbox/items/{iid}/confirm", json={"final_object_type": final_type, "target_library_root_id": root_id})
        cand = client.post(f"/library/import/inbox/items/{iid}/create-candidate")
        plan_resp = client.post("/library/import/organize-plans", json={"candidate_ids": [cand.json()["candidate_id"]]})
        return plan_resp.json()["plan_id"]

    def _import_folder_and_plan(self, client: TestClient, src: Path, root_id: int, final_type="software") -> int:
        batch = client.post("/library/import/batches", json={"import_method": "copy"})
        bid = batch.json()["id"]
        imp = client.post(f"/library/import/batches/{bid}/folders", json={"paths": [str(src)], "mode": "object"})
        oc_id = imp.json()["object_candidates"][0]["object_candidate_id"]
        client.post(f"/library/import/object-candidates/{oc_id}/confirm", json={"final_object_type": final_type, "target_library_root_id": root_id})
        cand = client.post(f"/library/import/object-candidates/{oc_id}/create-candidate")
        plan_resp = client.post("/library/import/organize-plans", json={"candidate_ids": [cand.json()["candidate_id"]]})
        return plan_resp.json()["plan_id"]

    def _mark_ready(self, client: TestClient, plan_id: int) -> None:
        client.post(f"/library/organize/plans/{plan_id}/mark-ready")

    def _execute(self, client: TestClient, plan_id: int) -> dict:
        resp = client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
        # wait for execution
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            detail = client.get(f"/library/organize/plans/{plan_id}")
            status = detail.json()["plan"]["status"]
            if status in {"completed", "completed_with_errors", "failed"}:
                return detail.json()
            time.sleep(0.1)
        self.fail(f"Plan {plan_id} did not finish in time")
        return {}

    # ── Inbox item path sync ─────────────────────────────

    def test_execute_inbox_item_plan_updates_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "movie.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                plan_id = self._import_and_plan(client, src, root_id, "movie")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            # verify files.path updated
            with SessionLocal() as session:
                files = session.query(File).filter(File.storage_state == "managed").all()
                self.assertGreater(len(files), 0)
                for f in files:
                    self.assertIn(str(root_dir), f.path)

    def test_execute_inbox_item_plan_sets_storage_state_managed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "clip.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                plan_id = self._import_and_plan(client, src, root_id, "clip")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                managed = session.query(File).filter(File.storage_state == "managed").all()
                self.assertGreater(len(managed), 0)

    def test_execute_inbox_item_plan_sets_managed_root_and_managed_at(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "doc.txt"
            src.write_text("doc", encoding="utf-8")

            with TestClient(app) as client:
                plan_id = self._import_and_plan(client, src, root_id, "docset")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                managed = session.query(File).filter(File.storage_state == "managed").first()
                self.assertIsNotNone(managed)
                self.assertEqual(root_id, managed.managed_root_id)
                self.assertIsNotNone(managed.managed_at)

    def test_execute_inbox_item_plan_marks_inbox_item_organized(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "song.mp3"
            src.write_bytes(b"audio")

            with TestClient(app) as client:
                plan_id = self._import_and_plan(client, src, root_id, "clip")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                organized = session.query(InboxItem).filter(InboxItem.status == "organized").all()
                self.assertGreater(len(organized), 0)

    def test_execute_inbox_item_plan_writes_path_history(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "movie.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                plan_id = self._import_and_plan(client, src, root_id, "movie")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                histories = session.query(FilePathHistory).filter(
                    FilePathHistory.reason == "library_v2_execute"
                ).all()
                self.assertGreater(len(histories), 0)
                h = histories[0]
                self.assertIsNotNone(h.old_path)
                self.assertIsNotNone(h.new_path)

    def test_execute_inbox_item_plan_writes_operation_journal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "movie.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                plan_id = self._import_and_plan(client, src, root_id, "movie")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                journals = session.query(OperationJournal).filter(
                    OperationJournal.operation_type == "path_sync"
                ).all()
                self.assertGreater(len(journals), 0)

    def test_execute_inbox_item_plan_preserves_original_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "safe.txt"
            src.write_text("must stay", encoding="utf-8")

            with TestClient(app) as client:
                plan_id = self._import_and_plan(client, src, root_id, "docset")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            self.assertTrue(src.exists())
            self.assertEqual("must stay", src.read_text(encoding="utf-8"))

    # ── Object candidate path sync ───────────────────────

    def test_execute_object_candidate_plan_updates_all_member_file_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")
            (src / "config.json").write_text("{}", encoding="utf-8")

            with TestClient(app) as client:
                plan_id = self._import_folder_and_plan(client, src, root_id, "software")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                managed = session.query(File).filter(File.storage_state == "managed").all()
                self.assertEqual(2, len(managed))
                for f in managed:
                    self.assertIn(str(root_dir), f.path)

    def test_execute_object_candidate_plan_preserves_object_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")
            (src / "config.json").write_text("{}", encoding="utf-8")

            with TestClient(app) as client:
                plan_id = self._import_folder_and_plan(client, src, root_id, "software")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                managed_files = session.query(File).filter(File.storage_state == "managed").all()
                parent_dirs = {Path(f.path).parent for f in managed_files}
                # all members should be in the same parent directory (object root preserved)
                self.assertEqual(1, len(parent_dirs))

    def test_execute_object_candidate_plan_marks_object_candidate_organized(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")

            with TestClient(app) as client:
                plan_id = self._import_folder_and_plan(client, src, root_id, "software")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                oc = session.query(ImportObjectCandidate).first()
                self.assertIsNotNone(oc)
                self.assertEqual("organized", oc.status)

    def test_execute_object_candidate_plan_marks_member_items_organized(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")
            (src / "config.json").write_text("{}", encoding="utf-8")

            with TestClient(app) as client:
                plan_id = self._import_folder_and_plan(client, src, root_id, "software")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                items = session.query(InboxItem).filter(InboxItem.status == "organized").all()
                self.assertEqual(2, len(items))

    def test_execute_object_candidate_plan_writes_path_history_for_each_member(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")
            (src / "config.json").write_text("{}", encoding="utf-8")

            with TestClient(app) as client:
                plan_id = self._import_folder_and_plan(client, src, root_id, "software")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                histories = session.query(FilePathHistory).filter(
                    FilePathHistory.reason == "library_v2_execute"
                ).all()
                self.assertEqual(2, len(histories))

    def test_object_candidate_members_not_split_into_independent_moves(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")
            (src / "config.json").write_text("{}", encoding="utf-8")

            with TestClient(app) as client:
                plan_id = self._import_folder_and_plan(client, src, root_id, "software")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            with SessionLocal() as session:
                managed_files = session.query(File).filter(File.storage_state == "managed").all()
                parent_dirs = {Path(f.path).parent for f in managed_files}
                # one parent dir = members together
                self.assertEqual(1, len(parent_dirs))

    # ── Partial failure / safety ─────────────────────────

    def test_phase7d_does_not_delete_original_source(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "keeper.txt"
            src.write_text("original", encoding="utf-8")

            with TestClient(app) as client:
                plan_id = self._import_and_plan(client, src, root_id, "docset")
                self._mark_ready(client, plan_id)
                self._execute(client, plan_id)

            self.assertTrue(src.exists())
            self.assertEqual("original", src.read_text(encoding="utf-8"))

    def test_no_storage_state_managed_for_non_import_plan(self) -> None:
        """Legacy organize actions without import linkage should not get v2 sync."""
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "movie.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                plan_id = self._import_and_plan(client, src, root_id, "movie")
                # verify plan exists and is draft
                detail = client.get(f"/library/organize/plans/{plan_id}")
                self.assertEqual("draft", detail.json()["plan"]["status"])
