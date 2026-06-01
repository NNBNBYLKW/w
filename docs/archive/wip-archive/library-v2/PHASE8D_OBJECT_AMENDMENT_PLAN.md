# Phase 8D — Object Amendment Add / Remove Member Plan

> Status: Planning / Analysis Only  
> No code implementation  
> Target: Phase 8D scope, risks, and implementation breakdown

---

## 1. Purpose

Phase 8D supports member adjustment for existing formal `library_object` records:

- **Add**: move managed loose files into an existing object directory and create `library_object_member` rows.
- **Remove**: move member files out of the object directory into a managed loose area, and deactivate/remove the membership.

All amendment operations that move files or change formal object members MUST go through a plan-first pipeline:

```
amendment draft plan → mark ready → preflight → execute → membership mutation
```

Direct member editing, bypassing the plan, is prohibited. No delete. No source cleanup. No auto execute.

---

## 2. Current Baseline

### 2.1 Current Facts

| Area | Current fact | Implication for 8D |
|---|---|---|
| LibraryObject model | `id, object_type, type_prefix, root_path, title, metadata_source, needs_review` | Can reference existing object by `id` and `root_path` |
| LibraryObjectMember model | `id, object_id, file_id, member_role, relative_path, absolute_path, hidden_from_global, sort_index, extension, size_bytes` | No `status`/`active` column. `hidden_from_global` is a boolean defaulting to `True`. Could be repurposed as soft-deactivate, but naming is misleading. A schema addition may be needed. |
| OrganizePlan.plan_kind | Free `String` — no enum constraint | Can add `object_amendment`, `object_amendment_add_members`, `object_amendment_remove_members` without migration |
| OrganizeAction.payload_json | `Text` — currently stores `file_id`, `member_role`, `selected_relative_path`, `object_creation_plan: true` | Can store amendment metadata: `object_amendment_plan`, `amendment_action`, `object_id`, `member_id`, `file_id` |
| OrganizeAction.inbox_item_id / import_object_candidate_id | `Integer`, nullable | Not applicable for amendment of formal objects; can remain null |
| Managed compose finalization | See `organize.py:_finalize_managed_compose` | Reusable pattern for amendment finalization: create/update members, update files.path, write history/journal |
| Object detail | `GET /library/browse/object-detail` supports `library_object` source with paginated member list | Can reuse for member display; need to add amendment action endpoints |
| Browse v2 loose files | `GET /library/browse` excludes `library_object_members` from loose file cards | Remove member must make the file visible as loose again (un-hide) |
| Path history | `FilePathHistory(old_path, new_path, reason)` | Amendment moves must write history |
| Operation journal | `OperationJournal(operation_id, operation_type, entity_type, entity_id)` | Amendment finalization must write journal |
| Object scanner (SUPPORTED_OBJECT_TYPES) | `object_parser.py` — reads `[TYPE]` folder prefixes | No amendment-specific scanning needed in 8D |
| Recovery | Read-only diagnostics for missing/inconsistent files | 8D-E should verify: removed member no longer listed as object member in false positive scans |
| Frontend compose modal | Supports 3 modes: inbox, external, managed | Amendment needs a different modal/flow — not "create new object" but "add to existing object" |

### 2.2 Safe Assumptions

- Existing managed compose finalization pattern can be adapted for amendment finalization.
- `OrganizePlan.plan_kind` can be extended without migration.
- `OrganizeAction.payload_json` has enough capacity for amendment metadata.
- Browse v2 currently hides object members from loose files via `library_object_members.file_id` exclusion.
- Object detail already supports `library_object` member listing with roles/paths.

### 2.3 Open Questions

Listed in Section 17.

### 2.4 Deferred Future Work

- Permanent delete / trash / recycle bin.
- AI auto member suggestions.
- Batch amendment across multiple objects.
- Advanced role editing.
- Nested object/franchise/series model.
- Scraper / poster wall / AI.

---

## 3. Locked Decisions Proposed

| # | Decision | Rationale |
|---|---|---|
| 1 | 8D only processes existing formal `library_object` records | Import candidates and inbox objects are not formal — they go through the existing review→compose flow |
| 2 | All amendment creates an `OrganizePlan` — no direct mutation | Preserves plan-first safety gate (preflight → execute) |
| 3 | `plan_kind = "object_amendment"` for all amendment types | Single plan kind with `summary_json.amendment_type` to distinguish add/remove/mixed. Simpler than multiple plan_kind values. |
| 4 | `completed_with_errors` does not create partial membership changes | Same all-or-nothing policy as managed compose |
| 5 | Add member moves files into the object directory | Same semantics as managed compose move actions |
| 6 | Remove member moves files out to a managed loose area | See Section 5 for options — recommend Option B |
| 7 | Remove member: soft-deactivate, do not hard-delete membership row | Preserves audit trail. See Section 6 for schema implications. |
| 8 | First version: separate add-only and remove-only plans. Mixed deferred. | Simplifies API, validation, and finalization. Mixed can be added in 8D revisit. |

