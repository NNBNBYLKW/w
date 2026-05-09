from concurrent.futures import ThreadPoolExecutor
import contextlib
from datetime import datetime
import io
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from threading import Lock
from unittest.mock import PropertyMock, patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select, text

from app.core.config.settings import Settings, settings
from app.db.models.file import File
from app.db.models.file_metadata import FileMetadata
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app
from app.services.thumbnails.service import PdfRenderSubprocessError, ThumbnailService, VIDEO_PREVIEW_FRAME_COUNT, VIDEO_PREVIEW_VERSION
from app.workers.thumbnails.exe_icon_generator import ExeIconGenerationError, ExeIconGeneratorWorker
from app.workers.thumbnails.generator import ThumbnailGeneratorWorker
from app.workers.thumbnails.pdf_generator import PdfThumbnailGenerationError, PdfThumbnailGeneratorWorker
from app.workers.thumbnails import pdf_render_cli
from app.workers.thumbnails.video_generator import VideoThumbnailGenerationError, VideoThumbnailGeneratorWorker


class Phase2BThumbnailSurfaceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_settings_support_packaged_runtime_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            ffmpeg_path = Path(data_dir) / "ffmpeg.exe"
            ffmpeg_path.write_text("fake", encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "WORKBENCH_DATA_DIR": str(Path(data_dir)),
                    "WORKBENCH_FFMPEG_PATH": str(ffmpeg_path),
                },
            ):
                configured_settings = Settings()

        self.assertEqual(Path(data_dir), configured_settings.data_dir)
        self.assertEqual(ffmpeg_path, configured_settings.ffmpeg_path)

    def test_video_generator_prefers_configured_ffmpeg_path(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            ffmpeg_path = Path(data_dir) / "ffmpeg.exe"
            ffmpeg_path.write_text("fake", encoding="utf-8")
            worker = VideoThumbnailGeneratorWorker()

            with patch.object(settings, "ffmpeg_path", ffmpeg_path):
                with patch(
                    "app.workers.thumbnails.video_generator.shutil.which",
                    side_effect=AssertionError("PATH lookup should not run when ffmpeg path is configured"),
                ):
                    resolved_path = worker._resolve_ffmpeg_path()

        self.assertEqual(str(ffmpeg_path), resolved_path)

    def test_video_generator_captures_ffmpeg_output_as_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            root = Path(data_dir)
            source_path = root / "clip.mp4"
            output_path = root / "thumb.jpg"
            source_path.write_bytes(b"fake-video")
            worker = VideoThumbnailGeneratorWorker()

            def complete_ffmpeg(command, **kwargs):
                output_path.write_bytes(b"jpg")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout=b"", stderr=b"")

            with patch.object(VideoThumbnailGeneratorWorker, "_resolve_ffmpeg_path", return_value="ffmpeg"):
                with patch("app.workers.thumbnails.video_generator.subprocess.run", side_effect=complete_ffmpeg) as run_mock:
                    worker._run_ffmpeg_frame_extract(source_path, output_path, seek_seconds=1, width=320)

        self.assertEqual(subprocess.PIPE, run_mock.call_args.kwargs["stdout"])
        self.assertEqual(subprocess.PIPE, run_mock.call_args.kwargs["stderr"])
        self.assertIs(run_mock.call_args.kwargs["text"], False)
        self.assertNotIn("shell", run_mock.call_args.kwargs)

    def test_video_generator_decodes_invalid_stderr_bytes_on_failed_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            root = Path(data_dir)
            source_path = root / "clip.mp4"
            output_path = root / "thumb.jpg"
            source_path.write_bytes(b"fake-video")
            completed = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"bad bytes \x80\x81")
            worker = VideoThumbnailGeneratorWorker()

            with patch.object(VideoThumbnailGeneratorWorker, "_resolve_ffmpeg_path", return_value="ffmpeg"):
                with patch("app.workers.thumbnails.video_generator.subprocess.run", return_value=completed):
                    with self.assertRaises(VideoThumbnailGenerationError) as captured:
                        worker._run_ffmpeg_frame_extract(source_path, output_path, seek_seconds=1, width=320)

        self.assertIn("bad bytes ��", str(captured.exception))

    def test_video_generator_bounds_failed_ffmpeg_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            root = Path(data_dir)
            source_path = root / "clip.mp4"
            output_path = root / "thumb.jpg"
            source_path.write_bytes(b"fake-video")
            completed = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"", stderr=(b"x" * 4100) + b"\x80\x81")
            worker = VideoThumbnailGeneratorWorker()

            with patch.object(VideoThumbnailGeneratorWorker, "_resolve_ffmpeg_path", return_value="ffmpeg"):
                with patch("app.workers.thumbnails.video_generator.subprocess.run", return_value=completed):
                    with self.assertRaises(VideoThumbnailGenerationError) as captured:
                        worker._run_ffmpeg_frame_extract(source_path, output_path, seek_seconds=1, width=320)

        self.assertLessEqual(len(str(captured.exception)), 4000)
        self.assertIn("��", str(captured.exception))

    def test_video_generator_decodes_invalid_stderr_bytes_on_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            root = Path(data_dir)
            source_path = root / "clip.mp4"
            output_path = root / "thumb.jpg"
            source_path.write_bytes(b"fake-video")
            timeout = subprocess.TimeoutExpired(cmd=["ffmpeg"], timeout=15, stderr=b"timeout bytes \x80\x81")
            worker = VideoThumbnailGeneratorWorker()

            with patch.object(VideoThumbnailGeneratorWorker, "_resolve_ffmpeg_path", return_value="ffmpeg"):
                with patch("app.workers.thumbnails.video_generator.subprocess.run", side_effect=timeout):
                    with self.assertRaises(VideoThumbnailGenerationError) as captured:
                        worker._run_ffmpeg_frame_extract(source_path, output_path, seek_seconds=1, width=320)

        self.assertIn("timeout bytes ��", str(captured.exception))

    def test_video_generator_missing_ffmpeg_raises_generation_error(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            root = Path(data_dir)
            source_path = root / "clip.mp4"
            output_path = root / "thumb.jpg"
            source_path.write_bytes(b"fake-video")
            worker = VideoThumbnailGeneratorWorker()

            with patch.object(VideoThumbnailGeneratorWorker, "_resolve_ffmpeg_path", return_value=None):
                with self.assertRaises(VideoThumbnailGenerationError):
                    worker._run_ffmpeg_frame_extract(source_path, output_path, seek_seconds=1, width=320)

    def test_video_generator_failed_ffmpeg_is_not_success_even_if_output_exists(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            root = Path(data_dir)
            source_path = root / "clip.mp4"
            output_path = root / "thumb.jpg"
            source_path.write_bytes(b"fake-video")
            output_path.write_bytes(b"existing-output")
            completed = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"failed")
            worker = VideoThumbnailGeneratorWorker()

            with patch.object(VideoThumbnailGeneratorWorker, "_resolve_ffmpeg_path", return_value="ffmpeg"):
                with patch("app.workers.thumbnails.video_generator.subprocess.run", return_value=completed):
                    with self.assertRaises(VideoThumbnailGenerationError):
                        worker._run_ffmpeg_frame_extract(source_path, output_path, seek_seconds=1, width=320)

    def test_video_generator_success_requires_non_empty_output(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            root = Path(data_dir)
            source_path = root / "clip.mp4"
            output_path = root / "thumb.jpg"
            source_path.write_bytes(b"fake-video")
            completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b"")
            worker = VideoThumbnailGeneratorWorker()

            with patch.object(VideoThumbnailGeneratorWorker, "_resolve_ffmpeg_path", return_value="ffmpeg"):
                with patch("app.workers.thumbnails.video_generator.subprocess.run", return_value=completed):
                    with self.assertRaises(VideoThumbnailGenerationError):
                        worker._run_ffmpeg_frame_extract(source_path, output_path, seek_seconds=1, width=320)

    def test_video_preview_seek_seconds_use_existing_fallback_for_invalid_duration(self) -> None:
        service = ThumbnailService()
        expected = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

        self.assertEqual(expected, service._build_video_preview_seek_seconds(None))
        self.assertEqual(expected, service._build_video_preview_seek_seconds(0))
        self.assertEqual(expected, service._build_video_preview_seek_seconds(-1000))

    def test_video_preview_seek_seconds_are_interior_for_short_duration(self) -> None:
        service = ThumbnailService()
        seeks = service._build_video_preview_seek_seconds(10_000)

        self.assertEqual(VIDEO_PREVIEW_FRAME_COUNT, len(seeks))
        self.assertEqual(sorted(seeks), seeks)
        self.assertTrue(all(0 < seek < 10 for seek in seeks))
        self.assertAlmostEqual(0.5 + 9 * (1 / 7), seeks[0])
        self.assertAlmostEqual(0.5 + 9 * (6 / 7), seeks[-1])

    def test_video_preview_seek_seconds_are_spread_for_medium_duration(self) -> None:
        service = ThumbnailService()
        seeks = service._build_video_preview_seek_seconds(60_000)

        self.assertEqual(VIDEO_PREVIEW_FRAME_COUNT, len(seeks))
        self.assertEqual(sorted(seeks), seeks)
        self.assertTrue(all(0 < seek < 60 for seek in seeks))
        self.assertLess(seeks[0], 10)
        self.assertGreater(seeks[-1], 50)

    def test_video_preview_seek_seconds_are_spread_for_long_duration(self) -> None:
        service = ThumbnailService()
        seeks = service._build_video_preview_seek_seconds(600_000)

        self.assertEqual(VIDEO_PREVIEW_FRAME_COUNT, len(seeks))
        self.assertEqual(sorted(seeks), seeks)
        self.assertTrue(all(0 < seek < 600 for seek in seeks))
        self.assertGreater(seeks[-1], 500)

    def test_video_preview_cache_key_includes_version(self) -> None:
        service = ThumbnailService()
        file_row = File(
            id=42,
            name="clip.mp4",
            path="C:\\media\\clip.mp4",
            extension="mp4",
            file_type="video",
            size_bytes=1234,
        )
        file_row.discovered_at = datetime(2024, 1, 1)

        current_path = service._build_video_preview_dir(file_row)
        with patch("app.services.thumbnails.service.VIDEO_PREVIEW_VERSION", "v1"):
            legacy_path = service._build_video_preview_dir(file_row)

        self.assertEqual("v2", VIDEO_PREVIEW_VERSION)
        self.assertNotEqual(legacy_path, current_path)

    def test_exe_icon_generator_gracefully_skips_non_windows_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            exe_path = Path(data_dir) / "tool.exe"
            exe_path.write_bytes(b"fake-exe")
            worker = ExeIconGeneratorWorker()

            with patch.object(ExeIconGeneratorWorker, "_is_windows", return_value=False):
                with self.assertRaises(ExeIconGenerationError):
                    worker.generate_icon(exe_path, Path(data_dir) / "icon.png")

    def test_exe_icon_normalization_centers_small_top_left_icon(self) -> None:
        worker = ExeIconGeneratorWorker()
        source = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        source.alpha_composite(Image.new("RGBA", (48, 48), (12, 34, 56, 255)), dest=(0, 0))

        normalized = worker.normalize_icon_canvas(source, target_size=256)
        alpha_bbox = normalized.getchannel("A").getbbox()

        self.assertEqual((256, 256), normalized.size)
        self.assertEqual("RGBA", normalized.mode)
        self.assertIsNotNone(alpha_bbox)
        assert alpha_bbox is not None
        left, top, right, bottom = alpha_bbox
        content_center = ((left + right) / 2, (top + bottom) / 2)
        self.assertAlmostEqual(128, content_center[0], delta=1)
        self.assertAlmostEqual(128, content_center[1], delta=1)
        self.assertGreaterEqual(right - left, 190)
        self.assertGreaterEqual(bottom - top, 190)

    def test_exe_icon_normalization_handles_empty_transparent_icon(self) -> None:
        worker = ExeIconGeneratorWorker()
        source = Image.new("RGBA", (256, 256), (0, 0, 0, 0))

        normalized = worker.normalize_icon_canvas(source, target_size=256)

        self.assertEqual((256, 256), normalized.size)
        self.assertEqual("RGBA", normalized.mode)
        self.assertIsNone(normalized.getchannel("A").getbbox())

    def test_exe_icon_normalization_preserves_full_canvas_icon(self) -> None:
        worker = ExeIconGeneratorWorker()
        source = Image.new("RGBA", (256, 256), (12, 34, 56, 255))

        normalized = worker.normalize_icon_canvas(source, target_size=256)

        self.assertEqual((256, 256), normalized.size)
        self.assertEqual("RGBA", normalized.mode)
        self.assertEqual((0, 0, 256, 256), normalized.getchannel("A").getbbox())

    def test_pdf_render_cli_returns_success_when_output_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            source_path = Path(data_dir) / "manual.pdf"
            output_path = Path(data_dir) / "manual.png"
            source_path.write_bytes(b"%PDF-1.7 fake-pdf")

            def write_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")

            with patch.object(PdfThumbnailGeneratorWorker, "generate_thumbnail", new=write_pdf_thumbnail):
                exit_code = pdf_render_cli.main(["--source", str(source_path), "--output", str(output_path), "--width", "384"])

            self.assertEqual(0, exit_code)
            self.assertTrue(output_path.exists())

    def test_pdf_render_cli_returns_failure_when_output_is_missing_or_zero_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            source_path = Path(data_dir) / "manual.pdf"
            missing_output_path = Path(data_dir) / "missing.png"
            zero_output_path = Path(data_dir) / "zero.png"
            source_path.write_bytes(b"%PDF-1.7 fake-pdf")

            def do_not_write_output(_, __, ___, *, width: int = 384) -> None:
                return None

            def write_zero_byte_output(_, __, output_path: Path, *, width: int = 384) -> None:
                output_path.write_bytes(b"")

            stderr = io.StringIO()
            with patch.object(PdfThumbnailGeneratorWorker, "generate_thumbnail", new=do_not_write_output):
                with contextlib.redirect_stderr(stderr):
                    missing_exit_code = pdf_render_cli.main(
                        ["--source", str(source_path), "--output", str(missing_output_path), "--width", "384"]
                    )
            with patch.object(PdfThumbnailGeneratorWorker, "generate_thumbnail", new=write_zero_byte_output):
                with contextlib.redirect_stderr(stderr):
                    zero_exit_code = pdf_render_cli.main(
                        ["--source", str(source_path), "--output", str(zero_output_path), "--width", "384"]
                    )

        self.assertNotEqual(0, missing_exit_code)
        self.assertNotEqual(0, zero_exit_code)
        self.assertIn("PDF render CLI did not create a valid output file", stderr.getvalue())

    def test_pdf_render_cli_returns_failure_with_traceback_when_generator_fails(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            source_path = Path(data_dir) / "manual.pdf"
            output_path = Path(data_dir) / "manual.png"
            source_path.write_bytes(b"%PDF-1.7 fake-pdf")

            def fail_pdf_thumbnail(_, __, ___, *, width: int = 384) -> None:
                raise PdfThumbnailGenerationError("cli render failed")

            stderr = io.StringIO()
            with patch.object(PdfThumbnailGeneratorWorker, "generate_thumbnail", new=fail_pdf_thumbnail):
                with contextlib.redirect_stderr(stderr):
                    exit_code = pdf_render_cli.main(["--source", str(source_path), "--output", str(output_path), "--width", "384"])

        self.assertNotEqual(0, exit_code)
        self.assertIn("Traceback", stderr.getvalue())
        self.assertIn("cli render failed", stderr.getvalue())

    def test_pdf_subprocess_runner_integration_renders_generated_pdf(self) -> None:
        try:
            import pypdfium2  # noqa: F401
        except Exception as error:
            self.skipTest(f"pypdfium2 is not available: {error}")

        with tempfile.TemporaryDirectory() as data_dir:
            source_path = Path(data_dir) / "generated.pdf"
            output_path = Path(data_dir) / "generated.png"
            Image.new("RGB", (32, 32), color=(255, 255, 255)).save(source_path, format="PDF")

            ThumbnailService()._render_pdf_thumbnail_subprocess(source_path, output_path, width=128)

            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)

    def test_pdf_subprocess_runner_uses_argv_without_shell(self) -> None:
        service = ThumbnailService()
        completed = subprocess.CompletedProcess(args=["python"], returncode=0, stdout="", stderr="")

        with patch("app.services.thumbnails.service.subprocess.run", return_value=completed) as run_mock:
            service._render_pdf_thumbnail_subprocess(Path("manual.pdf"), Path("manual.png"), width=384)

        command = run_mock.call_args.args[0]
        self.assertIsInstance(command, list)
        self.assertIn("-m", command)
        self.assertIn("app.workers.thumbnails.pdf_render_cli", command)
        self.assertEqual(service._get_backend_root(), run_mock.call_args.kwargs["cwd"])
        self.assertEqual(False, run_mock.call_args.kwargs["shell"])

    def test_pdf_subprocess_runner_reports_bounded_failure_output(self) -> None:
        service = ThumbnailService()
        completed = subprocess.CompletedProcess(
            args=["python"],
            returncode=7,
            stdout="o" * 1500,
            stderr="e" * 4500,
        )

        with patch("app.services.thumbnails.service.subprocess.run", return_value=completed):
            with self.assertRaises(RuntimeError) as raised:
                service._render_pdf_thumbnail_subprocess(Path("manual.pdf"), Path("manual.png"), width=384)

        message = str(raised.exception)
        self.assertIn("returncode=7", message)
        self.assertIn("stdout_tail=", message)
        self.assertIn("stderr_tail=", message)
        self.assertNotIn("o" * 1001, message)
        self.assertNotIn("e" * 4001, message)

    def test_pdf_subprocess_runner_reports_bounded_timeout_output(self) -> None:
        service = ThumbnailService()
        timeout = subprocess.TimeoutExpired(
            cmd=["python"],
            timeout=60,
            output="o" * 1500,
            stderr="e" * 4500,
        )

        with patch("app.services.thumbnails.service.subprocess.run", side_effect=timeout):
            with self.assertRaises(RuntimeError) as raised:
                service._render_pdf_thumbnail_subprocess(Path("manual.pdf"), Path("manual.png"), width=384)

        message = str(raised.exception)
        self.assertIn("timed out", message)
        self.assertIn("stdout_tail=", message)
        self.assertIn("stderr_tail=", message)
        self.assertNotIn("o" * 1001, message)
        self.assertNotIn("e" * 4001, message)

    def test_returns_thumbnail_for_image_file(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            self._create_image(root / "cover.png", (1200, 900))
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("cover.png")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    response = client.get(f"/files/{file_row.id}/thumbnail")

            self.assertEqual(200, response.status_code)
            self.assertEqual("image/jpeg", response.headers["content-type"])
            self.assertTrue((Path(data_dir) / "thumbnails").exists())
            self.assertGreater(len(response.content), 0)

    def test_returns_thumbnail_for_pdf_file_using_pdf_worker(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "manual.pdf").write_bytes(b"%PDF-1.7 fake-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("manual.pdf")
            self.assertIsNotNone(file_row)

            def write_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=write_pdf_thumbnail):
                    with TestClient(app) as client:
                        self._warmup_and_wait_for_file(client, file_row.id, Path(data_dir) / "thumbnails" / "pdf")
                        response = client.get(f"/files/{file_row.id}/thumbnail")

            self.assertEqual(200, response.status_code)
            self.assertEqual("image/png", response.headers["content-type"])
            generated_files = list((Path(data_dir) / "thumbnails" / "pdf").glob("*.png"))
            self.assertEqual(1, len(generated_files))
            with Image.open(generated_files[0]) as generated_thumbnail:
                self.assertEqual((384, 256), generated_thumbnail.size)
            self.assertGreater(len(response.content), 0)

    def test_pdf_warmup_uses_subprocess_runner_not_main_process_generator(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "manual.pdf").write_bytes(b"%PDF-1.7 fake-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("manual.pdf")
            self.assertIsNotNone(file_row)
            service = ThumbnailService()

            def write_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(
                    service.pdf_generator,
                    "generate_thumbnail",
                    side_effect=AssertionError("main-process PDF generator must not run from warmup"),
                ):
                    with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=write_pdf_thumbnail):
                        self.assertEqual("queued", service._warmup_file(file_row))
                        paths = self._wait_for_generated_files(Path(data_dir) / "thumbnails" / "pdf")

            self.assertEqual(1, len(paths))
            self.assertEqual({}, service._warmup_failures_by_cache_key)

    def test_returns_thumbnail_for_uppercase_pdf_extension_using_pdf_worker(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "manual.PDF").write_bytes(b"%PDF-1.7 fake-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("manual.PDF")
            self.assertIsNotNone(file_row)

            def write_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=write_pdf_thumbnail):
                    with TestClient(app) as client:
                        self._warmup_and_wait_for_file(client, file_row.id, Path(data_dir) / "thumbnails" / "pdf")
                        response = client.get(f"/files/{file_row.id}/thumbnail")

            self.assertEqual(200, response.status_code)
            self.assertEqual("image/png", response.headers["content-type"])

    def test_reuses_cached_pdf_thumbnail_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "manual.pdf").write_bytes(b"%PDF-1.7 fake-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("manual.pdf")
            self.assertIsNotNone(file_row)

            def write_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=write_pdf_thumbnail):
                        self._warmup_and_wait_for_file(client, file_row.id, Path(data_dir) / "thumbnails" / "pdf")
                        first_response = client.get(f"/files/{file_row.id}/thumbnail")
                    self.assertEqual(200, first_response.status_code)

                    with patch.object(
                        ThumbnailService,
                        "_render_pdf_thumbnail_subprocess",
                        side_effect=AssertionError("pdf thumbnail generator should not run when cache exists"),
                    ):
                        second_response = client.get(f"/files/{file_row.id}/thumbnail")

            self.assertEqual(200, second_response.status_code)
            self.assertEqual("image/png", second_response.headers["content-type"])

    def test_concurrent_pdf_thumbnail_requests_share_single_generation(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "manual.pdf").write_bytes(b"%PDF-1.7 fake-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("manual.pdf")
            self.assertIsNotNone(file_row)
            service = ThumbnailService()
            call_count = 0
            call_count_lock = Lock()

            def write_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                nonlocal call_count
                with call_count_lock:
                    call_count += 1
                time.sleep(0.05)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=write_pdf_thumbnail):
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        statuses = list(executor.map(lambda _: service._warmup_file(file_row), range(4)))
                    paths = self._wait_for_generated_files(Path(data_dir) / "thumbnails" / "pdf")

            self.assertEqual(1, call_count)
            self.assertIn("queued", statuses)
            self.assertTrue(all(status in {"queued", "in_progress"} for status in statuses))
            self.assertEqual(1, len(paths))

    def test_pdf_warmup_creates_missing_cache_dir_and_preserves_tmp_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "manual.pdf").write_bytes(b"%PDF-1.7 fake-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("manual.pdf")
            self.assertIsNotNone(file_row)
            pdf_dir = Path(data_dir) / "thumbnails" / "pdf"
            captured_output_paths: list[Path] = []

            def write_pdf_thumbnail_without_mkdir(_, __, output_path: Path, *, width: int = 384) -> None:
                captured_output_paths.append(output_path)
                self.assertTrue(output_path.parent.exists())
                self.assertEqual(".png", output_path.suffix)
                Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                self.assertFalse(pdf_dir.exists())
                with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=write_pdf_thumbnail_without_mkdir):
                    with TestClient(app) as client:
                        self._warmup_and_wait_for_file(client, file_row.id, pdf_dir)
                        response = client.get(f"/files/{file_row.id}/thumbnail")
                        second_warmup = client.post("/files/thumbnails/warmup", json={"file_ids": [file_row.id]})

            self.assertEqual(200, response.status_code)
            self.assertEqual("image/png", response.headers["content-type"])
            self.assertEqual([file_row.id], second_warmup.json()["cached"])
            self.assertEqual(1, len(captured_output_paths))
            self.assertIn(".tmp-", captured_output_paths[0].name)
            self.assertFalse(captured_output_paths[0].exists())

    def test_pdf_warmup_drains_fifty_items_without_failures(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            for index in range(50):
                (root / f"manual-{index:02d}.pdf").write_bytes(f"%PDF-1.7 fake-pdf-{index}".encode("utf-8"))
            source_id = self._create_source(root)
            self._run_scan(source_id)
            with SessionLocal() as session:
                file_rows = list(session.scalars(select(File).where(File.name.like("manual-%.pdf"))))
            self.assertEqual(50, len(file_rows))
            file_ids = [file_row.id for file_row in file_rows]
            pdf_dir = Path(data_dir) / "thumbnails" / "pdf"

            def write_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=write_pdf_thumbnail):
                    with TestClient(app) as client:
                        first_warmup = client.post("/files/thumbnails/warmup", json={"file_ids": file_ids})
                        self.assertEqual(200, first_warmup.status_code)
                        self.assertEqual([], first_warmup.json()["failed"])
                        self._wait_for_generated_files(pdf_dir, expected_count=50)
                        second_warmup = client.post("/files/thumbnails/warmup", json={"file_ids": file_ids})

            payload = second_warmup.json()
            self.assertEqual(sorted(file_ids), sorted(payload["cached"]))
            self.assertEqual([], payload["queued"])
            self.assertEqual([], payload["in_progress"])
            self.assertEqual([], payload["failed"])
            self.assertEqual(50, len(list(pdf_dir.glob("*.png"))))

    def test_pdf_warmup_serializes_generator_calls_across_distinct_files(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            for index in range(20):
                (root / f"parallel-{index:02d}.pdf").write_bytes(f"%PDF-1.7 fake-pdf-{index}".encode("utf-8"))
            source_id = self._create_source(root)
            self._run_scan(source_id)
            with SessionLocal() as session:
                file_rows = list(session.scalars(select(File).where(File.name.like("parallel-%.pdf"))))
            self.assertEqual(20, len(file_rows))
            file_ids = [file_row.id for file_row in file_rows]
            pdf_dir = Path(data_dir) / "thumbnails" / "pdf"
            active_count = 0
            max_active_count = 0
            concurrent_entry_errors: list[str] = []
            active_count_lock = Lock()

            def write_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                nonlocal active_count, max_active_count
                with active_count_lock:
                    active_count += 1
                    max_active_count = max(max_active_count, active_count)
                    if active_count > 1:
                        concurrent_entry_errors.append(str(output_path))
                try:
                    time.sleep(0.05)
                    Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")
                finally:
                    with active_count_lock:
                        active_count -= 1

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=write_pdf_thumbnail):
                    with TestClient(app) as client:
                        first_warmup = client.post("/files/thumbnails/warmup", json={"file_ids": file_ids})
                        self.assertEqual(200, first_warmup.status_code)
                        self.assertEqual([], first_warmup.json()["failed"])
                        self._wait_for_generated_files(pdf_dir, expected_count=20)
                        second_warmup = client.post("/files/thumbnails/warmup", json={"file_ids": file_ids})

            payload = second_warmup.json()
            self.assertEqual(1, max_active_count)
            self.assertEqual([], concurrent_entry_errors)
            self.assertEqual(sorted(file_ids), sorted(payload["cached"]))
            self.assertEqual([], payload["queued"])
            self.assertEqual([], payload["in_progress"])
            self.assertEqual([], payload["failed"])
            self.assertEqual(20, len(list(pdf_dir.glob("*.png"))))

    def test_pdf_thumbnail_lock_releases_after_generation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "manual.pdf").write_bytes(b"%PDF-1.7 fake-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("manual.pdf")
            self.assertIsNotNone(file_row)
            service = ThumbnailService()
            call_count = 0

            def flaky_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise PdfThumbnailGenerationError("temporary pdf failure")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=flaky_pdf_thumbnail):
                    self.assertEqual("queued", service._warmup_file(file_row))
                    self._wait_for_condition(lambda: call_count >= 1)
                    self.assertEqual("failed", service._warmup_file(file_row))
                    failure = next(iter(service._warmup_failures_by_cache_key.values()))
                    self.assertEqual(file_row.id, failure.file_id)
                    self.assertEqual("pdf", failure.kind)
                    self.assertIn("PdfThumbnailGenerationError: temporary pdf failure", failure.reason)
                    service._warmup_failures_by_cache_key.clear()
                    self.assertEqual("queued", service._warmup_file(file_row))
                    path = self._wait_for_generated_files(Path(data_dir) / "thumbnails" / "pdf")[0]

            self.assertEqual(2, call_count)
            self.assertTrue(path.exists())
            self.assertEqual({}, service._warmup_failures_by_cache_key)

    def test_pdf_warmup_cleans_temp_file_after_generator_failure(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "manual.pdf").write_bytes(b"%PDF-1.7 fake-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("manual.pdf")
            self.assertIsNotNone(file_row)
            service = ThumbnailService()
            captured_output_paths: list[Path] = []

            def failing_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                captured_output_paths.append(output_path)
                output_path.write_bytes(b"partial")
                raise PdfThumbnailGenerationError("boom")

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=failing_pdf_thumbnail):
                    self.assertEqual("queued", service._warmup_file(file_row))
                    self._wait_for_condition(lambda: bool(service._warmup_failures_by_cache_key))

            self.assertEqual(1, len(captured_output_paths))
            self.assertFalse(captured_output_paths[0].exists())
            self.assertEqual([], list((Path(data_dir) / "thumbnails" / "pdf").glob("pdf_*.png")))

    def test_pdf_warmup_failure_debug_includes_subprocess_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "manual.pdf").write_bytes(b"%PDF-1.7 fake-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("manual.pdf")
            self.assertIsNotNone(file_row)
            service = ThumbnailService()

            def fail_pdf_subprocess(_, source_path: Path, output_path: Path, *, width: int = 384) -> None:
                raise PdfRenderSubprocessError(
                    "PDF render subprocess failed returncode=9.",
                    {
                        "subprocess_command": ["python", "-m", "app.workers.thumbnails.pdf_render_cli"],
                        "subprocess_cwd": str(Path("apps/backend")),
                        "subprocess_returncode": 9,
                        "subprocess_stdout_tail": "stdout tail",
                        "subprocess_stderr_tail": "stderr tail",
                        "subprocess_timeout": False,
                    },
                )

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=fail_pdf_subprocess):
                    self.assertEqual("queued", service._warmup_file(file_row))
                    self._wait_for_condition(lambda: bool(service._warmup_failures_by_cache_key))

                with SessionLocal() as session:
                    debug = service.get_warmup_debug_for_file(session, file_row.id)

            failure = debug["failure"]
            self.assertIsNotNone(failure)
            self.assertEqual("pdf", failure["kind"])
            self.assertIn("PDF render subprocess failed", failure["reason"])
            self.assertIn(".tmp-", failure["tmp_path"])
            self.assertTrue(failure["source_exists"])
            self.assertGreater(failure["source_size"], 0)
            self.assertTrue(failure["source_first_bytes_hex"].startswith(b"%PDF".hex()))
            self.assertEqual(9, failure["subprocess_returncode"])
            self.assertEqual("stderr tail", failure["subprocess_stderr_tail"])
            self.assertFalse(failure["subprocess_timeout"])

    def test_returns_thumbnail_not_available_when_pdf_generation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "broken.pdf").write_bytes(b"not-a-real-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("broken.pdf")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(
                    ThumbnailService,
                    "_render_pdf_thumbnail_subprocess",
                    side_effect=PdfThumbnailGenerationError("pdf rendering failed"),
                ):
                    with TestClient(app) as client:
                        warmup_response = client.post("/files/thumbnails/warmup", json={"file_ids": [file_row.id]})
                        self.assertEqual(200, warmup_response.status_code)
                        response = self._wait_for_thumbnail_error_code(client, file_row.id, "THUMBNAIL_NOT_AVAILABLE")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {
                "error": {
                    "code": "THUMBNAIL_NOT_AVAILABLE",
                    "message": "Thumbnail is not available for this file.",
                }
            },
            response.json(),
        )

    def test_non_pdf_document_does_not_use_pdf_thumbnail_worker(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "book.epub").write_bytes(b"fake-epub")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("book.epub")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(
                    ThumbnailService,
                    "_render_pdf_thumbnail_subprocess",
                    side_effect=AssertionError("pdf generator should not run for non-pdf documents"),
                ):
                    with TestClient(app) as client:
                        warmup_response = client.post("/files/thumbnails/warmup", json={"file_ids": [file_row.id]})
                        self.assertEqual(200, warmup_response.status_code)
                        response = self._wait_for_thumbnail_error_code(client, file_row.id, "THUMBNAIL_NOT_AVAILABLE")

        self.assertEqual(404, response.status_code)
        self.assertEqual("THUMBNAIL_NOT_AVAILABLE", response.json()["error"]["code"])

    def test_returns_thumbnail_not_available_when_pdf_source_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            pdf_path = root / "missing.pdf"
            pdf_path.write_bytes(b"%PDF-1.7 fake-pdf")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("missing.pdf")
            self.assertIsNotNone(file_row)
            pdf_path.unlink()

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    response = client.get(f"/files/{file_row.id}/thumbnail")

        self.assertEqual(404, response.status_code)
        self.assertEqual("THUMBNAIL_NOT_AVAILABLE", response.json()["error"]["code"])

    def test_returns_file_not_found_for_unknown_file_id(self) -> None:
        with tempfile.TemporaryDirectory() as data_dir:
            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    response = client.get("/files/9999/thumbnail")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"error": {"code": "FILE_NOT_FOUND", "message": "File not found."}},
            response.json(),
        )

    def test_returns_thumbnail_not_available_for_non_image_file(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "notes.txt").write_text("doc", encoding="utf-8")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("notes.txt")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    response = client.get(f"/files/{file_row.id}/thumbnail")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {
                "error": {
                    "code": "THUMBNAIL_NOT_AVAILABLE",
                    "message": "Thumbnail is not available for this file.",
                }
            },
            response.json(),
        )

    def test_non_exe_file_does_not_use_exe_icon_generator(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "notes.txt").write_text("doc", encoding="utf-8")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("notes.txt")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(
                    ExeIconGeneratorWorker,
                    "generate_icon",
                    side_effect=AssertionError("exe icon generator should not run for non-exe files"),
                ):
                    with TestClient(app) as client:
                        warmup_response = client.post("/files/thumbnails/warmup", json={"file_ids": [file_row.id]})
                        self.assertEqual(200, warmup_response.status_code)
                        response = self._wait_for_thumbnail_error_code(client, file_row.id, "THUMBNAIL_NOT_AVAILABLE")

        self.assertEqual(404, response.status_code)
        self.assertEqual("THUMBNAIL_NOT_AVAILABLE", response.json()["error"]["code"])

    def test_returns_thumbnail_not_available_when_image_cannot_be_opened(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "broken.png").write_bytes(b"not-a-real-image")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("broken.png")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    response = client.get(f"/files/{file_row.id}/thumbnail")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {
                "error": {
                    "code": "THUMBNAIL_NOT_AVAILABLE",
                    "message": "Thumbnail is not available for this file.",
                }
            },
            response.json(),
        )

    def test_generates_thumbnail_lazily_when_cache_missing(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            self._create_image(root / "cover.png", (900, 600))
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("cover.png")
            self.assertIsNotNone(file_row)

            thumbnail_dir = Path(data_dir) / "thumbnails"
            self.assertFalse(thumbnail_dir.exists())

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    response = client.get(f"/files/{file_row.id}/thumbnail")

            self.assertEqual(200, response.status_code)
            generated_files = list(thumbnail_dir.glob("*.jpg"))
            self.assertEqual(1, len(generated_files))

    def test_reuses_cached_thumbnail_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            self._create_image(root / "cover.png", (1000, 700))
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("cover.png")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    first_response = client.get(f"/files/{file_row.id}/thumbnail")
                    self.assertEqual(200, first_response.status_code)

                    with patch.object(
                        ThumbnailGeneratorWorker,
                        "generate_thumbnail",
                        side_effect=AssertionError("thumbnail generator should not run when cache exists"),
                    ):
                        second_response = client.get(f"/files/{file_row.id}/thumbnail")

            self.assertEqual(200, second_response.status_code)

    def test_returns_thumbnail_for_video_file_using_ffmpeg_worker(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "clip.mp4").write_bytes(b"fake-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("clip.mp4")
            self.assertIsNotNone(file_row)

            def write_video_thumbnail(_, __, output_path: Path, *, width: int = 320) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._create_image(output_path, (width, 180))

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(VideoThumbnailGeneratorWorker, "generate_thumbnail", new=write_video_thumbnail):
                    with TestClient(app) as client:
                        response = client.get(f"/files/{file_row.id}/thumbnail")

            self.assertEqual(200, response.status_code)
            self.assertEqual("image/jpeg", response.headers["content-type"])
            generated_files = list((Path(data_dir) / "thumbnails" / "video").glob("*.jpg"))
            self.assertEqual(1, len(generated_files))
            self.assertGreater(len(response.content), 0)

    def test_reuses_cached_video_thumbnail_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "clip.mp4").write_bytes(b"fake-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("clip.mp4")
            self.assertIsNotNone(file_row)

            def write_video_thumbnail(_, __, output_path: Path, *, width: int = 320) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._create_image(output_path, (width, 180))

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(VideoThumbnailGeneratorWorker, "generate_thumbnail", new=write_video_thumbnail):
                        first_response = client.get(f"/files/{file_row.id}/thumbnail")
                    self.assertEqual(200, first_response.status_code)

                    with patch.object(
                        VideoThumbnailGeneratorWorker,
                        "generate_thumbnail",
                        side_effect=AssertionError("video thumbnail generator should not run when cache exists"),
                    ):
                        second_response = client.get(f"/files/{file_row.id}/thumbnail")

            self.assertEqual(200, second_response.status_code)

    def test_returns_thumbnail_for_exe_file_using_icon_worker(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "tool.exe").write_bytes(b"fake-exe")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("tool.exe")
            self.assertIsNotNone(file_row)

            def write_exe_icon(_, __, output_path: Path, *, size: int = 256) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (size, size), color=(12, 34, 56, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(ExeIconGeneratorWorker, "generate_icon", new=write_exe_icon):
                    with TestClient(app) as client:
                        self._warmup_and_wait_for_file(client, file_row.id, Path(data_dir) / "thumbnails" / "exe_icons")
                        response = client.get(f"/files/{file_row.id}/thumbnail")

            self.assertEqual(200, response.status_code)
            self.assertEqual("image/png", response.headers["content-type"])
            generated_files = list((Path(data_dir) / "thumbnails" / "exe_icons").glob("*.png"))
            self.assertEqual(1, len(generated_files))
            with Image.open(generated_files[0]) as generated_icon:
                self.assertEqual((256, 256), generated_icon.size)
            self.assertGreater(len(response.content), 0)

    def test_reuses_cached_exe_icon_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "tool.exe").write_bytes(b"fake-exe")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("tool.exe")
            self.assertIsNotNone(file_row)

            def write_exe_icon(_, __, output_path: Path, *, size: int = 256) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (size, size), color=(12, 34, 56, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(ExeIconGeneratorWorker, "generate_icon", new=write_exe_icon):
                        self._warmup_and_wait_for_file(client, file_row.id, Path(data_dir) / "thumbnails" / "exe_icons")
                        first_response = client.get(f"/files/{file_row.id}/thumbnail")
                    self.assertEqual(200, first_response.status_code)

                    with patch.object(
                        ExeIconGeneratorWorker,
                        "generate_icon",
                        side_effect=AssertionError("exe icon generator should not run when cache exists"),
                    ):
                        second_response = client.get(f"/files/{file_row.id}/thumbnail")

            self.assertEqual(200, second_response.status_code)
            self.assertEqual("image/png", second_response.headers["content-type"])

    def test_concurrent_exe_icon_requests_share_single_generation(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "tool.exe").write_bytes(b"fake-exe")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("tool.exe")
            self.assertIsNotNone(file_row)
            service = ThumbnailService()
            call_count = 0
            call_count_lock = Lock()

            def write_exe_icon(_, __, output_path: Path, *, size: int = 256) -> None:
                nonlocal call_count
                with call_count_lock:
                    call_count += 1
                time.sleep(0.05)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (size, size), color=(12, 34, 56, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(ExeIconGeneratorWorker, "generate_icon", new=write_exe_icon):
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        statuses = list(executor.map(lambda _: service._warmup_file(file_row), range(4)))
                    paths = self._wait_for_generated_files(Path(data_dir) / "thumbnails" / "exe_icons")

            self.assertEqual(1, call_count)
            self.assertIn("queued", statuses)
            self.assertTrue(all(status in {"queued", "in_progress"} for status in statuses))
            self.assertEqual(1, len(paths))

    def test_returns_thumbnail_not_available_when_exe_icon_generation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "broken.exe").write_bytes(b"fake-exe")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("broken.exe")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(
                    ExeIconGeneratorWorker,
                    "generate_icon",
                    side_effect=ExeIconGenerationError("icon extraction failed"),
                ):
                    with TestClient(app) as client:
                        warmup_response = client.post("/files/thumbnails/warmup", json={"file_ids": [file_row.id]})
                        self.assertEqual(200, warmup_response.status_code)
                        response = self._wait_for_thumbnail_error_code(client, file_row.id, "THUMBNAIL_NOT_AVAILABLE")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {
                "error": {
                    "code": "THUMBNAIL_NOT_AVAILABLE",
                    "message": "Thumbnail is not available for this file.",
                }
            },
            response.json(),
        )

    def test_returns_thumbnail_not_available_when_video_generation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "broken.mp4").write_bytes(b"not-a-real-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("broken.mp4")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(
                    VideoThumbnailGeneratorWorker,
                    "generate_thumbnail",
                    side_effect=VideoThumbnailGenerationError("ffmpeg failed"),
                ):
                    with TestClient(app) as client:
                        response = client.get(f"/files/{file_row.id}/thumbnail")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {
                "error": {
                    "code": "THUMBNAIL_NOT_AVAILABLE",
                    "message": "Thumbnail is not available for this file.",
                }
            },
            response.json(),
        )

    def test_video_warmup_expected_generation_failure_uses_warning_and_cleans_temp(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "broken.mp4").write_bytes(b"not-a-real-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("broken.mp4")
            self.assertIsNotNone(file_row)

            service = ThumbnailService()
            with self._patched_data_dir(Path(data_dir)):
                with patch.object(
                    VideoThumbnailGeneratorWorker,
                    "generate_thumbnail",
                    side_effect=VideoThumbnailGenerationError("moov atom not found; Invalid data found when processing input"),
                ):
                    with patch("app.services.thumbnails.service.logger.warning") as warning_mock:
                        with patch("app.services.thumbnails.service.logger.exception") as exception_mock:
                            self.assertEqual("queued", service._warmup_file(file_row))
                            self._wait_for_condition(lambda: bool(service._warmup_failures_by_cache_key))

            video_dir = Path(data_dir) / "thumbnails" / "video"
            self.assertEqual([], list(video_dir.glob("video_*.jpg")))
            self.assertEqual([], list(video_dir.glob(".*.tmp-*")))
            warning_mock.assert_called()
            exception_mock.assert_not_called()
            warning_args = " ".join(str(argument) for argument in warning_mock.call_args.args)
            self.assertIn("VideoThumbnailGenerationError", warning_args)
            self.assertIn("moov atom not found", warning_args)

    def test_video_warmup_warning_preserves_missing_ffmpeg_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "missing-ffmpeg.mp4").write_bytes(b"fake-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("missing-ffmpeg.mp4")
            self.assertIsNotNone(file_row)

            service = ThumbnailService()
            with self._patched_data_dir(Path(data_dir)):
                with patch.object(
                    VideoThumbnailGeneratorWorker,
                    "generate_thumbnail",
                    side_effect=VideoThumbnailGenerationError("ffmpeg was not found on PATH."),
                ):
                    with patch("app.services.thumbnails.service.logger.warning") as warning_mock:
                        self.assertEqual("queued", service._warmup_file(file_row))
                        self._wait_for_condition(lambda: bool(service._warmup_failures_by_cache_key))

            warning_args = " ".join(str(argument) for argument in warning_mock.call_args.args)
            self.assertIn("ffmpeg was not found on PATH", warning_args)
            with service._warmup_guard:
                failure = next(iter(service._warmup_failures_by_cache_key.values()))
            self.assertIn("ffmpeg was not found on PATH", failure.reason)

    def test_video_warmup_unexpected_failure_still_uses_exception_logging(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "unexpected.mp4").write_bytes(b"fake-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("unexpected.mp4")
            self.assertIsNotNone(file_row)

            service = ThumbnailService()
            with self._patched_data_dir(Path(data_dir)):
                with patch.object(VideoThumbnailGeneratorWorker, "generate_thumbnail", side_effect=RuntimeError("boom")):
                    with patch("app.services.thumbnails.service.logger.warning") as warning_mock:
                        with patch("app.services.thumbnails.service.logger.exception") as exception_mock:
                            self.assertEqual("queued", service._warmup_file(file_row))
                            self._wait_for_condition(lambda: bool(service._warmup_failures_by_cache_key))

            warning_mock.assert_not_called()
            exception_mock.assert_called()

    def test_video_warmup_failure_does_not_interrupt_following_job(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "broken.mp4").write_bytes(b"not-a-real-video")
            self._create_image(root / "cover.png", (320, 180))
            source_id = self._create_source(root)
            self._run_scan(source_id)
            broken_file = self._get_file_by_name("broken.mp4")
            image_file = self._get_file_by_name("cover.png")
            self.assertIsNotNone(broken_file)
            self.assertIsNotNone(image_file)

            service = ThumbnailService()
            with self._patched_data_dir(Path(data_dir)):
                with patch.object(
                    VideoThumbnailGeneratorWorker,
                    "generate_thumbnail",
                    side_effect=VideoThumbnailGenerationError("moov atom not found"),
                ):
                    self.assertEqual("queued", service._warmup_file(broken_file))
                    self.assertEqual("queued", service._warmup_file(image_file))

                    generated_paths: list[Path] = []

                    def image_thumbnail_generated() -> bool:
                        nonlocal generated_paths
                        generated_paths = list((Path(data_dir) / "thumbnails").glob("*.jpg"))
                        return len(generated_paths) == 1

                    self._wait_for_condition(image_thumbnail_generated)

            self.assertEqual(1, len(generated_paths))
            self.assertEqual("jpg", generated_paths[0].suffix.lstrip("."))

    def test_generates_video_preview_frames_when_single_thumbnail_cache_exists(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "clip.mp4").write_bytes(b"fake-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("clip.mp4")
            self.assertIsNotNone(file_row)

            def write_video_thumbnail(_, __, output_path: Path, *, width: int = 320) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._create_image(output_path, (width, 180))

            def write_preview_frames(_, __, output_dir: Path, *, seek_seconds: list[float], width: int = 320) -> None:
                output_dir.mkdir(parents=True, exist_ok=True)
                self.assertEqual(6, len(seek_seconds))
                for index in range(1, 7):
                    self._create_image(output_dir / f"{index:04d}.jpg", (width, 180))

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(VideoThumbnailGeneratorWorker, "generate_thumbnail", new=write_video_thumbnail):
                        thumbnail_response = client.get(f"/files/{file_row.id}/thumbnail")
                    self.assertEqual(200, thumbnail_response.status_code)

                    with patch.object(VideoThumbnailGeneratorWorker, "generate_preview_frames", new=write_preview_frames):
                        preview_response = client.get(f"/files/{file_row.id}/video-preview")

            self.assertEqual(200, preview_response.status_code)
            self.assertEqual(
                {
                    "item": {
                        "id": file_row.id,
                        "frame_count": 6,
                        "frame_indexes": [1, 2, 3, 4, 5, 6],
                    }
                },
                preview_response.json(),
            )
            generated_frames = list((Path(data_dir) / "thumbnails" / "video_preview").glob("*/*.jpg"))
            self.assertEqual(6, len(generated_frames))

    def test_video_preview_uses_persisted_duration_for_seek_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "clip.mp4").write_bytes(b"fake-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("clip.mp4")
            self.assertIsNotNone(file_row)

            with SessionLocal() as session:
                session.merge(
                    FileMetadata(
                        file_id=file_row.id,
                        width=1920,
                        height=1080,
                        duration_ms=600_000,
                        page_count=None,
                        updated_at=datetime(2026, 4, 16, 9, 30),
                    )
                )
                session.commit()

            captured_seek_seconds: list[float] = []

            def write_video_thumbnail(_, __, output_path: Path, *, width: int = 320) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._create_image(output_path, (width, 180))

            def write_preview_frames(_, __, output_dir: Path, *, seek_seconds: list[float], width: int = 320) -> None:
                captured_seek_seconds.extend(seek_seconds)
                output_dir.mkdir(parents=True, exist_ok=True)
                for index in range(1, 7):
                    self._create_image(output_dir / f"{index:04d}.jpg", (width, 180))

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(VideoThumbnailGeneratorWorker, "generate_thumbnail", new=write_video_thumbnail):
                        self.assertEqual(200, client.get(f"/files/{file_row.id}/thumbnail").status_code)

                    with patch.object(VideoThumbnailGeneratorWorker, "generate_preview_frames", new=write_preview_frames):
                        response = client.get(f"/files/{file_row.id}/video-preview")

        self.assertEqual(200, response.status_code)
        self.assertEqual(6, len(captured_seek_seconds))
        self.assertNotEqual([0.5, 1.0, 1.5, 2.0, 2.5, 3.0], captured_seek_seconds)
        self.assertTrue(all(0 < seek < 600 for seek in captured_seek_seconds))
        self.assertGreater(captured_seek_seconds[-1], 500)

    def test_reuses_cached_video_preview_frames_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "clip.mp4").write_bytes(b"fake-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("clip.mp4")
            self.assertIsNotNone(file_row)

            def write_video_thumbnail(_, __, output_path: Path, *, width: int = 320) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._create_image(output_path, (width, 180))

            def write_preview_frames(_, __, output_dir: Path, *, seek_seconds: list[float], width: int = 320) -> None:
                output_dir.mkdir(parents=True, exist_ok=True)
                for index in range(1, 7):
                    self._create_image(output_dir / f"{index:04d}.jpg", (width, 180))

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(VideoThumbnailGeneratorWorker, "generate_thumbnail", new=write_video_thumbnail):
                        self.assertEqual(200, client.get(f"/files/{file_row.id}/thumbnail").status_code)

                    with patch.object(VideoThumbnailGeneratorWorker, "generate_preview_frames", new=write_preview_frames):
                        first_response = client.get(f"/files/{file_row.id}/video-preview")
                    self.assertEqual(200, first_response.status_code)

                    with patch.object(
                        VideoThumbnailGeneratorWorker,
                        "generate_preview_frames",
                        side_effect=AssertionError("video preview generator should not run when cache exists"),
                    ):
                        second_response = client.get(f"/files/{file_row.id}/video-preview")

            self.assertEqual(200, second_response.status_code)
            self.assertEqual([1, 2, 3, 4, 5, 6], second_response.json()["item"]["frame_indexes"])

    def test_video_preview_requires_single_thumbnail_cache(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "clip.mp4").write_bytes(b"fake-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("clip.mp4")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with patch.object(
                    VideoThumbnailGeneratorWorker,
                    "generate_preview_frames",
                    side_effect=AssertionError("video preview should not generate without single thumbnail cache"),
                ):
                    with TestClient(app) as client:
                        response = client.get(f"/files/{file_row.id}/video-preview")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {
                "error": {
                    "code": "VIDEO_PREVIEW_NOT_AVAILABLE",
                    "message": "Video preview is not available for this file.",
                }
            },
            response.json(),
        )

    def test_video_preview_not_available_for_non_video_file(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            self._create_image(root / "cover.png", (600, 400))
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("cover.png")
            self.assertIsNotNone(file_row)

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    response = client.get(f"/files/{file_row.id}/video-preview")

        self.assertEqual(404, response.status_code)
        self.assertEqual("VIDEO_PREVIEW_NOT_AVAILABLE", response.json()["error"]["code"])

    def test_video_preview_not_available_when_generation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "broken.mp4").write_bytes(b"not-a-real-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("broken.mp4")
            self.assertIsNotNone(file_row)

            def write_video_thumbnail(_, __, output_path: Path, *, width: int = 320) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._create_image(output_path, (width, 180))

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(VideoThumbnailGeneratorWorker, "generate_thumbnail", new=write_video_thumbnail):
                        self.assertEqual(200, client.get(f"/files/{file_row.id}/thumbnail").status_code)

                    with patch.object(
                        VideoThumbnailGeneratorWorker,
                        "generate_preview_frames",
                        side_effect=VideoThumbnailGenerationError("ffmpeg failed"),
                    ):
                        response = client.get(f"/files/{file_row.id}/video-preview")

        self.assertEqual(404, response.status_code)
        self.assertEqual("VIDEO_PREVIEW_NOT_AVAILABLE", response.json()["error"]["code"])

    def test_video_preview_not_available_when_some_frames_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "clip.mp4").write_bytes(b"fake-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("clip.mp4")
            self.assertIsNotNone(file_row)

            def write_video_thumbnail(_, __, output_path: Path, *, width: int = 320) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._create_image(output_path, (width, 180))

            def write_incomplete_preview_frames(_, __, output_dir: Path, *, seek_seconds: list[float], width: int = 320) -> None:
                output_dir.mkdir(parents=True, exist_ok=True)
                for index in range(1, 6):
                    self._create_image(output_dir / f"{index:04d}.jpg", (width, 180))

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(VideoThumbnailGeneratorWorker, "generate_thumbnail", new=write_video_thumbnail):
                        self.assertEqual(200, client.get(f"/files/{file_row.id}/thumbnail").status_code)

                    with patch.object(VideoThumbnailGeneratorWorker, "generate_preview_frames", new=write_incomplete_preview_frames):
                        response = client.get(f"/files/{file_row.id}/video-preview")

        self.assertEqual(404, response.status_code)
        self.assertEqual("VIDEO_PREVIEW_NOT_AVAILABLE", response.json()["error"]["code"])

    def test_returns_video_preview_frame_from_cache(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            (root / "clip.mp4").write_bytes(b"fake-video")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("clip.mp4")
            self.assertIsNotNone(file_row)

            def write_video_thumbnail(_, __, output_path: Path, *, width: int = 320) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._create_image(output_path, (width, 180))

            def write_preview_frames(_, __, output_dir: Path, *, seek_seconds: list[float], width: int = 320) -> None:
                output_dir.mkdir(parents=True, exist_ok=True)
                for index in range(1, 7):
                    self._create_image(output_dir / f"{index:04d}.jpg", (width, 180))

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(VideoThumbnailGeneratorWorker, "generate_thumbnail", new=write_video_thumbnail):
                        self.assertEqual(200, client.get(f"/files/{file_row.id}/thumbnail").status_code)
                    with patch.object(VideoThumbnailGeneratorWorker, "generate_preview_frames", new=write_preview_frames):
                        self.assertEqual(200, client.get(f"/files/{file_row.id}/video-preview").status_code)

                    frame_response = client.get(f"/files/{file_row.id}/video-preview/frames/1")
                    invalid_frame_response = client.get(f"/files/{file_row.id}/video-preview/frames/99")

            self.assertEqual(200, frame_response.status_code)
            self.assertEqual("image/jpeg", frame_response.headers["content-type"])
            self.assertGreater(len(frame_response.content), 0)
            self.assertEqual(404, invalid_frame_response.status_code)
            self.assertEqual("VIDEO_PREVIEW_NOT_AVAILABLE", invalid_frame_response.json()["error"]["code"])

    def test_rescan_changes_cache_key_when_indexed_file_facts_change(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            image_path = root / "cover.png"
            self._create_image(image_path, (640, 480))
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("cover.png")
            self.assertIsNotNone(file_row)

            thumbnail_dir = Path(data_dir) / "thumbnails"

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    first_response = client.get(f"/files/{file_row.id}/thumbnail")
                    self.assertEqual(200, first_response.status_code)

                first_files = sorted(path.name for path in thumbnail_dir.glob("*.jpg"))
                self.assertEqual(1, len(first_files))

                self._create_image(image_path, (800, 600))
                self._run_scan(source_id)
                updated_file_row = self._get_file_by_name("cover.png")
                self.assertIsNotNone(updated_file_row)

                with TestClient(app) as client:
                    second_response = client.get(f"/files/{updated_file_row.id}/thumbnail")

                self.assertEqual(200, second_response.status_code)
                second_files = sorted(path.name for path in thumbnail_dir.glob("*.jpg"))

            self.assertEqual(2, len(second_files))
            self.assertEqual(1, len(set(second_files) - set(first_files)))

    def test_rescan_changes_exe_icon_cache_key_when_indexed_file_facts_change(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            exe_path = root / "tool.exe"
            exe_path.write_bytes(b"fake-exe-v1")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("tool.exe")
            self.assertIsNotNone(file_row)

            icon_dir = Path(data_dir) / "thumbnails" / "exe_icons"

            def write_exe_icon(_, __, output_path: Path, *, size: int = 256) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (size, size), color=(12, 34, 56, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(ExeIconGeneratorWorker, "generate_icon", new=write_exe_icon):
                        self._warmup_and_wait_for_file(client, file_row.id, icon_dir)
                        first_response = client.get(f"/files/{file_row.id}/thumbnail")
                    self.assertEqual(200, first_response.status_code)

                first_files = sorted(path.name for path in icon_dir.glob("*.png"))
                self.assertEqual(1, len(first_files))

                exe_path.write_bytes(b"fake-exe-v2-with-new-size")
                self._run_scan(source_id)
                updated_file_row = self._get_file_by_name("tool.exe")
                self.assertIsNotNone(updated_file_row)

                with TestClient(app) as client:
                    with patch.object(ExeIconGeneratorWorker, "generate_icon", new=write_exe_icon):
                        self._warmup_and_wait_for_file(client, updated_file_row.id, icon_dir, expected_count=2)
                        second_response = client.get(f"/files/{updated_file_row.id}/thumbnail")
                    self.assertEqual(200, second_response.status_code)

                second_files = sorted(path.name for path in icon_dir.glob("*.png"))

            self.assertEqual(2, len(second_files))
            self.assertEqual(1, len(set(second_files) - set(first_files)))

    def test_rescan_changes_pdf_thumbnail_cache_key_when_indexed_file_facts_change(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as data_dir:
            root = Path(source_dir)
            pdf_path = root / "manual.pdf"
            pdf_path.write_bytes(b"%PDF-1.7 fake-pdf-v1")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("manual.pdf")
            self.assertIsNotNone(file_row)

            pdf_dir = Path(data_dir) / "thumbnails" / "pdf"

            def write_pdf_thumbnail(_, __, output_path: Path, *, width: int = 384) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGBA", (width, 256), color=(255, 255, 255, 255)).save(output_path, format="PNG")

            with self._patched_data_dir(Path(data_dir)):
                with TestClient(app) as client:
                    with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=write_pdf_thumbnail):
                        self._warmup_and_wait_for_file(client, file_row.id, pdf_dir)
                        first_response = client.get(f"/files/{file_row.id}/thumbnail")
                    self.assertEqual(200, first_response.status_code)

                first_files = sorted(path.name for path in pdf_dir.glob("*.png"))
                self.assertEqual(1, len(first_files))

                pdf_path.write_bytes(b"%PDF-1.7 fake-pdf-v2-with-new-size")
                self._run_scan(source_id)
                updated_file_row = self._get_file_by_name("manual.pdf")
                self.assertIsNotNone(updated_file_row)

                with TestClient(app) as client:
                    with patch.object(ThumbnailService, "_render_pdf_thumbnail_subprocess", new=write_pdf_thumbnail):
                        self._warmup_and_wait_for_file(client, updated_file_row.id, pdf_dir, expected_count=2)
                        second_response = client.get(f"/files/{updated_file_row.id}/thumbnail")
                    self.assertEqual(200, second_response.status_code)

                second_files = sorted(path.name for path in pdf_dir.glob("*.png"))

            self.assertEqual(2, len(second_files))
            self.assertEqual(1, len(set(second_files) - set(first_files)))

    def _create_image(self, path: Path, size: tuple[int, int]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, color=(12, 34, 56)).save(path)

    def _create_source(self, root: Path) -> int:
        with TestClient(app) as client:
            response = client.post(
                "/sources",
                json={"path": str(root), "display_name": root.name or "Thumbnail Source"},
            )

        self.assertEqual(201, response.status_code)
        return int(response.json()["id"])

    def _run_scan(self, source_id: int) -> None:
        with TestClient(app) as client:
            response = client.post(f"/sources/{source_id}/scan")

        self.assertEqual(202, response.status_code)
        self.assertEqual("succeeded", response.json()["status"])

    def _get_file_by_name(self, name: str) -> File | None:
        with SessionLocal() as session:
            statement = select(File).where(File.name == name)
            return session.scalars(statement).first()

    def _warmup_and_wait_for_file(
        self,
        client: TestClient,
        file_id: int,
        thumbnail_dir: Path,
        *,
        expected_count: int = 1,
    ) -> list[Path]:
        response = client.post("/files/thumbnails/warmup", json={"file_ids": [file_id]})
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(
            any(file_id in payload[key] for key in ("cached", "queued", "in_progress")),
            payload,
        )
        return self._wait_for_generated_files(thumbnail_dir, expected_count=expected_count)

    def _wait_for_generated_files(self, thumbnail_dir: Path, *, expected_count: int = 1) -> list[Path]:
        found_paths: list[Path] = []

        def has_expected_files() -> bool:
            nonlocal found_paths
            found_paths = list(thumbnail_dir.glob("*.png"))
            return len(found_paths) >= expected_count

        self._wait_for_condition(has_expected_files)
        return found_paths

    def _wait_for_thumbnail_error_code(self, client: TestClient, file_id: int, expected_code: str):
        response = None

        def has_expected_error() -> bool:
            nonlocal response
            response = client.get(f"/files/{file_id}/thumbnail")
            if response.status_code != 404:
                return False
            return response.json()["error"]["code"] == expected_code

        self._wait_for_condition(has_expected_error)
        return response

    def _wait_for_condition(self, predicate) -> None:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.02)
        self.fail("Timed out waiting for asynchronous thumbnail warmup.")

    def _patched_data_dir(self, path: Path):
        return patch.object(type(settings), "data_dir", new_callable=PropertyMock, return_value=path)

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
