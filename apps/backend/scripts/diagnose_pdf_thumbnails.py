from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, Mapping

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.thumbnails.service import ThumbnailService
from app.services.diagnostics.runtime import get_runtime_diagnostics
from app.workers.thumbnails.pdf_generator import PdfThumbnailGeneratorWorker


@dataclass(frozen=True)
class PdfDiagnosticResult:
    id: int
    name: str
    path: str
    file_type: str
    source_exists: bool
    source_size: int | None
    cache_exists: bool
    cache_path: Path
    status: str
    reason: str | None = None
    exception_type: str | None = None
    exception_message: str | None = None
    output_path: Path | None = None
    zone_identifier_exists: bool = False
    zone_identifier_zone_id: str | None = None
    zone_identifier_content: str | None = None


def classify_pdf_thumbnail_failure(error: BaseException) -> str:
    chain = list(_iter_exception_chain(error))
    text = " | ".join(f"{type(item).__name__}: {item}" for item in chain).lower()

    if any(isinstance(item, (ImportError, ModuleNotFoundError)) for item in chain):
        return "pypdfium_missing"
    if any(isinstance(item, PermissionError) for item in chain) or "permission denied" in text or "access is denied" in text:
        return "permission"
    if "password" in text or "encrypted" in text or "security" in text:
        return "encrypted_or_password"
    if (
        "data format" in text
        or "failed to load document" in text
        or "no pages" in text
        or "invalid dimensions" in text
        or "could not be rendered" in text
    ):
        return "empty_or_invalid_pdf"
    if (
        "output file was not created" in text
        or "not a directory" in text
        or "no such file or directory" in text
        or "cannot find the path" in text
    ):
        return "cache_write_failed"
    return "unknown_render_failure"


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose PDF thumbnail generation for local Workbench data.")
    parser.add_argument("--db", type=Path, default=Path("data") / "workbench.db", help="SQLite database path.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of PDF rows to inspect.")
    parser.add_argument("--file-id", type=int, default=None, help="Diagnose a single PDF row by file id.")
    parser.add_argument("--path", type=Path, default=None, help="Diagnose a single PDF file path without reading the DB.")
    parser.add_argument("--failures", type=int, default=20, help="Number of failure samples to print.")
    parser.add_argument("--include-deleted", action="store_true", help="Include rows marked as deleted.")
    parser.add_argument("--use-real-cache", action="store_true", help="Write generated thumbnails to the real cache.")
    args = parser.parse_args()

    database_path = args.db.resolve()
    if not database_path.exists():
        if args.path is None:
            print(f"Database not found: {database_path}", file=sys.stderr)
            return 1

    rows = _load_rows_for_args(
        database_path,
        file_id=args.file_id,
        direct_path=args.path,
        include_deleted=args.include_deleted,
        limit=args.limit,
    )
    service = ThumbnailService()
    worker = PdfThumbnailGeneratorWorker()

    with tempfile.TemporaryDirectory(prefix="workbench-pdf-thumbnail-diagnostic-") as temp_dir:
        temp_root = Path(temp_dir)
        results = [
            _diagnose_pdf_row(row, service=service, worker=worker, temp_root=temp_root, use_real_cache=args.use_real_cache)
            for row in rows
        ]

    _print_summary(results, failure_limit=args.failures, database_path=database_path, used_real_cache=args.use_real_cache)
    return 0


def _load_rows_for_args(
    database_path: Path,
    *,
    file_id: int | None,
    direct_path: Path | None,
    include_deleted: bool,
    limit: int | None,
) -> list[dict[str, object]]:
    if direct_path is not None:
        return [_row_from_direct_path(direct_path)]
    if file_id is not None:
        row = _load_pdf_row_by_id(database_path, file_id=file_id, include_deleted=include_deleted)
        if row is None:
            print(f"No active PDF row found for file_id={file_id} in {database_path}", file=sys.stderr)
            return []
        return [row]
    return _load_pdf_rows(database_path, include_deleted=include_deleted, limit=limit)


