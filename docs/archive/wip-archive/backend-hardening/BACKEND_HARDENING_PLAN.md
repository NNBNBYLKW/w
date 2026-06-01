# Backend Hardening Plan

> Date: 2026-05-14 | Status: Planning Only — no code changes

---

## 1. Scope

Planning report only. No backend code changes. No API, schema, route, database, or business logic changes.

Based on:
- `docs/_wip/code-review/WORKBENCH_CODE_REVIEW.md` (F04, F08, F11, F12, F13, F14)
- `docs/_wip/architecture-review/WORKBENCH_COHESION_COUPLING_REVIEW.md`
- Direct code inspection of `organize.py`, `library_roots.py`, `main.py`, and related files.

---

## 2. Current Backend Safety Baseline

The backend already has meaningful safety boundaries:

| Boundary | Mechanism | Location |
|----------|-----------|----------|
| Path containment | `_is_path_within()` — `os.path.commonpath` + `os.path.normcase` | `organize.py:2067`, `object_scanner.py:353` |
| Managed root resolution | `_resolve_root_for_mkdir_or_asset()` — checks plan target root, then source roots | `organize.py:1213-1226` |
| Preflight blocking | `_preflight_action()` — validates mkdir, move, rename, backup, write_yaml before execution | `organize.py:832-951` |
| Asset YAML safety | Creates new asset.yaml only (never overwrites existing); backup via `shutil.copy2` | `organize.py:976-985`, `organize.py:992` |
| Execution guard | `ORGANIZE_EXECUTION_LOCK` — `BoundedSemaphore(1)` prevents concurrent plan execution | `organize.py:144` |
| Rollback safety | Draft only; requires user review and explicit execute | `organize.py:1496` |
| Suggestions safety | Rule-based, local, no file writes, no AI/cloud | `organize.py:168-189` |
| Template rendering guard | Blocks absolute paths, `..` traversal, drive letters, UNC paths in rendered output | `organize.py:1996-2004` |
| Tool run recovery | `mark_stale_runs_failed()` on startup (but only for `video_merge` tool runs) | `main.py:24` |
| Root overlap check | `_check_overlap()` validates new root doesn't overlap existing enabled roots | `library_roots.py:35-56` |

---

## 3. Risk Items

### H1 — Managed Root System Path Exclusion

**Current risk**: Any path that exists and is absolute can be registered as a managed library root. No protection prevents registering `C:\Windows`, `C:\Windows\System32`, `C:\Program Files`, the repo directory, or the backend data directory.

**Affected files**:
- `apps/backend/app/api/routes/library_roots.py` — `_resolve_path()` (lines 26-32), creation endpoint (lines 65-83)
- `apps/backend/app/schemas/library_root.py` — `CreateLibraryRootRequest` (no path validation)
- `apps/backend/app/repositories/library_roots/repository.py` — `get_by_path()` uses exact string match, no resolution

**Proposed validation rules** (add to `_resolve_path` or a new `_validate_root_path_safety`):

1. **System directory blocklist** — reject paths whose resolved (real) path is under any of:
   - `C:\Windows` (and `%WINDIR%`)
   - `C:\Program Files`, `C:\Program Files (x86)`
   - Known Windows system locations: `System32`, `SysWOW64`, `WinSxS`, `$Recycle.Bin`
   - Platform-appropriate: use `os.environ.get("SystemRoot")`, `os.environ.get("ProgramFiles")`

2. **Self-protection** — reject paths that resolve to or contain:
   - The backend's `base_dir` (repo root)
   - The backend's `data_dir` (where `workbench.db` lives)
   - These are read from `settings.base_dir` / `settings.data_dir`

3. **Path normalization gap** — use `Path.resolve()` for the blocklist comparison, matching the existing `_resolve_path` behavior (which already calls `.resolve()`).

4. **Error message** — return HTTP 400 with a descriptive message: `"This directory cannot be registered as a library root because it is a protected system location."` or `"...it contains the Workbench data directory."`

**False positive risk**: Very low. None of the blocked paths are legitimate user data directories. Users store media/books/games/software in `Downloads`, `Documents`, `Videos`, or custom drives — none of which would be blocked.

**Tests to add**:
- `test_create_root_rejects_system32`
- `test_create_root_rejects_windows_dir`
- `test_create_root_rejects_program_files`
- `test_create_root_rejects_backend_data_dir`
- `test_create_root_accepts_user_data_dir` (e.g., `C:\Users\...\Documents`)

