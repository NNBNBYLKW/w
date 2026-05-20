"""Regression tests for Phase 8 audit P0/P1 stabilization fixes."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models.file import File
from app.db.models.library_object import LibraryObject, LibraryObjectMember
from app.db.models.library_root import LibraryRoot
from app.db.models.organize import OrganizeAction, OrganizePlan
from app.db.models.source import Source
from app.db.session.engine import engine, initialize_database
from app.db.session.session import SessionLocal
from app.main import app
from app.services.library.organize import organize_service


def _dt() -> datetime:
    return datetime(2026, 5, 15, 10, tzinfo=UTC).replace(tzinfo=None)


class Phase8AuditFixesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        initialize_database()
        self._reset_database()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.managed_dir = self.tmp / "managed"
        self.managed_dir.mkdir()
        self.client = TestClient(app)
        self.source_id = self._seed_source()
        self.root_id = self._seed_root()

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

    def _seed_source(self) -> int:
        with SessionLocal() as session:
            source = Source(
                path="__workbench_managed_import__",
                display_name="Managed Import",
                is_enabled=True,
                scan_mode="manual",
                last_scan_status="not_applicable",
                created_at=_dt(),
                updated_at=_dt(),
            )
            session.add(source)
            session.commit()
            return source.id

    def _seed_root(self) -> int:
        with SessionLocal() as session:
            root = LibraryRoot(
                root_path=str(self.managed_dir.resolve()),
                display_name="Test Root",
                root_kind="managed",
                is_enabled=True,
                is_default=True,
                scan_policy="manual",
                created_at=_dt(),
                updated_at=_dt(),
            )
            session.add(root)
            session.commit()
            return root.id

    def _seed_managed_file(self, name: str, *, file_kind: str = "image", parent: Path | None = None) -> int:
        parent = parent or self.managed_dir
        parent.mkdir(parents=True, exist_ok=True)
        path = parent / name
        path.write_bytes(b"data")
        with SessionLocal() as session:
            file = File(
                source_id=self.source_id,
                path=str(path),
                parent_path=str(parent),
                name=path.name,
                stem=path.stem,
                extension=path.suffix.lstrip("."),
                file_type=file_kind,
                file_kind=file_kind,
                auto_placement="media",
                storage_state="managed",
                managed_root_id=self.root_id,
                managed_at=_dt(),
                size_bytes=100,
                discovered_at=_dt(),
                last_seen_at=_dt(),
                updated_at=_dt(),
            )
            session.add(file)
            session.commit()
            return file.id

    def _seed_object(self, root_name: str, member_names: list[str], *, title: str | None = None) -> tuple[int, list[int], list[int]]:
        object_dir = self.managed_dir / "30_Images" / "Image_Sets" / root_name
        object_dir.mkdir(parents=True, exist_ok=True)
        member_ids: list[int] = []
        file_ids: list[int] = []
        with SessionLocal() as session:
            lo = LibraryObject(
                object_type="imgset",
                type_prefix="IMGSET",
                root_path=str(object_dir),
                root_name=root_name,
                title=title or root_name,
                filesystem_title=title or root_name,
                metadata_source="test",
                needs_review=False,
                last_scanned_at=_dt(),
                created_at=_dt(),
                updated_at=_dt(),
            )
            session.add(lo)
            session.flush()
            for index, name in enumerate(member_names):
                path = object_dir / name
                path.write_bytes(b"data")
                file = File(
                    source_id=self.source_id,
                    path=str(path),
                    parent_path=str(object_dir),
                    name=path.name,
                    stem=path.stem,
                    extension=path.suffix.lstrip("."),
                    file_type="image",
                    file_kind="image",
                    auto_placement="media",
                    storage_state="managed",
                    managed_root_id=self.root_id,
                    managed_at=_dt(),
                    size_bytes=100 + index,
                    discovered_at=_dt(),
                    last_seen_at=_dt(),
                    updated_at=_dt(),
                )
                session.add(file)
                session.flush()
                member = LibraryObjectMember(
                    object_id=lo.id,
                    file_id=file.id,
                    relative_path=name,
                    absolute_path=str(path),
                    member_role="image_member",
                    member_status="active",
                    created_at=_dt(),
                )
                session.add(member)
                session.flush()
                member_ids.append(member.id)
                file_ids.append(file.id)
            session.commit()
            return lo.id, member_ids, file_ids

    def _create_amendment(self, object_id: int, *, add_ids: list[int] | None = None, remove_ids: list[int] | None = None) -> int:
        response = self.client.post(
            f"/library/objects/{object_id}/amendment-plans",
            json={
                "add_file_ids": add_ids or [],
                "remove_member_ids": remove_ids or [],
                "target_library_root_id": self.root_id,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["plan_id"]

    def _mark_ready_and_preflight(self, plan_id: int) -> None:
        ready = self.client.post(f"/library/organize/plans/{plan_id}/mark-ready")
        assert ready.status_code == 200, ready.text
        preflight = self.client.post(f"/library/organize/plans/{plan_id}/preflight")
        assert preflight.status_code == 200, preflight.text
        assert preflight.json()["can_execute"], preflight.text

    def _execute_and_wait(self, plan_id: int) -> str:
        response = self.client.post(f"/library/organize/plans/{plan_id}/execute", json={"confirm": True})
        assert response.status_code == 200, response.text
        deadline = time.time() + 5
        while time.time() < deadline:
            with SessionLocal() as session:
                plan = session.query(OrganizePlan).filter(OrganizePlan.id == plan_id).first()
                if plan is not None and plan.status != "executing":
                    return plan.status
            time.sleep(0.1)
        self.fail(f"Plan {plan_id} did not finish execution.")

    def _cancel_move_action(self, plan_id: int, *, file_id: int | None = None, member_id: int | None = None) -> int:
        with SessionLocal() as session:
            actions = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id,
                OrganizeAction.action_type == "move",
            ).order_by(OrganizeAction.action_order.asc()).all()
            for action in actions:
                payload = json.loads(action.payload_json or "{}")
                if file_id is not None and payload.get("file_id") != file_id:
                    continue
                if member_id is not None and payload.get("member_id") != member_id:
                    continue
                action.status = "cancelled"
                action.updated_at = _dt()
                session.commit()
                return action.id
        self.fail("No matching move action found to cancel.")

    def _plan_summary(self, plan_id: int) -> dict:
        with SessionLocal() as session:
            plan = session.query(OrganizePlan).filter(OrganizePlan.id == plan_id).first()
            assert plan is not None
            return json.loads(plan.summary_json or "{}")

    def _browse(self, **params) -> dict:
        response = self.client.get("/library/browse", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    # P0: completed_with_errors must not mutate object membership

    def test_amendment_skipped_add_action_does_not_create_member(self):
        object_id, _, _ = self._seed_object("[IMGSET] SkipAdd", ["member.jpg"])
        add_id = self._seed_managed_file("skip_add.jpg")
        plan_id = self._create_amendment(object_id, add_ids=[add_id])
        self._cancel_move_action(plan_id, file_id=add_id)
        self._mark_ready_and_preflight(plan_id)
        status = self._execute_and_wait(plan_id)
        with SessionLocal() as session:
            action = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id,
                OrganizeAction.action_type == "move",
            ).first()
            members = session.query(LibraryObjectMember).filter(
                LibraryObjectMember.object_id == object_id,
                LibraryObjectMember.file_id == add_id,
            ).all()
            assert status == "completed_with_errors"
            assert action.status == "skipped"
            assert members == []

    def test_amendment_cancelled_add_action_does_not_create_member(self):
        object_id, _, _ = self._seed_object("[IMGSET] CancelAdd", ["member.jpg"])
        add_id = self._seed_managed_file("cancel_add.jpg")
        plan_id = self._create_amendment(object_id, add_ids=[add_id])
        self._mark_ready_and_preflight(plan_id)
        self._cancel_move_action(plan_id, file_id=add_id)
        self._execute_and_wait(plan_id)
        with SessionLocal() as session:
            assert session.query(LibraryObjectMember).filter(
                LibraryObjectMember.object_id == object_id,
                LibraryObjectMember.file_id == add_id,
            ).count() == 0

    def test_amendment_skipped_remove_action_does_not_mark_removed(self):
        object_id, member_ids, _ = self._seed_object("[IMGSET] SkipRemove", ["member.jpg"])
        plan_id = self._create_amendment(object_id, remove_ids=[member_ids[0]])
        self._cancel_move_action(plan_id, member_id=member_ids[0])
        self._mark_ready_and_preflight(plan_id)
        self._execute_and_wait(plan_id)
        with SessionLocal() as session:
            member = session.query(LibraryObjectMember).filter(LibraryObjectMember.id == member_ids[0]).first()
            action = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id,
                OrganizeAction.action_type == "move",
            ).first()
            assert action.status == "skipped"
            assert member.member_status == "active"

    def test_amendment_cancelled_remove_action_does_not_mark_removed(self):
        object_id, member_ids, _ = self._seed_object("[IMGSET] CancelRemove", ["member.jpg"])
        plan_id = self._create_amendment(object_id, remove_ids=[member_ids[0]])
        self._mark_ready_and_preflight(plan_id)
        self._cancel_move_action(plan_id, member_id=member_ids[0])
        self._execute_and_wait(plan_id)
        with SessionLocal() as session:
            member = session.query(LibraryObjectMember).filter(LibraryObjectMember.id == member_ids[0]).first()
            assert member.member_status == "active"

    def test_completed_with_errors_does_not_set_finalized_true(self):
        object_id, _, _ = self._seed_object("[IMGSET] NoFinalize", ["member.jpg"])
        add_id = self._seed_managed_file("no_finalize.jpg")
        plan_id = self._create_amendment(object_id, add_ids=[add_id])
        self._cancel_move_action(plan_id, file_id=add_id)
        self._mark_ready_and_preflight(plan_id)
        status = self._execute_and_wait(plan_id)
        summary = self._plan_summary(plan_id)
        assert status == "completed_with_errors"
        assert summary.get("finalized") is not True

    def test_finalized_amendment_guard_prevents_duplicate_finalization(self):
        object_id, _, _ = self._seed_object("[IMGSET] FinalizedGuard", ["member.jpg"])
        add_id = self._seed_managed_file("finalized_guard.jpg")
        plan_id = self._create_amendment(object_id, add_ids=[add_id])
        self._mark_ready_and_preflight(plan_id)
        self._execute_and_wait(plan_id)
        with SessionLocal() as session:
            before = session.query(LibraryObjectMember).filter(
                LibraryObjectMember.object_id == object_id,
                LibraryObjectMember.file_id == add_id,
            ).count()
            organize_service._finalize_object_amendment(session, plan_id, 0)
            session.commit()
            after = session.query(LibraryObjectMember).filter(
                LibraryObjectMember.object_id == object_id,
                LibraryObjectMember.file_id == add_id,
            ).count()
            assert before == 1
            assert after == 1

    def test_partial_success_does_not_mutate_membership(self):
        object_id, _, _ = self._seed_object("[IMGSET] PartialAdd", ["member.jpg"])
        add_ok = self._seed_managed_file("partial_ok.jpg")
        add_skip = self._seed_managed_file("partial_skip.jpg")
        plan_id = self._create_amendment(object_id, add_ids=[add_ok, add_skip])
        self._cancel_move_action(plan_id, file_id=add_skip)
        self._mark_ready_and_preflight(plan_id)
        status = self._execute_and_wait(plan_id)
        with SessionLocal() as session:
            assert status == "completed_with_errors"
            assert session.query(LibraryObjectMember).filter(
                LibraryObjectMember.object_id == object_id,
                LibraryObjectMember.file_id.in_([add_ok, add_skip]),
            ).count() == 0

    # P1: remove-member target dir fresh flow

    def test_remove_member_plan_creates_or_includes_removed_target_dir(self):
        object_id, member_ids, _ = self._seed_object("[IMGSET] TargetPlan", ["member.jpg"])
        plan_id = self._create_amendment(object_id, remove_ids=[member_ids[0]])
        with SessionLocal() as session:
            actions = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).order_by(OrganizeAction.action_order.asc()).all()
            assert actions[0].action_type == "mkdir"
            assert "90_Loose" in actions[0].target_path
            assert "Removed_[IMGSET] TargetPlan" in actions[0].target_path

    def test_remove_member_fresh_flow_preflight_passes_with_target_dir(self):
        object_id, member_ids, _ = self._seed_object("[IMGSET] FreshPreflight", ["member.jpg"])
        plan_id = self._create_amendment(object_id, remove_ids=[member_ids[0]])
        assert not (self.managed_dir / "90_Loose" / "Removed_[IMGSET] FreshPreflight").exists()
        self._mark_ready_and_preflight(plan_id)

    def test_remove_member_fresh_flow_execute_succeeds(self):
        object_id, member_ids, file_ids = self._seed_object("[IMGSET] FreshExecute", ["member.jpg"])
        plan_id = self._create_amendment(object_id, remove_ids=[member_ids[0]])
        self._mark_ready_and_preflight(plan_id)
        status = self._execute_and_wait(plan_id)
        target_dir = self.managed_dir / "90_Loose" / "Removed_[IMGSET] FreshExecute"
        with SessionLocal() as session:
            member = session.query(LibraryObjectMember).filter(LibraryObjectMember.id == member_ids[0]).first()
            file = session.query(File).filter(File.id == file_ids[0]).first()
            assert status == "completed"
            assert target_dir.is_dir()
            assert member.member_status == "removed"
            assert Path(file.path).parent == target_dir

    def test_remove_target_dir_must_stay_inside_managed_root(self):
        object_id, member_ids, _ = self._seed_object("[IMGSET] InsideRoot", ["member.jpg"])
        plan_id = self._create_amendment(object_id, remove_ids=[member_ids[0]])
        with SessionLocal() as session:
            mkdir = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id,
                OrganizeAction.action_type == "mkdir",
            ).first()
            target = Path(mkdir.target_path).resolve()
            target.relative_to(self.managed_dir.resolve())

    # P1: Browse v2 combined pagination/count and member_count

    def test_browse_v2_combined_total_matches_object_plus_loose(self):
        self._seed_object("[IMGSET] ObjA", ["a.jpg"])
        self._seed_object("[IMGSET] ObjB", ["b.jpg"])
        for name in ["loose1.jpg", "loose2.jpg", "loose3.jpg", "loose4.jpg"]:
            self._seed_managed_file(name)
        data = self._browse(domain="media", storage_state="managed", page=1, page_size=10)
        assert data["total"] == 6
        assert data["summary"]["total_objects"] == 2
        assert data["summary"]["total_loose_files"] == 4

    def test_browse_v2_combined_pagination_no_duplicates(self):
        self._seed_object("[IMGSET] PageObjA", ["a.jpg"])
        self._seed_object("[IMGSET] PageObjB", ["b.jpg"])
        for name in ["page_loose1.jpg", "page_loose2.jpg", "page_loose3.jpg", "page_loose4.jpg"]:
            self._seed_managed_file(name)
        first = self._browse(domain="media", storage_state="managed", page=1, page_size=3)
        second = self._browse(domain="media", storage_state="managed", page=2, page_size=3)
        first_ids = {item.get("namespaced_id") or f"loose_file:{item['file_id']}" for item in first["items"]}
        second_ids = {item.get("namespaced_id") or f"loose_file:{item['file_id']}" for item in second["items"]}
        assert first_ids.isdisjoint(second_ids)
        assert len(first_ids | second_ids) == 6

    def test_browse_v2_combined_pagination_page_size_respected(self):
        self._seed_object("[IMGSET] SizeObj", ["a.jpg"])
        for name in ["size_loose1.jpg", "size_loose2.jpg", "size_loose3.jpg"]:
            self._seed_managed_file(name)
        data = self._browse(domain="media", storage_state="managed", page=1, page_size=2)
        assert data["total"] == 4
        assert len(data["items"]) == 2
        assert data["page_size"] == 2

    def test_browse_v2_card_kind_object_total_correct(self):
        self._seed_object("[IMGSET] OnlyObjA", ["a.jpg"])
        self._seed_object("[IMGSET] OnlyObjB", ["b.jpg"])
        self._seed_managed_file("not_object.jpg")
        data = self._browse(domain="media", storage_state="managed", card_kind="object")
        assert data["total"] == 2
        assert all(item["card_kind"] == "object" for item in data["items"])

    def test_browse_v2_card_kind_loose_total_correct(self):
        self._seed_object("[IMGSET] NoLooseObj", ["a.jpg"])
        self._seed_managed_file("loose_a.jpg")
        self._seed_managed_file("loose_b.jpg")
        data = self._browse(domain="media", storage_state="managed", card_kind="loose_file")
        assert data["total"] == 2
        assert all(item["card_kind"] == "loose_file" for item in data["items"])

    def test_formal_object_card_member_count_counts_active_members(self):
        self._seed_object("[IMGSET] CountActive", ["one.jpg", "two.jpg"])
        data = self._browse(domain="media", storage_state="managed", card_kind="object")
        card = next(item for item in data["items"] if item["display_title"] == "[IMGSET] CountActive")
        assert card["member_count"] == 2

    def test_formal_object_card_member_count_excludes_removed_members(self):
        object_id, member_ids, _ = self._seed_object("[IMGSET] CountRemoved", ["one.jpg", "two.jpg"])
        with SessionLocal() as session:
            member = session.query(LibraryObjectMember).filter(LibraryObjectMember.id == member_ids[1]).first()
            member.member_status = "removed"
            session.commit()
        data = self._browse(domain="media", storage_state="managed", card_kind="object")
        card = next(item for item in data["items"] if item["source_id"] == object_id)
        detail = self.client.get("/library/browse/object-detail", params={
            "object_source": "library_object",
            "source_id": object_id,
        }).json()
        assert card["member_count"] == 1
        assert detail["member_count"] == 1

    def test_member_count_updates_after_add_and_remove_amendment(self):
        object_id, member_ids, _ = self._seed_object("[IMGSET] CountAmend", ["one.jpg"])
        add_id = self._seed_managed_file("count_add.jpg")
        add_plan = self._create_amendment(object_id, add_ids=[add_id])
        self._mark_ready_and_preflight(add_plan)
        self._execute_and_wait(add_plan)
        data_after_add = self._browse(domain="media", storage_state="managed", card_kind="object")
        add_card = next(item for item in data_after_add["items"] if item["source_id"] == object_id)
        assert add_card["member_count"] == 2

        remove_plan = self._create_amendment(object_id, remove_ids=[member_ids[0]])
        self._mark_ready_and_preflight(remove_plan)
        self._execute_and_wait(remove_plan)
        data_after_remove = self._browse(domain="media", storage_state="managed", card_kind="object")
        remove_card = next(item for item in data_after_remove["items"] if item["source_id"] == object_id)
        assert remove_card["member_count"] == 1

    # Related guard: removed members are loose again, active members still blocked

    def test_removed_member_file_can_be_used_for_managed_compose(self):
        object_id, member_ids, file_ids = self._seed_object("[IMGSET] RemovedCompose", ["member.jpg"])
        remove_plan = self._create_amendment(object_id, remove_ids=[member_ids[0]])
        self._mark_ready_and_preflight(remove_plan)
        self._execute_and_wait(remove_plan)
        response = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": [file_ids[0]],
            "object_name": "Recomposed Object",
            "object_type": "imgset",
            "target_library_root_id": self.root_id,
        })
        detail = self.client.get("/library/browse/object-detail", params={
            "object_source": "library_object",
            "source_id": object_id,
        }).json()
        browse = self._browse(domain="media", storage_state="managed", card_kind="loose_file")
        loose_ids = {item["file_id"] for item in browse["items"]}
        assert response.status_code == 201, response.text
        assert detail["member_count"] == 0
        assert file_ids[0] in loose_ids

    def test_removed_member_file_can_be_used_for_add_member_amendment(self):
        object_a, member_ids, file_ids = self._seed_object("[IMGSET] RemovedAddA", ["member.jpg"])
        object_b, _, _ = self._seed_object("[IMGSET] RemovedAddB", ["other.jpg"])
        remove_plan = self._create_amendment(object_a, remove_ids=[member_ids[0]])
        self._mark_ready_and_preflight(remove_plan)
        self._execute_and_wait(remove_plan)
        response = self.client.post(f"/library/objects/{object_b}/amendment-plans", json={
            "add_file_ids": [file_ids[0]],
            "remove_member_ids": [],
            "target_library_root_id": self.root_id,
        })
        assert response.status_code == 201, response.text

    def test_active_member_file_still_rejected_as_loose(self):
        _, _, file_ids = self._seed_object("[IMGSET] ActiveReject", ["member.jpg"])
        response = self.client.post("/library/organize/plans/managed-compose", json={
            "file_ids": [file_ids[0]],
            "object_name": "Should Reject",
            "object_type": "imgset",
            "target_library_root_id": self.root_id,
        })
        assert response.status_code == 400
        assert "already a member" in response.text
