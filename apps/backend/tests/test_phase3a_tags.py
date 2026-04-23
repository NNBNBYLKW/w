import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.db.models.file import File
from app.db.models.file_tag import FileTag
from app.db.models.source import Source
from app.db.models.tag import Tag
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 16, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase3ATagsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()

    def test_creates_tag_and_reuses_existing_normalized_name(self) -> None:
        with TestClient(app) as client:
            created = client.post("/tags", json={"name": "Reference"})
            reused = client.post("/tags", json={"name": "  reference  "})

        self.assertEqual(201, created.status_code)
        self.assertEqual(200, reused.status_code)
        self.assertEqual(created.json()["item"], reused.json()["item"])

        with SessionLocal() as session:
            tag_count = session.scalar(select(func.count()).select_from(Tag))
        self.assertEqual(1, int(tag_count or 0))

        engine.dispose()

    def test_rejects_empty_after_normalization_with_tag_name_invalid(self) -> None:
        with TestClient(app) as client:
            response = client.post("/tags", json={"name": "   "})

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"error": {"code": "TAG_NAME_INVALID", "message": "Tag name cannot be empty."}},
            response.json(),
        )

        engine.dispose()

    def test_lists_tags_sorted_by_normalized_name_then_id(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            client.post(f"/files/{file_id}/tags", json={"name": "beta"})
            client.post(f"/files/{file_id}/tags", json={"name": "Alpha"})
            client.post(f"/files/{file_id}/tags", json={"name": "Gamma"})
            response = client.get("/tags")

        self.assertEqual(200, response.status_code)
        self.assertEqual(["Alpha", "beta", "Gamma"], [item["name"] for item in response.json()["items"]])

        engine.dispose()

    def test_does_not_list_tags_without_active_files(self) -> None:
        with TestClient(app) as client:
            client.post("/tags", json={"name": "Orphan"})
            response = client.get("/tags")

        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json()["items"])

        engine.dispose()

    def test_does_not_list_tags_attached_only_to_deleted_files(self) -> None:
        self._seed_deleted_file_with_tag("DeletedOnly")

        with TestClient(app) as client:
            response = client.get("/tags")

        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json()["items"])

        engine.dispose()

    def test_attaches_tag_by_name_and_is_idempotent(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            first_attach = client.post(f"/files/{file_id}/tags", json={"name": "Reference"})
            second_attach = client.post(f"/files/{file_id}/tags", json={"name": "  reference "})

        self.assertEqual(200, first_attach.status_code)
        self.assertEqual(first_attach.json(), second_attach.json())
        self.assertEqual([{"id": first_attach.json()["items"][0]["id"], "name": "Reference"}], first_attach.json()["items"])

        with SessionLocal() as session:
            relation_count = session.scalar(select(func.count()).select_from(FileTag))
        self.assertEqual(1, int(relation_count or 0))

        engine.dispose()

    def test_removes_attached_tag_and_returns_remaining_tags(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            alpha = client.post(f"/files/{file_id}/tags", json={"name": "Alpha"})
            beta = client.post(f"/files/{file_id}/tags", json={"name": "beta"})
            alpha_id = alpha.json()["items"][0]["id"]
            beta_id = next(item["id"] for item in beta.json()["items"] if item["name"] == "beta")
            response = client.delete(f"/files/{file_id}/tags/{alpha_id}")

        self.assertEqual(200, response.status_code)
        self.assertEqual([{"id": beta_id, "name": "beta"}], response.json()["items"])

        engine.dispose()

    def test_removing_last_active_file_tag_deletes_orphan_tag(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            created = client.post(f"/files/{file_id}/tags", json={"name": "Reference"})
            tag_id = created.json()["items"][0]["id"]
            removed = client.delete(f"/files/{file_id}/tags/{tag_id}")
            tags = client.get("/tags")

        self.assertEqual(200, removed.status_code)
        self.assertEqual([], removed.json()["items"])
        self.assertEqual([], tags.json()["items"])

        with SessionLocal() as session:
            remaining_tag = session.get(Tag, tag_id)
        self.assertIsNone(remaining_tag)

        engine.dispose()

    def test_removing_one_of_multiple_active_file_relations_keeps_tag_visible(self) -> None:
        first_file_id = self._seed_file(
            path="D:\\Assets\\Refs\\Cover.PNG",
            parent_path="D:\\Assets\\Refs",
            name="Cover.PNG",
            stem="Cover",
        )
        second_file_id = self._seed_file(
            path="D:\\Assets\\Refs\\Poster.PNG",
            parent_path="D:\\Assets\\Refs",
            name="Poster.PNG",
            stem="Poster",
        )

        with TestClient(app) as client:
            first_attach = client.post(f"/files/{first_file_id}/tags", json={"name": "Shared"})
            tag_id = first_attach.json()["items"][0]["id"]
            second_attach = client.post(f"/files/{second_file_id}/tags", json={"name": "Shared"})
            removed = client.delete(f"/files/{first_file_id}/tags/{tag_id}")
            tags = client.get("/tags")

        self.assertEqual(200, second_attach.status_code)
        self.assertEqual(200, removed.status_code)
        self.assertEqual([], removed.json()["items"])
        self.assertEqual(["Shared"], [item["name"] for item in tags.json()["items"]])

        with SessionLocal() as session:
            remaining_tag = session.get(Tag, tag_id)
        self.assertIsNotNone(remaining_tag)

        engine.dispose()

    def test_returns_file_not_found_when_attaching_to_missing_file(self) -> None:
        with TestClient(app) as client:
            response = client.post("/files/9999/tags", json={"name": "Reference"})

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"error": {"code": "FILE_NOT_FOUND", "message": "File not found."}},
            response.json(),
        )

        engine.dispose()

    def test_returns_tag_not_found_when_removing_missing_tag(self) -> None:
        file_id = self._seed_file()

        with TestClient(app) as client:
            response = client.delete(f"/files/{file_id}/tags/9999")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"error": {"code": "TAG_NOT_FOUND", "message": "Tag not found."}},
            response.json(),
        )

        engine.dispose()

    def _seed_file(
        self,
        *,
        path: str = "D:\\Assets\\Refs\\Cover.PNG",
        parent_path: str = "D:\\Assets\\Refs",
        name: str = "Cover.PNG",
        stem: str = "Cover",
    ) -> int:
        with SessionLocal() as session:
            source = session.scalars(select(Source).where(Source.path == "D:\\Assets")).first()
            if source is None:
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
                path=path,
                parent_path=parent_path,
                name=name,
                stem=stem,
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=123,
                created_at_fs=_dt(9, 30),
                modified_at_fs=_dt(10),
                discovered_at=_dt(9, 35),
                last_seen_at=_dt(10),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10),
            )
            session.add(file)
            session.commit()
            return int(file.id)

    def _seed_deleted_file_with_tag(self, tag_name: str) -> None:
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

            tag = Tag(
                name=tag_name,
                normalized_name=tag_name.casefold(),
                created_at=_dt(8),
                updated_at=_dt(8),
            )
            session.add(tag)
            session.flush()

            file = File(
                source_id=source.id,
                path="D:\\Assets\\Refs\\Deleted.PNG",
                parent_path="D:\\Assets\\Refs",
                name="Deleted.PNG",
                stem="Deleted",
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=123,
                created_at_fs=_dt(9, 30),
                modified_at_fs=_dt(10),
                discovered_at=_dt(9, 35),
                last_seen_at=_dt(10),
                is_deleted=True,
                checksum_hint=None,
                updated_at=_dt(10),
            )
            session.add(file)
            session.flush()

            session.add(
                FileTag(
                    file_id=file.id,
                    tag_id=tag.id,
                    created_at=_dt(10, 15),
                )
            )
            session.commit()

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
