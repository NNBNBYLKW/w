from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from app.core.config.settings import settings


PROCESS_START_TIME = time.time()


def get_runtime_diagnostics() -> dict:
    pypdfium = get_pypdfium_diagnostics()
    return {
        "process_id": os.getpid(),
        "process_start_time": PROCESS_START_TIME,
        "sys_executable": sys.executable,
        "cwd": str(Path.cwd()),
        "data_dir": str(settings.data_dir),
        "database_path": str(settings.database_path),
        "database_url": settings.database_url,
        "pypdfium2_import": pypdfium["import"],
        "pypdfium2_version": pypdfium["version"],
        "pypdfium2_error": pypdfium["error"],
        "packaged_backend": _is_packaged_backend(),
    }


def get_pypdfium_diagnostics() -> dict:
    try:
        import pypdfium2 as pdfium
    except Exception as error:
        return {"import": "failed", "version": None, "error": f"{type(error).__name__}: {error}"}

    return {"import": "ok", "version": getattr(pdfium, "__version__", "unknown"), "error": None}


def _is_packaged_backend() -> bool:
    executable = Path(sys.executable)
    if getattr(sys, "frozen", False):
        return True
    return executable.name.lower().endswith(".exe") and "workbench-backend" in executable.name.lower()
