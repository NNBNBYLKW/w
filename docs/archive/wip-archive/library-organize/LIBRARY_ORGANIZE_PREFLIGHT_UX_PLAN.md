# Library Organize Preflight UX Plan

> Date: 2026-05-14 | Type: Design Plan | Phase: Pre-implementation

## 1. Problem

After `mark-ready` and `preflight`, blocked/warning actions are scattered flat across the action list in `action_order`, making it difficult for users to:

- **Find** which files have problems
- **Understand** why they are blocked or warned
- **Decide** what to do next
- **Act** on the problems before execution

The current UX provides aggregate counts ("Blocked: N . Warning: M") but no structured navigation, no severity grouping, and no guided action path. The user is left reading a flat list of 50-100+ actions manually hunting for blocked/warning entries.

## 2. Current Behavior

### Current Preflight Data Available

The `POST /library/organize/plans/{id}/preflight` endpoint returns:

```json
{
  "plan_id": 42,
  "can_execute": false,
  "blocked_count": 2,
  "warning_count": 1,
  "actions": [ /* all actions with conflict_status */ ],
  "messages": [ /* aggregated messages */ ]
}
```

Each action carries:
| Field | Values | Meaning |
|-------|--------|---------|
| `conflict_status` | `"ok"`, `"warning"`, `"blocked"`, `"stale"`, `"unchecked"` | Preflight result |
| `conflict_message` | `str \| null` | Human-readable reason |
| `action_type` | `"mkdir"`, `"move"`, `"rename"`, `"write_asset_yaml"`, `"backup_asset_yaml"`, `"write_asset_yaml_update"`, `"update_metadata"` | What the action does |
| `source_path` | `str \| null` | Source file/dir |
| `target_path` | `str \| null` | Target file/dir |
| `status` | `"ready"`, `"cancelled"`, etc. | Lifecycle status |
| `action_order` | `int` | Position in plan |

### Current User Capabilities

| Scenario | Available? | How |
|----------|-----------|-----|
| See blocked count | Yes | Preflight notice bar |
| See warning count | Yes | Preflight notice bar |
| See individual blocked action details | Manual | Scroll the flat action list looking for `status-pill--danger` |
| See individual warning action details | Manual | Warning is styled same as `ok` (neutral pill), indistinguishable |
| Cancel plan | Yes | Cancel button (draft/ready only) |
| Re-run preflight | Yes | Preflight button |
| Execute when blocked | No | Execute disabled when `can_execute == false` |
| Execute when warnings only | Yes | Execute enabled; warnings don't block `can_execute` |
| Skip/Exclude actions | No | No per-action exclusion UX |
| Execute safe subset | No | No mechanism to exclude blocked actions |
| Regenerate plan from same candidates | No (by design) | Generate rejects non-pending candidates (candidate lifecycle fix) |
| Copy failed/blocked actions | Only post-execution | `copy_failed_actions` requires completed/completed_with_errors/failed |
| Rollback | Only post-execution | `generate_rollback_plan` requires completed/completed_with_errors/failed |
| See blocked actions grouped | No | Flat list, no grouping |
| See which files are blocked | Manual | Must scan `target_path` on each blocked action |

## 3. Current Data Available (Detailed)

### Action Ordering (Backend)

Actions come from the repository ordered by `action_order ASC, id ASC` — this is candidate-sequential: candidate 1's `mkdir → move → write_asset_yaml`, then candidate 2's, etc.

### Conflict Status Population

After `_run_preflight` completes, every action has `conflict_status` set. The statuses are:
- `"ok"` — action is safe to execute
- `"warning"` — action has a non-blocking issue (e.g., mkdir target already exists)
- `"blocked"` — action cannot proceed (e.g., target_exists, parent missing, outside root)
- `"stale"` — source path no longer exists on disk
- `"unchecked"` — not yet checked (should not appear after preflight runs)

### `can_execute` Logic

`can_execute = (blocked_count == 0)`. Warning actions do NOT block `can_execute`.

### Visual Display

