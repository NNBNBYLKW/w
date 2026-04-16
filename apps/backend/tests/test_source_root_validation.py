import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.source import Source
from app.db.session.engine import engine
from app.db.session.session import SessionLocal
from app.main import app


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SourceRootValidationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()

    def test_create_rejects_duplicate_equivalent_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with TestClient(app) as client:
                first_response = client.post(
                    "/sources",
                    json={"path": str(root), "display_name": "Primary"},
                )
                self.assertEqual(201, first_response.status_code)

                duplicate_response = client.post(
                    "/sources",
                    json={"path": str(root / "."), "display_name": "Duplicate Equivalent"},
                )
                self.assertEqual(409, duplicate_response.status_code)
                self.assertEqual(
                    "SOURCE_ALREADY_EXISTS",
                    duplicate_response.json()["error"]["code"],
                )

        engine.dispose()

    def test_create_rejects_overlapping_source_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "nested"
            nested.mkdir()

            with TestClient(app) as client:
                first_response = client.post(
                    "/sources",
                    json={"path": str(root), "display_name": "Parent Root"},
                )
                self.assertEqual(201, first_response.status_code)

                overlap_response = client.post(
                    "/sources",
                    json={"path": str(nested), "display_name": "Nested Root"},
                )
                self.assertEqual(409, overlap_response.status_code)
                self.assertEqual(
                    "SOURCE_ROOT_OVERLAP",
                    overlap_response.json()["error"]["code"],
                )

        engine.dispose()

    def test_update_canonicalizes_existing_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_path = str(root / ".")

            with SessionLocal() as session:
                source = Source(
                    path=raw_path,
                    display_name="Needs Canonicalization",
                    is_enabled=True,
                    scan_mode="manual_plus_basic_incremental",
                    last_scan_at=None,
                    last_scan_status=None,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
                session.add(source)
                session.commit()
                source_id = source.id

            with TestClient(app) as client:
                update_response = client.patch(
                    f"/sources/{source_id}",
                    json={"display_name": "Canonicalized"},
                )
                self.assertEqual(200, update_response.status_code)
                self.assertEqual(str(root.resolve(strict=False)), update_response.json()["path"])

        engine.dispose()

    def test_update_rejects_legacy_overlapping_source_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "nested"
            nested.mkdir()

            with SessionLocal() as session:
                first = Source(
                    path=str(root),
                    display_name="Parent",
                    is_enabled=True,
                    scan_mode="manual_plus_basic_incremental",
                    last_scan_at=None,
                    last_scan_status=None,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
                second = Source(
                    path=str(nested),
                    display_name="Legacy Nested",
                    is_enabled=True,
                    scan_mode="manual_plus_basic_incremental",
                    last_scan_at=None,
                    last_scan_status=None,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
                session.add(first)
                session.add(second)
                session.commit()
                second_id = second.id

            with TestClient(app) as client:
                update_response = client.patch(
                    f"/sources/{second_id}",
                    json={"display_name": "Should Fail"},
                )
                self.assertEqual(409, update_response.status_code)
                self.assertEqual("SOURCE_ROOT_OVERLAP", update_response.json()["error"]["code"])

        engine.dispose()

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM tasks"))
            session.execute(text("DELETE FROM file_metadata"))
            session.execute(text("DELETE FROM file_tags"))
            session.execute(text("DELETE FROM file_user_meta"))
            session.execute(text("DELETE FROM files"))
            session.execute(text("DELETE FROM source_ignore_rules"))
            session.execute(text("DELETE FROM tags"))
            session.execute(text("DELETE FROM sources"))
            session.commit()


if __name__ == "__main__":
    unittest.main()
