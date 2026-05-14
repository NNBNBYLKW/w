"""Pure path safety helpers for managed library root creation — no DB access."""

import os
from pathlib import Path
from typing import Protocol


class SettingsLike(Protocol):
    base_dir: Path
    data_dir: Path


_DANGEROUS_DIR_NAMES = {"node_modules", ".git", "__pycache__", ".venv", "venv"}


def _is_drive_root(path: Path) -> bool:
    resolved = path.resolve()
    return resolved == resolved.parent


def _parts_contain_dangerous_name(path: Path) -> bool:
    resolved = path.resolve()
    return bool(_DANGEROUS_DIR_NAMES & set(resolved.parts))


def _blocked_system_roots() -> list[Path]:
    candidates: list[str] = []
    for key in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
        value = os.environ.get(key)
        if value:
            candidates.append(value)
    return [Path(c).resolve() for c in candidates if Path(c).exists()]


def validate_managed_library_root_path(resolved: Path, settings: SettingsLike | None = None) -> None:
    """Raise ValueError if the path is a protected system, application, or internal directory."""

    if _is_drive_root(resolved):
        raise ValueError("Managed library root cannot be a drive root.")

    for blocked in _blocked_system_roots():
        try:
            resolved.relative_to(blocked)
            raise ValueError("Managed library root cannot be a system or application directory.")
        except ValueError as exc:
            if "Managed library root" in str(exc):
                raise
            continue

    if _parts_contain_dangerous_name(resolved):
        raise ValueError("Managed library root cannot contain a repository or build directory (node_modules, .git, __pycache__, .venv).")

    if settings is not None:
        for internal in (settings.base_dir, settings.data_dir):
            try:
                resolved.relative_to(internal.resolve())
                raise ValueError("Managed library root cannot be the application's own internal directory.")
            except ValueError as exc:
                if "Managed library root" in str(exc):
                    raise
                continue
