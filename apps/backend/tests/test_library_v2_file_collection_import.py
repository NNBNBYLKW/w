"""Phase 7H-3 tests: multi-file collection import."""

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app
from app.services.importing.service import ImportService


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class TestCollectionNameSuggestion(unittest.TestCase):
    def test_common_prefix_lesson(self):
        name = ImportService.suggest_collection_name([
            "/tmp/Lesson 01.mp4",
            "/tmp/Lesson 02.mp4",
            "/tmp/Lesson 03.mp4",
        ])
        assert name == "Lesson"

    def test_common_prefix_trim_trailing_number(self):
        name = ImportService.suggest_collection_name([
            "/tmp/IMG_0001.jpg",
            "/tmp/IMG_0002.jpg",
            "/tmp/IMG_0003.jpg",
        ])
        assert "Collection" in name

    def test_no_common_prefix_fallback(self):
        name = ImportService.suggest_collection_name([
            "/tmp/dog.jpg",
            "/tmp/run.mp4",
            "/tmp/notes.pdf",
        ])
        assert "Collection" in name

    def test_single_file_uses_its_stem(self):
        name = ImportService.suggest_collection_name([
            "/tmp/My Video.mp4",
        ])
        assert name == "My Video"

    def test_separators_normalized(self):
        name = ImportService.suggest_collection_name([
            "/tmp/My_Video-01.mp4",
            "/tmp/My.video-02.mp4",
        ])
        assert "My" in name

    def test_windows_unsafe_chars_stripped(self):
        name = ImportService.suggest_collection_name([
            "/tmp/Test:File?.mp4",
        ])
        assert ":" not in name
        assert "?" not in name


class TestTypeSuggestion(unittest.TestCase):
    def test_multiple_videos_default_video_collection(self):
        t, conf = ImportService.suggest_type_for_files([
            "/tmp/video1.mp4",
            "/tmp/video2.mkv",
            "/tmp/video3.avi",
        ])
        assert t == "video_collection"

    def test_video_plus_documents_default_course(self):
        t, conf = ImportService.suggest_type_for_files([
            "/tmp/lecture.mp4",
            "/tmp/slides.pdf",
            "/tmp/notes.docx",
        ])
        assert t == "course"

    def test_multiple_images_default_imgset(self):
        t, conf = ImportService.suggest_type_for_files([
            "/tmp/img1.jpg",
            "/tmp/img2.png",
            "/tmp/img3.webp",
        ])
        assert t == "imgset"

    def test_multiple_audio_default_audio(self):
        t, conf = ImportService.suggest_type_for_files([
            "/tmp/track1.mp3",
            "/tmp/track2.wav",
            "/tmp/track3.flac",
        ])
        assert t == "audio"

    def test_mixed_assets_default_asset_pack(self):
        t, conf = ImportService.suggest_type_for_files([
            "/tmp/texture.png",
            "/tmp/sound.wav",
            "/tmp/doc.pdf",
        ])
        assert t == "asset_pack"

    def test_empty_list_returns_none(self):
        t, conf = ImportService.suggest_type_for_files([])
        assert t is None


class LibraryV2FileCollectionImportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.managed_dir = self.tmp / "managed"
        self.managed_dir.mkdir()
        self.source_dir = self.tmp / "source"
        self.source_dir.mkdir()
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

    def _create_source_files(self, names: list[str]) -> list[Path]:
        paths = []
        for name in names:
            p = self.source_dir / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"fake content")
            paths.append(p)
        return paths

    def test_import_collection_creates_object_candidate(self) -> None:
        paths = self._create_source_files(["Lesson 01.mp4", "Lesson 02.mp4", "cover.jpg"])
        resp = self.client.post("/library/import/file-collections", json={
            "paths": [str(p) for p in paths],
            "collection_name": "Lesson",
            "suggested_object_type": "video_collection",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["batch_id"] > 0
        assert data["object_candidate_id"] > 0
        assert data["member_count"] == 3
        assert len(data["failed_items"]) == 0

    def test_source_files_preserved(self) -> None:
        paths = self._create_source_files(["test1.mp4", "test2.mp4"])
        resp = self.client.post("/library/import/file-collections", json={
            "paths": [str(p) for p in paths],
            "collection_name": "Test",
        })
        assert resp.status_code == 201
        # source files must still exist
        for p in paths:
            assert p.exists(), f"Source file should be preserved: {p}"

    def test_empty_selection_rejected(self) -> None:
        resp = self.client.post("/library/import/file-collections", json={
            "paths": [],
            "collection_name": "Test",
        })
        assert resp.status_code == 400

    def test_directory_path_rejected(self) -> None:
        resp = self.client.post("/library/import/file-collections", json={
            "paths": [str(self.source_dir)],
            "collection_name": "Test",
        })
        assert resp.status_code == 400

    def test_empty_collection_name_rejected(self) -> None:
        paths = self._create_source_files(["test.mp4"])
        resp = self.client.post("/library/import/file-collections", json={
            "paths": [str(p) for p in paths],
            "collection_name": "",
        })
        assert resp.status_code == 400

    def test_no_overwrite_suffix_for_same_basename(self) -> None:
        paths = self._create_source_files(["cover.jpg"])
        sub = self.source_dir / "sub"
        sub.mkdir()
        same_name = sub / "cover.jpg"
        same_name.write_bytes(b"different")
        paths.append(same_name)
        resp = self.client.post("/library/import/file-collections", json={
            "paths": [str(p) for p in paths],
            "collection_name": "Test",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["member_count"] == 2
        assert len(data["failed_items"]) == 0
        # both source files preserved
        assert paths[0].exists()
        assert same_name.exists()

    def test_multiple_videos_default_video_collection(self) -> None:
        paths = self._create_source_files(["video1.mp4", "video2.mkv", "video3.avi"])
        resp = self.client.post("/library/import/file-collections", json={
            "paths": [str(p) for p in paths],
            "collection_name": "Videos",
            "suggested_object_type": "video_collection",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["suggested_object_type"] == "video_collection"
