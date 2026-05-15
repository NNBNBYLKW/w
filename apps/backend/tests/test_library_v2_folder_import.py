import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.importing import ImportObjectCandidate, ImportObjectMember, InboxItem
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryV2FolderImportTestCase(unittest.TestCase):
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
            if session.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none() is None:
                session.add(Source(
                    path="__workbench_managed_import__",
                    display_name="Managed Import",
                    is_enabled=True, scan_mode="manual",
                    last_scan_status="not_applicable",
                    created_at=_dt(), updated_at=_dt(),
                ))
                session.commit()

    def _seed_managed_root(self, path: Path) -> int:
        with SessionLocal() as session:
            root = LibraryRoot(
                root_path=str(path.resolve()),
                display_name=path.name, root_kind="managed",
                is_enabled=True, is_default=True, scan_policy="manual",
                created_at=_dt(), updated_at=_dt(),
            )
            session.add(root)
            session.commit()
            return root.id

    # ── folder boundary preservation ───────────────────────

    def test_import_folder_as_object_preserves_folder_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "MyTool.exe").write_bytes(b"exe")
            (src / "config.json").write_text("{}", encoding="utf-8")
            (src / "readme.txt").write_text("readme", encoding="utf-8")

            with TestClient(app) as client:
                batch = client.post("/library/import/batches", json={"import_method": "copy"})
                batch_id = batch.json()["id"]
                resp = client.post(
                    f"/library/import/batches/{batch_id}/folders",
                    json={"paths": [str(src)], "mode": "object"},
                )
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertEqual(1, len(data["object_candidates"]))
            oc = data["object_candidates"][0]
            self.assertEqual("software", oc["suggested_object_type"])
            self.assertGreaterEqual(oc["member_count"], 3)

            # verify source preserved
            self.assertTrue(src.exists())
            self.assertTrue((src / "MyTool.exe").exists())

            # verify object candidate in DB
            with SessionLocal() as session:
                oc_db = session.get(ImportObjectCandidate, oc["object_candidate_id"])
                self.assertIsNotNone(oc_db)
                self.assertEqual("pending_review", oc_db.status)
                members = session.query(ImportObjectMember).filter(
                    ImportObjectMember.import_object_candidate_id == oc_db.id
                ).all()
                self.assertEqual(3, len(members))

    # ── loose files mode ───────────────────────────────────

    def test_import_folder_as_loose_files_splits_items_only_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            src = Path(td) / "LooseFiles"
            src.mkdir()
            (src / "a.txt").write_text("a", encoding="utf-8")
            (src / "b.txt").write_text("b", encoding="utf-8")

            with TestClient(app) as client:
                batch = client.post("/library/import/batches", json={"import_method": "copy"})
                batch_id = batch.json()["id"]
                resp = client.post(
                    f"/library/import/batches/{batch_id}/folders",
                    json={"paths": [str(src)], "mode": "loose_files"},
                )
            self.assertEqual(200, resp.status_code)
            data = resp.json()
            self.assertEqual(0, len(data["object_candidates"]))
            self.assertEqual(1, len(data["created_items"]))
            self.assertEqual(2, len(data["created_items"][0]["created_items"]))

    # ── source folder preserved ────────────────────────────

    def test_folder_import_copy_preserves_source_folder(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            src = Path(td) / "PreserveMe"
            src.mkdir()
            (src / "data.bin").write_bytes(b"important")
            original_stat = src.stat()

            with TestClient(app) as client:
                batch = client.post("/library/import/batches", json={"import_method": "copy"})
                batch_id = batch.json()["id"]
                client.post(
                    f"/library/import/batches/{batch_id}/folders",
                    json={"paths": [str(src)], "mode": "object"},
                )

            self.assertTrue(src.exists())
            self.assertEqual(original_stat.st_ino, src.stat().st_ino)
            self.assertTrue((src / "data.bin").exists())
            self.assertEqual(b"important", (src / "data.bin").read_bytes())

    # ── no overwrite suffix ────────────────────────────────

    def test_folder_import_no_overwrite_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            src = Path(td) / "MyFolder"
            src.mkdir()
            (src / "file.txt").write_text("v1", encoding="utf-8")

            with TestClient(app) as client:
                batch = client.post("/library/import/batches", json={"import_method": "copy"})
                batch_id = batch.json()["id"]
                # first import
                client.post(
                    f"/library/import/batches/{batch_id}/folders",
                    json={"paths": [str(src)], "mode": "object"},
                )
                # second import — should get suffix
                resp = client.post(
                    f"/library/import/batches/{batch_id}/folders",
                    json={"paths": [str(src)], "mode": "object"},
                )
                self.assertEqual(200, resp.status_code)
                oc2 = resp.json()["object_candidates"][0]

            # verify both inbox folders exist
            inbox_dir = root_dir / "00_Inbox" / str(batch_id)
            folders = [d for d in inbox_dir.iterdir() if d.is_dir()]
            self.assertGreaterEqual(len(folders), 2)

    # ── object candidate list/detail ───────────────────────

    def test_list_object_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            src = Path(td) / "TestApp"
            src.mkdir()
            (src / "app.exe").write_bytes(b"exe")

            with TestClient(app) as client:
                batch = client.post("/library/import/batches", json={"import_method": "copy"})
                batch_id = batch.json()["id"]
                client.post(
                    f"/library/import/batches/{batch_id}/folders",
                    json={"paths": [str(src)], "mode": "object"},
                )
                list_resp = client.get("/library/import/object-candidates")
                self.assertEqual(200, list_resp.status_code)
                self.assertEqual(1, list_resp.json()["total"])

    def test_get_object_candidate_detail_with_members(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)

            src = Path(td) / "MyGame"
            src.mkdir()
            (src / "game.exe").write_bytes(b"exe")
            (src / "data/").mkdir(exist_ok=True)
            (src / "data/assets.bin").write_bytes(b"data")

            with TestClient(app) as client:
                batch = client.post("/library/import/batches", json={"import_method": "copy"})
                batch_id = batch.json()["id"]
                import_resp = client.post(
                    f"/library/import/batches/{batch_id}/folders",
                    json={"paths": [str(src)], "mode": "object"},
                )
                oc_id = import_resp.json()["object_candidates"][0]["object_candidate_id"]
                detail = client.get(f"/library/import/object-candidates/{oc_id}")
                self.assertEqual(200, detail.status_code)
                self.assertEqual(oc_id, detail.json()["id"])
                self.assertGreater(len(detail.json()["members"]), 0)

    # ── invalid modes rejected ─────────────────────────────

    def test_folder_import_rejects_invalid_mode(self) -> None:
        with TestClient(app) as client:
            batch = client.post("/library/import/batches", json={"import_method": "copy"})
            batch_id = batch.json()["id"]
            resp = client.post(
                f"/library/import/batches/{batch_id}/folders",
                json={"paths": ["/nonexistent"], "mode": "move"},
            )
            self.assertEqual(400, resp.status_code)
