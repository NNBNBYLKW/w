# Backend Hardening Status Review

> Date: 2026-05-14 | Status: Review — no code changes

---

## 1. Current Baseline

| Metric | Before Hardening | After Hardening |
|--------|-----------------|-----------------|
| `organize.py` lines | 2,083 | 1,887 (−196) |
| Path safety functions duplicated | 2 copies of `_is_path_within`, 2 copies of overlap check | 1 shared `path_safety.py` |
| Template rendering | Inline in organize.py | `organize_template_renderer.py` |
| Stale executing plans on crash | Forever stuck | Recovered on startup |
| Unsafe library roots | Allowed | Blocked (system, app, build dirs) |
| Rollback containment | Relied on source scanning only | Source + library root scanning |

**Commits**: H1(63209d3) H2(63209d3) H3(4b41959) H4-Step1(0452681) H4-Step2(9cbd007)

---

## 2. Completed Hardening Items

| Item | Description | Commit | Tests |
|------|-------------|--------|-------|
| **H1** | Unsafe managed root exclusion | `63209d3` | +14 tests |
| **H2** | Stale executing plan startup recovery | `63209d3` | +11 tests |
| **H3** | Rollback plan root containment | `4b41959` | +6 tests |
| **H4-Step1** | Extract shared path safety helpers | `0452681` | 0 regressions |
| **H4-Step2** | Extract organize template renderer | `9cbd007` | 0 regressions |

**Total new tests**: 31 (14 H1 + 11 H2 + 6 H3)

---

## 3. organize.py Current Responsibility Map

### Already Extracted (6 modules)

| What | Where |
|------|-------|
| Path containment, path keys, overlap checks | `path_safety.py` |
| System path validation for library roots | `root_safety.py` |
| Template definitions, rendering, variable substitution | `organize_template_renderer.py` |
| String helpers (`_safe_title`, etc.) | `organize_template_renderer.py` |
| DB queries (candidates, plans, actions, logs) | `repository.py` |
| API routing, HTTP concerns | `library_organize.py` (routes) |

### Remaining in organize.py (1,887 lines, ~38 methods)

| Group | Methods | Lines (approx) | Risk |
|-------|---------|---------------|------|
| Candidate scanning + CRUD | `scan_candidates`, `list_candidates`, `get_candidate`, `ignore_candidate` | ~150 | Low — well-scoped |
| Suggestions | `generate_candidate_suggestions`, `list_candidate_suggestions`, `accept_suggestion`, `reject_suggestion` + `RuleBasedOrganizeSuggestionProvider` | ~110 | Low — small class |
| Plan CRUD + lifecycle | `list_plans`, `get_plan_detail`, `update_plan`, `update_action`, `mark_ready`, `cancel_plan`, `organize_stats` | ~140 | Low — thin wrappers |
| Plan generation | `generate_plan`, `_build_actions_for_plan`, `_target_dir` | ~130 | Medium — orchestration, but well-bounded |
| Preflight | `preflight_plan`, `_run_preflight`, `_preflight_action` | ~130 | Medium — path safety critical |
| Execution | `execute_plan`, `_execute_plan_worker`, `_execute_action` | ~220 | High — filesystem mutations, threading |
| Conflict detection | `_refresh_plan_conflicts`, `_refresh_action_conflict` | ~110 | Medium — many condition branches |
| Root resolution | `_source_root_for_path`, `_source_root_for_path_safe`, `_resolve_root_for_mkdir_or_asset` | ~55 | Medium — DB-coupled but critical |
| Copy failed actions | `copy_failed_actions_to_new_plan` | ~60 | Low — self-contained |
| Rollback | `generate_rollback_plan`, `_check_rollback_preconditions` | ~95 | Low — H3-hardened |
| Asset YAML merge | `generate_asset_yaml_merge_draft`, `_compute_field_diff`, `_build_merged_yaml` | ~180 | Medium — complex diff logic |
| Reconcile | `reconcile_plan`, `_reconcile_action` | ~140 | Low — read-only filesystem checks |
| DTO converters | `_plan_item`, `_action_item`, `_candidate_item`, `_suggestion_item`, `_log_item`, `_plan_title` | ~110 | Low — pure mapping |
| Candidate drafting | `_candidate_from_object`, `_candidate_from_file`, `_is_candidate_file` | ~80 | Low |
| Helpers | `_required_source`, `_required_target`, `_make_action`, `_log_event`, `_render_asset_yaml`, `_source_root_for_path_safe` | ~75 | Low — small utilities |

### Must Stay (this iteration)

