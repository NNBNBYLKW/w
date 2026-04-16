import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.db.models.file import File
from app.db.models.file_user_meta import FileUserMeta
from app.db.models.source import Source
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 16, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase3BColorTagsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()

    def test_sets_color_tag_for_file_without_existing_user_meta(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            response = client.patch(f"/files/{file_id}/color-tag", json={"color_tag": "blue"})

        self.assertEqual(200, response.status_code)
        self.assertEqual({"item": {"id": file_id, "color_tag": "blue"}}, response.json())

        with SessionLocal() as session:
            meta = session.get(FileUserMeta, file_id)
            assert meta is not None
            self.assertEqual("blue", meta.color_tag)
            self.assertFalse(meta.is_favorite)
            self.assertIsNone(meta.status)
            self.assertIsNone(meta.rating)

        engine.dispose()

    def test_returns_persisted_normalized_color_tag_value(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            response = client.patch(f"/files/{file_id}/color-tag", json={"color_tag": " Blue "})

        self.assertEqual(200, response.status_code)
        self.assertEqual({"item": {"id": file_id, "color_tag": "blue"}}, response.json())

        engine.dispose()

    def test_updates_existing_color_tag_without_overwriting_other_user_meta_fields(self) -> None:
        file_id = self._seed_file(color_tag="red", status="kept", rating=5, is_favorite=True)

        with TestClient(app) as client:
            response = client.patch(f"/files/{file_id}/color-tag", json={"color_tag": "green"})

        self.assertEqual(200, response.status_code)

        with SessionLocal() as session:
            meta = session.get(FileUserMeta, file_id)
            assert meta is not None
            self.assertEqual("green", meta.color_tag)
            self.assertEqual("kept", meta.status)
            self.assertEqual(5, meta.rating)
            self.assertTrue(meta.is_favorite)

        engine.dispose()

    def test_clears_color_tag_on_existing_user_meta_row(self) -> None:
        file_id = self._seed_file(color_tag="purple", status="kept", rating=2, is_favorite=True)

        with TestClient(app) as client:
            response = client.patch(f"/files/{file_id}/color-tag", json={"color_tag": None})

        self.assertEqual(200, response.status_code)
        self.assertEqual({"item": {"id": file_id, "color_tag": None}}, response.json())

        with SessionLocal() as session:
            meta = session.get(FileUserMeta, file_id)
            assert meta is not None
            self.assertIsNone(meta.color_tag)
            self.assertEqual("kept", meta.status)
            self.assertEqual(2, meta.rating)
            self.assertTrue(meta.is_favorite)

        engine.dispose()

    def test_clear_without_existing_user_meta_is_no_op_success(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            response = client.patch(f"/files/{file_id}/color-tag", json={"color_tag": None})

        self.assertEqual(200, response.status_code)
        self.assertEqual({"item": {"id": file_id, "color_tag": None}}, response.json())

        with SessionLocal() as session:
            self.assertIsNone(session.get(FileUserMeta, file_id))

        engine.dispose()

    def test_returns_color_tag_invalid_for_empty_or_whitespace_string(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            response = client.patch(f"/files/{file_id}/color-tag", json={"color_tag": "   "})

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"error": {"code": "COLOR_TAG_INVALID", "message": "Color tag is invalid."}},
            response.json(),
        )

        engine.dispose()

    def test_returns_color_tag_invalid_for_unsupported_value(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            response = client.patch(f"/files/{file_id}/color-tag", json={"color_tag": "orange"})

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"error": {"code": "COLOR_TAG_INVALID", "message": "Color tag is invalid."}},
            response.json(),
        )

        engine.dispose()

    def test_returns_file_not_found_for_missing_file(self) -> None:
        with TestClient(app) as client:
            response = client.patch("/files/9999/color-tag", json={"color_tag": "blue"})

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"error": {"code": "FILE_NOT_FOUND", "message": "File not found."}},
            response.json(),
        )

        engine.dispose()

    def test_preserves_single_row_per_file_user_meta_invariant_across_repeated_updates(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            client.patch(f"/files/{file_id}/color-tag", json={"color_tag": "blue"})
            client.patch(f"/files/{file_id}/color-tag", json={"color_tag": "green"})
            client.patch(f"/files/{file_id}/color-tag", json={"color_tag": None})
            client.patch(f"/files/{file_id}/color-tag", json={"color_tag": "red"})

        with SessionLocal() as session:
            rows = list(session.scalars(select(FileUserMeta).where(FileUserMeta.file_id == file_id)))
            self.assertEqual(1, len(rows))
            self.assertEqual("red", rows[0].color_tag)

        engine.dispose()

    def _seed_file(
        self,
        *,
        color_tag: str | None = None,
        status: str | None = None,
        rating: int | None = None,
        is_favorite: bool = False,
    ) -> int:
        with SessionLocal() as session:
            source = Source(
                path="D:\\Assets",
                display_name="Assets",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9),
                last_scan_status="succeeded",
                created_at=_dt(8),
                updated_at=_dt(9),
            )
            session.add(source)
            session.flush()

            file = File(
                source_id=source.id,
                path="D:\\Assets\\Refs\\ColorTest.PNG",
                parent_path="D:\\Assets\\Refs",
                name="ColorTest.PNG",
                stem="ColorTest",
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=456,
                created_at_fs=_dt(9, 30),
                modified_at_fs=_dt(10),
                discovered_at=_dt(9, 35),
                last_seen_at=_dt(10),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10),
            )
            session.add(file)
            session.flush()

            if color_tag is not None or status is not None or rating is not None or is_favorite:
                session.add(
                    FileUserMeta(
                        file_id=file.id,
                        color_tag=color_tag,
                        status=status,
                        rating=rating,
                        is_favorite=is_favorite,
                        updated_at=_dt(10, 5),
                    )
                )

            session.commit()
            return int(file.id)

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
