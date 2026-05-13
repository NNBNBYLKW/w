import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.organize import OrganizeCandidate, OrganizePlan
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 1, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryPhase5D3SuggestionsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_generate_suggestions_creates_pending_rule_based_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir)
            with TestClient(app) as client:
                resp = client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
            self.assertEqual(200, resp.status_code, resp.text)
            items = resp.json()["items"]
            types = {item["suggestion_type"] for item in items}
            self.assertGreaterEqual(types, {"object_type", "title", "tags", "asset_yaml", "template_key"})
            for item in items:
                self.assertEqual("rule_based", item["provider"])
                self.assertEqual("pending", item["status"])

    def test_suggestion_types_limited_to_allowed_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir)
            with TestClient(app) as client:
                resp = client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
            allowed = {"object_type", "title", "tags", "asset_yaml", "template_key"}
            self.assertTrue({item["suggestion_type"] for item in resp.json()["items"]}.issubset(allowed))

    def test_title_suggestion_generated_from_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir, name="Blade.Runner.2049.2017.2160p.mkv")
            with TestClient(app) as client:
                resp = client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
            title = self._payload_for(resp.json()["items"], "title")
            self.assertIn("Blade Runner", title["title"])
            self.assertNotIn(".mkv", title["title"])

    def test_year_extracted_into_asset_yaml_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir, name="Inception.2010.1080p.mkv")
            with TestClient(app) as client:
                resp = client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
            payload = self._payload_for(resp.json()["items"], "asset_yaml")
            self.assertEqual(2010, payload["year"])

    def test_template_key_suggestion_matches_object_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir)
            with TestClient(app) as client:
                resp = client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
            payload = self._payload_for(resp.json()["items"], "template_key")
            self.assertEqual("movie_default", payload["template_key"])

    def test_template_key_suggestion_uses_anime_default_for_anime_candidate(self) -> None:
        candidate_id = self._seed_candidate("anime", "[ANIME] Frieren (2023) [S01]")
        with TestClient(app) as client:
            resp = client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
        payload = self._payload_for(resp.json()["items"], "template_key")
        self.assertEqual("anime_default", payload["template_key"])

    def test_asset_yaml_suggestion_contains_core_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir)
            with TestClient(app) as client:
                resp = client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
            payload = self._payload_for(resp.json()["items"], "asset_yaml")
            self.assertEqual(1, payload["schema_version"])
            self.assertEqual("movie", payload["type"])
            self.assertTrue(payload["title"])

    def test_get_suggestions_returns_candidate_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir)
            with TestClient(app) as client:
                client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
                resp = client.get(f"/library/organize/candidates/{candidate_id}/suggestions")
            self.assertEqual(200, resp.status_code)
            self.assertGreaterEqual(len(resp.json()["items"]), 5)

    def test_accept_suggestion_updates_status_and_accepted_at(self) -> None:
        suggestion_id = self._first_suggestion_id()
        with TestClient(app) as client:
            resp = client.post(f"/library/organize/suggestions/{suggestion_id}/accept")
        self.assertEqual(200, resp.status_code)
        data = resp.json()
        self.assertEqual("accepted", data["status"])
        self.assertIsNotNone(data["accepted_at"])
        self.assertIsNone(data["rejected_at"])

    def test_reject_suggestion_updates_status_and_rejected_at(self) -> None:
        suggestion_id = self._first_suggestion_id()
        with TestClient(app) as client:
            resp = client.post(f"/library/organize/suggestions/{suggestion_id}/reject")
        self.assertEqual(200, resp.status_code)
        data = resp.json()
        self.assertEqual("rejected", data["status"])
        self.assertIsNotNone(data["rejected_at"])
        self.assertIsNone(data["accepted_at"])

    def test_accepted_suggestion_cannot_be_rejected(self) -> None:
        suggestion_id = self._first_suggestion_id()
        with TestClient(app) as client:
            client.post(f"/library/organize/suggestions/{suggestion_id}/accept")
            resp = client.post(f"/library/organize/suggestions/{suggestion_id}/reject")
        self.assertEqual(400, resp.status_code)

    def test_rejected_suggestion_cannot_be_accepted(self) -> None:
        suggestion_id = self._first_suggestion_id()
        with TestClient(app) as client:
            client.post(f"/library/organize/suggestions/{suggestion_id}/reject")
            resp = client.post(f"/library/organize/suggestions/{suggestion_id}/accept")
        self.assertEqual(400, resp.status_code)

    def test_generate_suggestions_does_not_create_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir)
            with TestClient(app) as client:
                client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
        with SessionLocal() as session:
            self.assertEqual(0, session.query(OrganizePlan).count())

    def test_generate_suggestions_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir)
            before = {str(path) for path in Path(temp_dir).rglob("*")}
            with TestClient(app) as client:
                client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
            after = {str(path) for path in Path(temp_dir).rglob("*")}
            self.assertEqual(before, after)

    def test_accept_does_not_write_asset_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir)
            with TestClient(app) as client:
                gen = client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
                suggestion_id = gen.json()["items"][0]["id"]
                client.post(f"/library/organize/suggestions/{suggestion_id}/accept")
            self.assertEqual([], list(Path(temp_dir).rglob("asset.yaml")))

    def test_accept_does_not_mark_ready_or_execute(self) -> None:
        suggestion_id = self._first_suggestion_id()
        with TestClient(app) as client:
            client.post(f"/library/organize/suggestions/{suggestion_id}/accept")
        with SessionLocal() as session:
            self.assertEqual(0, session.query(OrganizePlan).count())

    def test_invalid_candidate_returns_404(self) -> None:
        with TestClient(app) as client:
            resp = client.post("/library/organize/candidates/999999/suggestions/generate")
        self.assertEqual(404, resp.status_code)

    def test_invalid_suggestion_returns_404(self) -> None:
        with TestClient(app) as client:
            resp = client.post("/library/organize/suggestions/999999/accept")
        self.assertEqual(404, resp.status_code)

    def _first_suggestion_id(self) -> int:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_id = self._setup_movie_candidate(temp_dir)
            with TestClient(app) as client:
                resp = client.post(f"/library/organize/candidates/{candidate_id}/suggestions/generate")
            return resp.json()["items"][0]["id"]

    def _payload_for(self, items: list[dict], suggestion_type: str) -> dict:
        item = next(item for item in items if item["suggestion_type"] == suggestion_type)
        return json.loads(item["payload_json"])

    def _setup_movie_candidate(self, temp_dir: str, name: str = "Inception.2010.1080p.mkv") -> int:
        source = Path(temp_dir) / "source_root"
        video = source / "00_Inbox" / "_to_sort" / name
        video.parent.mkdir(parents=True)
        video.write_bytes(b"video")
        self._seed_source(source)
        self._seed_file(video, "video")
        with TestClient(app) as client:
            client.post("/library/organize/candidates/scan")
            candidates = client.get("/library/organize/candidates")
        return candidates.json()["items"][0]["id"]

    def _seed_candidate(self, detected_type: str, display_name: str) -> int:
        now = _dt()
        with SessionLocal() as session:
            candidate = OrganizeCandidate(
                candidate_type="loose_file",
                source_kind="file",
                source_file_id=None,
                source_object_id=None,
                source_path=str(Path("G:/virtual") / display_name),
                display_name=display_name,
                detected_type=detected_type,
                confidence="high",
                reason="Seeded test candidate.",
                status="pending",
                ignored_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(candidate)
            session.commit()
            return candidate.id

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

    def _source_root_for(self, path: Path) -> Path:
        current = path
        while current.parent != current:
            if current.name in {"00_Inbox", "_to_sort"}:
                return current.parent if current.name == "00_Inbox" else current.parent.parent
            current = current.parent
        return path.parent

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM organize_suggestions"))
            session.execute(text("DELETE FROM organize_plan_candidates"))
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
            session.execute(text("DELETE FROM files"))
            session.execute(text("DELETE FROM source_ignore_rules"))
            session.execute(text("DELETE FROM tags"))
            session.execute(text("DELETE FROM library_roots"))
            session.execute(text("DELETE FROM sources"))
            session.commit()
