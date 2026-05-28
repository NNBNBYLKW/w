import tempfile
import unittest
from pathlib import Path
from app.services.importing.service import _move_or_copy


class MoveImportTestCase(unittest.TestCase):
    def test_move_same_volume(self):
        d = tempfile.mkdtemp()
        try:
            src = Path(d) / "src.txt"; dst = Path(d) / "sub" / "dst.txt"
            (Path(d) / "sub").mkdir(exist_ok=True)
            src.write_text("test content")
            _move_or_copy(str(src), str(dst))
            self.assertFalse(src.exists())
            self.assertEqual("test content", dst.read_text())
        finally:
            import shutil; shutil.rmtree(d, ignore_errors=True)

    def test_import_preserves_content(self):
        d = tempfile.mkdtemp()
        try:
            src = Path(d) / "original.txt"; dst = Path(d) / "target" / "copied.txt"
            Path(d, "target").mkdir(exist_ok=True)
            src.write_text("hello world content")
            _move_or_copy(str(src), str(dst))
            self.assertEqual("hello world content", Path(dst).read_text())
        finally:
            import shutil; shutil.rmtree(d, ignore_errors=True)

    def test_nonexistent_source_raises(self):
        with self.assertRaises(FileNotFoundError):
            _move_or_copy("/nonexistent/src.txt", "/tmp/dst.txt")
