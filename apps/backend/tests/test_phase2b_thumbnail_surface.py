import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import PropertyMock, patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select, text

from app.core.config.settings import Settings, settings
from app.db.models.file import File
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app
from app.workers.thumbnails.generator import ThumbnailGeneratorWorker
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
            (root / "notes.pdf").write_text("doc", encoding="utf-8")
            source_id = self._create_source(root)
            self._run_scan(source_id)
            file_row = self._get_file_by_name("notes.pdf")
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
            self.assertNotEqual(first_files[0], second_files[-1])

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