In `PlanDetailPanel.tsx`:
- Preflight notice bar: `library-execution-notice--blocked` (danger border) when `!can_execute`, `--ok` (green) when `can_execute`
- Action rows: `status-pill--danger` for `"blocked"` or `"stale"`, `status-pill--neutral` for everything else (including `"warning"` and `"ok"`)
- No sorting: actions render in `action_order`

## 4. UX Goals

### Core Principles

1. **Problem actions must be instantly visible** — no scrolling or manual hunting
2. **Severity must be visually distinct** — blocked ≠ warning ≠ ok
3. **Every blocked/warning must have a clear reason** — `conflict_message` must be prominent
4. **The user must know what to do next** — guided actions per severity level
5. **Safety invariants must hold** — no silent overwrite, no skip-blocked without confirmation

### Non-goals

- No action-level skip/exclude mechanism (deferred to Phase 7)
- No execute-safe-subset (deferred)
- No automatic resolution of blocked actions
- No schema changes
- No new API endpoints

## 5. Path Preview Prioritization

### Proposed Sort Order

```
Severity 1: blocked    ──┤ (must fix before execute, blocks can_execute)
Severity 2: stale      ──┤ (source missing — same as blocked for can_execute)
                          │
Severity 3: warning    ──┤ (review recommended, does NOT block execute)
                          │
Severity 4: ok         ──┤ (ready to execute, no issues)
```

Within each severity group, sort by:
1. `action_order` (preserves candidate grouping — mkdir → move → write sequence stays together)
2. If multiple candidates share same severity, within that subgroup by `target_path` alphabetically

### Frontend Sorting vs Backend Sorting

**Assessment: Frontend-only sorting is sufficient.**

Reasoning:
- The `PreflightResponse.actions[]` list already carries `conflict_status` on every action
- Sorting is a pure display concern
- No backend schema or API changes needed
- The frontend already receives all the data it needs

Implementation:
```typescript
function sortActionsForDisplay(actions: OrganizeActionItemVM[]): OrganizeActionItemVM[] {
  const severityOrder: Record<string, number> = {
    blocked: 1,
    stale: 2,
    warning: 3,
    ok: 4,
    unchecked: 5,
  };
  const sorted = [...actions].sort((a, b) => {
    const sa = severityOrder[a.conflict_status] ?? 5;
    const sb = severityOrder[b.conflict_status] ?? 5;
    if (sa !== sb) return sa - sb;
    return a.action_order - b.action_order;
  });
  return sorted;
}
```

### Display Mode Options

**Option A — Always severity-sorted** (Recommended)
All actions always sorted by severity. Blocked/warning always on top. Simple, predictable.

**Option B — Tabbed/filtered**
Tabs: "Problems (N)" | "Warnings (M)" | "All Actions". Problem tab auto-selected when blocked_count > 0.

**Recommendation: Option A for initial implementation, Option B as follow-up enhancement.** Option A requires only a sort function. Option B adds filter state but would be more helpful for large plans (50+ actions).

### Visual Severity Distinction

| Severity | Pill CSS Class | Icon/Treatment |
|----------|---------------|----------------|
| `blocked` | `status-pill--danger` (existing) | Red pill + block icon |
| `stale` | `status-pill--danger` (existing) | Red pill + stale icon |
| `warning` | `status-pill--warning` (NEW) | Amber/yellow pill — this is KEY: warning currently uses neutral |
| `ok` | `status-pill--neutral` (existing) | Grey/muted pill |
| `unchecked` | `status-pill--neutral` (existing) | Grey pill |

The critical missing piece is `status-pill--warning` — warning actions currently share the `neutral` class with `ok`, making them invisible in the list.

## 6. User Action Space

### A. Review only (Blocked Preflight)

**Scenario:** `can_execute == false` (has blocked actions)

**Recommended UX:**
- Preflight notice bar shows: ❌ "Cannot execute — 2 blocked, 3 warnings"
- Problem actions are at the top of the path preview
- Each blocked action shows: `conflict_message` in a prominent position
- Execute button is disabled (existing behavior — correct)
- User CAN: re-run preflight, cancel plan, inspect actions
- User CANNOT: execute, skip actions, selectively execute

