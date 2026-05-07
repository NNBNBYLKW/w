import unittest
from unittest.mock import patch

from app.services.diagnostics import runtime


class RuntimeDiagnosticsTestCase(unittest.TestCase):
    def test_get_pypdfium_diagnostics_reports_success(self) -> None:
        diagnostics = runtime.get_pypdfium_diagnostics()

        self.assertIn(diagnostics["import"], {"ok", "failed"})
        if diagnostics["import"] == "ok":
            self.assertIsNotNone(diagnostics["version"])

    def test_get_pypdfium_diagnostics_reports_import_failure(self) -> None:
        original_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "pypdfium2":
                raise ModuleNotFoundError("No module named 'pypdfium2'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            diagnostics = runtime.get_pypdfium_diagnostics()

        self.assertEqual("failed", diagnostics["import"])
        self.assertIsNone(diagnostics["version"])
        self.assertIn("ModuleNotFoundError", diagnostics["error"])

    def test_get_runtime_diagnostics_contains_environment_fingerprint(self) -> None:
        diagnostics = runtime.get_runtime_diagnostics()

        self.assertIn("process_id", diagnostics)
        self.assertIn("process_start_time", diagnostics)
        self.assertIn("sys_executable", diagnostics)
        self.assertIn("cwd", diagnostics)
        self.assertIn("data_dir", diagnostics)
        self.assertIn("database_path", diagnostics)
        self.assertIn("database_url", diagnostics)
        self.assertIn("pypdfium2_import", diagnostics)


if __name__ == "__main__":
    unittest.main()
