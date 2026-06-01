# Commercial-Quality UX Optimization — Design Spec

> Date: 2026-05-27 | Status: Design approved | Based on: v0.2.0 main branch

## 1. Goal

Make Workbench feel like commercial software by reducing operational friction. The core insight: **keep all safety gates, but automate everything between them**. Users should confirm, not configure.

## 2. Architecture Decision

**No structural changes needed.** The current architecture (Route → Service → Repository, SQLite, plan-first safety, hybrid mode) is sound. This design adds convenience endpoints on top — existing endpoints remain untouched.

## 3. Design: Three Batches

### 3.1 Batch 1 — Core Flow Automation

#### 3.1.1 POST /plans/{id}/prepare (New Atomic Endpoint)

Combines `mark-ready` + `preflight` into a single call.

```
POST /library/organize/plans/{id}/prepare

Response:
{
  "plan_id": 5,
  "status": "ready",
  "can_execute": true,
  "blocked_count": 0,
  "warning_count": 0,
  "actions": [...],
  "messages": [...]
}
```

- Calls `_refresh_plan_conflicts` + mark-ready + preflight in sequence
- Returns the same preflight response shape
- Does NOT execute — user must still confirm

#### 3.1.2 POST /inbox/items/{id}/process (New Atomic Endpoint)

Chains: confirm → create-candidate → generate-plan.

```
POST /library/import/inbox/items/{id}/process

Request: { "final_object_type": "movie", "target_library_root_id": 1 }
Response: { "plan_id": 5, "plan_status": "draft", "candidate_id": 3 }
```

- All three operations in one transaction
- If confirm fails → 400 with reason
- If candidate creation fails → 400 with reason
- Returns plan_id for immediate redirect to execute panel

#### 3.1.3 Smart Pre-fill Engine

**Object type detection** enhancements (classification.py + organize.py):

| Signal | Current | Added |
|---|---|---|
| Folder name | Not used | Parse [TAG], year, type prefixes |
| File relationships | Not used | Same-parent grouping, companion files |
| Video duration | Not used | Long → movie, short → clip via metadata |
| Audio files | → unknown | → audio object type |
| Numbered image sequences | → imgset | → comic if sequential naming detected |
| Historical choices | Not used | Same type → same root preference |

**Target root selection** — priority:

1. File path belongs to a known root's subdirectory → inherit
2. Same object_type last used root (from inbox_items history)
3. Most recently used root (global, any type)
4. System default root (explicitly set by user)

**Confidence gating** — Process button behavior:

| Confidence | UI | Action |
|---|---|---|
| high | Green badge, pre-filled fields collapsed | Process enabled |
| medium | Yellow badge, reason shown | Process enabled |
| low / unknown | Red badge, "Needs your judgment" | Process DISABLED — user must manually confirm type |

#### 3.1.4 Modal Execute Panel (Frontend)

A slide-out panel in Browse v2 that handles plan execution without leaving the page.

- Triggered by: Compose success banner → "Review & Execute" button
- Also triggered by: Import process → auto-redirect after plan generation
- Panel content:
  1. Auto-calls `POST /plans/{id}/prepare`
  2. Shows preflight result (blocked actions highlighted)
  3. If can_execute → "Execute" confirmation button
  4. If blocked → shows which actions are blocked and why
  5. On execute → shows result summary (files moved, objects created, members changed)
  6. Close → returns to Browse with refreshed data

**New UI files:**
- `features/browse-v2/ExecutePlanPanel.tsx` — modal panel component
- `features/browse-v2/hooks/useExecutePlan.ts` — prepare + execute logic

**Reuses from Library Plans:**
- Preflight result display logic
- Action path preview
- Execute confirmation logic

### 3.2 Batch 2 — Feedback and Visibility

#### 3.2.1 Execution Result Summary

After execute completes, the modal panel (3.1.4) shows a structured summary:

```
✓ Plan executed — #5

3 files moved
1 object created
2 members added
0 errors

[View in Browse]  [View Plan Detail]
```

Backend: Include `execution_summary_json` in plan detail response with structured counts.

#### 3.2.2 Actionable Error Messages

Every error response that the user might see must include `suggested_action`:

```json
{
  "detail": "Source file not found: C:\\Users\\...\\file.mp4",
  "suggested_action": "The original file may have been moved or deleted. Check the path and retry, or reject this inbox item."
}
```

