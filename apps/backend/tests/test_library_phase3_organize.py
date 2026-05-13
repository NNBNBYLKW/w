import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_object import LibraryObject
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
            session.execute(text("DELETE FROM sources"))
            session.commit()


if __name__ == "__main__":
    unittest.main()