def _load_pdf_row_by_id(database_path: Path, *, file_id: int, include_deleted: bool) -> dict[str, object] | None:
    where = "id = ? AND lower(extension) = 'pdf'"
    if not include_deleted:
        where += " AND COALESCE(is_deleted, 0) = 0"
    query = f"""
        SELECT id, name, path, extension, file_type, source_id, size_bytes, modified_at_fs, discovered_at, is_deleted
        FROM files
        WHERE {where}
    """
    connection = sqlite3.connect(database_path)
    try:
        connection.row_factory = sqlite3.Row
        row = connection.execute(query, (file_id,)).fetchone()
        return None if row is None else dict(row)
    finally:
        connection.close()


def _row_from_direct_path(path: Path) -> dict[str, object]:
    resolved_path = path.resolve()
    stat_result = resolved_path.stat() if resolved_path.exists() else None
    modified = datetime.fromtimestamp(stat_result.st_mtime) if stat_result is not None else datetime.fromtimestamp(0)
    return {
        "id": 0,
        "name": resolved_path.name,
        "path": str(resolved_path),
        "extension": resolved_path.suffix.lstrip("."),
        "file_type": "document",
        "source_id": None,
        "size_bytes": stat_result.st_size if stat_result is not None else None,
        "modified_at_fs": modified.isoformat(sep=" "),
        "discovered_at": modified.isoformat(sep=" "),
        "is_deleted": 0,
    }


def _load_pdf_rows(database_path: Path, *, include_deleted: bool, limit: int | None) -> list[dict[str, object]]:
    where = "lower(extension) = 'pdf'"
    if not include_deleted:
        where += " AND COALESCE(is_deleted, 0) = 0"
    limit_clause = "" if limit is None else " LIMIT ?"
    parameters: tuple[int, ...] = () if limit is None else (limit,)
    query = f"""
        SELECT id, name, path, extension, file_type, source_id, size_bytes, modified_at_fs, discovered_at, is_deleted
        FROM files
        WHERE {where}
        ORDER BY id ASC
        {limit_clause}
    """
    connection = sqlite3.connect(database_path)
    try:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query, parameters)]
    finally:
        connection.close()


def _diagnose_pdf_row(
    row: Mapping[str, object],
    *,
    service: ThumbnailService,
    worker: PdfThumbnailGeneratorWorker,
    temp_root: Path,
    use_real_cache: bool,
) -> PdfDiagnosticResult:
    file_like = _row_to_file_like(row)
    source_path = Path(str(row["path"]))
    source_exists = source_path.exists()
    source_size = source_path.stat().st_size if source_exists else None
    cache_path = service._build_pdf_thumbnail_path(file_like)
    cache_exists = cache_path.exists()
    zone_identifier = read_zone_identifier(source_path)

    if not source_exists:
        return PdfDiagnosticResult(
            id=int(row["id"]),
            name=str(row["name"]),
            path=str(row["path"]),
            file_type=str(row["file_type"]),
            source_exists=False,
            source_size=None,
            cache_exists=cache_exists,
            cache_path=cache_path,
            status="failed",
            reason="source_missing",
            zone_identifier_exists=zone_identifier.exists,
            zone_identifier_zone_id=zone_identifier.zone_id,
            zone_identifier_content=zone_identifier.content,
        )

    output_path = cache_path if use_real_cache else temp_root / cache_path.name
    try:
        worker.generate_thumbnail(source_path, output_path)
    except Exception as error:
        return PdfDiagnosticResult(
            id=int(row["id"]),
            name=str(row["name"]),
            path=str(row["path"]),
            file_type=str(row["file_type"]),
            source_exists=True,
            source_size=source_size,
            cache_exists=cache_exists,
            cache_path=cache_path,
            status="failed",
            reason=classify_pdf_thumbnail_failure(error),
            exception_type=type(error).__name__,
            exception_message=str(error),
            output_path=output_path,
            zone_identifier_exists=zone_identifier.exists,
            zone_identifier_zone_id=zone_identifier.zone_id,
            zone_identifier_content=zone_identifier.content,
        )

    return PdfDiagnosticResult(
        id=int(row["id"]),
        name=str(row["name"]),
        path=str(row["path"]),
        file_type=str(row["file_type"]),
        source_exists=True,
        source_size=source_size,
        cache_exists=cache_exists,
        cache_path=cache_path,
        status="success",
        output_path=output_path,
        zone_identifier_exists=zone_identifier.exists,
        zone_identifier_zone_id=zone_identifier.zone_id,
        zone_identifier_content=zone_identifier.content,
    )