Affected endpoints: import files, import folders, retry import, execute plan.

#### 3.2.3 Browse Summary Strip

A compact metrics bar above Browse results:

```
[Browse results]  12 objects · 45 loose files · 8 managed · 3 inbox · 34 external
```

Reuses existing `get_storage_summary()` data. Frontend: add `<MetricStrip>` to BrowseV2Feature masthead area.

#### 3.2.4 Library Breadcrumbs

Add breadcrumb navigation within Library tabs:

```
File Library > Plans > Plan #5
File Library > Inbox > Batch #3 > Item review
```

Frontend change only — use existing tab state + selected item.

### 3.3 Batch 3 — Commercial Polish (Intentionally Deferred)

Batch 3 is a placeholder for post-B1/B2 polish. Items are listed for visibility but will be designed separately after B1 and B2 are complete and validated:

- Async operation progress notifications (SSE or polling for scan/import progress)
- Empty state guidance full coverage (all panels, all tabs)
- Visual consistency full sweep (remaining bare `<p>` loading states)
- Recovery summary badge on Library Overview

**Implementation note**: This spec targets Batch 1 for immediate implementation. Batch 2 follows. Batch 3 is deferred.

## 4. Non-Goals

- No architecture restructure
- No database schema changes (except possibly user_preferences — evaluate in implementation)
- No endpoint deletions (all existing endpoints preserved)
- No old feature removal (still waiting for beta feedback)
- No CSS split (too fragile for manual work)
- No Alembic (idempotent SQL sufficient for SQLite)
- No mixed amendment, removed member history, direct execute from detail (these require independent designs)

## 5. Test Strategy

- Backend: New endpoint tests for /prepare and /process
- Backend: Classification enhancement tests
- Frontend: ExecutePlanPanel component tests
- Regression: All existing Library v2 tests (140+), all frontend tests (27)
- Manual: Smoke test the full Import → Process → Execute chain end-to-end

## 6. Files Affected

### Batch 1

| File | Change |
|---|---|
| `api/routes/library_organize.py` | +POST /plans/{id}/prepare |
| `api/routes/importing.py` | +POST /inbox/items/{id}/process |
| `services/library/organize.py` | +prepare_plan() method |
| `services/importing/service.py` | +process_inbox_item() method |
| `core/classification.py` | +folder_name parsing, +audio type hints |
| `services/library/organize.py` | _detect_file_type enhancements |
| `features/browse-v2/ExecutePlanPanel.tsx` | NEW modal component |
| `features/browse-v2/hooks/useExecutePlan.ts` | NEW hook |
| `features/browse-v2/BrowseV2Feature.tsx` | Wire up ExecutePlanPanel |
| `features/browse-v2/ComposeObjectModal.tsx` | "Review & Execute" button |
| `features/library/LibraryInboxPanel.tsx` | "Process" button, auto-fill UI |
| `services/api/libraryOrganizeApi.ts` | +preparePlan() |
| `services/api/importingApi.ts` | +processInboxItem() |
| `locales/en/features.ts` | New keys for execute panel, process button |
| `locales/zh-CN/features.ts` | Same, Chinese |

### Batch 2

| File | Change |
|---|---|
| `api/routes/importing.py` | +suggested_action in error responses |
| `api/routes/library_organize.py` | +execution_summary in responses |
| `features/browse-v2/BrowseV2Feature.tsx` | +summary strip |
| `features/library/LibraryFeature.tsx` | +breadcrumbs |
| `features/library/` panel files | +error suggested_action display |

## 7. Risks

| Risk | Mitigation |
|---|---|
| /process transaction rollback | All three operations wrapped in single DB transaction |
| Pre-fill accuracy | Confidence gate: low confidence disables Process |
| Modal panel complexity | Reuse Plans page logic, not rewrite |
| Old API breakage | All new endpoints are additive, old ones untouched |

## 8. Rejected Alternatives

- **Delete Mark Ready** — too destructive; /prepare adds convenience without removing manual path
- **Inline execute in object detail** — too tightly coupled; modal panel is more maintainable
- **Merge Source and Managed Root** — design boundary, not a UX problem
- **Introduce Alembic** — overkill for SQLite single-user app
