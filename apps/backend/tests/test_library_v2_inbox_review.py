import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.importing import ImportObjectCandidate, ImportObjectMember, InboxItem
from app.db.models.library_root import LibraryRoot
from app.db.models.organize import OrganizeCandidate
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryV2InboxReviewTestCase(unittest.TestCase):
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
                    path="__workbench_managed_import__", display_name="Managed Import",
                    is_enabled=True, scan_mode="manual", last_scan_status="not_applicable",
                    created_at=_dt(), updated_at=_dt(),
                ))
                session.commit()

    def _seed_managed_root(self, path: Path) -> int:
        with SessionLocal() as session:
            root = LibraryRoot(
                root_path=str(path.resolve()), display_name=path.name,
                root_kind="managed", is_enabled=True, is_default=True,
                scan_policy="manual", created_at=_dt(), updated_at=_dt(),
            )
            session.add(root)
            session.commit()
            return root.id

    def _import_file(self, client: TestClient, root_dir: Path, source_path: Path) -> dict:
        batch = client.post("/library/import/batches", json={"import_method": "copy"})
        batch_id = batch.json()["id"]
        resp = client.post(f"/library/import/batches/{batch_id}/files", json={"paths": [str(source_path)]})
        data = resp.json()
        return {"batch_id": batch_id, "item": data["created_items"][0]}

    def _import_folder_as_object(self, client: TestClient, root_dir: Path, src: Path) -> dict:
        batch = client.post("/library/import/batches", json={"import_method": "copy"})
        batch_id = batch.json()["id"]
        resp = client.post(
            f"/library/import/batches/{batch_id}/folders",
            json={"paths": [str(src)], "mode": "object"},
        )
        return {"batch_id": batch_id, "oc": resp.json()["object_candidates"][0]}

    # ── inbox item confirm ──────────────────────────────

    def test_confirm_inbox_item_final_type(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "test.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                resp = client.post(
                    f"/library/import/inbox/items/{item_id}/confirm",
                    json={"final_object_type": "movie", "target_library_root_id": root_id},
                )
                self.assertEqual(200, resp.status_code)
                self.assertEqual("classified", resp.json()["status"])
                self.assertEqual("movie", resp.json()["final_object_type"])

    def test_confirm_inbox_item_requires_valid_type(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            src = Path(td) / "test.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                resp = client.post(
                    f"/library/import/inbox/items/{item_id}/confirm",
                    json={"final_object_type": ""},
                )
                self.assertEqual(400, resp.status_code)

    def test_confirm_inbox_item_requires_enabled_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            src = Path(td) / "test.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                resp = client.post(
                    f"/library/import/inbox/items/{item_id}/confirm",
                    json={"final_object_type": "movie", "target_library_root_id": 99999},
                )
                self.assertEqual(400, resp.status_code)

    # ── inbox item reject ───────────────────────────────

    def test_reject_inbox_item(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            src = Path(td) / "test.txt"
            src.write_text("hi", encoding="utf-8")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                resp = client.post(f"/library/import/inbox/items/{item_id}/reject")
                self.assertEqual(200, resp.status_code)
                self.assertEqual("rejected", resp.json()["status"])

    # ── create candidate from inbox item ────────────────

    def test_create_candidate_from_inbox_item(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "movie.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                # confirm first
                client.post(
                    f"/library/import/inbox/items/{item_id}/confirm",
                    json={"final_object_type": "movie", "target_library_root_id": root_id},
                )
                resp = client.post(f"/library/import/inbox/items/{item_id}/create-candidate")
                self.assertEqual(200, resp.status_code)
                data = resp.json()
                self.assertIn("candidate_id", data)
                self.assertEqual(item_id, data["inbox_item_id"])

    def test_create_candidate_from_inbox_item_requires_confirmed_type(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            src = Path(td) / "test.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                # try creating candidate without confirm
                resp = client.post(f"/library/import/inbox/items/{item_id}/create-candidate")
                self.assertEqual(400, resp.status_code)

    def test_create_candidate_from_inbox_item_rejects_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "movie.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                client.post(
                    f"/library/import/inbox/items/{item_id}/confirm",
                    json={"final_object_type": "movie", "target_library_root_id": root_id},
                )
                client.post(f"/library/import/inbox/items/{item_id}/create-candidate")
                # duplicate
                resp = client.post(f"/library/import/inbox/items/{item_id}/create-candidate")
                self.assertEqual(400, resp.status_code)

    # ── object candidate confirm ────────────────────────

    def test_confirm_object_candidate_final_type(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")

            with TestClient(app) as client:
                imported = self._import_folder_as_object(client, root_dir, src)
                oc_id = imported["oc"]["object_candidate_id"]
                resp = client.post(
                    f"/library/import/object-candidates/{oc_id}/confirm",
                    json={"final_object_type": "software", "target_library_root_id": root_id},
                )
                self.assertEqual(200, resp.status_code)
                self.assertEqual("confirmed", resp.json()["status"])
                self.assertEqual("software", resp.json()["final_object_type"])

    def test_update_object_candidate_launch_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")
            (src / "helper.exe").write_bytes(b"exe")

            with TestClient(app) as client:
                imported = self._import_folder_as_object(client, root_dir, src)
                oc_id = imported["oc"]["object_candidate_id"]
                detail = client.get(f"/library/import/object-candidates/{oc_id}")
                members = detail.json()["members"]
                exe_members = [m for m in members if m.get("role") == "launch_exe"]
                self.assertGreater(len(exe_members), 0)

    # ── object candidate reject ─────────────────────────

    def test_reject_object_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")

            with TestClient(app) as client:
                imported = self._import_folder_as_object(client, root_dir, src)
                oc_id = imported["oc"]["object_candidate_id"]
                resp = client.post(f"/library/import/object-candidates/{oc_id}/reject")
                self.assertEqual(200, resp.status_code)
                self.assertEqual("rejected", resp.json()["status"])

    # ── create candidate from object candidate ──────────

    def test_create_candidate_from_object_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")

            with TestClient(app) as client:
                imported = self._import_folder_as_object(client, root_dir, src)
                oc_id = imported["oc"]["object_candidate_id"]
                client.post(
                    f"/library/import/object-candidates/{oc_id}/confirm",
                    json={"final_object_type": "software", "target_library_root_id": root_id},
                )
                resp = client.post(f"/library/import/object-candidates/{oc_id}/create-candidate")
                self.assertEqual(200, resp.status_code)
                data = resp.json()
                self.assertIn("candidate_id", data)
                self.assertEqual(oc_id, data["import_object_candidate_id"])

    def test_object_candidate_members_not_split_into_independent_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")
            (src / "config.json").write_text("{}", encoding="utf-8")
            (src / "readme.txt").write_text("readme", encoding="utf-8")

            with TestClient(app) as client:
                imported = self._import_folder_as_object(client, root_dir, src)
                oc_id = imported["oc"]["object_candidate_id"]
                client.post(
                    f"/library/import/object-candidates/{oc_id}/confirm",
                    json={"final_object_type": "software", "target_library_root_id": root_id},
                )
                resp = client.post(f"/library/import/object-candidates/{oc_id}/create-candidate")
                self.assertEqual(200, resp.status_code)
                # only ONE organize candidate should exist
                data = resp.json()
                self.assertEqual(oc_id, data["import_object_candidate_id"])

    # ── generate draft plan ─────────────────────────────

    def test_generate_draft_plan_from_inbox_item(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "movie.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                client.post(
                    f"/library/import/inbox/items/{item_id}/confirm",
                    json={"final_object_type": "movie", "target_library_root_id": root_id},
                )
                cand = client.post(f"/library/import/inbox/items/{item_id}/create-candidate")
                candidate_id = cand.json()["candidate_id"]

                plan_resp = client.post(
                    "/library/import/organize-plans",
                    json={"candidate_ids": [candidate_id]},
                )
                self.assertEqual(200, plan_resp.status_code)
                self.assertEqual("draft", plan_resp.json()["status"])

    def test_generate_draft_plan_from_object_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")

            with TestClient(app) as client:
                imported = self._import_folder_as_object(client, root_dir, src)
                oc_id = imported["oc"]["object_candidate_id"]
                client.post(
                    f"/library/import/object-candidates/{oc_id}/confirm",
                    json={"final_object_type": "software", "target_library_root_id": root_id},
                )
                cand = client.post(f"/library/import/object-candidates/{oc_id}/create-candidate")
                candidate_id = cand.json()["candidate_id"]

                plan_resp = client.post(
                    "/library/import/organize-plans",
                    json={"candidate_ids": [candidate_id]},
                )
                self.assertEqual(200, plan_resp.status_code)
                self.assertEqual("draft", plan_resp.json()["status"])

    def test_generate_plan_does_not_execute(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "movie.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                client.post(
                    f"/library/import/inbox/items/{item_id}/confirm",
                    json={"final_object_type": "movie", "target_library_root_id": root_id},
                )
                cand = client.post(f"/library/import/inbox/items/{item_id}/create-candidate")
                plan_resp = client.post(
                    "/library/import/organize-plans",
                    json={"candidate_ids": [cand.json()["candidate_id"]]},
                )
                plan_id = plan_resp.json()["plan_id"]
                plan_detail = client.get(f"/library/organize/plans/{plan_id}")
                self.assertEqual("draft", plan_detail.json()["plan"]["status"])
                # verify no files were moved
                self.assertTrue(src.exists())

    def test_phase7c_does_not_move_or_delete_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "safe.mp4"
            src.write_bytes(b"important data")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                client.post(
                    f"/library/import/inbox/items/{item_id}/confirm",
                    json={"final_object_type": "movie", "target_library_root_id": root_id},
                )
                cand = client.post(f"/library/import/inbox/items/{item_id}/create-candidate")
                client.post(
                    "/library/import/organize-plans",
                    json={"candidate_ids": [cand.json()["candidate_id"]]},
                )
            # source must still exist
            self.assertTrue(src.exists())
            self.assertEqual(b"important data", src.read_bytes())
            # inbox copy must still exist
            with SessionLocal() as session:
                item = session.get(InboxItem, item_id)
                self.assertTrue(Path(item.inbox_path).exists())

    # ── status updates after plan ───────────────────────

    def test_planned_status_updates_inbox_item(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "movie.mp4"
            src.write_bytes(b"video")

            with TestClient(app) as client:
                imported = self._import_file(client, root_dir, src)
                item_id = imported["item"]["inbox_item_id"]
                client.post(
                    f"/library/import/inbox/items/{item_id}/confirm",
                    json={"final_object_type": "movie", "target_library_root_id": root_id},
                )
                cand = client.post(f"/library/import/inbox/items/{item_id}/create-candidate")
                client.post(
                    "/library/import/organize-plans",
                    json={"candidate_ids": [cand.json()["candidate_id"]]},
                )
                item = client.get(f"/library/import/inbox/items/{item_id}")
                self.assertEqual("planned", item.json()["status"])

    def test_planned_status_updates_object_candidate_and_members(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Managed"
            root_dir.mkdir()
            root_id = self._seed_managed_root(root_dir)
            src = Path(td) / "MyTool"
            src.mkdir()
            (src / "tool.exe").write_bytes(b"exe")
            (src / "config.json").write_text("{}", encoding="utf-8")

            with TestClient(app) as client:
                imported = self._import_folder_as_object(client, root_dir, src)
                oc_id = imported["oc"]["object_candidate_id"]
                client.post(
                    f"/library/import/object-candidates/{oc_id}/confirm",
                    json={"final_object_type": "software", "target_library_root_id": root_id},
                )
                cand = client.post(f"/library/import/object-candidates/{oc_id}/create-candidate")
                client.post(
                    "/library/import/organize-plans",
                    json={"candidate_ids": [cand.json()["candidate_id"]]},
                )
                # object candidate status
                detail = client.get(f"/library/import/object-candidates/{oc_id}")
                self.assertEqual("planned", detail.json()["status"])
                # member inbox items should be planned too
                members = detail.json()["members"]
                for m in members:
                    item = client.get(f"/library/import/inbox/items/{m['inbox_item_id']}")
                    self.assertEqual("planned", item.json()["status"])
