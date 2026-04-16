import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.source import Source
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _aware_dt(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _naive_utc(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(tzinfo=None)


FIXED_NOW = _aware_dt(2026, 4, 16, 12, 0)


class Phase5BRecentImportsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_returns_active_indexed_files_ordered_by_discovered_at_desc(self) -> None:
        self._seed_sources_and_files()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                response = client.get("/recent")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [
                "Boundary Now.zip",
                "Recent Cover.png",
                "Alpha Twin.png",
                "Beta Twin.png",
                "Boundary Cutoff.pdf",
                "Within Seven Days.mp4",
            ],
            [item["name"] for item in response.json()["items"]],
        )

    def test_defaults_to_7d_range_when_omitted(self) -> None:
        self._seed_sources_and_files()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                omitted_response = client.get("/recent")
                explicit_response = client.get("/recent", params={"range": "7d"})

        self.assertEqual(omitted_response.json(), explicit_response.json())

    def test_returns_recent_range_invalid_for_invalid_or_blank_range(self) -> None:
        self._seed_sources_and_files()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                invalid_response = client.get("/recent", params={"range": "90d"})
                blank_response = client.get("/recent", params={"range": "   "})

        self.assertEqual(400, invalid_response.status_code)
        self.assertEqual("RECENT_RANGE_INVALID", invalid_response.json()["error"]["code"])
        self.assertEqual(400, blank_response.status_code)
        self.assertEqual("RECENT_RANGE_INVALID", blank_response.json()["error"]["code"])

    def test_filters_by_1d_7d_30d_ranges(self) -> None:
        self._seed_sources_and_files()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                one_day = client.get("/recent", params={"range": "1d"})
                seven_day = client.get("/recent", params={"range": "7d"})
                thirty_day = client.get("/recent", params={"range": "30d"})

        self.assertEqual(
            ["Boundary Now.zip", "Recent Cover.png", "Alpha Twin.png", "Beta Twin.png", "Boundary Cutoff.pdf"],
            [item["name"] for item in one_day.json()["items"]],
        )
        self.assertEqual(
            [
                "Boundary Now.zip",
                "Recent Cover.png",
                "Alpha Twin.png",
                "Beta Twin.png",
                "Boundary Cutoff.pdf",
                "Within Seven Days.mp4",
            ],
            [item["name"] for item in seven_day.json()["items"]],
        )
        self.assertEqual(
            [
                "Boundary Now.zip",
                "Recent Cover.png",
                "Alpha Twin.png",
                "Beta Twin.png",
                "Boundary Cutoff.pdf",
                "Within Seven Days.mp4",
                "Within Thirty Days.bin",
            ],
            [item["name"] for item in thirty_day.json()["items"]],
        )

    def test_includes_discovered_at_equal_to_cutoff(self) -> None:
        self._seed_sources_and_files()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                response = client.get("/recent", params={"range": "1d"})

        self.assertIn("Boundary Cutoff.pdf", [item["name"] for item in response.json()["items"]])

    def test_includes_discovered_at_equal_to_now(self) -> None:
        self._seed_sources_and_files()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                response = client.get("/recent", params={"range": "1d"})

        by_name = {item["name"]: item for item in response.json()["items"]}
        self.assertEqual("2026-04-16T12:00:00", by_name["Boundary Now.zip"]["discovered_at"])

    def test_excludes_deleted_rows(self) -> None:
        self._seed_sources_and_files()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                response = client.get("/recent", params={"range": "30d"})

        names = [item["name"] for item in response.json()["items"]]
        self.assertNotIn("deleted-file.png", names)

    def test_supports_ascending_order(self) -> None:
        self._seed_sources_and_files()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                response = client.get("/recent", params={"range": "7d", "sort_order": "asc"})

        self.assertEqual(
            [
                "Within Seven Days.mp4",
                "Boundary Cutoff.pdf",
                "Alpha Twin.png",
                "Beta Twin.png",
                "Recent Cover.png",
                "Boundary Now.zip",
            ],
            [item["name"] for item in response.json()["items"]],
        )

    def test_paginates_and_orders_stably_across_repeated_requests(self) -> None:
        self._seed_sources_and_files()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                first_response = client.get("/recent", params={"range": "7d", "page": 1, "page_size": 6})
                repeated_response = client.get("/recent", params={"range": "7d", "page": 1, "page_size": 6})
                page_one = client.get("/recent", params={"range": "7d", "page": 1, "page_size": 3})
                page_two = client.get("/recent", params={"range": "7d", "page": 2, "page_size": 3})

        self.assertEqual(
            [item["id"] for item in first_response.json()["items"]],
            [item["id"] for item in repeated_response.json()["items"]],
        )
        self.assertEqual(
            ["Boundary Now.zip", "Recent Cover.png", "Alpha Twin.png"],
            [item["name"] for item in page_one.json()["items"]],
        )
        self.assertEqual(
            ["Beta Twin.png", "Boundary Cutoff.pdf", "Within Seven Days.mp4"],
            [item["name"] for item in page_two.json()["items"]],
        )

    def test_preserves_nullable_size_bytes_in_recent_response(self) -> None:
        self._seed_sources_and_files()

        with patch("app.services.recent.service.utc_now", return_value=FIXED_NOW):
            with TestClient(app) as client:
                response = client.get("/recent", params={"range": "7d"})

        by_name = {item["name"]: item for item in response.json()["items"]}
        self.assertIsNone(by_name["Boundary Cutoff.pdf"]["size_bytes"])

    def _seed_sources_and_files(self) -> None:
        with SessionLocal() as session:
            source = Source(
                path=r"D:\Assets",
                display_name="Assets",
                is_enabled=True,
                scan_mode="manual_plus_basic_incremental",
                last_scan_at=_naive_utc(_aware_dt(2026, 4, 16, 9)),
                last_scan_status="succeeded",
                created_at=_naive_utc(_aware_dt(2026, 4, 16, 8)),
                updated_at=_naive_utc(_aware_dt(2026, 4, 16, 9)),
            )
            session.add(source)
            session.flush()

            session.add_all(
                [
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\New\Boundary Now.zip",
                        parent_path=r"D:\Assets\New",
                        name="Boundary Now.zip",
                        stem="Boundary Now",
                        extension="zip",
                        file_type="archive",
                        mime_type=None,
                        size_bytes=1024,
                        created_at_fs=None,
                        modified_at_fs=None,
                        discovered_at=_naive_utc(FIXED_NOW),
                        last_seen_at=_naive_utc(FIXED_NOW),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_naive_utc(FIXED_NOW),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\New\Recent Cover.png",
                        parent_path=r"D:\Assets\New",
                        name="Recent Cover.png",
                        stem="Recent Cover",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=320,
                        created_at_fs=None,
                        modified_at_fs=None,
                        discovered_at=_naive_utc(_aware_dt(2026, 4, 16, 11)),
                        last_seen_at=_naive_utc(_aware_dt(2026, 4, 16, 11)),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_naive_utc(_aware_dt(2026, 4, 16, 11)),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\New\Alpha Twin.png",
                        parent_path=r"D:\Assets\New",
                        name="Alpha Twin.png",
                        stem="Alpha Twin",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=512,
                        created_at_fs=None,
                        modified_at_fs=None,
                        discovered_at=_naive_utc(_aware_dt(2026, 4, 15, 18)),
                        last_seen_at=_naive_utc(_aware_dt(2026, 4, 15, 18)),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_naive_utc(_aware_dt(2026, 4, 15, 18)),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\New\Beta Twin.png",
                        parent_path=r"D:\Assets\New",
                        name="Beta Twin.png",
                        stem="Beta Twin",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=640,
                        created_at_fs=None,
                        modified_at_fs=None,
                        discovered_at=_naive_utc(_aware_dt(2026, 4, 15, 18)),
                        last_seen_at=_naive_utc(_aware_dt(2026, 4, 15, 18)),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_naive_utc(_aware_dt(2026, 4, 15, 18)),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\Docs\Boundary Cutoff.pdf",
                        parent_path=r"D:\Assets\Docs",
                        name="Boundary Cutoff.pdf",
                        stem="Boundary Cutoff",
                        extension="pdf",
                        file_type="document",
                        mime_type=None,
                        size_bytes=None,
                        created_at_fs=None,
                        modified_at_fs=None,
                        discovered_at=_naive_utc(_aware_dt(2026, 4, 15, 12)),
                        last_seen_at=_naive_utc(_aware_dt(2026, 4, 15, 12)),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_naive_utc(_aware_dt(2026, 4, 15, 12)),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\Videos\Within Seven Days.mp4",
                        parent_path=r"D:\Assets\Videos",
                        name="Within Seven Days.mp4",
                        stem="Within Seven Days",
                        extension="mp4",
                        file_type="video",
                        mime_type=None,
                        size_bytes=2048,
                        created_at_fs=None,
                        modified_at_fs=None,
                        discovered_at=_naive_utc(_aware_dt(2026, 4, 10, 15)),
                        last_seen_at=_naive_utc(_aware_dt(2026, 4, 10, 15)),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_naive_utc(_aware_dt(2026, 4, 10, 15)),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\Misc\Within Thirty Days.bin",
                        parent_path=r"D:\Assets\Misc",
                        name="Within Thirty Days.bin",
                        stem="Within Thirty Days",
                        extension="bin",
                        file_type="other",
                        mime_type=None,
                        size_bytes=4096,
                        created_at_fs=None,
                        modified_at_fs=None,
                        discovered_at=_naive_utc(_aware_dt(2026, 3, 25, 9)),
                        last_seen_at=_naive_utc(_aware_dt(2026, 3, 25, 9)),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_naive_utc(_aware_dt(2026, 3, 25, 9)),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\Archive\Too Old.zip",
                        parent_path=r"D:\Assets\Archive",
                        name="Too Old.zip",
                        stem="Too Old",
                        extension="zip",
                        file_type="archive",
                        mime_type=None,
                        size_bytes=55,
                        created_at_fs=None,
                        modified_at_fs=None,
                        discovered_at=_naive_utc(_aware_dt(2026, 3, 10, 9)),
                        last_seen_at=_naive_utc(_aware_dt(2026, 3, 10, 9)),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_naive_utc(_aware_dt(2026, 3, 10, 9)),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Assets\New\deleted-file.png",
                        parent_path=r"D:\Assets\New",
                        name="deleted-file.png",
                        stem="deleted-file",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=123,
                        created_at_fs=None,
                        modified_at_fs=None,
                        discovered_at=_naive_utc(_aware_dt(2026, 4, 16, 10)),
                        last_seen_at=_naive_utc(_aware_dt(2026, 4, 16, 10)),
                        is_deleted=True,
                        checksum_hint=None,
                        updated_at=_naive_utc(_aware_dt(2026, 4, 16, 10)),
                    ),
                ]
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