**What this enables:**
User sees exactly what's wrong, understands why, and can decide next steps.

### B. Cancel Plan

**Scenario:** User decides the plan is not fixable as-is.

**Current behavior:** Cancel resets plan status to `cancelled`, resets candidates from `added_to_plan` to `pending` (per candidate lifecycle fix).

**Recommended UX:**
- Cancel button already available for draft/ready plans
- After cancel confirmation: show what was released (N candidates back to pending)
- User can re-scan or re-generate a new plan

**Status:** Already works correctly. No changes needed.

### C. Regenerate Plan

**Scenario:** User wants to re-generate a plan after cancelling.

**Current behavior:** After cancel, candidates are back to `pending`. User can re-generate. But they must re-select candidates manually.

**Recommendation:** No changes for now. Regenerate-with-same-candidates could be a convenience shortcut (pre-fill the candidate selection) but is out of scope. The manual flow works.

### D. Copy Problematic Actions (like copy_failed_actions)

**Scenario:** User wants to isolate blocked/warning actions into a separate plan.

**Current behavior:** `copy_failed_actions` only works post-execution (requires completed/completed_with_errors/failed).

**Assessment:** NOT appropriate for pre-execution. Blocked actions are fundamentally different from failed actions:
- Failed actions: were executed, the file operation failed
- Blocked actions: never executed, the precondition wasn't met

Creating a new plan from blocked actions would just produce the same blocked preconditions. The user needs to fix the underlying issue (resolve target_exists conflict, fix source_missing, etc.) rather than re-plan.

**Recommendation:** Do NOT implement. Guide users to cancel and re-scan instead.

### E. Execute Safe Subset

**Scenario:** User wants to skip blocked actions and execute only the ready ones.

**Assessment:** DEFER to Phase 7. This is complex:
- Skipping blocked mkdir actions would cascade-dependency-skip subsequent move + write_asset_yaml for that candidate
- The plan's coverage becomes partial — half-organized objects
- Reconcile/rollback semantics for partial execution need careful design
- The user may not realize which files were skipped

**Current workaround:** Cancel the plan, resolve the issues in the source directory (move conflicting files, etc.), and re-scan/re-generate.

**Recommendation:** Do NOT implement now. Too risky without a full partial-execution design.

### Action Space Summary

| Action | Avail Before Execute? | Avail After Execute? | Note |
|--------|----------------------|---------------------|------|
| View blocked/warning (sorted) | ✅ NEW | ✅ | Severity-sorted list |
| Cancel plan | ✅ | ❌ (only draft/ready) | Resets candidates |
| Re-run preflight | ✅ | N/A | Refreshes conflict status |
| Execute (all or nothing) | ✅ (no blocked) | N/A | Existing behavior preserved |
| Execute safe subset | ❌ DEFER | N/A | Phase 7 |
| Copy failed/blocked actions | ❌ (not appropriate) | ✅ | Post-execution only |
| Generate rollback | ❌ (not appropriate) | ✅ | Post-execution only |
| Reconcile | ❌ (not appropriate) | ✅ | Post-execution only |

## 7. Recommended Implementation Option

**Option 1 — Frontend-only minimal** (RECOMMENDED)

### Changes

| File | Change |
|------|--------|
| `PlanDetailPanel.tsx` | Sort actions by severity; add warning pill; add action advice banner |
| `library.css` | Add `.status-pill--warning` class; add `.library-action-row--blocked`/`--warning` border hints |
| `features.ts` (en + zh-CN) | Add warning banner text, blocked explanation text |

### Advantages
- Zero backend changes, zero API changes, zero schema changes
- All data already available in the preflight/action responses
- Low risk — sort is pure display logic
- Ships immediately without backend deployment

### Risk Assessment
- None. This is presentation-only. No execution behavior changes.
- The `conflict_status` field on actions in the PlanDetail response might be stale if preflight hasn't run. This is already the case today.

### Why Not Option 2 or 3

**Option 2 (small API enhancement):** Not needed. The `actions[]` array already contains `conflict_status`, `conflict_message`, `source_path`, `target_path`, and `action_type`. Severity is derivable from `conflict_status`. No new backend fields needed.

