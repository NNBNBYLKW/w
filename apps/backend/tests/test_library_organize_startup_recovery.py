import json
import unittest
from datetime import UTC, datetime

from sqlalchemy import select, text

from app.db.models.library_root import LibraryRoot
from app.db.models.organize import OrganizeAction, OrganizeActionLog, OrganizePlan
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.repositories.library_organize.repository import LibraryOrganizeRepository


def _now() -> datetime:
    return datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC).replace(tzinfo=None)


class LibraryOrganizeStartupRecoveryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()

    def tearDown(self) -> None:
        self._reset_database()
        engine.dispose()

    # ── Recovery core behavior ──────────────────────────────────

    def test_executing_plan_marked_failed(self) -> None:
        with SessionLocal() as session:
            plan = OrganizePlan(
                title="Test executing plan",
                status="executing",
                plan_kind="organize_inbox",
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(plan)
            session.commit()
            plan_id = plan.id

        repo = LibraryOrganizeRepository()
        with SessionLocal() as session:
            count = repo.mark_stale_executing_plans_failed(session, now=_now())
            session.commit()

        self.assertEqual(1, count)
        with SessionLocal() as session:
            recovered = session.get(OrganizePlan, plan_id)
            self.assertIsNotNone(recovered)
            self.assertEqual("failed", recovered.status)
            self.assertIsNotNone(recovered.execution_finished_at)
            summary = json.loads(recovered.execution_summary_json or "{}")
            self.assertEqual("interrupted", summary.get("error"))
            self.assertIn("Interrupted on application startup", summary.get("message", ""))

    def test_executing_actions_marked_failed(self) -> None:
        with SessionLocal() as session:
            plan = OrganizePlan(
                title="Test plan with executing actions",
                status="executing",
                plan_kind="organize_inbox",
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(plan)
            session.flush()
            action = OrganizeAction(
                plan_id=plan.id,
                action_order=1,
                action_type="move",
                source_path="/tmp/a",
                target_path="/tmp/b",
                status="executing",
                conflict_status="clear",
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(action)
            session.commit()
            plan_id = plan.id

        repo = LibraryOrganizeRepository()
        with SessionLocal() as session:
            repo.mark_stale_executing_plans_failed(session, now=_now())
            session.commit()

        with SessionLocal() as session:
            actions = session.scalars(
                select(OrganizeAction).where(OrganizeAction.plan_id == plan_id)
            ).all()
            self.assertEqual(1, len(actions))
            self.assertEqual("failed", actions[0].status)
            self.assertIn("Interrupted on application startup", actions[0].error_message or "")

    def test_recovery_logs_entries(self) -> None:
        with SessionLocal() as session:
            plan = OrganizePlan(
                title="Test plan for log check",
                status="executing",
                plan_kind="organize_inbox",
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(plan)
            session.commit()
            plan_id = plan.id

        repo = LibraryOrganizeRepository()
        with SessionLocal() as session:
            repo.mark_stale_executing_plans_failed(session, now=_now())
            session.commit()

        with SessionLocal() as session:
            logs = session.scalars(
                select(OrganizeActionLog).where(
                    OrganizeActionLog.plan_id == plan_id,
                    OrganizeActionLog.event_type == "startup_recovery",
                )
            ).all()
            self.assertEqual(1, len(logs))
            self.assertIn("Interrupted on application startup", logs[0].message)

    # ── Unaffected statuses ─────────────────────────────────────

    def test_draft_plan_unaffected(self) -> None:
        self._assert_status_unaffected("draft")

    def test_ready_plan_unaffected(self) -> None:
        self._assert_status_unaffected("ready")

    def test_completed_plan_unaffected(self) -> None:
        self._assert_status_unaffected("completed")

    def test_failed_plan_unaffected(self) -> None:
        self._assert_status_unaffected("failed")

    def test_cancelled_plan_unaffected(self) -> None:
        self._assert_status_unaffected("cancelled")

    def _assert_status_unaffected(self, status: str) -> None:
        with SessionLocal() as session:
            plan = OrganizePlan(
                title=f"Test {status} plan",
                status=status,
                plan_kind="organize_inbox",
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(plan)
            session.commit()
            plan_id = plan.id

        repo = LibraryOrganizeRepository()
        with SessionLocal() as session:
            count = repo.mark_stale_executing_plans_failed(session, now=_now())
            session.commit()

        self.assertEqual(0, count, f"No executing plans, count should be 0 (had {status})")
        with SessionLocal() as session:
            unchanged = session.get(OrganizePlan, plan_id)
            self.assertEqual(status, unchanged.status, f"Status should remain {status}")

    # ── Multiple executing plans ────────────────────────────────

    def test_multiple_executing_plans_count(self) -> None:
        with SessionLocal() as session:
            for i in range(3):
                session.add(OrganizePlan(
                    title=f"Stale executing plan {i}",
                    status="executing",
                    plan_kind="organize_inbox",
                    created_at=_now(),
                    updated_at=_now(),
                ))
            session.commit()

        repo = LibraryOrganizeRepository()
        with SessionLocal() as session:
            count = repo.mark_stale_executing_plans_failed(session, now=_now())
            session.commit()

        self.assertEqual(3, count)

    # ── No file operations ──────────────────────────────────────

    def test_recovery_does_not_touch_filesystem(self) -> None:
        """Recovery only updates DB records — no file I/O."""
        with SessionLocal() as session:
            plan = OrganizePlan(
                title="Test plan",
                status="executing",
                plan_kind="organize_inbox",
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(plan)
            session.commit()

        repo = LibraryOrganizeRepository()
        with SessionLocal() as session:
            count = repo.mark_stale_executing_plans_failed(session, now=_now())
            session.commit()

        self.assertEqual(1, count)
        # No file operations happen — this test passes by not crashing

    # ── App startup integration ─────────────────────────────────

    def test_app_create_triggers_recovery(self) -> None:
        with SessionLocal() as session:
            plan = OrganizePlan(
                title="Test stale plan for app startup",
                status="executing",
                plan_kind="organize_inbox",
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(plan)
            session.commit()
            plan_id = plan.id

        # Importing create_app triggers recovery (module-level app = create_app())
        # Since app is already created at import time in the test process,
        # seed the plan, then call create_app explicitly.
        from app.main import create_app
        create_app()

        with SessionLocal() as session:
            recovered = session.get(OrganizePlan, plan_id)
            self.assertIsNotNone(recovered)
            self.assertEqual("failed", recovered.status)

    # ── Helpers ─────────────────────────────────────────────────

    def _reset_database(self) -> None:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM organize_action_logs"))
            conn.execute(text("DELETE FROM organize_actions"))
            conn.execute(text("DELETE FROM organize_plan_candidates"))
            conn.execute(text("DELETE FROM organize_suggestions"))
            conn.execute(text("DELETE FROM organize_candidates"))
            conn.execute(text("DELETE FROM organize_plans"))