- `_execute_plan_worker`, `_execute_action` — threading, filesystem writes, ORGANIZE_EXECUTION_LOCK. Cannot extract without a full execution engine redesign.
- `_preflight_action` — deeply coupled to root resolution, conflict detection, and plan state.
- `generate_plan` — orchestrates candidate validation, template lookup, action building, conflict refresh.
- `_resolve_root_for_mkdir_or_asset` — DB-coupled to two repositories.
- `reconcile_plan` — filesystem state checking, action status transitions.

---

## 4. Remaining Risks

| Risk | Severity | Current Mitigation |
|------|----------|-------------------|
| `organize.py` still 1,887 lines | Low-Medium | Split into 3 extracted modules; remaining code is well-organized by method group |
| `_execute_plan_worker` threading + filesystem | Medium | `ORGANIZE_EXECUTION_LOCK`, preflight gate, confirm gate |
| `shutil.move` cross-volume non-atomic | Low | Only move/rename with pre-existing checks; target-exists blocked |
| `_compute_field_diff` complex diff logic | Low | Well-tested (18 asset merge tests) |
| No operation journal | Low | Actions are committed one-by-one; failed actions are logged; H2 handles stale plans |

---

## 5. Continue H4 or Pause?

### Recommendation: **Pause H4 decomposition. Current state is sufficient.**

**Reasoning**:
- The highest-risk extraction (path safety, templates) is done.
- The remaining methods are either: (a) thin CRUD wrappers (low value to extract), (b) tightly coupled to the plan lifecycle (high risk to extract without behavioral changes), or (c) already well-isolated within the class (DTO converters, candidate drafting).
- Further extraction would require either passing many dependencies or creating service orchestrators — both add complexity without proportional safety benefit.

### If H4 were continued, lowest-risk next steps:

| Step | What | Risk | Value |
|------|------|------|-------|
| H4-Step3 | Extract `AssetYamlMergeService` | Medium | Medium — ~180 lines, well-tested, clear boundary |
| H4-Step4 | Extract `RuleBasedOrganizeSuggestionProvider` + helpers | Low | Low — already a standalone class, just move it |
| H4-Step5 | Extract DTO converters to `_response_mapping.py` | Low | Low — pure functions, no DB |
| H4-Step6 | Extract reconcile to `reconcile_service.py` | Medium | Medium — read-only, self-contained |
| H4-Step7 | Extract preflight (risky) | High | High — central to all safety guarantees |
| H4-Step8 | Extract execution (very risky) | Very High | High — threading, filesystem, lock |

---

## 6. H5 Move Atomicity Assessment

### Current state

- Single `shutil.move` call at `organize.py:907` (post-extraction)
- Same-volume moves are atomic (`os.rename`)
- Cross-volume moves fall back to copy+unlink (non-atomic)
- Preflight blocks if target already exists
- Generic `except Exception` catches move failures, marks action as `"failed"`

### Does this block Phase 6 planning? **No.**

Cross-volume library reorganization is an edge case. Most users keep managed libraries on a single volume. The existing safety net (preflight + failure logging + H2 stale plan recovery) is adequate for the current risk level.

### If fixed later, minimal design

- Check `os.stat(src).st_dev == os.stat(tgt).st_dev` before move
- Same-volume: use `os.replace` (atomic)
- Cross-volume: use `shutil.move` with explicit `OSError` handling and a clearer error message
- **Do NOT add an operation journal** — over-engineering for this risk level

---

## 7. Phase 6 Readiness

### Can Phase 6 planning start now? **Yes.**

All P1 hardening items are complete:
- System path exclusion ✅
- Stale plan recovery ✅
- Rollback containment ✅
- Path safety deduplication ✅
- Template renderer extraction ✅

### Before Phase 6 implementation, recommend:

1. **Add** `AssetYamlMergeService` extraction (H4-Step3) — low-risk, ~30 min
2. **Run** full backend test suite one more time
3. **Optionally** address H5 (move atomicity) — but can defer

### Can be deferred:

- H5 move atomicity (edge case, low risk)
- Full organize.py service split (diminishing returns)
- Operation journal (over-engineering)
- Backend performance optimization

---

## 8. Recommended Next Step

1. **Immediate**: Enter Phase 6 planning (no code changes)
2. **Before Phase 6 code**: Optionally do H4-Step3 (AssetYamlMergeService) — one low-risk extraction
3. **During Phase 6**: Keep organize.py as-is; extract further only if Phase 6 work touches a specific area
4. **Defer**: H5 (move atomicity), full organize.py split, operation journal

---

## 9. Explicitly Not Doing

- No further organize.py extraction (unless Phase 6 demands it)
- No operation journal
- No move atomicity fix
- No API/schema/migration changes
- No frontend changes
- No Phase 6 implementation yet