---

## 4. Product Flows

### 4.1 Add Members

```
Browse v2 / Object detail
→ select existing object
→ select managed loose files to add
→ create amendment plan (plan_kind=object_amendment, amendment_type=add_members)
→ mark ready
→ preflight
→ execute
→ move files into object root directory
→ create library_object_member rows
→ update files.path / name / parent_path
→ write file_path_history
→ write operation_journal
→ Browse v2: members hidden from loose files
→ Object detail: members visible
```

### 4.2 Remove Members

```
Object detail
→ select members to remove
→ create amendment plan (plan_kind=object_amendment, amendment_type=remove_members)
→ mark ready
→ preflight
→ execute
→ move files out of object directory to managed loose target
→ deactivate library_object_member rows
→ update files.path / name / parent_path
→ write file_path_history
→ write operation_journal
→ Browse v2: files appear as managed loose files
→ Object detail: members no longer listed
```

### 4.3 Mixed Amendment

**Recommendation: Defer to after add-only and remove-only are stable.**

Single-plan mixed amendment adds complexity: duplicate file checks across add/remove sets, potential path conflicts if a removed file's target collides with an added file's source, harder rollback. Safer to validate and execute separately.

---

## 5. Remove Member Policy Options

### Option A — Deactivate membership only, no file move

- **Pros**: Simple, no file risk
- **Cons**: File remains in object directory. Browse v2 might see non-member files in object folder. Confusing for users.
- **Verdict**: Not recommended for v1.

### Option B — Move removed member to managed loose area **(Recommended)**

- **Pros**: Semantically clear — object directory only contains active members. File becomes browse-able as managed loose.
- **Cons**: Need to define target loose directory. Requires path resolution.
- **Target directory proposal**: Use the same managed root as the object. Place removed files in `<managed_root>/_removed/<object_name>/<filename>` or simply `<managed_root>/<filename>`. For v1, recommend flat: `<managed_root>/<filename>` (same level as original loose files). Add `_removed/` subdirectory only if flat causes name collision issues.

### Option C — Move to object-local `_Removed` folder

- **Pros**: Close to original object context
- **Cons**: Still inside object folder tree — recovery and browse semantics are complex (object folder now has non-member files)
- **Verdict**: Not recommended for v1.

---

## 6. Data Model Decision

### Current `LibraryObjectMember` limitations

No `status`/`active`/`removed_at` field. `hidden_from_global` is a boolean defaulting to `True`, originally intended for global file listing.

### Recommendation: Add `member_status` column

```sql
ALTER TABLE library_object_members ADD COLUMN member_status TEXT NOT NULL DEFAULT 'active';
```

Values: `active`, `removed`.

**Pros**: Clear semantic. Browse v2 can filter `WHERE member_status = 'active'`. Object detail can show/hide removed members. Preserves audit trail.

**Cons**: Requires a migration. This is acceptable — Phase 8C already required no migration; Phase 8D is a new phase with higher risk and warrants schema refinement.

### Alternative: Repurpose `hidden_from_global`

Not recommended. The field name is misleading for amendment semantics. Adding a dedicated `member_status` column is cleaner and costs one `ALTER TABLE`.

### Deferred migrations (8D revisit)

- `library_object_members.removed_by_plan_id` — links removal to amendment plan
- `library_object_members.added_by_plan_id` — links addition to amendment plan
- `library_object_members.removed_at` — timestamp of removal

These can be deferred if the amendment plan's `summary_json` already traces which plan created/removed which member.

---

## 7. Amendment Plan Model

### OrganizePlan

```
plan_kind = "object_amendment"
status = "draft"
target_library_root_id = <managed root>
summary_json = {
  "plan_type": "object_amendment",
  "amendment_type": "add_members | remove_members",
  "object_id": 123,
  "object_root_path": "...",
  "object_type": "imgset",
  "planned_add_file_ids": [1, 2],
  "planned_add_members": [
    {"file_id": 1, "role": "image_member", "relative_path": "img001.jpg"}
  ],
  "planned_remove_member_ids": [10, 11],
  "planned_remove_members": [
    {"member_id": 10, "file_id": 456, "role": "image_member"}
  ],
  "finalize_policy": "all_or_nothing_object_amendment"
}
```

### OrganizeAction — Add member move

```
action_type = "move"
source_path = "<managed loose file path>"
target_path = "<object_root_path>/<filename>"
payload_json = {
  "object_amendment_plan": true,
  "amendment_action": "add_member",
  "object_id": 123,
  "file_id": 456,
  "member_role": "image_member",
  "member_relative_path": "img001.jpg"
}
```

### OrganizeAction — Remove member move