**Implementation priority**: P1 — low effort, high safety impact, no behavioral change for legitimate users.

---

### H2 — Stale Executing Plan Startup Recovery

**Current risk**: If the backend process crashes during plan execution, plans stuck in `"executing"` status remain that way forever. No startup code detects or repairs this. The `ORGANIZE_EXECUTION_LOCK` (in-memory `BoundedSemaphore`) dies with the process, so a new process could start executing a different plan while a stale `"executing"` plan still has partially-applied filesystem changes. Actions are committed one-by-one during execution (line ~703-759), so mid-crash state can include a mix of `"succeeded"`, `"ready"`, and `"executing"` action statuses.

**Affected files**:
- `apps/backend/app/main.py` — `create_app()` (lines 21-56): only recovers `ToolRun`, not `OrganizePlan`
- `apps/backend/app/services/library/organize.py` — `execute_plan()` (line 564): sets `plan.status = "executing"`; `_execute_plan_worker()` (lines 682-817): transitions to completed/failed/errors
- `apps/backend/app/repositories/library_organize/repository.py` — needs a `mark_stale_plans_interrupted()` method

**Proposed startup behavior**:

1. Add a new repository method: `mark_stale_executing_plans_interrupted(session)` — bulk UPDATE on `organize_plans` where `status = "executing"`:
   - Set status to `"failed"`
   - Set `execution_summary_json` to `{"error": "interrupted", "message": "Execution was interrupted because the backend process restarted."}`
   - Set `execution_finished_at` to current UTC time
   - Also update any `OrganizeAction` records with `status = "executing"` to `status = "failed"` with log message `"interrupted: backend restart"`

2. Call this in `main.py`'s `create_app()`, after `initialize_database()`, alongside the existing `tools_service.mark_stale_runs_failed()`.

**State transition**:
```
Before (stale after crash):  plan.status = "executing"
After (startup recovery):    plan.status = "failed"
                             plan.execution_summary = {"error": "interrupted", ...}
                             plan.execution_finished_at = <now>
                             stale executing actions → status = "failed"
```

**Logging**: Log at WARNING level the count of interrupted plans and actions.

**What NOT to do**:
- Do NOT auto-resume execution
- Do NOT auto-move files
- Do NOT auto-rollback
- Do NOT delete any data

**Tests to add**:
- `test_startup_recovers_stale_executing_plan`
- `test_startup_does_not_touch_completed_plan`
- `test_startup_does_not_touch_draft_plan`
- `test_startup_recovers_stale_executing_actions`

**Implementation priority**: P1 — prevents permanent stuck state and potential concurrent execution.

---

### H3 — Rollback Plan Root Containment

**Current risk**: `generate_rollback_plan()` at line 1546 explicitly sets `target_library_root_id=None`. The rollback relies on generic source root scanning (`_resolve_root_for_mkdir_or_asset` falls through to checking all enabled sources when no plan target root exists). Additionally, `_check_rollback_preconditions()` (lines 1733-1746) only validates filesystem existence — it does not verify the rollback target path is within the same root the original plan targeted.

If the original source root was de-registered between plan execution and rollback generation, the rollback could bypass containment entirely.

**Affected files**:
- `apps/backend/app/services/library/organize.py` — `generate_rollback_plan()` (lines 1496-1572), `_check_rollback_preconditions()` (lines 1733-1746)

**Proposed fix**:

1. **Preserve `target_library_root_id`**: Copy the source plan's `target_library_root_id` to the rollback plan. If the source plan had one, the rollback should use the same root for containment checks. This ensures the rollback's file moves are bounded by the same managed root the original execution used.

2. **Add containment check to `_check_rollback_preconditions`**: After the existing filesystem existence checks, verify that the rollback target path is within the plan's `target_library_root_id` root (if set) or a registered source root. Use `_is_path_within()`.

3. **Rollback still stays draft**: No change to the draft-only nature of rollback. The user must still explicitly preflight and execute.

**What NOT to do**:
- Do NOT allow direct rollback execution
- Do NOT change the rollback action generation logic (source/target swap is correct)
- Do NOT add automatic rollback

**Tests to add**:
- `test_rollback_preserves_target_library_root_id`
- `test_rollback_precondition_rejects_path_outside_root`
- `test_rollback_precondition_accepts_path_within_root`

