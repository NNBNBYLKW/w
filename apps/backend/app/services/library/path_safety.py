"""Pure path utility functions — no DB, no HTTP, no class state, no filesystem writes."""

import os
from pathlib import Path


def is_path_within(path: Path, root: Path) -> bool:
    normalized_path = os.path.normcase(os.path.abspath(path))
    normalized_root = os.path.normcase(os.path.abspath(root))
    try:
        common = os.path.commonpath([normalized_path, normalized_root])
    except ValueError:
        return False
    return common == normalized_root


def path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def paths_overlap(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    return shorter == longer[: len(shorter)]


def parent_available(target: Path, planned_dirs: set[str]) -> bool:
    return target.parent.exists() or path_key(target.parent) in planned_dirs
