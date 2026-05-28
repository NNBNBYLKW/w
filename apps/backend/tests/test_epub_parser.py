import unittest
from app.workers.epub.parser import EpubParser


class EpubParserTestCase(unittest.TestCase):
    def test_parse_nonexistent_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            EpubParser().parse("/nonexistent/file.epub")