```
action_type = "move"
source_path = "<current member file path>"
target_path = "<managed loose target>/<filename>"
payload_json = {
  "object_amendment_plan": true,
  "amendment_action": "remove_member",
  "object_id": 123,
  "member_id": 789,
  "file_id": 456,
  "previous_member_role": "image_member"
}
```

---

## 8. API Draft

### Recommended: Single endpoint with amendment_type

`POST /library/objects/{object_id}/amendment-plans`

**Request (add only)**:
```json
{
  "add_file_ids": [1, 2],
  "amendment_type": "add_members",
  "target_library_root_id": 1
}
```

**Request (remove only)**:
```json
{
  "remove_member_ids": [10, 11],
  "amendment_type": "remove_members",
  "target_library_root_id": 1,
  "remove_target_policy": "managed_loose_area"
}
```

**Response**:
```json
{
  "plan_id": 123,
  "plan_kind": "object_amendment",
  "object_id": 55,
  "amendment_type": "add_members",
  "status": "draft",
  "add_count": 2,
  "remove_count": 0,
  "planned_actions": [...]
}
```

### Why NOT split endpoints

- Single endpoint with `amendment_type` keeps the API surface small.
- Validation and plan creation logic is similar for both types (validate object, validate files/members, create plan).
- If mixed amendment is added later, a single endpoint already supports it via the `add_file_ids` + `remove_member_ids` fields.

---

## 9. Backend Implementation Breakdown

### 8D-A — Amendment Draft Plan Backend

- `POST /library/objects/{object_id}/amendment-plans`
- Validate: object exists, files exist and are managed loose, members belong to object
- Generate draft `OrganizePlan(plan_kind="object_amendment")`
- Create mkdir + move actions
- No file movement. No member mutation.
- Tests: `test_library_v2_amendment_plan.py`

### 8D-B — Amendment Preflight

- Extend `_preflight_action()` for `object_amendment` plans
- Validate: source paths exist, target paths safe, files/members still eligible, no conflicts
- Reuse mark_ready / preflight endpoints
- Tests: `test_library_v2_amendment_preflight.py`

### 8D-C — Amendment Execute / Finalize

- Extend `_execute_plan_worker` for `object_amendment` plans
- After all moves succeed: create/deactivate members, update files.path, write history/journal
- `completed_with_errors` → no membership mutation
- Add `member_status` column migration
- Tests: `test_library_v2_amendment_execute.py`

### 8D-D — Frontend Amendment UI

- Object detail: "Add member" button → file picker → create amendment plan
- Member row: "Remove" button → confirmation → create amendment plan
- Reuse ComposeObjectModal patterns with amendment-specific warnings
- "创建修改计划" not "创建对象候选"
- Tests: manual smoke

### 8D-E — Recovery / Docs / Acceptance

- Recovery diagnostic: removed members not false-positive
- Docs update: API_REFERENCE, ARCHITECTURE, KNOWN_LIMITATIONS, MANUAL_ACCEPTANCE
- Tests: `test_library_v2_amendment_recovery.py`

---

## 10. Validation Rules

### Add member validation