**Option 3 (later advanced):** Deferred by explicit user instruction. The advanced features (execute safe subset, action exclusion, regenerate plan) require backend changes and thorough safety analysis.

## 8. Frontend Changes Proposed

### 8.1 Severity-Sorted Action List

```tsx
// In PlanDetailPanel.tsx, before rendering .library-action-list:

const sortedActions = useMemo(() => {
  const severity: Record<string, number> = {
    blocked: 0, stale: 1, warning: 2, ok: 3, unchecked: 4,
  };
  return [...(detail.actions)].sort((a, b) => {
    const sa = severity[a.conflict_status] ?? 4;
    const sb = severity[b.conflict_status] ?? 4;
    if (sa !== sb) return sa - sb;
    return a.action_order - b.action_order;
  });
}, [detail.actions]);

// Render sortedActions instead of detail.actions
```

### 8.2 Warning Status Pill

Add `status-pill--warning` CSS class with amber/yellow color:

```css
.status-pill--warning {
  background: var(--accent-warning);
  color: #1d2026; /* dark text on amber for readability */
}
```

Update `PlanActionRow` line 29-31 to use `warning` variant:
```tsx
const conflictClass = 
  action.conflict_status === "blocked" || action.conflict_status === "stale" ? "danger" :
  action.conflict_status === "warning" ? "warning" :
  "neutral";
```

### 8.3 Problem Action Row Emphasis

Give blocked/stale action rows a subtle left border indicator:

```css
.library-action-row--blocked {
  border-left: 3px solid var(--accent-danger);
}
.library-action-row--warning {
  border-left: 3px solid var(--accent-warning);
}
```

### 8.4 Preflight Notice Bar Enhancement

Replace the current "Blocked: N . Warning: M" text with a more actionable banner:

**When blocked:**
> ⛔ Cannot execute — 2 actions have blocking issues. Review them at the top of the path preview below. Fix the underlying file conflicts in your source directory, then re-run preflight.

**When warnings only (no blocked):**
> ⚠️ 3 warnings found. Execution can proceed, but review the highlighted items first. Warnings do not block execution.

**When all ok:**
> ✅ Preflight passed — all actions are safe to execute.

(The existing `.library-execution-notice--ok` and `--blocked` classes support this.)

### 8.5 Conflict Message Prominence

Move `conflict_message` to be more prominent in the action row — display it immediately after the action type, before source/target paths, when it's non-null and non-ok.

### 8.6 Summary Cards

Add a severity summary row between the notice bar and path preview:

```
[Blocked: 2] [Stale: 0] [Warnings: 3] [Ready: 145]
```

Each card shows the count and a colored background matching the severity level.

### 8.7 Cancel Guidance

When `can_execute == false`, show text below the execute button:
> "Fix the blocked issues above, then re-run preflight. Or cancel the plan and re-generate."

This gives the user a clear action path.

## 9. Backend/API Changes Proposed

**None.**

All required data is already present:
- `conflict_status` on every action → severity
- `conflict_message` on every action → reason
- `source_path`/`target_path` → which file
- `blocked_count`/`warning_count`/`can_execute` → aggregate

The only potential backend enhancement (deferred) would be adding a `severity_sort_key` or `reason_code` to actions for richer frontend logic, but the current `conflict_status` string is sufficient for sorting and display.

## 10. Safety Rules

| Rule | Current | After Changes |
|------|---------|---------------|
| Execute disabled when blocked | ✅ | ✅ (unchanged) |
| Execute allowed when warnings only | ✅ | ✅ (unchanged — but warnings now visible) |
| No silent overwrite | ✅ | ✅ (unchanged) |
| No delete/rmdir | ✅ | ✅ (unchanged) |
| No auto retry | ✅ | ✅ (unchanged) |
| No auto rollback | ✅ | ✅ (unchanged) |
| No execute safe subset | ✅ | ✅ (unchanged — deferred) |
| Cancel preserves safety | ✅ | ✅ (unchanged) |
| Blocked actions visible at top | ❌ | ✅ NEW |
| Warning actions visually distinct | ❌ | ✅ NEW |
| User knows next action | ❌ | ✅ NEW |