**Implementation priority**: P2 — medium risk (requires source root de-registration AND crash), low effort to fix.

---

### H4 — organize.py Decomposition Path

**Current state**: `organize.py` is 2,078 lines with 51 methods in `LibraryOrganizeService`, 12 module-level functions, and 2 standalone classes (`CandidateDraft`, `SuggestionDraft`, `RuleBasedOrganizeSuggestionProvider`). The file handles candidate scanning, suggestions, templates, plan generation, preflight, execution, reconcile, rollback, copy-failed, and asset YAML merge — all in one class.

**Decomposition strategy**: Extract the least-coupled pieces first. Keep existing API/schema/route/tests unchanged at each step.

#### Step 1: Extract module-level pure functions → `path_safety.py`

All 12 module-level functions (lines 1840-2078) are pure with no class dependencies. Move to a new `path_safety.py` module:

| Function | Purpose |
|----------|---------|
| `_is_path_within()` | Path containment check |
| `_path_key()` | Normalized path key |
| `_safe_title()` | Directory/file name sanitizer |
| `_strip_extension()` | Remove file extension |
| `_year_from_text()` | Extract year from text |
| `_serialize_diff_val()` / `_deserialize_diff_val()` | Value serialization |

Also moves `render_organize_template()` (lines 1947-2006) and its helpers `_strip_missing_var()` (2014-2044), `_extract_season()` (2009-2011).

**Tests**: Existing Phase 5 tests pass without changes. Module-level functions become independently unit-testable.

**Risk**: Very low — pure functions, no dependency injection changes.

#### Step 2: Extract template renderer → `template_renderer.py`

Move `render_organize_template()` + `_strip_missing_var()` + `_extract_season()` + `BUILTIN_TEMPLATES` constant (lines 52-142) into a dedicated `TemplateRenderer` class in `template_renderer.py`. The class exposes one public method: `render(template, candidate) -> dict`.

**Risk**: Low — templates are static data, no DB access needed.

#### Step 3: Extract asset YAML merge → `asset_yaml_merge.py`

Move `generate_asset_yaml_merge_draft()`, `_compute_field_diff()`, `_build_merged_yaml()`, `_render_asset_yaml()`, `_serialize_diff_val()`, `_deserialize_diff_val()` into an `AssetYamlMergeService` class. Constructor injects `LibraryOrganizeRepository`.

**Risk**: Medium — uses repository, but the logic is well-contained. Existing Phase 5D tests provide coverage.

#### Step 4: Extract suggestion provider → `suggestions.py`

Move `RuleBasedOrganizeSuggestionProvider` (lines 168-189) + its dependency functions (`_safe_title`, `_strip_extension`, `_year_from_text`, `_suggestion_tags`, `_suggested_template_key`, `_asset_yaml_draft`, `_confidence_score`) into `suggestions.py`.

**Risk**: Low — already a standalone class with one public method.

#### What NOT to extract yet:
- Execution engine (`_execute_plan_worker`, `_execute_action`) — tightly coupled to plan lifecycle
- Preflight (`_preflight_action`, `_run_preflight`) — depends on root resolution and conflict detection
- Plan generation (`generate_plan`) — weaves too many concerns
- Candidate scanning (`scan_candidates`) — largest method, best saved for later

#### Tests after each step:
```
cd apps/backend
python -m pytest tests/test_library_phase3_organize.py tests/test_library_phase5*.py -v
```

**Implementation priority**: P1 (Step 1), P2 (Steps 2-4). Step 1 is the highest-value/lowest-risk extraction.

---

### H5 — Move Atomicity / Operation Journal

**Current risk**: One `shutil.move()` call at `organize.py:968`. On the same filesystem, `shutil.move` delegates to `os.rename` (atomic). Across volumes, it falls back to `copy2` + `unlink` (non-atomic). If the process crashes during the copy phase of a cross-volume move:
- The target file may be incomplete or missing
- The source file may still exist (orphaned on the source volume)
- The action's status is set to `"failed"` in the outer `except Exception` handler
- But the partial state on disk is unrecoverable without manual inspection

**Affected files**:
- `apps/backend/app/services/library/organize.py` — `_execute_action()` (lines 953-1024, especially 968)

