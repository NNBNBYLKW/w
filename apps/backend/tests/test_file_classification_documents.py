import sqlite3
import unittest

from app.core.classification import FILE_KIND_ARCHIVE, FILE_KIND_DOCUMENT, FILE_KIND_EBOOK, PLACEMENT_BOOKS, PLACEMENT_NONE, classify_file
from app.db.session.engine import _backfill_file_classification, _ensure_classification_columns


class FileClassificationDocumentsTestCase(unittest.TestCase):
    def test_document_extensions_map_to_documents_placement(self) -> None:
        cases = {
            "pdf": FILE_KIND_EBOOK,
            "epub": FILE_KIND_EBOOK,
            "docx": FILE_KIND_DOCUMENT,
            "xlsx": FILE_KIND_DOCUMENT,
            "csv": FILE_KIND_DOCUMENT,
            "pptx": FILE_KIND_DOCUMENT,
            "odt": FILE_KIND_DOCUMENT,
            "ods": FILE_KIND_DOCUMENT,
            "odp": FILE_KIND_DOCUMENT,
        }

        for extension, expected_kind in cases.items():
            with self.subTest(extension=extension):
                result = classify_file(extension, path=f"D:\\Docs\\sample.{extension}")
                self.assertEqual(expected_kind, result.file_kind)
                self.assertEqual(PLACEMENT_BOOKS, result.auto_placement)

    def test_archive_stays_files_only_by_default_classification(self) -> None:
        result = classify_file("zip", path=r"D:\Docs\ordinary.zip")

        self.assertEqual(FILE_KIND_ARCHIVE, result.file_kind)
        self.assertEqual(PLACEMENT_NONE, result.auto_placement)

    def test_backfill_classifies_documents_without_overwriting_manual_placement(self) -> None:
        connection = sqlite3.connect(":memory:")
        try:
            connection.executescript(
                """
                CREATE TABLE files (
                  id INTEGER PRIMARY KEY,
                  path TEXT NOT NULL,
                  extension TEXT NULL,
                  file_kind TEXT NOT NULL DEFAULT 'other',
                  auto_placement TEXT NOT NULL DEFAULT 'none'
                );
                CREATE TABLE file_user_meta (
                  file_id INTEGER PRIMARY KEY,
                  manual_placement TEXT NULL,
                  placement_updated_at DATETIME NULL
                );
                INSERT INTO files (id, path, extension, file_kind, auto_placement)
                VALUES
                  (1, 'D:\\Docs\\report.docx', 'docx', 'other', 'none'),
                  (2, 'D:\\Docs\\sheet.xlsx', 'xlsx', 'document', 'none'),
                  (3, 'D:\\Docs\\notes.csv', 'csv', 'document', 'none');
                INSERT INTO file_user_meta (file_id, manual_placement)
                VALUES (2, 'files_only');
                """
            )

            _ensure_classification_columns(connection)
            _backfill_file_classification(connection)

            rows = {
                row[0]: row
                for row in connection.execute(
                    """
                    SELECT f.id, f.file_kind, f.auto_placement, m.manual_placement
                    FROM files f
                    LEFT JOIN file_user_meta m ON m.file_id = f.id
                    ORDER BY f.id
                    """
                )
            }
        finally:
            connection.close()

        self.assertEqual((1, "document", "books", None), rows[1])
        self.assertEqual((2, "document", "books", "files_only"), rows[2])
        self.assertEqual((3, "document", "books", None), rows[3])


if __name__ == "__main__":
    unittest.main()
