import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.file_user_meta import FileUserMeta
from app.db.models.source import Source
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 22, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase7BFileUserMetaTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_updates_favorite_and_rating_and_exposes_them_in_details(self) -> None:
        seeded = self._seed_files()

        with TestClient(app) as client:
            favorite_response = client.patch(
                f"/files/{seeded['media_id']}/user-meta",
                json={"is_favorite": True},
            )
            rating_response = client.patch(
                f"/files/{seeded['media_id']}/user-meta",
                json={"rating": 3},
            )
            detail_response = client.get(f"/files/{seeded['media_id']}")

        self.assertEqual(200, favorite_response.status_code)
        self.assertTrue(favorite_response.json()["item"]["is_favorite"])
        self.assertEqual(5, favorite_response.json()["item"]["rating"])

        self.assertEqual(200, rating_response.status_code)
        self.assertTrue(rating_response.json()["item"]["is_favorite"])
        self.assertEqual(3, rating_response.json()["item"]["rating"])

        self.assertEqual(200, detail_response.status_code)
        self.assertTrue(detail_response.json()["item"]["is_favorite"])
        self.assertEqual(3, detail_response.json()["item"]["rating"])

    def test_clears_rating_with_null_and_updates_favorite_together(self) -> None:
        seeded = self._seed_files()

        with TestClient(app) as client:
            response = client.patch(
                f"/files/{seeded['book_id']}/user-meta",
                json={"is_favorite": False, "rating": None},
            )
            detail_response = client.get(f"/files/{seeded['book_id']}")

        self.assertEqual(200, response.status_code)
        self.assertFalse(response.json()["item"]["is_favorite"])
        self.assertIsNone(response.json()["item"]["rating"])
        self.assertFalse(detail_response.json()["item"]["is_favorite"])
        self.assertIsNone(detail_response.json()["item"]["rating"])

    def test_rejects_empty_payload_and_invalid_rating(self) -> None:
        seeded = self._seed_files()

        with TestClient(app) as client:
            empty_response = client.patch(f"/files/{seeded['software_id']}/user-meta", json={})
            invalid_rating_response = client.patch(
                f"/files/{seeded['software_id']}/user-meta",
                json={"rating": 6},
            )
            invalid_favorite_response = client.patch(
                f"/files/{seeded['software_id']}/user-meta",
                json={"is_favorite": None},
            )

        self.assertEqual(400, empty_response.status_code)
        self.assertEqual("FILE_USER_META_PATCH_EMPTY", empty_response.json()["error"]["code"])
        self.assertEqual(400, invalid_rating_response.status_code)
        self.assertEqual("FILE_RATING_INVALID", invalid_rating_response.json()["error"]["code"])
        self.assertEqual(400, invalid_favorite_response.status_code)
        self.assertEqual("FILE_FAVORITE_INVALID", invalid_favorite_response.json()["error"]["code"])

    def test_returns_404_for_missing_file(self) -> None:
        self._seed_files()

        with TestClient(app) as client:
            response = client.patch("/files/999999/user-meta", json={"is_favorite": True})

        self.assertEqual(404, response.status_code)
        self.assertEqual("FILE_NOT_FOUND", response.json()["error"]["code"])

    def test_library_surfaces_echo_favorite_and_rating_without_changing_game_status(self) -> None:
        self._seed_files()

        with TestClient(app) as client:
            media_response = client.get("/library/media", params={"sort_by": "name", "sort_order": "asc"})
            books_response = client.get("/library/books", params={"sort_by": "name", "sort_order": "asc"})
            games_response = client.get("/library/games", params={"sort_by": "name", "sort_order": "asc"})
            software_response = client.get("/library/software", params={"sort_by": "name", "sort_order": "asc"})

        media_item = media_response.json()["items"][0]
        self.assertEqual("Poster.png", media_item["name"])
        self.assertTrue(media_item["is_favorite"])
        self.assertEqual(5, media_item["rating"])

        book_item = books_response.json()["items"][0]
        self.assertEqual("Blue Manual", book_item["display_title"])
        self.assertFalse(book_item["is_favorite"])
        self.assertEqual(2, book_item["rating"])

        game_item = games_response.json()["items"][0]
        self.assertEqual("Launcher Shortcut", game_item["display_title"])
        self.assertTrue(game_item["is_favorite"])
        self.assertEqual(4, game_item["rating"])
        self.assertEqual("playing", game_item["status"])

        software_item = software_response.json()["items"][0]
        self.assertEqual("Utility Pack", software_item["display_title"])
        self.assertFalse(software_item["is_favorite"])
        self.assertIsNone(software_item["rating"])

    def _seed_files(self) -> dict[str, int]:
        with SessionLocal() as session:
            source = Source(
                path=r"D:\Library",
                display_name="Library",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_dt(9),
                last_scan_status="succeeded",
                created_at=_dt(8),
                updated_at=_dt(9),
            )
            session.add(source)
            session.flush()

            media_file = File(
                source_id=source.id,
                path=r"D:\Library\Media\Poster.png",
                parent_path=r"D:\Library\Media",
                name="Poster.png",
                stem="Poster",
                extension="png",
                file_type="image",
                mime_type=None,
                size_bytes=120,
                created_at_fs=_dt(9, 10),
                modified_at_fs=_dt(9, 30),
                discovered_at=_dt(9, 15),
                last_seen_at=_dt(9, 30),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(9, 30),
            )
            book_file = File(
                source_id=source.id,
                path=r"D:\Library\Books\Blue Manual.pdf",
                parent_path=r"D:\Library\Books",
                name="Blue Manual.pdf",
                stem="Blue Manual",
                extension="pdf",
                file_type="document",
                mime_type=None,
                size_bytes=220,
                created_at_fs=_dt(9, 40),
                modified_at_fs=_dt(9, 55),
                discovered_at=_dt(9, 42),
                last_seen_at=_dt(9, 55),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(9, 55),
            )
            game_file = File(
                source_id=source.id,
                path=r"D:\Library\Games\Launcher Shortcut.lnk",
                parent_path=r"D:\Library\Games",
                name="Launcher Shortcut.lnk",
                stem="Launcher Shortcut",
                extension="lnk",
                file_type="other",
                mime_type=None,
                size_bytes=12,
                created_at_fs=_dt(10, 5),
                modified_at_fs=_dt(10, 25),
                discovered_at=_dt(10, 6),
                last_seen_at=_dt(10, 25),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10, 25),
            )
            software_file = File(
                source_id=source.id,
                path=r"D:\Library\Software\Utility Pack.zip",
                parent_path=r"D:\Library\Software",
                name="Utility Pack.zip",
                stem="Utility Pack",
                extension="zip",
                file_type="archive",
                mime_type=None,
                size_bytes=440,
                created_at_fs=_dt(10, 40),
                modified_at_fs=_dt(10, 45),
                discovered_at=_dt(10, 41),
                last_seen_at=_dt(10, 45),
                is_deleted=False,
                checksum_hint=None,
                updated_at=_dt(10, 45),
            )
            session.add_all([media_file, book_file, game_file, software_file])
            session.flush()

            session.add_all(
                [
                    FileUserMeta(
                        file_id=media_file.id,
                        color_tag=None,
                        status=None,
                        rating=5,
                        is_favorite=True,
                        updated_at=_dt(11),
                    ),
                    FileUserMeta(
                        file_id=book_file.id,
                        color_tag=None,
                        status=None,
                        rating=2,
                        is_favorite=False,
                        updated_at=_dt(11, 1),
                    ),
                    FileUserMeta(
                        file_id=game_file.id,
                        color_tag=None,
                        status="playing",
                        rating=4,
                        is_favorite=True,
                        updated_at=_dt(11, 2),
                    ),
                ]
            )
            session.commit()

            return {
                "media_id": int(media_file.id),
                "book_id": int(book_file.id),
                "software_id": int(software_file.id),
            }

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
