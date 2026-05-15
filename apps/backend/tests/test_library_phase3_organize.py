import json
import tempfile
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_object import LibraryObject
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 1, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryPhase3OrganizeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_candidate_scan_creates_object_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "[UNKNOWN] Strange"
            root.mkdir()
            self._seed_source(Path(temp_dir))
            self._seed_object(root, object_type="unknown_object", needs_review=True, metadata_source="inferred")

            with TestClient(app) as client:
                scan = client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")

        self.assertEqual(200, scan.status_code)
        self.assertEqual(1, scan.json()["candidates_created"])
        self.assertEqual("unknown_object", candidates.json()["items"][0]["candidate_type"])

    def test_candidate_scan_creates_inbox_movie_file_candidate_without_touching_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            video = source / "00_Inbox" / "_to_sort" / "Inception.2010.1080p.mkv"
            video.parent.mkdir(parents=True)
            video.write_bytes(b"video")
            self._seed_source(source)
            self._seed_file(video, "video")

            with TestClient(app) as client:
                response = client.post("/library/organize/candidates/scan")
                candidates = client.get("/library/organize/candidates")

            self.assertEqual(200, response.status_code)
            item = candidates.json()["items"][0]
            self.assertEqual("inbox_file", item["candidate_type"])
            self.assertEqual("movie", item["detected_type"])
            self.assertTrue(video.exists())
            self.assertFalse((video.parent / "asset.yaml").exists())

    def test_ignore_candidate_updates_database_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            video = source / "movie.2020.mp4"
            video.write_bytes(b"video")
            self._seed_source(source)
            self._seed_file(video, "video")

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                ignored = client.post(f"/library/organize/candidates/{candidate_id}/ignore")

            self.assertEqual(200, ignored.status_code)
            self.assertEqual("ignored", ignored.json()["status"])
            self.assertTrue(video.exists())

    def test_generate_plan_creates_draft_actions_and_asset_yaml_payload_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            video = source / "00_Inbox" / "Inception.2010.mkv"
            video.parent.mkdir()
            video.write_bytes(b"video")
            self._seed_source(source)
            self._seed_file(video, "video")

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                generated = client.post("/library/organize/plans/generate", json={"candidate_ids": [candidate_id]})
                detail = client.get(f"/library/organize/plans/{generated.json()['plan_id']}")

            self.assertEqual(200, generated.status_code)
            self.assertEqual("draft", generated.json()["status"])
            actions = detail.json()["actions"]
            self.assertEqual(["mkdir", "move", "write_asset_yaml"], [action["action_type"] for action in actions])
            yaml_action = actions[-1]
            self.assertIn('"schema_version": 1', yaml_action["payload_json"])
            self.assertFalse(Path(yaml_action["target_path"]).exists())
            self.assertTrue(video.exists())

    def test_conflict_check_blocks_existing_target_and_mark_ready_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            video = source / "00_Inbox" / "Conflict.2020.mp4"
            video.parent.mkdir()
            video.write_bytes(b"video")
            target = source / "10_Movies_Anime" / "Movies" / "[MOVIE] Conflict 2020 (2020)" / "Conflict 2020 (2020).mp4"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"existing")
            self._seed_source(source)
            self._seed_file(video, "video")

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                plan_id = client.post("/library/organize/plans/generate", json={"candidate_ids": [candidate_id]}).json()["plan_id"]
                detail = client.get(f"/library/organize/plans/{plan_id}")
                ready = client.post(f"/library/organize/plans/{plan_id}/mark-ready")

            self.assertTrue(any(action["conflict_status"] == "blocked" for action in detail.json()["actions"]))
            self.assertEqual(400, ready.status_code)
            self.assertTrue(video.exists())

    def test_mark_ready_succeeds_without_executing_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            video = source / "00_Inbox" / "Clean.2022.mp4"
            video.parent.mkdir()
            video.write_bytes(b"video")
            self._seed_source(source)
            self._seed_file(video, "video")

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                plan_id = client.post("/library/organize/plans/generate", json={"candidate_ids": [candidate_id]}).json()["plan_id"]
                ready = client.post(f"/library/organize/plans/{plan_id}/mark-ready")

            self.assertEqual(200, ready.status_code)
            self.assertEqual("ready", ready.json()["plan"]["status"])
            self.assertTrue(video.exists())
            self.assertFalse((source / "10_Movies_Anime").exists())

    def test_cancel_plan_changes_status_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            video = source / "clip.mp4"
            video.write_bytes(b"video")
            self._seed_source(source)
            self._seed_file(video, "video")
            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                plan_id = client.post("/library/organize/plans/generate", json={"candidate_ids": [candidate_id]}).json()["plan_id"]
                cancelled = client.post(f"/library/organize/plans/{plan_id}/cancel")
                plans = client.get("/library/organize/plans")

            self.assertEqual(200, cancelled.status_code)
            self.assertEqual("cancelled", plans.json()["items"][0]["status"])
            self.assertTrue(video.exists())

    # ── Candidate lifecycle: resolved, non-pending guard, cancel reset, re-scan ──

    def _seed_library_root(
        self, path: Path, *,
        display_name: str | None = None,
        is_enabled: bool = True,
        is_default: bool = False,
    ) -> int:
        now = _dt()
        with SessionLocal() as session:
            root = LibraryRoot(
                root_path=str(path.resolve()),
                display_name=display_name or path.name,
                root_kind="managed",
                is_enabled=is_enabled,
                is_default=is_default,
                scan_policy="manual",
                created_at=now,
                updated_at=now,
            )
            session.add(root)
            session.commit()
            return root.id

    def _wait_for_plan(self, client: TestClient, plan_id: int, timeout: float = 6.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            resp = client.get(f"/library/organize/plans/{plan_id}")
            data = resp.json()
            status = data["plan"]["status"]
            if status in {"completed", "completed_with_errors", "failed", "cancelled"}:
                return data
            time.sleep(0.2)
        return client.get(f"/library/organize/plans/{plan_id}").json()

    def test_generate_plan_rejects_non_pending_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            video = source / "movie.2020.mp4"
            video.write_bytes(b"video")
            self._seed_source(source)
            self._seed_file(video, "video")

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                # First plan — should succeed and transition candidate to "added_to_plan"
                gen1 = client.post("/library/organize/plans/generate", json={"candidate_ids": [candidate_id]})
                self.assertEqual(200, gen1.status_code)
                # Second plan with same candidate — should be rejected
                gen2 = client.post("/library/organize/plans/generate", json={"candidate_ids": [candidate_id]})

            self.assertEqual(400, gen2.status_code)
            self.assertIn("not in 'pending' status", gen2.json()["detail"])

    def test_cancelled_plan_resets_candidates_to_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            video = source / "movie.2021.mp4"
            video.write_bytes(b"video")
            self._seed_source(source)
            self._seed_file(video, "video")

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                # Generate plan — candidate moves to "added_to_plan"
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [candidate_id]})
                plan_id = gen.json()["plan_id"]
                # Cancel — candidate should reset to "pending"
                client.post(f"/library/organize/plans/{plan_id}/cancel")
                candidate = client.get(f"/library/organize/candidates/{candidate_id}")

            self.assertEqual("pending", candidate.json()["status"])

    def test_candidates_resolved_after_completed_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source_root"
            video = source / "00_Inbox" / "_to_sort" / "Inception.2010.1080p.mkv"
            video.parent.mkdir(parents=True)
            video.write_bytes(b"video")
            managed = Path(temp_dir) / "managed_lib"
            managed.mkdir()
            self._seed_source(source)
            self._seed_file(video, "video")
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                gen = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [candidate_id],
                    "target_library_root_id": root_id,
                })
                plan_id = gen.json()["plan_id"]
                client.post(f"/library/organize/plans/{plan_id}/mark-ready")
                pf = client.post(f"/library/organize/plans/{plan_id}/preflight")
                self.assertTrue(pf.json()["can_execute"], f"Preflight blocked: {pf.json()}")
                exe = client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self.assertEqual(200, exe.status_code)
                detail = self._wait_for_plan(client, plan_id)
                candidate = client.get(f"/library/organize/candidates/{candidate_id}")

            self.assertEqual("completed", detail["plan"]["status"])
            self.assertEqual("resolved", candidate.json()["status"])

    def test_repeat_scan_keeps_resolved_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source_root"
            video = source / "00_Inbox" / "_to_sort" / "Tenet.2020.1080p.mkv"
            video.parent.mkdir(parents=True)
            video.write_bytes(b"video")
            managed = Path(temp_dir) / "managed_lib"
            managed.mkdir()
            self._seed_source(source)
            self._seed_file(video, "video")
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                gen = client.post("/library/organize/plans/generate", json={
                    "candidate_ids": [candidate_id],
                    "target_library_root_id": root_id,
                })
                plan_id = gen.json()["plan_id"]
                client.post(f"/library/organize/plans/{plan_id}/mark-ready")
                client.post(f"/library/organize/plans/{plan_id}/preflight")
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                self._wait_for_plan(client, plan_id)
                # Before re-scan, status should be resolved
                before = client.get(f"/library/organize/candidates/{candidate_id}")
                self.assertEqual("resolved", before.json()["status"])
                # Re-scan — must not reset resolved candidate back to pending
                client.post("/library/organize/candidates/scan")
                after = client.get(f"/library/organize/candidates/{candidate_id}")

            self.assertEqual("resolved", after.json()["status"],
                             "Re-scan must not reset a resolved candidate back to pending")

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

    def _seed_file(self, path: Path, file_type: str) -> int:
        now = _dt()
        with SessionLocal() as session:
            source = session.query(Source).filter(Source.path == str(self._source_root_for(path))).one()
            file = File(
                source_id=source.id,
                path=str(path),
                parent_path=str(path.parent),
                name=path.name,
                stem=path.stem,
                extension=path.suffix.lstrip("."),
                file_type=file_type,
                mime_type=None,
                size_bytes=path.stat().st_size,
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

    def _seed_object(self, path: Path, *, object_type: str, needs_review: bool, metadata_source: str) -> int:
        now = _dt()
        with SessionLocal() as session:
            item = LibraryObject(
                object_type=object_type,
                type_prefix="UNKNOWN",
                root_path=str(path),
                root_name=path.name,
                filesystem_title=path.name,
                title=path.name,
                original_title=None,
                romanized_title=None,
                localized_title_json=None,
                sort_title=None,
                year=None,
                tags_json=json.dumps([]),
                cover_path=None,
                primary_file_path=None,
                metadata_source=metadata_source,
                needs_review=needs_review,
                review_reason="unknown_type_prefix",
                created_at=now,
                updated_at=now,
                last_scanned_at=now,
            )
            session.add(item)
            session.commit()
            return item.id

    def _source_root_for(self, path: Path) -> Path:
        current = path
        while current.parent != current:
            if current.name in {"00_Inbox", "_to_sort"}:
                return current.parent if current.name == "00_Inbox" else current.parent.parent
            current = current.parent
        return path.parent

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM organize_plan_candidates"))
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
            session.execute(text("DELETE FROM files"))
            session.execute(text("DELETE FROM source_ignore_rules"))
            session.execute(text("DELETE FROM tags"))
            session.execute(text("DELETE FROM library_roots"))
            session.execute(text("DELETE FROM sources"))
            session.commit()


    def test_edit_ready_action_resets_plan_to_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            video = source / "00_Inbox" / "EditReady.2022.mp4"
            video.parent.mkdir(parents=True)
            video.write_bytes(b"video")
            self._seed_source(source)
            self._seed_file(video, "video")

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [candidate_id]})
                plan_id = gen.json()["plan_id"]
                client.post(f"/library/organize/plans/{plan_id}/mark-ready")
                detail = client.get(f"/library/organize/plans/{plan_id}")
                self.assertEqual("ready", detail.json()["plan"]["status"])
                action = detail.json()["actions"][0]
                new_target = str(Path(temp_dir) / "managed" / "NewName")

                edit = client.patch(f"/library/organize/actions/{action['id']}", json={"target_path": new_target})

            self.assertEqual(200, edit.status_code)
            self.assertEqual("draft", edit.json()["plan"]["status"])

    def test_edit_completed_plan_action_rejected(self) -> None:
        import time
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source_root"
            video = source / "00_Inbox" / "_to_sort" / "NoEdit.2020.1080p.mkv"
            video.parent.mkdir(parents=True)
            video.write_bytes(b"video")
            managed = Path(temp_dir) / "managed_lib"
            managed.mkdir()
            self._seed_source(source)
            self._seed_file(video, "video")
            root_id = self._seed_library_root(managed)

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                cid = client.get("/library/organize/candidates").json()["items"][0]["id"]
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [cid], "target_library_root_id": root_id})
                plan_id = gen.json()["plan_id"]
                client.post(f"/library/organize/plans/{plan_id}/mark-ready")
                client.post(f"/library/organize/plans/{plan_id}/preflight")
                client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
                deadline = time.monotonic() + 6
                while time.monotonic() < deadline:
                    d = client.get(f"/library/organize/plans/{plan_id}").json()
                    if d["plan"]["status"] in {"completed", "completed_with_errors", "failed"}:
                        break
                    time.sleep(0.15)
                detail = client.get(f"/library/organize/plans/{plan_id}")
                self.assertIn(detail.json()["plan"]["status"], {"completed", "completed_with_errors", "failed"})
                action = detail.json()["actions"][0]
                edit = client.patch(f"/library/organize/actions/{action['id']}", json={"target_path": str(managed / "changed")})

            self.assertEqual(400, edit.status_code)

    def test_edit_draft_action_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            video = source / "movie.2020.mp4"
            video.write_bytes(b"video")
            self._seed_source(source)
            self._seed_file(video, "video")

            with TestClient(app) as client:
                client.post("/library/organize/candidates/scan")
                candidate_id = client.get("/library/organize/candidates").json()["items"][0]["id"]
                gen = client.post("/library/organize/plans/generate", json={"candidate_ids": [candidate_id]})
                plan_id = gen.json()["plan_id"]
                detail = client.get(f"/library/organize/plans/{plan_id}")
                self.assertEqual("draft", detail.json()["plan"]["status"])
                action = detail.json()["actions"][0]
                new_target = str(Path(temp_dir) / "managed" / "Renamed")
                edit = client.patch(f"/library/organize/actions/{action['id']}", json={"target_path": new_target})

            self.assertEqual(200, edit.status_code)
            self.assertEqual("draft", edit.json()["plan"]["status"])
            self.assertEqual(new_target, edit.json()["actions"][0]["target_path"])

if __name__ == "__main__":
    unittest.main()
