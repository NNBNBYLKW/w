import tempfile
import unittest
from pathlib import Path
from unittest.mock import PropertyMock, patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select, text

from app.core.config.settings import settings
from app.db.models.file import File
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app
from app.workers.thumbnails.generator import ThumbnailGeneratorWorker


class Phase2BThumbnailSurfaceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

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
