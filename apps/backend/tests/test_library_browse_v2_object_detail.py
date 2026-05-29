"""Phase 8B tests: object detail API for library_object and import_object_candidate."""

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.importing import ImportObjectCandidate, ImportObjectMember, InboxItem, ImportBatch
from app.db.models.library_object import LibraryObject, LibraryObjectMember
from app.db.models.library_root import LibraryRoot
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class BrowseV2ObjectDetailTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
        self._ensure_managed_source()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.managed_dir = self.tmp / "managed"
        self.managed_dir.mkdir()
        self.client = TestClient(app)
        self._seed_root()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()
        self._reset_database()
        engine.dispose()

    def _reset_database(self) -> None:
        with SessionLocal() as session:
            for tbl in [
                "import_object_members", "import_object_candidates",
                "file_path_history", "operation_journal", "inbox_items", "import_batches",
                "organize_plan_candidates", "organize_suggestions", "organize_action_logs",
                "organize_actions", "organize_plans", "organize_candidates",
                "asset_metadata_cache", "library_object_members", "library_objects",
                "tool_runs", "tasks", "file_metadata", "file_tags", "file_user_meta",
                "collections", "files", "source_ignore_rules", "tags",
                "library_roots", "sources",
            ]:
                session.execute(text(f"DELETE FROM {tbl}"))
            session.commit()

    def _ensure_managed_source(self) -> None:
        with SessionLocal() as session:
            if session.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none() is None:
                session.add(Source(
                    path="__workbench_managed_import__", display_name="Managed Import",
                    is_enabled=True, scan_mode="manual", last_scan_status="not_applicable",
                    created_at=_dt(), updated_at=_dt(),
                ))
                session.commit()

    def _seed_root(self) -> int:
        with SessionLocal() as session:
            root = LibraryRoot(
                root_path=str(self.managed_dir.resolve()), display_name="Test Root",
                root_kind="managed", is_enabled=True, is_default=True,
                scan_policy="manual", created_at=_dt(), updated_at=_dt(),
            )
            session.add(root)
            session.commit()
            return root.id

    def _seed_file(self, path: str, file_kind: str = "image", storage_state: str = "inbox") -> int:
        with SessionLocal() as session:
            p = Path(path)
            f = File(
                source_id=1, path=str(p), parent_path=str(p.parent), name=p.name,
                stem=p.stem, extension=p.suffix.lstrip("."),
                file_type=file_kind, file_kind=file_kind, auto_placement="media",
                storage_state=storage_state, size_bytes=1000,
                discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt(),
            )
            session.add(f)
            session.commit()
            return f.id

    def _seed_import_object_candidate(self) -> tuple[int, int]:
        """Create an import candidate with 2 members. Returns (candidate_id, file_id)."""
        obj_dir = self.managed_dir / "00_Inbox" / "1" / "TestAlbum"
        obj_dir.mkdir(parents=True)
        f1_path = obj_dir / "img001.jpg"
        f2_path = obj_dir / "img002.jpg"
        f1_path.write_bytes(b"fake1")
        f2_path.write_bytes(b"fake2")
        fid1 = self._seed_file(str(f1_path), file_kind="image", storage_state="inbox")
        fid2 = self._seed_file(str(f2_path), file_kind="image", storage_state="inbox")
        with SessionLocal() as session:
            batch = ImportBatch(source_kind="file_collection", import_method="copy", status="completed",
                               created_at=_dt())
            session.add(batch)
            session.flush()
            ioc = ImportObjectCandidate(
                import_batch_id=batch.id, source_root_path=str(self.tmp / "source"),
                inbox_root_path=str(obj_dir), suggested_object_type="imgset",
                confidence="high", status="pending_review", member_count=2,
                reason_json="{}", created_at=_dt(), updated_at=_dt(),
            )
            session.add(ioc)
            session.flush()
            ii1 = InboxItem(import_batch_id=batch.id, file_id=fid1, source_path=str(self.tmp / "source" / "img001.jpg"),
                            inbox_path=str(f1_path), status="imported", created_at=_dt(), updated_at=_dt())
            session.add(ii1)
            session.flush()
            ii2 = InboxItem(import_batch_id=batch.id, file_id=fid2, source_path=str(self.tmp / "source" / "img002.jpg"),
                            inbox_path=str(f2_path), status="imported", created_at=_dt(), updated_at=_dt())
            session.add(ii2)
            session.flush()
            iom1 = ImportObjectMember(import_object_candidate_id=ioc.id, inbox_item_id=ii1.id,
                                     role="image_member", created_at=_dt())
            session.add(iom1)
            iom2 = ImportObjectMember(import_object_candidate_id=ioc.id, inbox_item_id=ii2.id,
                                     role="cover", created_at=_dt())
            session.add(iom2)
            session.commit()
            return ioc.id, fid1

    def _seed_library_object(self) -> tuple[int, list[int]]:
        obj_dir = self.managed_dir / "10_Movies_Anime" / "Movies" / "[MOVIE] Test Movie (2025)"
        obj_dir.mkdir(parents=True)
        f1 = obj_dir / "movie.mp4"
        f2 = obj_dir / "cover.jpg"
        f1.write_bytes(b"fake1")
        f2.write_bytes(b"fake2")
        fid1 = self._seed_file(str(f1), file_kind="video", storage_state="managed")
        fid2 = self._seed_file(str(f2), file_kind="image", storage_state="managed")
        with SessionLocal() as session:
            lo = LibraryObject(
                root_path=str(obj_dir), root_name=obj_dir.name, object_type="movie",
                type_prefix="MOVIE", title="Test Movie", filesystem_title="Test Movie",
                metadata_source="scan", needs_review=False, last_scanned_at=_dt(),
                created_at=_dt(), updated_at=_dt(),
            )
            session.add(lo)
            session.flush()
            lom1 = LibraryObjectMember(object_id=lo.id, file_id=fid1, member_role="main_video",
                                      relative_path="movie.mp4", absolute_path=str(f1),
                                      created_at=_dt())
            session.add(lom1)
            lom2 = LibraryObjectMember(object_id=lo.id, file_id=fid2, member_role="cover",
                                      relative_path="cover.jpg", absolute_path=str(f2),
                                      created_at=_dt())
            session.add(lom2)
            session.commit()
            return lo.id, [fid1, fid2]

    # ── Tests ─────────────────────────────────────────

    def test_object_detail_for_import_object_candidate(self):
        ioc_id, fid = self._seed_import_object_candidate()
        resp = self.client.get("/library/browse/object-detail", params={
            "object_source": "import_object_candidate",
            "source_id": ioc_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["object_id"] == f"import_object_candidate:{ioc_id}"
        assert data["object_source"] == "import_object_candidate"
        assert data["member_count"] == 2
        assert data["members"][0]["role"] in ("image_member", "cover")
        assert data["status"] == "pending_review"

    def test_object_detail_for_library_object(self):
        lo_id, fids = self._seed_library_object()
        resp = self.client.get("/library/browse/object-detail", params={
            "object_source": "library_object",
            "source_id": lo_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["object_id"] == f"library_object:{lo_id}"
        assert data["object_source"] == "library_object"
        assert data["member_count"] == 2
        assert data["members"][0]["file_id"] is not None

    def test_object_detail_invalid_source_404(self):
        resp = self.client.get("/library/browse/object-detail", params={
            "object_source": "library_object",
            "source_id": 99999,
        })
        assert resp.status_code == 404

    def test_object_detail_member_metadata(self):
        ioc_id, fid = self._seed_import_object_candidate()
        resp = self.client.get("/library/browse/object-detail", params={
            "object_source": "import_object_candidate",
            "source_id": ioc_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        for m in data["members"]:
            assert "role" in m
            assert "file_id" in m
            assert "name" in m

    def test_object_detail_is_read_only_no_db_write(self):
        ioc_id, fid = self._seed_import_object_candidate()
        with SessionLocal() as session:
            from app.db.models.importing import ImportObjectCandidate as IOC
            prev = session.query(IOC).filter(IOC.id == ioc_id).first()
            prev_status = prev.status
        resp = self.client.get("/library/browse/object-detail", params={
            "object_source": "import_object_candidate",
            "source_id": ioc_id,
        })
        assert resp.status_code == 200
        with SessionLocal() as session:
            from app.db.models.importing import ImportObjectCandidate as IOC
            curr = session.query(IOC).filter(IOC.id == ioc_id).first()
            assert curr.status == prev_status, "Object detail API must not mutate data"

    def test_object_detail_member_page_size_max(self):
        ioc_id, fid = self._seed_import_object_candidate()
        resp = self.client.get("/library/browse/object-detail", params={
            "object_source": "import_object_candidate",
            "source_id": ioc_id,
            "member_page_size": 100,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["member_page_size"] == 100

    def test_object_detail_notes_present(self):
        ioc_id, fid = self._seed_import_object_candidate()
        resp = self.client.get("/library/browse/object-detail", params={
            "object_source": "import_object_candidate",
            "source_id": ioc_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["notes"]) >= 1
        assert "object detail" in data["notes"][0].lower()