- `object_id` exists and is a `library_object`
- `add_file_ids` non-empty
- All files exist and have `storage_state = "managed"`
- All files are loose (not in `library_object_members`, not in active `import_object_members`)
- All files under same `managed_root_id` (or at minimum, target is within object's managed root)
- Target object directory exists (from `library_objects.root_path`)
- No filename collision within target object directory (no-overwrite suffix if needed)

### Remove member validation

- `object_id` exists
- `remove_member_ids` non-empty
- All member IDs belong to this object
- All member files exist on disk
- All member files have `storage_state = "managed"`
- Remove target path resolves within valid managed root
- No filename collision at remove target

---

## 11. Safety Invariants

- No delete.
- No source cleanup.
- No direct member mutation before execute.
- No direct file move before execute.
- Preflight required before execute.
- Execute all-or-nothing for membership changes.
- `completed_with_errors` must not mutate membership.
- `file_path_history` required for every moved file.
- `operation_journal` required for amendment finalization.
- Object detail must not display inconsistent half-state.
- Browse v2 must not show active members as loose files.
- After remove, removed member file must appear as managed loose file (not hidden).

---

## 12. Test Plan

### 8D-A tests (draft plan)

- Creates add-member amendment plan from managed loose files
- Creates remove-member amendment plan from object members
- Rejects invalid object_id
- Rejects add file that is already member of same/different object
- Rejects add file with storage_state != managed
- Rejects remove member_id not belonging to object
- No file movement
- No membership mutation
- Validates member_role derivation

### 8D-B tests (preflight)

- Add-member preflight passes with valid plan
- Add-member preflight rejects missing source file
- Add-member preflight rejects file that became member after plan creation (stale)
- Add-member preflight rejects target conflict
- Remove-member preflight passes
- Remove-member preflight rejects stale member path
- Preflight never moves files
- Preflight never mutates members

### 8D-C tests (execute)

- Add members: moves files, creates member rows, updates paths, writes history/journal
- Remove members: moves files, deactivates member rows, updates paths, writes history/journal
- Browse v2 hides added files from loose, shows removed files as loose
- Object detail shows new members, hides removed members
- `completed_with_errors` does not create/deactivate any members
- Unrelated files not affected

### 8D-D tests (frontend)

- Object detail shows "Add member" action when managed loose files exist
- Member row shows "Remove" action
- Modal creates amendment plan (not execute)
- Success feedback: "Amendment plan created"
- No direct execute/delete buttons

### 8D-E tests (recovery)

- Recovery clean after successful amendment
- Recovery does not false-positive removed files
- Recovery detects missing moved member if applicable

---

## 13. Manual Acceptance Plan

1. **Add member smoke**: Object detail → Add member → select managed loose files → create plan → mark ready → preflight → execute → verify new members in object detail → verify files hidden from Browse v2 loose.
2. **Remove member smoke**: Object detail → Remove member → select members → create plan → mark ready → preflight → execute → verify members removed from object detail → verify files appear in Browse v2 loose.
3. **Failed preflight**: Create plan → corrupt source file path → preflight should reject.
4. **Stale plan**: Create plan → file becomes member of another object → preflight should reject.
5. **Recovery smoke**: Run recovery scan after successful amendment → no false positives.

---

## 14. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Existing object corruption | P0 | Plan-first only. Preflight validates object still exists. |
| Accidental member deletion | P0 | Soft-deactivate, never hard-delete. Audit trail in plan summary_json. |
| File moved out but member still active | P0 | All-or-nothing finalization. No partial mutation. |
| Member deactivated but file still in object dir | P1 | Option B removes file from object dir. |
| Duplicate filenames in object dir | P1 | No-overwrite suffix on add. |
| Object root stale (object deleted after plan creation) | P1 | Preflight checks object exists and root_path still valid. |
| Plan conflicts with another plan on same object | P2 | First version: no plan lock. Document as known limitation. |
| Recovery false positive after amendment | P2 | Recovery tests for post-amendment state. |
| Frontend implies immediate mutation | P1 | Amendment modal uses "create plan" language only. |
| User confusion between remove and delete | P1 | Remove modal explicitly states "file will be moved to loose area, not deleted". |

---

## 15. Out of Scope

- Permanent delete / trash / recycle bin.
- Source cleanup.
- AI auto member suggestions.
- Scraper / poster wall / AI.
- Batch amendment across multiple objects.
- Nested object / franchise / series model.
- Advanced role editing.
- Cover / primary file selection beyond minimal role assignment.
- External/inbox files added directly to existing object (must go through compose→execute first, THEN amendment).

---

## 16. Recommended Execution Breakdown

```
8D-A: Backend amendment draft plan      (backend only, no file ops)
8D-B: Backend amendment preflight       (extend existing preflight)
8D-C: Backend amendment execute/finalize + member_status migration
8D-D: Frontend amendment UI             (object detail actions)
8D-E: Recovery/docs/acceptance          (read-only diagnostics + docs)
```

**Implement sequentially. Do not batch 8D-A through 8D-D into one phase.**

---

## 17. Open Questions

| # | Question | Recommendation |
|---|---|---|
| 1 | Soft deactivate vs hard delete `library_object_member` on remove? | Soft deactivate via `member_status = 'removed'`. Requires migration for `member_status` column. |
| 2 | Remove target directory? | `<managed_root>/<filename>` flat. Add `_removed/` subdirectory only if collision rate proves high. |
| 3 | Allow mixed add+remove in v1? | No. Separate plans simplify validation and reduce risk. Mixed deferred. |
| 4 | Need plan locks to prevent concurrent plans on same object? | Deferred. Document as known limitation. Single-user app reduces risk. |
| 5 | Need `source_file_id` or action trace migration? | No. `payload_json` already stores `file_id` and `member_id`. |
| 6 | Role editing in 8D or later? | Later. First version: auto-derive role from file_kind (same as managed compose). |
| 7 | Object cover/primary update on member add/remove? | Deferred. Current object scan can re-derive. |
| 8 | Should removed member history show in object detail? | Yes, as a collapsed "removed members" section. |
| 9 | Add external/inbox to existing object? | No in 8D. These must go through compose→execute first. |
| 10 | Empty object after all members removed? | Object remains (empty). Document as valid state. Future: prune empty objects. |

---

## Validation

```
git status --short --untracked-files=all:
  ?? docs/_wip/library-v2/PHASE8D_OBJECT_AMENDMENT_PLAN.md
```

No code changes. No tests changed. No schema changed. No commit. No push.