**Should this be fixed now?** Not urgently. Cross-volume library reorganization is likely uncommon (most users keep managed libraries on a single volume). The existing preflight check catches cross-volume issues indirectly (path containment via `_is_path_within`). The code already has error handling: the generic `except Exception` at line 741 catches move failures and marks the action as `"failed"`.

**Design options for future consideration:**

**Option A: Prefer same-volume moves**
Before the `shutil.move`, check if source and target are on the same volume using `os.stat(source).st_dev == os.stat(target).st_dev`. If they differ, either:
- Skip the action with status `"blocked"` and message `"cross-volume move not supported"`
- Or log a warning and proceed (accepting the risk)

**Option B: Operation journal**
Before executing any filesystem-mutating action, write a journal entry to the `organize_action_logs` table with `event_type = "move_started"` and include `source_path`, `target_path`. After successful move, write `event_type = "move_completed"`. On startup recovery, scan for `"move_started"` without matching `"move_completed"` and flag them.

However, a full journal is complex: it needs to be written BEFORE the move (so it survives a crash during the move), which adds latency. And recovery logic gets complicated quickly.

**Option C: `os.replace` for same-volume**
On same-volume (detected via `st_dev`), use `os.replace` instead of `shutil.move` for guaranteed atomicity. On cross-volume, fall back to `shutil.move` with explicit `OSError` handling.

**Recommendation**: Defer. The current behavior is safe (failed actions are logged and visible in the plan detail). If cross-volume move support becomes a user requirement, implement Option C (same-volume `os.replace` + cross-volume `shutil.move` with dedicated error handling). A full operation journal (Option B) is over-engineering for this risk level.

**Implementation priority**: P3 — defer until user demand or a concrete incident.

---

## 4. Recommended Implementation Order

| Order | Item | Priority | Effort | Risk of implementation | Risk if NOT implemented |
|-------|------|----------|--------|----------------------|------------------------|
| 1 | **H2 — Stale plan recovery** | P1 | Small (~30 lines) | Very low | Medium — stuck plans, potential concurrent execution |
| 2 | **H1 — System path exclusion** | P1 | Small (~40 lines) | Very low | Medium — data loss if system dirs registered |
| 3 | **H4-Step1 — Extract path helpers** | P1 | Small (move ~150 lines) | Very low | Low — code quality only |
| 4 | **H3 — Rollback root containment** | P2 | Small (~20 lines) | Low | Low — requires specific conditions |
| 5 | **H4-Step2 — Template renderer** | P2 | Medium (~180 lines) | Low | Low — code quality only |
| 6 | **H4-Step3 — Asset YAML merge** | P2 | Medium (~250 lines) | Medium | Low — code quality only |
| 7 | **H4-Step4 — Suggestion provider** | P2 | Small (~80 lines) | Low | Low — code quality only |
| 8 | **H5 — Move atomicity** | P3 | Medium (design only) | N/A (deferred) | Low — edge case |

---

## 5. Tests Required

### H1 — System Path Exclusion
```python
test_create_root_rejects_windows_system_dir()
test_create_root_rejects_program_files()
test_create_root_rejects_backend_repo_dir()
test_create_root_rejects_backend_data_dir()
test_create_root_accepts_user_documents_dir()
test_create_root_accepts_custom_drive_root()
```

### H2 — Stale Plan Recovery
```python
test_startup_marks_executing_plan_as_failed()
test_startup_marks_executing_actions_as_failed()
test_startup_does_not_touch_draft_plan()
test_startup_does_not_touch_completed_plan()
test_startup_does_not_touch_ready_plan()
test_startup_logs_interruption_count()
```

### H3 — Rollback Containment
```python
test_rollback_plan_preserves_target_library_root_id()
test_rollback_precondition_rejects_target_outside_root()
test_rollback_precondition_accepts_target_within_root()
test_rollback_still_draft_only()
```

### H4 — Decomposition
Existing Phase 5 tests (116 tests across 8 files) must continue to pass after each extraction step.

---

## 6. Explicitly NOT Doing

- No API contract changes
- No database schema changes (unless `mark_stale_executing_plans_interrupted` is considered a new query, which it isn't — it's a bulk UPDATE)
- No frontend changes
- No new features
- No automatic execution resumption
- No automatic rollback execution
- No direct rollback execution
- No plugin system
- No complex permission system
- No Phase 6
- No `shutil.move` rewrite (deferred)
