import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.services.thumbnails.service import ThumbnailService
from app.workers.thumbnails.pdf_generator import PdfThumbnailGenerationError
from scripts.diagnose_pdf_thumbnails import (
    _diagnose_pdf_row,
    _load_pdf_rows,
    _load_rows_for_args,
    _row_from_direct_path,
    classify_pdf_thumbnail_failure,
    parse_zone_id,
)


class PdfThumbnailDiagnosticsTestCase(unittest.TestCase):
    def test_classifies_pypdfium_missing(self) -> None:
        try:
            raise PdfThumbnailGenerationError("pypdfium2 is not available.") from ModuleNotFoundError(
                "No module named 'pypdfium2'"
            )
        except PdfThumbnailGenerationError as error:
            self.assertEqual("pypdfium_missing", classify_pdf_thumbnail_failure(error))

    def test_classifies_pdfium_data_format_error(self) -> None:
        try:
            raise PdfThumbnailGenerationError("PDF first page could not be rendered.") from RuntimeError(
                "Failed to load document (PDFium: Data format error)."
            )
        except PdfThumbnailGenerationError as error:
            self.assertEqual("empty_or_invalid_pdf", classify_pdf_thumbnail_failure(error))

    def test_classifies_permission_error(self) -> None:
        self.assertEqual("permission", classify_pdf_thumbnail_failure(PermissionError("Access is denied.")))

    def test_classifies_cache_write_failure(self) -> None:
        error = PdfThumbnailGenerationError("PDF thumbnail output file was not created.")
        self.assertEqual("cache_write_failed", classify_pdf_thumbnail_failure(error))

    def test_classifies_unknown_failure(self) -> None:
        error = PdfThumbnailGenerationError("PDF thumbnail could not be generated.")
        self.assertEqual("unknown_render_failure", classify_pdf_thumbnail_failure(error))

    def test_parse_zone_id_reads_zone_identifier_content(self) -> None:
        self.assertEqual("3", parse_zone_id("[ZoneTransfer]\nZoneId=3\nReferrerUrl=https://example.test\n"))

    def test_parse_zone_id_returns_none_when_missing(self) -> None:
        self.assertIsNone(parse_zone_id("[ZoneTransfer]\nHostUrl=https://example.test\n"))

    def test_load_rows_for_args_can_select_single_file_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "workbench.db"
            self._create_files_table(database_path)
            self._insert_pdf_row(database_path, file_id=2, name="selected.pdf", path=Path(temp_dir) / "selected.pdf")

            rows = _load_rows_for_args(
                database_path,
                file_id=2,
                direct_path=None,
                include_deleted=False,
                limit=None,
            )

        self.assertEqual(1, len(rows))
        self.assertEqual(2, rows[0]["id"])
        self.assertEqual("selected.pdf", rows[0]["name"])

    def test_row_from_direct_path_builds_single_file_diagnostic_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "manual.pdf"
            pdf_path.write_bytes(b"%PDF-1.7 fake")

            row = _row_from_direct_path(pdf_path)

        self.assertEqual(0, row["id"])
        self.assertEqual("manual.pdf", row["name"])
        self.assertEqual("pdf", row["extension"])
        self.assertEqual("document", row["file_type"])

    def test_diagnose_pdf_row_reports_missing_source_without_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            database_path = temp_path / "workbench.db"
            missing_pdf = temp_path / "missing.pdf"
            self._create_files_table(database_path)
            self._insert_pdf_row(database_path, file_id=1, name="missing.pdf", path=missing_pdf)

            row = _load_pdf_rows(database_path, include_deleted=False, limit=None)[0]
            result = _diagnose_pdf_row(
                row,
                service=ThumbnailService(),
                worker=_ExplodingPdfWorker(),
                temp_root=temp_path,
                use_real_cache=False,
            )

            self.assertEqual("failed", result.status)
            self.assertEqual("source_missing", result.reason)
            self.assertFalse(result.source_exists)

    def _insert_pdf_row(self, database_path: Path, *, file_id: int, name: str, path: Path) -> None:
        connection = sqlite3.connect(database_path)
        try:
            connection.execute(
                """
                INSERT INTO files (
                    id, name, path, extension, file_type, source_id, size_bytes,
                    modified_at_fs, discovered_at, is_deleted
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    name,
                    str(path),
                    "pdf",
                    "document",
                    1,
                    100,
                    "2026-01-01 00:00:00.000000",
                    "2026-01-01 00:00:00.000000",
                    0,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def _create_files_table(self, database_path: Path) -> None:
        connection = sqlite3.connect(database_path)
        try:
            connection.execute(
                """
                CREATE TABLE files (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    extension TEXT,
                    file_type TEXT NOT NULL,
                    source_id INTEGER,
                    size_bytes INTEGER,
                    modified_at_fs TEXT,
                    discovered_at TEXT,
                    is_deleted INTEGER DEFAULT 0
                )
                """
            )
            connection.commit()
        finally:
            connection.close()


class _ExplodingPdfWorker:
    def generate_thumbnail(self, *_args, **_kwargs) -> None:
        raise AssertionError("missing source rows should not call the PDF generator")


if __name__ == "__main__":
    unittest.main()