**No safety invariants are weakened.** The changes are purely display-level.

## 11. Test Plan

### Backend Tests

**No new backend tests required** — preflight behavior unchanged.

Existing tests that verify correctness:
- `test_preflight_target_inside_root_passes` — verifies ok actions
- `test_target_exists_blocked_in_preflight` — verifies blocked target_exists
- `test_preflight_disabled_root_blocked` — verifies blocked root disabled
- `test_preflight_legacy_cross_source_blocked` — verifies blocked cross-source
- `test_conflict_check_blocks_existing_target_and_mark_ready_fails` — verifies blocked prevents mark-ready
- `test_asset_yaml_create_only_no_overwrite` — verifies blocked overwrite prevention

### Frontend Manual Acceptance

| Test | What to verify |
|------|---------------|
| Blocked actions appear first | Sort function: blocked/stale → warning → ok |
| Warning actions before ok | Sort function verifies warning severity tier |
| Warning pill is amber, not grey | CSS `.status-pill--warning` renders |
| Blocked pill is red (existing) | `.status-pill--danger` still works |
| Execute disabled when blocked | `canExecute` still depends on `can_execute` |
| Warning banner shown | Notice bar content matches severity |
| Cancel works after preflight | Existing cancel flow unchanged |
| Re-run preflight works | Refresh conflict statuses |
| Light/dark readable | Verify in both themes |
| No raw JSON shown | UI renders structured fields only |

### Regression

Run existing test suites:
```bash
python -m pytest tests/test_library_phase3_organize.py -v
python -m pytest tests/test_library_phase5a_reconcile.py tests/test_library_phase5b_copy_failed_actions.py tests/test_library_phase5c_generate_rollback.py tests/test_library_phase5d_asset_yaml_merge.py tests/test_library_phase5d_templates.py -v
python -m pytest tests/test_library_roots_and_cross_source.py -v
python -m pytest tests/test_library_organize_partial_failure.py -v
```

And frontend build:
```bash
cd apps/frontend && npm run build
```

## 12. Deferred Ideas

These are explicitly deferred to future phases:

| Idea | Phase | Reason |
|------|-------|--------|
| Execute safe subset (skip blocked) | Phase 7 | Requires action exclusion semantics, partial execution design, rollback/reconcile implications |
| Action-level skip/exclude toggle | Phase 7 | Backend needs action exclusion list, preflight re-evaluation after exclusion |
| Regenerate from same candidates | Phase 7 | Convenience shortcut — manual re-scan + re-select works today |
| Auto-resolve conflict suggestions | Future | Would need AI or rule-based suggestions for target_exists, source_missing |
| Conflict resolver dialog | Future | Interactive dialog for each conflict type |
| Operation journal | Future | Full operation history across plans |

## 13. Recommendation

### Answering the specific questions

**Is frontend-only enough?** Yes. All necessary data (conflict_status, conflict_message, source_path, target_path) is already in the API response. The missing pieces are display-level: sorting, visual distinction for warnings, and guidance text.

**Is API change needed?** No. The `PreflightResponse` and `OrganizeActionItem` schemas already contain everything needed. No new fields, endpoints, or schema changes required.

**Must-fix before next manual acceptance:**
1. Severity-sorted action list (blocked/stale first, then warning, then ok)
2. Warning status pill (amber, distinct from neutral grey)
3. Blocked action rows with left border emphasis
4. Enhanced preflight notice bar with actionable guidance text
5. Summary cards showing counts per severity

**Recommended implementation order:**
1. CSS: Add `.status-pill--warning`, `.library-action-row--blocked`, `.library-action-row--warning`
2. PlanDetailPanel: Sort actions, use warning pill class, enhance notice bar
3. Locales: Add guidance text strings in `en/features.ts` and `zh-CN/features.ts`
4. Manual acceptance: Verify blocked-first, warning distinction, execute disabled, cancel works
5. Regression: Run full test suite + `npm run build`
