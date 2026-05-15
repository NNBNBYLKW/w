import tempfile, unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt():
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class LibraryV2StorageScopeTestCase(unittest.TestCase):
    def setUp(self):
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()
        self._seed_data()

    def tearDown(self):
        self._reset_database()
        engine.dispose()

    def _reset_database(self):
        with SessionLocal() as s:
            for t in ["import_object_members","import_object_candidates","file_path_history","operation_journal","inbox_items","import_batches","organize_plan_candidates","organize_suggestions","organize_action_logs","organize_actions","organize_plans","organize_candidates","asset_metadata_cache","library_object_members","library_objects","tool_runs","tasks","file_metadata","file_tags","file_user_meta","collections","files","source_ignore_rules","tags","library_roots","sources"]:
                s.execute(text(f"DELETE FROM {t}"))
            s.commit()

    def _ensure_managed_source(self):
        with SessionLocal() as s:
            if s.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none() is None:
                s.add(Source(path="__workbench_managed_import__", display_name="MI", is_enabled=True, scan_mode="manual", last_scan_status="na", created_at=_dt(), updated_at=_dt()))
                s.commit()

    def _seed_data(self):
        with SessionLocal() as s:
            src = Source(path="/fake/external", display_name="ext", is_enabled=True, scan_mode="manual", created_at=_dt(), updated_at=_dt())
            s.add(src); s.commit()
            sid = src.id
            for i, (ss, fn) in enumerate([
                ("external", "external_file.txt"),
                ("inbox", "inbox_file.txt"),
                ("managed", "managed_file.txt"),
                ("external", "external_video.mp4"),
                ("managed", "managed_video.mp4"),
            ]):
                f = File(source_id=sid, path=f"/fake/{fn}", parent_path="/fake", name=fn,
                         stem=Path(fn).stem, extension=Path(fn).suffix.lstrip("."),
                         file_type="video" if "video" in fn else "document",
                         file_kind="video" if "video" in fn else "document",
                         auto_placement="media" if "video" in fn else "books",
                         storage_state=ss, discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt())
                s.add(f)
            s.commit()

    # ── search filters ─────────────────────────────────

    def test_search_default_all_includes_all_storage_states(self):
        with TestClient(app) as c:
            r = c.get("/search")
            self.assertEqual(200, r.status_code)
            self.assertEqual(5, r.json()["total"])

    def test_search_filter_external(self):
        with TestClient(app) as c:
            r = c.get("/search?storage_state=external")
            self.assertEqual(200, r.status_code)
            items = r.json()["items"]
            for i in items:
                self.assertEqual("external", i.get("storage_state", "external"))

    def test_search_filter_inbox(self):
        with TestClient(app) as c:
            r = c.get("/search?storage_state=inbox")
            self.assertEqual(200, r.status_code)
            self.assertEqual(1, r.json()["total"])

    def test_search_filter_managed(self):
        with TestClient(app) as c:
            r = c.get("/search?storage_state=managed")
            self.assertEqual(200, r.status_code)
            self.assertEqual(2, r.json()["total"])

    def test_search_invalid_storage_state_rejected(self):
        with TestClient(app) as c:
            r = c.get("/search?storage_state=deleted")
            self.assertEqual(422, r.status_code)

    # ── browse filters ─────────────────────────────────

    def test_books_filter_external(self):
        with TestClient(app) as c:
            r = c.get("/library/books?storage_state=external")
            self.assertEqual(200, r.status_code)
            self.assertEqual(1, r.json()["total"])

    def test_media_filter_managed(self):
        with TestClient(app) as c:
            r = c.get("/library/media?storage_state=managed")
            self.assertEqual(200, r.status_code)
            self.assertEqual(1, r.json()["total"])

    def test_games_filter_all(self):
        with TestClient(app) as c:
            r = c.get("/library/games")
            self.assertEqual(200, r.status_code)

    def test_software_filter_all(self):
        with TestClient(app) as c:
            r = c.get("/library/software")
            self.assertEqual(200, r.status_code)

    # ── storage summary ────────────────────────────────

    def test_library_storage_summary_counts(self):
        with TestClient(app) as c:
            r = c.get("/library/storage-summary")
            self.assertEqual(200, r.status_code)
            d = r.json()
            self.assertEqual(5, d["total_count"])
            self.assertEqual(2, d["external_count"])
            self.assertEqual(1, d["inbox_count"])
            self.assertEqual(2, d["managed_count"])

    # ── default all ─────────────────────────────────────

    def test_existing_external_files_remain_visible_by_default(self):
        with TestClient(app) as c:
            r = c.get("/search")
            paths = [item["path"] for item in r.json()["items"]]
            self.assertIn("/fake/external_file.txt", paths)