def _row_to_file_like(row: Mapping[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        id=int(row["id"]),
        path=str(row["path"]),
        extension=row["extension"],
        file_type=row["file_type"],
        size_bytes=row["size_bytes"],
        modified_at_fs=_parse_datetime(row["modified_at_fs"]),
        discovered_at=_parse_datetime(row["discovered_at"]),
    )


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return datetime.fromtimestamp(0)


def _print_summary(results: list[PdfDiagnosticResult], *, failure_limit: int, database_path: Path, used_real_cache: bool) -> None:
    reason_counts = Counter(result.reason for result in results if result.reason is not None)
    failed = [result for result in results if result.status == "failed"]

    print("PDF thumbnail diagnostics")
    _print_runtime_block(database_path)
    print(f"database: {database_path}")
    print(f"writes real cache: {'yes' if used_real_cache else 'no'}")
    print(f"total pdf count: {len(results)}")
    print(f"existing source count: {sum(1 for result in results if result.source_exists)}")
    print(f"source missing count: {reason_counts.get('source_missing', 0)}")
    print(f"existing pdf cache count: {sum(1 for result in results if result.cache_exists)}")
    print(f"render success count: {sum(1 for result in results if result.status == 'success')}")
    print(f"render failed count: {len(failed)}")
    print("failure categories:")
    for reason, count in sorted(reason_counts.items()):
        print(f"  {reason}: {count}")

    print(f"failure samples (first {failure_limit}):")
    for result in failed[:failure_limit]:
        print(
            f"  id={result.id} name={result.name!r} reason={result.reason} "
            f"exception={result.exception_type or '-'} message={result.exception_message or '-'} path={result.path}"
        )
    if len(results) == 1:
        _print_single_file_details(results[0])


def _print_runtime_block(database_path: Path) -> None:
    runtime = get_runtime_diagnostics()
    print("runtime:")
    print(f"  sys.executable: {runtime['sys_executable']}")
    print(f"  cwd: {runtime['cwd']}")
    print(f"  settings.data_dir: {runtime['data_dir']}")
    print(f"  settings.database_path: {runtime['database_path']}")
    print(f"  settings.database_url: {runtime['database_url']}")
    print(f"  diagnostic db path: {database_path}")
    print(f"  pypdfium2 import: {runtime['pypdfium2_import']}")
    print(f"  pypdfium2 version: {runtime['pypdfium2_version']}")
    print(f"  pypdfium2 error: {runtime['pypdfium2_error']}")
    print(f"  packaged backend: {runtime['packaged_backend']}")


def _print_single_file_details(result: PdfDiagnosticResult) -> None:
    print("single file:")
    print(f"  id: {result.id}")
    print(f"  name: {result.name}")
    print(f"  path: {result.path}")
    print(f"  file_type: {result.file_type}")
    print(f"  source exists: {result.source_exists}")
    print(f"  source size: {result.source_size}")
    print(f"  cache path: {result.cache_path}")
    print(f"  cache exists: {result.cache_exists}")
    print(f"  output temp PNG path: {result.output_path}")
    print(f"  status: {result.status}")
    print(f"  reason: {result.reason}")
    print(f"  exception: {result.exception_type or '-'} {result.exception_message or ''}".rstrip())
    print(f"  Zone.Identifier exists: {result.zone_identifier_exists}")
    print(f"  ZoneId: {result.zone_identifier_zone_id}")
    if result.zone_identifier_content:
        print("  Zone.Identifier content:")
        for line in result.zone_identifier_content.splitlines():
            print(f"    {line}")


@dataclass(frozen=True)
class ZoneIdentifierInfo:
    exists: bool
    zone_id: str | None = None
    content: str | None = None


def read_zone_identifier(path: Path) -> ZoneIdentifierInfo:
    if sys.platform != "win32":
        return ZoneIdentifierInfo(exists=False)
    stream_path = f"{path}:Zone.Identifier"
    try:
        content = Path(stream_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ZoneIdentifierInfo(exists=False)
    return ZoneIdentifierInfo(exists=True, zone_id=parse_zone_id(content), content=content.strip())


def parse_zone_id(content: str) -> str | None:
    for line in content.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip().lower() == "zoneid":
            return value.strip()
    return None


def _iter_exception_chain(error: BaseException) -> Iterable[BaseException]:
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


if __name__ == "__main__":
    raise SystemExit(main())
