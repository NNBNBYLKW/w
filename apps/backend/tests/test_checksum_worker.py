import hashlib
import tempfile
import unittest
from pathlib import Path
from app.workers.checksum.worker import ChecksumWorker


class ChecksumWorkerTestCase(unittest.TestCase):
    def test_compute_sha256_known_content(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"hello world")
            path = f.name
        try:
            expected = hashlib.sha256(b"hello world").hexdigest()
            self.assertEqual(expected, ChecksumWorker.compute_sha256(path))
        finally:
            Path(path).unlink()

    def test_compute_sha256_empty_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            expected = hashlib.sha256(b"").hexdigest()
            self.assertEqual(expected, ChecksumWorker.compute_sha256(path))
        finally:
            Path(path).unlink()

    def test_compute_sha256_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            ChecksumWorker.compute_sha256("/nonexistent/path/file.txt")
