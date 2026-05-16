"""Phase 8A tests: Browse v2 read model adapter."""

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_object import LibraryObject, LibraryObjectMember
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class BrowseV2ReadModelTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.managed_dir = self.tmp / "managed"
        self.managed_dir.mkdir()
        self.client = TestClient(app)
        self._seed_root()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()
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

    def _seed_root(self) -> int:
        with SessionLocal() as session:
            root = LibraryRoot(
                root_path=str(self.managed_dir.resolve()), display_name="Test Root",
                root_kind="managed", is_enabled=True, is_default=True,
                scan_policy="manual", created_at=_dt(), updated_at=_dt(),
            )
            session.add(root)
            session.commit()
            return root.id

    def _create_file(self, path: str, file_kind: str = "video", storage_state: str = "external") -> int:
        with SessionLocal() as session:
            p = Path(path)
            f = File(
                source_id=1, path=str(p), parent_path=str(p.parent), name=p.name,
                stem=p.stem, extension=p.suffix.lstrip("."),
                file_type=file_kind, file_kind=file_kind, auto_placement="media",
                storage_state=storage_state, size_bytes=100,
                discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
            )
            session.add(f)
            session.commit()
            return f.id

    def _create_library_object(self, root_path: str, object_type: str = "movie", title: str = "Test Movie") -> int:
        prefix_map = {"movie": "MOVIE", "anime": "ANIME", "game": "GAME", "software": "SOFTWARE",
                       "course": "COURSE", "imgset": "IMGSET", "docset": "DOCSET", "clip": "CLIP"}
        with SessionLocal() as session:
            lo = LibraryObject(
                root_path=root_path, root_name=Path(root_path).name,
                object_type=object_type, type_prefix=prefix_map.get(object_type, "CLIP"),
                title=title, filesystem_title=title,
                metadata_source="scan", needs_review=False,
                last_scanned_at=_dt(),
                created_at=_dt(), updated_at=_dt(),
            )
            session.add(lo)
            session.commit()
            return lo.id

    # ── Tests ─────────────────────────────────────────

    def test_browse_returns_object_card_for_library_object(self) -> None:
        obj_dir = self.managed_dir / "10_Movies_Anime" / "Movies" / "[MOVIE] Test (2025)"
        obj_dir.mkdir(parents=True)
        lo_id = self._create_library_object(str(obj_dir), object_type="movie", title="Test Movie")
        resp = self.client.get("/library/browse?domain=media&category=movie")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_objects"] >= 1
        obj_cards = [i for i in data["items"] if i["card_kind"] == "object"]
        assert any(i["namespaced_id"] == f"library_object:{lo_id}" for i in obj_cards)

    def test_browse_returns_loose_file_card_for_unmembered_file(self) -> None:
        fp = self.managed_dir / "loose_video.mp4"
        fp.write_bytes(b"fake")
        file_id = self._create_file(str(fp), file_kind="video", storage_state="external")
        resp = self.client.get("/library/browse?domain=media")
        assert resp.status_code == 200
        data = resp.json()
        loose = [i for i in data["items"] if i["card_kind"] == "loose_file"]
        assert any(i["file_id"] == file_id for i in loose)

    def test_browse_excludes_object_member_from_loose_files(self) -> None:
        obj_dir = self.managed_dir / "10_Movies_Anime" / "Movies" / "[MOVIE] Collection (2025)"
        obj_dir.mkdir(parents=True)
        member_file = obj_dir / "video.mp4"
        member_file.write_bytes(b"fake")
        lo_id = self._create_library_object(str(obj_dir), object_type="movie", title="Collection")
        with SessionLocal() as session:
            f = File(
                source_id=1, path=str(member_file), parent_path=str(obj_dir),
                name="video.mp4", stem="video", extension="mp4",
                file_type="video", file_kind="video", auto_placement="media",
                storage_state="external", size_bytes=100,
                discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
            )
            session.add(f)
            session.flush()
            lom = LibraryObjectMember(
                object_id=lo_id, file_id=f.id,
                member_role="main_video", relative_path="video.mp4",
                absolute_path=str(member_file), extension="mp4",
                created_at=_dt(),
            )
            session.add(lom)
            session.commit()

        resp = self.client.get("/library/browse?domain=media")
        assert resp.status_code == 200
        data = resp.json()
        loose = [i for i in data["items"] if i["card_kind"] == "loose_file"]
        # The member file should NOT appear as loose file
        assert not any(i["file_id"] == f.id for i in loose), "Object member should not appear as loose file"

    def test_browse_category_movie(self) -> None:
        obj_dir = self.managed_dir / "[MOVIE] A Movie"
        obj_dir.mkdir(parents=True)
        self._create_library_object(str(obj_dir), object_type="movie", title="A Movie")
        resp = self.client.get("/library/browse?domain=media&category=movie")
        assert resp.status_code == 200
        data = resp.json()
        obj_cards = [i for i in data["items"] if i["card_kind"] == "object"]
        assert all(i["object_type"] == "movie" for i in obj_cards)

    def test_browse_storage_state_all_includes_external(self) -> None:
        fp = self.managed_dir / "external_video.mp4"
        fp.write_bytes(b"fake")
        self._create_file(str(fp), file_kind="video", storage_state="external")
        resp = self.client.get("/library/browse?domain=media&storage_state=all")
        assert resp.status_code == 200
        data = resp.json()
        loose = [i for i in data["items"] if i["card_kind"] == "loose_file"]
        assert any(i["storage_state"] == "external" for i in loose), "External files should be visible by default"

    def test_browse_storage_state_filter_managed(self) -> None:
        fp = self.managed_dir / "managed_video.mp4"
        fp.write_bytes(b"fake")
        self._create_file(str(fp), file_kind="video", storage_state="managed")
        resp = self.client.get("/library/browse?domain=media&storage_state=managed")
        assert resp.status_code == 200
        data = resp.json()
        loose = [i for i in data["items"] if i["card_kind"] == "loose_file"]
        for i in loose:
            assert i["storage_state"] == "managed"

    def test_browse_summary_counts(self) -> None:
        obj_dir = self.managed_dir / "[MOVIE] Summary Test"
        obj_dir.mkdir(parents=True)
        self._create_library_object(str(obj_dir), object_type="movie", title="Summary Test")
        resp = self.client.get("/library/browse?domain=media")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert data["summary"]["total_objects"] >= 1

    def test_browse_is_read_only_no_db_write(self) -> None:
        # Verify browsing does not create new records
        prev_count = 0
        with SessionLocal() as session:
            from sqlalchemy import func, select as sa_select
            prev_count = session.scalar(sa_select(func.count()).select_from(File)) or 0

        resp = self.client.get("/library/browse?domain=media")
        assert resp.status_code == 200

        with SessionLocal() as session:
            from sqlalchemy import func, select as sa_select
            post_count = session.scalar(sa_select(func.count()).select_from(File)) or 0
        assert post_count == prev_count, "Browse API must not write to DB"

    def test_browse_object_card_has_namespaced_id(self) -> None:
        obj_dir = self.managed_dir / "[MOVIE] Namespaced Test"
        obj_dir.mkdir(parents=True)
        lo_id = self._create_library_object(str(obj_dir), object_type="movie", title="Namespaced Test")
        resp = self.client.get("/library/browse?domain=media&category=movie")
        assert resp.status_code == 200
        data = resp.json()
        obj_cards = [i for i in data["items"] if i["card_kind"] == "object"]
        assert all(":" in i["namespaced_id"] for i in obj_cards), "Object cards must have namespaced IDs"
        assert any(i["namespaced_id"] == f"library_object:{lo_id}" for i in obj_cards)
        assert any(i["object_source"] == "library_object" for i in obj_cards)
