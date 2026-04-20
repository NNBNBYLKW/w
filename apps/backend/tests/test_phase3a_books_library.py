import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.source import Source
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 18, hour, minute, tzinfo=UTC).replace(tzinfo=None)


class Phase3ABooksLibraryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    def test_returns_active_epub_and_pdf_files_only(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/books")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(6, payload["total"])
        self.assertEqual(
            [
                "Zeta Notes",
                "Beta Manual",
                "Alpha Guide",
                "Gamma Notes.pdf",
                "Deep Space Vol. 1",
                "Space Opera Draft.pdf",
            ],
            [item["display_title"] for item in payload["items"]],
        )

    def test_excludes_deleted_and_non_book_rows(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/books", params={"sort_by": "name", "sort_order": "asc"})

        titles = [item["display_title"] for item in response.json()["items"]]
        self.assertNotIn("deleted-book", titles)
        self.assertNotIn("Cover", titles)
        self.assertNotIn("Notes", titles)

    def test_maps_display_title_book_format_and_modified_at_fallback(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/books", params={"sort_by": "name", "sort_order": "asc"})

        by_title = {item["display_title"]: item for item in response.json()["items"]}
        self.assertEqual("epub", by_title["Alpha Guide"]["book_format"])
        self.assertEqual("pdf", by_title["Beta Manual"]["book_format"])
        self.assertEqual("2026-04-18T12:00:00", by_title["Beta Manual"]["modified_at"])
        self.assertEqual("Gamma Notes.pdf", by_title["Gamma Notes.pdf"]["display_title"])
        self.assertEqual("Deep Space Vol. 1", by_title["Deep Space Vol. 1"]["display_title"])
        self.assertEqual("Space Opera Draft.pdf", by_title["Space Opera Draft.pdf"]["display_title"])

    def test_normalizes_underscores_and_whitespace_conservatively(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            response = client.get("/library/books", params={"sort_by": "name", "sort_order": "asc"})

        titles = [item["display_title"] for item in response.json()["items"]]
        self.assertIn("Deep Space Vol. 1", titles)
        self.assertIn("Space Opera Draft.pdf", titles)
        self.assertIn("Gamma Notes.pdf", titles)

    def test_supports_name_and_discovered_at_sorting(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            name_response = client.get("/library/books", params={"sort_by": "name", "sort_order": "asc"})
            discovered_response = client.get("/library/books", params={"sort_by": "discovered_at", "sort_order": "asc"})

        self.assertEqual(
            [
                "Space Opera Draft.pdf",
                "Alpha Guide",
                "Beta Manual",
                "Deep Space Vol. 1",
                "Gamma Notes.pdf",
                "Zeta Notes",
            ],
            [item["display_title"] for item in name_response.json()["items"]],
        )
        self.assertEqual(
            [
                "Alpha Guide",
                "Gamma Notes.pdf",
                "Deep Space Vol. 1",
                "Space Opera Draft.pdf",
                "Beta Manual",
                "Zeta Notes",
            ],
            [item["display_title"] for item in discovered_response.json()["items"]],
        )

    def test_paginates_and_sorts_stably(self) -> None:
        self._seed_sources_and_files()

        with TestClient(app) as client:
            first_response = client.get(
                "/library/books",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 6},
            )
            repeated_response = client.get(
                "/library/books",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 6},
            )
            page_one = client.get(
                "/library/books",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 1, "page_size": 3},
            )
            page_two = client.get(
                "/library/books",
                params={"sort_by": "modified_at", "sort_order": "desc", "page": 2, "page_size": 3},
            )

        first_items = first_response.json()["items"]
        repeated_items = repeated_response.json()["items"]
        self.assertEqual([item["id"] for item in first_items], [item["id"] for item in repeated_items])
        self.assertEqual(
            [
                "Zeta Notes",
                "Beta Manual",
                "Alpha Guide",
                "Gamma Notes.pdf",
                "Deep Space Vol. 1",
                "Space Opera Draft.pdf",
            ],
            [item["display_title"] for item in first_items],
        )
        self.assertEqual(
            ["Zeta Notes", "Beta Manual", "Alpha Guide"],
            [item["display_title"] for item in page_one.json()["items"]],
        )
        self.assertEqual(
            ["Gamma Notes.pdf", "Deep Space Vol. 1", "Space Opera Draft.pdf"],
            [item["display_title"] for item in page_two.json()["items"]],
        )

    def _seed_sources_and_files(self) -> None:
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

            session.add_all(
                [
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Books\Alpha Guide.epub",
                        parent_path=r"D:\Library\Books",
                        name="Alpha Guide.epub",
                        stem="Alpha Guide",
                        extension="epub",
                        file_type="other",
                        mime_type=None,
                        size_bytes=1200,
                        created_at_fs=_dt(9, 20),
                        modified_at_fs=_dt(11),
                        discovered_at=_dt(9, 25),
                        last_seen_at=_dt(11),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(11),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Books\Beta Manual.pdf",
                        parent_path=r"D:\Library\Books",
                        name="Beta Manual.pdf",
                        stem="Beta Manual",
                        extension="PDF",
                        file_type="document",
                        mime_type=None,
                        size_bytes=2100,
                        created_at_fs=_dt(11, 30),
                        modified_at_fs=None,
                        discovered_at=_dt(12),
                        last_seen_at=_dt(12),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(12),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Books\Gamma Notes.pdf",
                        parent_path=r"D:\Library\Books",
                        name="Gamma Notes.pdf",
                        stem=None,
                        extension="pdf",
                        file_type="document",
                        mime_type=None,
                        size_bytes=None,
                        created_at_fs=_dt(9, 22),
                        modified_at_fs=_dt(11),
                        discovered_at=_dt(9, 28),
                        last_seen_at=_dt(11),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(11),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Books\Zeta Notes.epub",
                        parent_path=r"D:\Library\Books",
                        name="Zeta Notes.epub",
                        stem="Zeta Notes",
                        extension="epub",
                        file_type="other",
                        mime_type=None,
                        size_bytes=3400,
                        created_at_fs=_dt(12, 15),
                        modified_at_fs=_dt(13),
                        discovered_at=_dt(12, 20),
                        last_seen_at=_dt(13),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(13),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Books\Deep_Space__Vol._1.epub",
                        parent_path=r"D:\Library\Books",
                        name="Deep_Space__Vol._1.epub",
                        stem="Deep_Space__Vol._1",
                        extension="epub",
                        file_type="other",
                        mime_type=None,
                        size_bytes=4100,
                        created_at_fs=_dt(10, 5),
                        modified_at_fs=_dt(10, 40),
                        discovered_at=_dt(9, 40),
                        last_seen_at=_dt(10, 40),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(10, 40),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Books\  Space__Opera   Draft.pdf",
                        parent_path=r"D:\Library\Books",
                        name="  Space__Opera   Draft.pdf",
                        stem="   ",
                        extension="pdf",
                        file_type="document",
                        mime_type=None,
                        size_bytes=1900,
                        created_at_fs=_dt(10, 10),
                        modified_at_fs=_dt(10, 15),
                        discovered_at=_dt(9, 50),
                        last_seen_at=_dt(10, 15),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(10, 15),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Covers\Cover.png",
                        parent_path=r"D:\Library\Covers",
                        name="Cover.png",
                        stem="Cover",
                        extension="png",
                        file_type="image",
                        mime_type=None,
                        size_bytes=900,
                        created_at_fs=_dt(10),
                        modified_at_fs=_dt(10, 30),
                        discovered_at=_dt(10, 35),
                        last_seen_at=_dt(10, 30),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(10, 30),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Docs\Notes.docx",
                        parent_path=r"D:\Library\Docs",
                        name="Notes.docx",
                        stem="Notes",
                        extension="docx",
                        file_type="document",
                        mime_type=None,
                        size_bytes=300,
                        created_at_fs=_dt(10),
                        modified_at_fs=_dt(10, 30),
                        discovered_at=_dt(10, 35),
                        last_seen_at=_dt(10, 30),
                        is_deleted=False,
                        checksum_hint=None,
                        updated_at=_dt(10, 30),
                    ),
                    File(
                        source_id=source.id,
                        path=r"D:\Library\Books\deleted-book.pdf",
                        parent_path=r"D:\Library\Books",
                        name="deleted-book.pdf",
                        stem="deleted-book",
                        extension="pdf",
                        file_type="document",
                        mime_type=None,
                        size_bytes=80,
                        created_at_fs=_dt(8, 45),
                        modified_at_fs=_dt(9),
                        discovered_at=_dt(9),
                        last_seen_at=_dt(9),
                        is_deleted=True,
                        checksum_hint=None,
                        updated_at=_dt(14),
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
