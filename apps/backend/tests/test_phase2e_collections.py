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
    return datetime(2026, 4, 17, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase2ECollectionsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_creates_collection_with_valid_minimal_payload(self) -> None:
        tag_id, _, source_id = self._seed_library()

        with TestClient(app) as client:
            response = client.post(
                "/collections",
                json={
                    "name": "Blue images",
                    "file_type": "image",
                    "tag_id": tag_id,
                    "color_tag": "blue",
                    "source_id": source_id,
                    "parent_path": "D:\\Assets\\Refs",
                },
            )

        self.assertEqual(201, response.status_code)
        payload = response.json()
        self.assertEqual("Blue images", payload["name"])
        self.assertEqual("image", payload["file_type"])
        self.assertEqual(tag_id, payload["tag_id"])
        self.assertEqual("blue", payload["color_tag"])
        self.assertEqual(source_id, payload["source_id"])
        self.assertEqual("D:\\Assets\\Refs", payload["parent_path"])

    def test_allows_duplicate_collection_names(self) -> None:
        tag_id, _, _ = self._seed_library()

        with TestClient(app) as client:
            first = client.post("/collections", json={"name": "References", "tag_id": tag_id})
            second = client.post("/collections", json={"name": "References", "color_tag": "blue"})
            listed = client.get("/collections")

        self.assertEqual(201, first.status_code)
        self.assertEqual(201, second.status_code)
        self.assertEqual(2, listed.json()["items"][0]["id"] - listed.json()["items"][1]["id"] + 1)
        self.assertEqual(["References", "References"], [item["name"] for item in listed.json()["items"]])

    def test_allows_name_only_collection(self) -> None:
        self._seed_library()

        with TestClient(app) as client:
            create_response = client.post("/collections", json={"name": "Everything"})
            collection_id = create_response.json()["id"]
            files_response = client.get(f"/collections/{collection_id}/files")

        self.assertEqual(201, create_response.status_code)
        self.assertEqual(5, files_response.json()["total"])

    def test_rejects_blank_collection_name(self) -> None:
        self._seed_library()

        with TestClient(app) as client:
            response = client.post("/collections", json={"name": "   "})

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"error": {"code": "COLLECTION_NAME_INVALID", "message": "Collection name cannot be empty."}},
            response.json(),
        )

    def test_rejects_invalid_color_tag(self) -> None:
        self._seed_library()

        with TestClient(app) as client:
            response = client.post("/collections", json={"name": "Bad color", "color_tag": "orange"})

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"error": {"code": "COLOR_TAG_INVALID", "message": "Color tag is invalid."}},
            response.json(),
        )

    def test_returns_tag_not_found_for_unknown_tag_id(self) -> None:
        self._seed_library()

        with TestClient(app) as client:
            response = client.post("/collections", json={"name": "Missing tag", "tag_id": 999999})

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"error": {"code": "TAG_NOT_FOUND", "message": "Tag not found."}},
            response.json(),
        )

    def test_returns_source_not_found_for_unknown_source_id(self) -> None:
        self._seed_library()

        with TestClient(app) as client:
            response = client.post("/collections", json={"name": "Missing source", "source_id": 999999})

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {"error": {"code": "SOURCE_NOT_FOUND", "message": "Source not found."}},
            response.json(),
        )

    def test_requires_source_when_parent_path_is_provided(self) -> None:
        self._seed_library()

        with TestClient(app) as client:
            response = client.post("/collections", json={"name": "Bad path", "parent_path": "D:\\Assets\\Refs"})

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {"error": {"code": "PARENT_PATH_REQUIRES_SOURCE", "message": "Parent path requires a source."}},
            response.json(),
        )

    def test_lists_collections_in_created_at_desc_order(self) -> None:
        self._seed_library()

        with TestClient(app) as client:
            first = client.post("/collections", json={"name": "Older"})
            second = client.post("/collections", json={"name": "Newer"})
            response = client.get("/collections")

        self.assertEqual(201, first.status_code)
        self.assertEqual(201, second.status_code)
        self.assertEqual(["Newer", "Older"], [item["name"] for item in response.json()["items"]])

    def test_deletes_collection(self) -> None:
        self._seed_library()

        with TestClient(app) as client:
            created = client.post("/collections", json={"name": "Delete me"})
            collection_id = created.json()["id"]
            deleted = client.delete(f"/collections/{collection_id}")
            listed = client.get("/collections")

        self.assertEqual(200, deleted.status_code)
        self.assertEqual({"message": "Collection deleted."}, deleted.json())
        self.assertEqual([], listed.json()["items"])

    def test_returns_collection_not_found_for_unknown_collection_id(self) -> None:
        self._seed_library()

        with TestClient(app) as client:
            delete_response = client.delete("/collections/999999")
            files_response = client.get("/collections/999999/files")

        expected = {"error": {"code": "COLLECTION_NOT_FOUND", "message": "Collection not found."}}
        self.assertEqual(404, delete_response.status_code)
        self.assertEqual(expected, delete_response.json())
        self.assertEqual(404, files_response.status_code)
        self.assertEqual(expected, files_response.json())

    def test_collection_files_apply_saved_filters_with_and_semantics(self) -> None:
        tag_id, _, source_id = self._seed_library()

        with TestClient(app) as client:
            created = client.post(
                "/collections",
                json={
                    "name": "Blue image refs",
                    "file_type": "image",
                    "tag_id": tag_id,
                    "color_tag": "blue",
                    "source_id": source_id,
                    "parent_path": "D:\\Assets\\Refs",
                },
            )
            response = client.get(f"/collections/{created.json()['id']}/files")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, payload["total"])
        self.assertEqual(["blue-ref.png"], [item["name"] for item in payload["items"]])

    def test_collection_files_preserve_exact_directory_semantics(self) -> None:
        _, _, source_id = self._seed_library()

        with TestClient(app) as client:
            created = client.post(
                "/collections",
                json={
                    "name": "Refs only",
                    "source_id": source_id,
                    "parent_path": "D:\\Assets\\Refs",
                },
            )
            response = client.get(f"/collections/{created.json()['id']}/files", params={"sort_by": "name", "sort_order": "asc"})

        self.assertEqual(["blue-ref.png", "red-ref.png"], [item["name"] for item in response.json()["items"]])
        self.assertNotIn("nested-ref.png", [item["name"] for item in response.json()["items"]])

    def test_collection_files_preserve_stable_ordering(self) -> None:
        _, _, _ = self._seed_library()

        with TestClient(app) as client:
            created = client.post("/collections", json={"name": "Everything"})
            collection_id = created.json()["id"]
            first = client.get(f"/collections/{collection_id}/files", params={"sort_by": "modified_at", "sort_order": "desc"})
            second = client.get(f"/collections/{collection_id}/files", params={"sort_by": "modified_at", "sort_order": "desc"})

        self.assertEqual(
            [item["id"] for item in first.json()["items"]],
            [item["id"] for item in second.json()["items"]],
        )

    def test_collection_files_do_not_duplicate_rows_or_total(self) -> None:
        tag_id, _, _ = self._seed_library()

        with TestClient(app) as client:
            created = client.post("/collections", json={"name": "Tagged blue", "tag_id": tag_id, "color_tag": "blue"})
            response = client.get(f"/collections/{created.json()['id']}/files", params={"sort_by": "name", "sort_order": "asc"})

        payload = response.json()
        self.assertEqual(2, payload["total"])
        self.assertEqual(["blue-ref.png", "nested-ref.png"], [item["name"] for item in payload["items"]])

    def test_collection_files_return_empty_when_saved_source_or_tag_no_longer_exists(self) -> None:
        tag_id, _, source_id = self._seed_library()

        with TestClient(app) as client:
            source_collection = client.post("/collections", json={"name": "Source refs", "source_id": source_id})
            tag_collection = client.post("/collections", json={"name": "Tagged refs", "tag_id": tag_id})

        with SessionLocal() as session:
            session.execute(text("DELETE FROM sources WHERE id = :source_id"), {"source_id": source_id})
            session.execute(text("DELETE FROM tags WHERE id = :tag_id"), {"tag_id": tag_id})
            session.commit()

        with TestClient(app) as client:
            source_response = client.get(f"/collections/{source_collection.json()['id']}/files")
            tag_response = client.get(f"/collections/{tag_collection.json()['id']}/files")

        self.assertEqual(200, source_response.status_code)
        self.assertEqual(0, source_response.json()["total"])
        self.assertEqual([], source_response.json()["items"])
        self.assertEqual(200, tag_response.status_code)
        self.assertEqual(0, tag_response.json()["total"])
        self.assertEqual([], tag_response.json()["items"])

    def _seed_library(self) -> tuple[int, int, int]:
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
            other_source = Source(
                path="D:\\Secondary",
                display_name="Secondary",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9, 5),
                last_scan_status="succeeded",
                created_at=_dt(8, 5),
                updated_at=_dt(9, 5),
            )
            session.add_all([source, other_source])
            session.flush()

            ref_tag = Tag(name="Reference", normalized_name="reference", created_at=_dt(8), updated_at=_dt(8))
            other_tag = Tag(name="Ignore", normalized_name="ignore", created_at=_dt(8, 10), updated_at=_dt(8, 10))
            session.add_all([ref_tag, other_tag])
            session.flush()

            files = [
                File(
                    source_id=source.id,
                    path="D:\\Assets\\Refs\\blue-ref.png",
                    parent_path="D:\\Assets\\Refs",
                    name="blue-ref.png",
                    stem="blue-ref",
                    extension="png",
                    file_type="image",
                    mime_type="image/png",
                    size_bytes=111,
                    created_at_fs=_dt(9),
                    modified_at_fs=_dt(10),
                    discovered_at=_dt(9, 30),
                    last_seen_at=_dt(10),
                    is_deleted=False,
                    checksum_hint=None,
                    updated_at=_dt(10),
                ),
                File(
                    source_id=source.id,
                    path="D:\\Assets\\Refs\\red-ref.png",
                    parent_path="D:\\Assets\\Refs",
                    name="red-ref.png",
                    stem="red-ref",
                    extension="png",
                    file_type="image",
                    mime_type="image/png",
                    size_bytes=112,
                    created_at_fs=_dt(9, 5),
                    modified_at_fs=_dt(10),
                    discovered_at=_dt(9, 35),
                    last_seen_at=_dt(10),
                    is_deleted=False,
                    checksum_hint=None,
                    updated_at=_dt(10),
                ),
                File(
                    source_id=source.id,
                    path="D:\\Assets\\Refs\\Nested\\nested-ref.png",
                    parent_path="D:\\Assets\\Refs\\Nested",
                    name="nested-ref.png",
                    stem="nested-ref",
                    extension="png",
                    file_type="image",
                    mime_type="image/png",
                    size_bytes=113,
                    created_at_fs=_dt(9, 10),
                    modified_at_fs=_dt(10),
                    discovered_at=_dt(9, 40),
                    last_seen_at=_dt(10),
                    is_deleted=False,
                    checksum_hint=None,
                    updated_at=_dt(10),
                ),
                File(
                    source_id=source.id,
                    path="D:\\Assets\\Docs\\notes.pdf",
                    parent_path="D:\\Assets\\Docs",
                    name="notes.pdf",
                    stem="notes",
                    extension="pdf",
                    file_type="document",
                    mime_type="application/pdf",
                    size_bytes=210,
                    created_at_fs=_dt(9, 15),
                    modified_at_fs=_dt(11),
                    discovered_at=_dt(9, 45),
                    last_seen_at=_dt(11),
                    is_deleted=False,
                    checksum_hint=None,
                    updated_at=_dt(11),
                ),
                File(
                    source_id=other_source.id,
                    path="D:\\Secondary\\other.png",
                    parent_path="D:\\Secondary",
                    name="other.png",
                    stem="other",
                    extension="png",
                    file_type="image",
                    mime_type="image/png",
                    size_bytes=333,
                    created_at_fs=_dt(9, 20),
                    modified_at_fs=_dt(12),
                    discovered_at=_dt(9, 50),
                    last_seen_at=_dt(12),
                    is_deleted=False,
                    checksum_hint=None,
                    updated_at=_dt(12),
                ),
            ]
            session.add_all(files)
            session.flush()

            session.add_all(
                [
                    FileTag(file_id=files[0].id, tag_id=ref_tag.id, created_at=_dt(12)),
                    FileTag(file_id=files[2].id, tag_id=ref_tag.id, created_at=_dt(12)),
                    FileTag(file_id=files[3].id, tag_id=other_tag.id, created_at=_dt(12)),
                ]
            )
            session.add_all(
                [
                    FileUserMeta(file_id=files[0].id, color_tag="blue", status=None, rating=None, is_favorite=False, updated_at=_dt(12)),
                    FileUserMeta(file_id=files[1].id, color_tag="red", status=None, rating=None, is_favorite=False, updated_at=_dt(12)),
                    FileUserMeta(file_id=files[2].id, color_tag="blue", status=None, rating=None, is_favorite=False, updated_at=_dt(12)),
                ]
            )
            session.commit()
            return int(ref_tag.id), int(other_tag.id), int(source.id)

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM collections"))
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
