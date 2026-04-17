import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.db.models.file import File
from app.db.models.file_metadata import FileMetadata
from app.db.models.source import Source
from app.db.models.task import Task
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app
from app.repositories.file_metadata.repository import FileMetadataRepository


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 16, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase2AMetadataExtractionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()

    def test_extracts_image_dimensions_and_persists_metadata_during_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._create_image(root / "cover.png", (320, 200))

            source_id = self._create_source(root)
            response = self._run_scan(source_id)

            self.assertEqual(202, response.status_code)
            self.assertEqual("succeeded", response.json()["status"])

            file_row = self._get_file_by_name("cover.png")
            self.assertIsNotNone(file_row)
            metadata_row = self._get_metadata(file_row.id)
            self.assertIsNotNone(metadata_row)
            self.assertEqual(320, metadata_row.width)
            self.assertEqual(200, metadata_row.height)
            self.assertIsNone(metadata_row.duration_ms)
            self.assertIsNone(metadata_row.page_count)

            latest_task = self._get_latest_task()
            self.assertIsNotNone(latest_task)
            self.assertEqual("succeeded", latest_task.status)

        engine.dispose()

    def test_does_not_backfill_existing_files_without_rescan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "existing.png"
            self._create_image(image_path, (640, 480))

            file_id = self._seed_existing_indexed_image_without_metadata(image_path)
            self.assertIsNone(self._get_metadata(file_id))

            with TestClient(app) as client:
                response = client.get(f"/files/{file_id}")

            self.assertEqual(200, response.status_code)
            self.assertIsNone(response.json()["item"]["metadata"])
            self.assertIsNone(self._get_metadata(file_id))

        engine.dispose()

    def test_skips_unsupported_file_types_without_creating_metadata_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "notes.pdf").write_text("document", encoding="utf-8")

            source_id = self._create_source(root)
            response = self._run_scan(source_id)

            self.assertEqual(202, response.status_code)
            self.assertEqual("succeeded", response.json()["status"])

            file_row = self._get_file_by_name("notes.pdf")
            self.assertIsNotNone(file_row)
            self.assertEqual("document", file_row.file_type)
            self.assertIsNone(self._get_metadata(file_row.id))

        engine.dispose()

    def test_metadata_extraction_failure_does_not_fail_source_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "broken.png").write_bytes(b"not-a-real-png")

            source_id = self._create_source(root)
            response = self._run_scan(source_id)

            self.assertEqual(202, response.status_code)
            self.assertEqual("succeeded", response.json()["status"])

            file_row = self._get_file_by_name("broken.png")
            self.assertIsNotNone(file_row)
            self.assertIsNone(self._get_metadata(file_row.id))

            latest_task = self._get_latest_task()
            self.assertIsNotNone(latest_task)
            self.assertEqual("succeeded", latest_task.status)

        engine.dispose()

    def test_metadata_persistence_failure_is_isolated_to_one_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._create_image(root / "keep.png", (100, 50))
            self._create_image(root / "fail.png", (80, 40))

            source_id = self._create_source(root)
            original_upsert = FileMetadataRepository.upsert_metadata

            def flaky_upsert(self, session, file_id, **kwargs):
                file_row = session.get(File, file_id)
                if file_row is not None and file_row.name == "fail.png":
                    raise SQLAlchemyError("forced metadata persistence failure")
                return original_upsert(self, session, file_id, **kwargs)

            with patch.object(FileMetadataRepository, "upsert_metadata", new=flaky_upsert):
                response = self._run_scan(source_id)

            self.assertEqual(202, response.status_code)
            self.assertEqual("succeeded", response.json()["status"])

            keep_file = self._get_file_by_name("keep.png")
            fail_file = self._get_file_by_name("fail.png")
            self.assertIsNotNone(keep_file)
            self.assertIsNotNone(fail_file)
            self.assertIsNotNone(self._get_metadata(keep_file.id))
            self.assertIsNone(self._get_metadata(fail_file.id))

            latest_task = self._get_latest_task()
            self.assertIsNotNone(latest_task)
            self.assertEqual("succeeded", latest_task.status)

        engine.dispose()

    def test_rescan_updates_existing_image_metadata_for_same_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "cover.png"
            self._create_image(image_path, (40, 30))

            source_id = self._create_source(root)
            first_scan = self._run_scan(source_id)
            self.assertEqual(202, first_scan.status_code)
            first_file = self._get_file_by_name("cover.png")
            self.assertIsNotNone(first_file)
            first_metadata = self._get_metadata(first_file.id)
            self.assertIsNotNone(first_metadata)
            self.assertEqual((40, 30), (first_metadata.width, first_metadata.height))

            self._create_image(image_path, (80, 60))

            second_scan = self._run_scan(source_id)
            self.assertEqual(202, second_scan.status_code)
            second_file = self._get_file_by_name("cover.png")
            self.assertIsNotNone(second_file)
            self.assertEqual(first_file.id, second_file.id)

            updated_metadata = self._get_metadata(second_file.id)
            self.assertIsNotNone(updated_metadata)
            self.assertEqual((80, 60), (updated_metadata.width, updated_metadata.height))

        engine.dispose()

    def _create_image(self, path: Path, size: tuple[int, int]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, color=(12, 34, 56)).save(path)

    def _create_source(self, root: Path) -> int:
        with TestClient(app) as client:
            response = client.post(
                "/sources",
                json={"path": str(root), "display_name": root.name or "Metadata Source"},
            )

        self.assertEqual(201, response.status_code)
        return int(response.json()["id"])

    def _run_scan(self, source_id: int):
        with TestClient(app) as client:
            return client.post(f"/sources/{source_id}/scan")

    def _seed_existing_indexed_image_without_metadata(self, image_path: Path) -> int:
        with SessionLocal() as session:
            source = Source(
                path=str(image_path.parent),
                display_name="Existing Source",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9),
                last_scan_status="succeeded",
                created_at=_dt(8),
                updated_at=_dt(9),
            )
            session.add(source)
            session.flush()

            file_row = File(
                source_id=source.id,
                path=str(image_path),
                parent_path=str(image_path.parent),
                name=image_path.name,
                stem=image_path.stem,
                extension=image_path.suffix.lstrip("."),
                file_type="image",
                mime_type=None,
                size_bytes=image_path.stat().st_size,
                created_at_fs=None,
                modified_at_fs=_dt(9, 30),
                discovered_at=_dt(9, 35),
                last_seen_at=_dt(10),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10),
            )
            session.add(file_row)
            session.commit()
            return int(file_row.id)

    def _get_file_by_name(self, name: str) -> File | None:
        with SessionLocal() as session:
            statement = select(File).where(File.name == name)
            return session.scalars(statement).first()

    def _get_metadata(self, file_id: int) -> FileMetadata | None:
        with SessionLocal() as session:
            return session.get(FileMetadata, file_id)

    def _get_latest_task(self) -> Task | None:
        with SessionLocal() as session:
            statement = select(Task).order_by(Task.id.desc())
            return session.scalars(statement).first()

    def _reset_database(self) -> None:
        with SessionLocal() as session:
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
