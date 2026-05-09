import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
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
from app.workers.metadata.extractor import MetadataExtractorWorker


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

    def test_extracts_video_metadata_from_ffprobe_stream_duration(self) -> None:
        file_row = self._build_video_file(Path("C:/Video Library/clip.mp4"))
        worker = MetadataExtractorWorker()
        completed = CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                b'{"streams":[{"codec_type":"video","width":1920,"height":1080,"duration":"12.345"}],'
                b'"format":{"duration":"99.000"}}'
            ),
            stderr=b"",
        )

        with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
            with patch("app.workers.metadata.extractor.subprocess.run", return_value=completed) as run_mock:
                metadata = worker.extract_for_file(file_row)

        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertEqual(1920, metadata.width)
        self.assertEqual(1080, metadata.height)
        self.assertEqual(12345, metadata.duration_ms)
        command = run_mock.call_args.args[0]
        self.assertEqual("ffprobe", command[0])
        self.assertEqual(str(file_row.path), command[-1])
        self.assertIs(run_mock.call_args.kwargs["check"], False)
        self.assertIs(run_mock.call_args.kwargs["text"], False)
        self.assertEqual(subprocess.PIPE, run_mock.call_args.kwargs["stdout"])
        self.assertEqual(subprocess.PIPE, run_mock.call_args.kwargs["stderr"])
        self.assertEqual(10, run_mock.call_args.kwargs["timeout"])

    def test_extracts_video_metadata_uses_format_duration_fallback(self) -> None:
        file_row = self._build_video_file(Path("C:/Video Library/clip.mp4"))
        worker = MetadataExtractorWorker()
        completed = CompletedProcess(
            args=[],
            returncode=0,
            stdout=b'{"streams":[{"codec_type":"video","width":1280,"height":720}],"format":{"duration":"42.500"}}',
            stderr=b"",
        )

        with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
            with patch("app.workers.metadata.extractor.subprocess.run", return_value=completed):
                metadata = worker.extract_for_file(file_row)

        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertEqual((1280, 720, 42500), (metadata.width, metadata.height, metadata.duration_ms))

    def test_extracts_video_metadata_handles_missing_dimensions_and_invalid_duration(self) -> None:
        file_row = self._build_video_file(Path("C:/Video Library/clip.mp4"))
        worker = MetadataExtractorWorker()
        completed = CompletedProcess(
            args=[],
            returncode=0,
            stdout=b'{"streams":[{"codec_type":"video","duration":"not-a-number"}],"format":{"duration":"0"}}',
            stderr=b"",
        )

        with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
            with patch("app.workers.metadata.extractor.subprocess.run", return_value=completed):
                metadata = worker.extract_for_file(file_row)

        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertIsNone(metadata.width)
        self.assertIsNone(metadata.height)
        self.assertIsNone(metadata.duration_ms)

    def test_video_metadata_expected_failures_do_not_escape_scan(self) -> None:
        worker = MetadataExtractorWorker()
        file_row = self._build_video_file(Path("C:/Video Library/clip.mp4"))

        with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
            with patch(
                "app.workers.metadata.extractor.subprocess.run",
                side_effect=TimeoutExpired(cmd=["ffprobe"], timeout=10, stderr=b"\x80\x81"),
            ):
                with self.assertRaises(OSError) as captured:
                    worker.extract_for_file(file_row)

        self.assertTrue(worker.is_expected_extraction_failure(captured.exception))
        self.assertIn("��", str(captured.exception))

    def test_video_metadata_nonzero_ffprobe_exit_is_expected_failure(self) -> None:
        worker = MetadataExtractorWorker()
        file_row = self._build_video_file(Path("C:/Video Library/clip.mp4"))
        completed = CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"invalid data \x80\x81")

        with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
            with patch("app.workers.metadata.extractor.subprocess.run", return_value=completed):
                with self.assertRaises(OSError) as captured:
                    worker.extract_for_file(file_row)

        self.assertTrue(worker.is_expected_extraction_failure(captured.exception))
        self.assertIn("invalid data ��", str(captured.exception))

    def test_video_metadata_nonzero_ffprobe_stderr_is_bounded(self) -> None:
        worker = MetadataExtractorWorker()
        file_row = self._build_video_file(Path("C:/Video Library/clip.mp4"))
        completed = CompletedProcess(args=[], returncode=1, stdout=b"", stderr=(b"x" * 4100) + b"\x80\x81")

        with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
            with patch("app.workers.metadata.extractor.subprocess.run", return_value=completed):
                with self.assertRaises(OSError) as captured:
                    worker.extract_for_file(file_row)

        self.assertTrue(worker.is_expected_extraction_failure(captured.exception))
        self.assertLessEqual(len(str(captured.exception)), 4000)
        self.assertIn("��", str(captured.exception))

    def test_video_metadata_invalid_json_is_expected_failure(self) -> None:
        worker = MetadataExtractorWorker()
        file_row = self._build_video_file(Path("C:/Video Library/clip.mp4"))
        completed = CompletedProcess(args=[], returncode=0, stdout=b"not-json\x80", stderr=b"")

        with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
            with patch("app.workers.metadata.extractor.subprocess.run", return_value=completed):
                with self.assertRaises(ValueError) as captured:
                    worker.extract_for_file(file_row)

        self.assertTrue(worker.is_expected_extraction_failure(captured.exception))

    def test_video_metadata_large_stdout_json_is_not_truncated_before_parse(self) -> None:
        file_row = self._build_video_file(Path("C:/Video Library/clip.mp4"))
        worker = MetadataExtractorWorker()
        padding = ",".join(f'"tag_{index}":"value"' for index in range(700))
        completed = CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                b'{"streams":[{"codec_type":"video","width":640,"height":360,"duration":"5"}],'
                + f'"format":{{"duration":"5","tags":{{{padding}}}}}}}'.encode("utf-8")
            ),
            stderr=b"",
        )

        with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
            with patch("app.workers.metadata.extractor.subprocess.run", return_value=completed):
                metadata = worker.extract_for_file(file_row)

        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertEqual((640, 360, 5000), (metadata.width, metadata.height, metadata.duration_ms))

    def test_video_metadata_missing_ffprobe_is_expected_failure(self) -> None:
        worker = MetadataExtractorWorker()
        file_row = self._build_video_file(Path("C:/Video Library/clip.mp4"))

        with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value=None):
            with self.assertRaises(FileNotFoundError) as captured:
                worker.extract_for_file(file_row)

        self.assertTrue(worker.is_expected_extraction_failure(captured.exception))

    def test_extracts_video_metadata_passes_windows_path_as_single_subprocess_arg(self) -> None:
        file_path = Path("C:/视频 Clips/long sample.mp4")
        file_row = self._build_video_file(file_path)
        worker = MetadataExtractorWorker()
        completed = CompletedProcess(
            args=[],
            returncode=0,
            stdout=b'{"streams":[{"codec_type":"video","width":640,"height":360,"duration":"5"}],"format":{}}',
            stderr=b"",
        )

        with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
            with patch("app.workers.metadata.extractor.subprocess.run", return_value=completed) as run_mock:
                worker.extract_for_file(file_row)

        command = run_mock.call_args.args[0]
        self.assertEqual(str(file_path), command[-1])
        self.assertNotIn("shell", run_mock.call_args.kwargs)

    def test_resolves_ffprobe_from_configured_ffmpeg_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ffmpeg_path = root / "ffmpeg.exe"
            ffprobe_path = root / "ffprobe.exe"
            ffmpeg_path.write_text("fake", encoding="utf-8")
            ffprobe_path.write_text("fake", encoding="utf-8")

            with patch("app.workers.metadata.extractor.settings.ffmpeg_path", ffmpeg_path):
                with patch(
                    "app.workers.metadata.extractor.shutil.which",
                    side_effect=AssertionError("PATH lookup should not run when ffprobe sibling exists"),
                ):
                    resolved_path = MetadataExtractorWorker()._resolve_ffprobe_path()

        self.assertEqual(str(ffprobe_path), resolved_path)

    def test_extracts_video_metadata_and_persists_during_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "clip.mp4").write_bytes(b"fake-video")
            completed = CompletedProcess(
                args=[],
                returncode=0,
                stdout=b'{"streams":[{"codec_type":"video","width":1920,"height":1080,"duration":"123.456"}],"format":{}}',
                stderr=b"",
            )

            with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
                with patch("app.workers.metadata.extractor.subprocess.run", return_value=completed):
                    source_id = self._create_source(root)
                    response = self._run_scan(source_id)

            self.assertEqual(202, response.status_code)
            self.assertEqual("succeeded", response.json()["status"])
            file_row = self._get_file_by_name("clip.mp4")
            self.assertIsNotNone(file_row)
            metadata_row = self._get_metadata(file_row.id)
            self.assertIsNotNone(metadata_row)
            assert metadata_row is not None
            self.assertEqual((1920, 1080, 123456), (metadata_row.width, metadata_row.height, metadata_row.duration_ms))

        engine.dispose()

    def test_extracts_duration_only_video_metadata_and_persists_during_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "duration-only.mp4").write_bytes(b"fake-video")
            completed = CompletedProcess(
                args=[],
                returncode=0,
                stdout=b'{"streams":[{"codec_type":"video","duration":"33.250"}],"format":{}}',
                stderr=b"",
            )

            with patch.object(MetadataExtractorWorker, "_resolve_ffprobe_path", return_value="ffprobe"):
                with patch("app.workers.metadata.extractor.subprocess.run", return_value=completed):
                    source_id = self._create_source(root)
                    response = self._run_scan(source_id)

            self.assertEqual(202, response.status_code)
            self.assertEqual("succeeded", response.json()["status"])
            file_row = self._get_file_by_name("duration-only.mp4")
            self.assertIsNotNone(file_row)
            metadata_row = self._get_metadata(file_row.id)
            self.assertIsNotNone(metadata_row)
            assert metadata_row is not None
            self.assertIsNone(metadata_row.width)
            self.assertIsNone(metadata_row.height)
            self.assertEqual(33250, metadata_row.duration_ms)

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

    def _build_video_file(self, path: Path) -> File:
        return File(
            source_id=1,
            path=str(path),
            parent_path=str(path.parent),
            name=path.name,
            stem=path.stem,
            extension=path.suffix.lstrip("."),
            file_type="video",
            mime_type=None,
            size_bytes=1024,
            created_at_fs=None,
            modified_at_fs=_dt(9),
            discovered_at=_dt(9),
            last_seen_at=_dt(9),
            is_deleted=False,
            checksum_hint=None,
            updated_at=_dt(9),
        )

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
