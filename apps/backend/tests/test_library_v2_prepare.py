import tempfile, unittest
from pathlib import Path
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db.models.file import File
from app.db.models.library_root import LibraryRoot
from app.db.models.organize import OrganizeAction, OrganizePlan
from app.db.models.source import Source
from app.db.session.session import SessionLocal
from app.main import app


def _dt():
    return datetime.now(UTC).replace(tzinfo=None)


class PreparePlanTestCase(unittest.TestCase):
    def setUp(self):
        with SessionLocal() as s:
            if s.query(Source).filter(Source.path == "__workbench_managed_import__").one_or_none() is None:
                s.add(Source(path="__workbench_managed_import__", display_name="MI",
                    is_enabled=True, scan_mode="manual", last_scan_status="na",
                    created_at=_dt(), updated_at=_dt()))
                s.commit()

    def _seed_root(self, path: Path) -> int:
        with SessionLocal() as s:
            root = LibraryRoot(root_path=str(path.resolve()), display_name=path.name,
                root_kind="managed", is_enabled=True, is_default=True,
                scan_policy="manual", created_at=_dt(), updated_at=_dt())
            s.add(root); s.commit()
            return root.id

    def _seed_file(self, path: str, root_id: int) -> int:
        with SessionLocal() as s:
            si = s.query(Source).filter(Source.path == "__workbench_managed_import__").first()
            f = File(source_id=si.id, path=path,
                parent_path=str(Path(path).parent), name=Path(path).name,
                file_type="other", file_kind="other", auto_placement="none",
                storage_state="managed", managed_root_id=root_id,
                discovered_at=_dt(), last_seen_at=_dt(), updated_at=_dt())
            s.add(f); s.commit()
            return f.id

    def _seed_draft_plan(self) -> int:
        with SessionLocal() as s:
            plan = OrganizePlan(title="Test Plan", status="draft",
                plan_kind="organize_inbox", created_at=_dt(), updated_at=_dt())
            s.add(plan); s.commit()
            return plan.id

    def test_prepare_passes_when_no_conflicts(self):
        plan_id = self._seed_draft_plan()
        with TestClient(app) as c:
            r = c.post(f"/library/organize/plans/{plan_id}/prepare")
            self.assertEqual(200, r.status_code)
            d = r.json()
            self.assertEqual(plan_id, d["plan_id"])
            self.assertTrue(d["can_execute"])
            self.assertEqual(0, d["blocked_count"])

    def test_prepare_returns_404_for_missing_plan(self):
        with TestClient(app) as c:
            r = c.post("/library/organize/plans/99999/prepare")
            self.assertEqual(404, r.status_code)

    def test_prepare_on_already_ready_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = Path(td) / "Lib"
            root_dir.mkdir()
            (root_dir / "target").mkdir()
            rid = self._seed_root(root_dir)
            src = str(root_dir / "a.txt")
            Path(src).write_text("hi")
            self._seed_file(src, rid)
            plan_id = self._seed_draft_plan()
            with SessionLocal() as s:
                s.add(OrganizeAction(plan_id=plan_id, action_order=1,
                    action_type="move", source_path=src,
                    target_path=str(root_dir / "target" / "a.txt"),
                    status="draft", conflict_status="unchecked",
                    created_at=_dt(), updated_at=_dt()))
                s.commit()
            with TestClient(app) as c:
                r1 = c.post(f"/library/organize/plans/{plan_id}/prepare")
                self.assertEqual(200, r1.status_code)
                self.assertTrue(r1.json()["can_execute"])
                r2 = c.post(f"/library/organize/plans/{plan_id}/prepare")
                self.assertEqual(200, r2.status_code)


if __name__ == "__main__":
    unittest.main()
