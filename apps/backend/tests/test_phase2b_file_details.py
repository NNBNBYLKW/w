import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.file_tag import FileTag
from app.db.models.file_user_meta import FileUserMeta
from app.db.models.source import Source
from app.db.models.tag import Tag
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 16, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase2BFileDetailsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()

    def test_returns_minimal_detail_payload_for_existing_file(self) -> None:
        file_id, source_id, _ = self._seed_file()

        with TestClient(app) as client:
            response = client.get(f"/files/{file_id}")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "id": file_id,
                "name": "Cover.PNG",
                "path": "D:\\Assets\\Refs\\Cover.PNG",
                "file_type": "image",
                "size_bytes": 123,
                "created_at_fs": "2026-04-16T09:30:00",
                "modified_at_fs": "2026-04-16T10:00:00",
                "discovered_at": "2026-04-16T09:35:00",
                "last_seen_at": "2026-04-16T10:00:00",
                "is_deleted": False,
                "source_id": source_id,
                "tags": [],
                "color_tag": None,
            },
            response.json()["item"],
        )

        engine.dispose()

    def test_returns_deleted_file_row_by_id_with_is_deleted_true(self) -> None:
        file_id, _, _ = self._seed_file(is_deleted=True)

        with TestClient(app) as client:
            response = client.get(f"/files/{file_id}")

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["item"]["is_deleted"])

        engine.dispose()

    def test_returns_404_with_file_not_found_for_missing_file_id(self) -> None:
        self._seed_file()

        with TestClient(app) as client:
            response = client.get("/files/9999")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"error": {"code": "FILE_NOT_FOUND", "message": "File not found."}},
            response.json(),
        )

        engine.dispose()

    def test_preserves_nullable_basic_fields_in_response(self) -> None:
        file_id, _, _ = self._seed_file(size_bytes=None, created_at_fs=None, modified_at_fs=None)

        with TestClient(app) as client:
            response = client.get(f"/files/{file_id}")

        self.assertEqual(200, response.status_code)
        item = response.json()["item"]
        self.assertIsNone(item["size_bytes"])
        self.assertIsNone(item["created_at_fs"])
        self.assertIsNone(item["modified_at_fs"])
        self.assertEqual([], item["tags"])
        self.assertIsNone(item["color_tag"])

        engine.dispose()

    def test_returns_tags_sorted_in_detail_payload(self) -> None:
        file_id, _, tag_ids = self._seed_file(
            tags=[("beta", "beta"), ("Alpha", "alpha"), ("Gamma", "gamma")]
        )

        with TestClient(app) as client:
            response = client.get(f"/files/{file_id}")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [
                {"id": tag_ids[1], "name": "Alpha"},
                {"id": tag_ids[0], "name": "beta"},
                {"id": tag_ids[2], "name": "Gamma"},
            ],
            response.json()["item"]["tags"],
        )

        engine.dispose()

    def test_returns_stored_color_tag_in_detail_payload(self) -> None:
        file_id, _, _ = self._seed_file(color_tag="blue")

        with TestClient(app) as client:
            response = client.get(f"/files/{file_id}")

        self.assertEqual(200, response.status_code)
        self.assertEqual("blue", response.json()["item"]["color_tag"])

        engine.dispose()

    def _seed_file(
        self,
        *,
        is_deleted: bool = False,
        size_bytes: int | None = 123,
        created_at_fs: datetime | None = _dt(9, 30),
        modified_at_fs: datetime | None = _dt(10),
        tags: list[tuple[str, str]] | None = None,
        color_tag: str | None = None,
    ) -> tuple[int, int, list[int]]:
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
                path="D:\\Assets\\Refs\\Cover.PNG",
                parent_path="D:\\Assets\\Refs",
                name="Cover.PNG",
                stem="Cover",
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=size_bytes,
                created_at_fs=created_at_fs,
                modified_at_fs=modified_at_fs,
                discovered_at=_dt(9, 35),
                last_seen_at=_dt(10),
                is_deleted=is_deleted,
                checksum_hint=None,
                updated_at=_dt(10),
            )
            session.add(file)
            session.flush()

            created_tag_ids: list[int] = []
            for name, normalized_name in tags or []:
                tag = Tag(
                    name=name,
                    normalized_name=normalized_name,
                    created_at=_dt(8, 45),
                    updated_at=_dt(8, 45),
                )
                session.add(tag)
                session.flush()
                session.add(
                    FileTag(
                        file_id=file.id,
                        tag_id=tag.id,
                        created_at=_dt(9, 40),
                    )
                )
                created_tag_ids.append(int(tag.id))

            if color_tag is not None:
                session.add(
                    FileUserMeta(
                        file_id=file.id,
                        color_tag=color_tag,
                        status=None,
                        rating=None,
                        is_favorite=False,
                        updated_at=_dt(9, 50),
                    )
                )
            session.commit()
            return int(file.id), int(source.id), created_tag_ids

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
