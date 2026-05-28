import os
import shutil
import tempfile
import unittest
from pathlib import Path


class MoveImportTestCase(unittest.TestCase):
    def test_move_same_volume(self):
        d = tempfile.mkdtemp()
        try:
            src = Path(d) / "src.txt"
            dst = Path(d) / "sub" / "dst.txt"
            (Path(d) / "sub").mkdir(exist_ok=True)
            src.write_text("test content")
            shutil.move(str(src), str(dst))
            self.assertFalse(src.exists())
            self.assertTrue(dst.exists())
            self.assertEqual("test content", dst.read_text())
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_copy_preserves_content(self):
        d = tempfile.mkdtemp()
        try:
            src = Path(d) / "original.txt"
            dst = Path(d) / "target" / "copied.txt"
            Path(d, "target").mkdir(exist_ok=True)
            src.write_text("hello world content")
            shutil.copy2(str(src), str(dst))
            self.assertTrue(src.exists())
            self.assertTrue(dst.exists())
            self.assertEqual("hello world content", dst.read_text())
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_move_nonexistent_raises(self):
        with self.assertRaises(FileNotFoundError):
            shutil.move("/nonexistent/src.txt", "/tmp/dst.txt")
