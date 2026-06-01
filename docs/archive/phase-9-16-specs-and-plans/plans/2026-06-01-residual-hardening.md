# Residual Workflow Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining verification gaps from the workflow UI hardening pass without expanding beyond the P0 local asset workflow.

**Architecture:** Backend trash behavior should be enforced both by service logic and the SQLite schema, with routers still delegating to `TrashService`. Frontend fixes should make the existing typed locale and component contracts compile without loosening type safety or adding new product semantics. The removed "Add to collection" context action remains intentionally unimplemented because current collections are saved retrieval/filter definitions, not manual membership containers.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, pytest, React, TypeScript, Vite, Vitest.

---

## Scope Understanding

This follow-up addresses only known unfinished hardening items:

- The trash API already rejects duplicate trash requests at service level, but the table still permits duplicate `file_id` rows.
- `npm run build` passes, but `npx tsc -p tsconfig.json --noEmit` exposes missing locale keys and a few typed component mismatches.
- The previous Browse v2 context-menu "Add to collection" affordance was removed because it advertised behavior that does not currently exist in the API model.

## Files To Change

- `apps/backend/app/db/session/engine.py`: bump schema version and create an idempotent unique index for `trash_entries.file_id`.
- `apps/backend/app/db/models/trash_entry.py`: mirror the one-entry-per-file invariant in the ORM model.
- `apps/backend/app/services/trash/service.py`: convert unique-index races into the existing `ALREADY_TRASHED` response.
- `apps/backend/tests/test_trash.py`: assert direct duplicate rows are rejected by the schema.
- `apps/frontend/src/locales/en/*.ts` and `apps/frontend/src/locales/zh-CN/*.ts`: add missing text keys already referenced by active UI.
- `apps/frontend/src/features/batch-organize/BatchActionBar.tsx`: make placement controls optional for subset pages that only expose tags and color tags.
- `apps/frontend/src/features/home-overview/HomeOverviewFeature.tsx` and `apps/frontend/src/features/system-status/SystemStatusFeature.tsx`: either support or remove the compact variant without changing settings behavior.
- `apps/frontend/src/features/browse-v2/ExecutePlanPanel.tsx`: narrow execution summary values before rendering.
- `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`: keep media file-type typing aligned with `image | video` rows.
- Existing feature call sites using wrong locale keys: update only when the correct nested key already exists.

## Files Not To Change

- Do not edit generated `dist` output.
- Do not introduce a new collection-membership API or manual "add to collection" behavior.
- Do not refactor the app shell, shared details panel, router layout, or backend route/service/repository layers beyond the files above.
- Do not add P1/P2 concepts such as cloud sync, accounts, AI/OCR, semantic indexing, or plugin architecture.

## Dependencies

- Backend uses existing SQLite initialization in `engine.py`; the unique index must work for both new databases and databases already at schema version 9.
- Frontend text keys are typed from the English locale dictionary, so English additions must lead and zh-CN must stay structurally aligned.
- Existing tests and build scripts remain the validation source of truth.

## Validation Plan

- Backend targeted tests:
  - `python -m pytest tests/test_trash.py -q`
  - `python -m pytest tests/test_files_duplicates.py tests/test_library_v2_object_amendment_execute.py tests/test_library_v2_object_amendment_plan.py tests/test_library_v2_object_amendment_preflight.py -q`
- Frontend targeted tests:
  - `npm run test -- tests/browse-v2-interactions.test.tsx tests/action-menu.test.tsx tests/modal.test.tsx tests/i18n-coverage.test.ts tests/page-smoke.test.tsx`
- Frontend static verification:
  - `npx tsc -p tsconfig.json --noEmit`
  - `npm run build`
- Desktop verification:
  - `npm run build` in `apps/desktop`
- Hygiene:
  - `git diff --check`

---

### Task 1: Enforce One Trash Entry Per File

**Files:**
- Modify: `apps/backend/app/db/session/engine.py`
- Modify: `apps/backend/app/db/models/trash_entry.py`
- Modify: `apps/backend/app/services/trash/service.py`
- Test: `apps/backend/tests/test_trash.py`
- Docs: `docs/api/core-workbench.md`

- [x] **Step 1: Add a failing schema-level duplicate test**

Add a test that inserts one trash row directly, then verifies a second direct insert for the same `file_id` raises an integrity error. This proves the database, not just `TrashService`, owns the invariant.

- [x] **Step 2: Run the focused test and confirm the failure**

Run: `python -m pytest tests/test_trash.py::TrashTestCase::test_trash_file_id_is_unique -q`

Expected before implementation: the duplicate insert succeeds or the assertion does not observe an integrity failure.

- [x] **Step 3: Add the idempotent unique index migration**

Change `_ensure_trash_entries` to:

- keep the existing table creation;
- remove invalid duplicate rows by keeping the newest `trashed_at`, highest `id` row per file;
- create `idx_trash_entries_file_id_unique` as a unique index;
- keep or recreate the non-unique expiry index;
- bump `CURRENT_SCHEMA_VERSION` from `9` to `10`;
- call `_ensure_trash_entries` for databases at version 9.

- [x] **Step 4: Mirror the invariant in the ORM model and service**

Set `TrashEntry.file_id` to `unique=True`, and catch `IntegrityError` in `TrashService.trash_file()` so a concurrent duplicate returns `ALREADY_TRASHED` through the existing error shape.

- [x] **Step 5: Re-run focused backend tests**

Run: `python -m pytest tests/test_trash.py -q`

Expected: all trash tests pass, including duplicate API rejection and direct schema rejection.

### Task 2: Close Frontend TypeScript Locale And Contract Gaps

**Files:**
- Modify: `apps/frontend/src/locales/en/common.ts`
- Modify: `apps/frontend/src/locales/zh-CN/common.ts`
- Modify: `apps/frontend/src/locales/en/details.ts`
- Modify: `apps/frontend/src/locales/zh-CN/details.ts`
- Modify: `apps/frontend/src/locales/en/features.ts`
- Modify: `apps/frontend/src/locales/zh-CN/features.ts`
- Modify: `apps/frontend/src/locales/en/navigation.ts`
- Modify: `apps/frontend/src/locales/zh-CN/navigation.ts`
- Modify: `apps/frontend/src/locales/en/shell.ts`
- Modify: `apps/frontend/src/locales/zh-CN/shell.ts`
- Modify: `apps/frontend/src/locales/en/settings.ts`
- Modify: `apps/frontend/src/locales/zh-CN/settings.ts`
- Modify: `apps/frontend/src/features/batch-organize/BatchActionBar.tsx`
- Modify: `apps/frontend/src/features/browse-v2/ExecutePlanPanel.tsx`
- Modify: `apps/frontend/src/features/home-overview/HomeOverviewFeature.tsx`
- Modify: `apps/frontend/src/features/system-status/SystemStatusFeature.tsx`
- Modify: `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`
- Modify only if needed: feature files that reference `features.homeOverview.scanCardAction` or `features.homeOverview.browseCardAction`

- [x] **Step 1: Run TypeScript once to capture the active failure list**

Run: `npx tsc -p tsconfig.json --noEmit --pretty false`

Expected before implementation: missing key errors for shell/navigation/common/details/features/settings plus component type errors in batch organize, home overview, execute plan, and media library.

- [x] **Step 2: Add missing locale keys rather than weakening the typed translator**

Add keys that are already referenced by UI code:

- shell: `skipToContent`, `sidebar.navigationLabel`, `sidebar.footerKicker`, `sidebar.footerCopy`
- navigation: `items.tools`
- common actions/states/labels/ratings: `favorite`, `unfavorite`, `history`, `moveUp`, `moveDown`, `retry`, `rating`, star labels
- details: storage labels, placement labels/options/summary, missing metadata fields, preview alt, PDF/software preview notes, show-in-folder action, remove-tag confirmation, placement update/error text
- settings source history: `settings.sourceManagement.savedSources.noHistory`
- feature quick actions: English `search` and `sources` keys for books/media/games/software, keeping zh-CN aligned

- [x] **Step 3: Fix incorrect home overview key call sites**

Replace `features.homeOverview.scanCardAction` and `features.homeOverview.browseCardAction` with the existing nested keys under `features.homeOverview.overview.*` unless the call site intentionally needs a different label.

- [x] **Step 4: Make batch placement optional where subset pages do not expose placement actions**

Update `BatchActionBarProps` so `isApplyingPlacement` and `onApplyPlacement` are optional. Render the placement `<select>` only when `onApplyPlacement` is provided, while preserving behavior for Recent Imports and any page that does pass placement actions.

- [x] **Step 5: Fix remaining strict render/type mismatches**

Narrow `ExecutePlanPanel` summary values to strings/numbers before rendering. Support `SystemStatusFeature` compact variant or remove the unused prop in a way that preserves the home and settings layouts. Narrow media row file types to `image | video` before passing them into `MediaLibraryRow` and media summary helpers.

- [x] **Step 6: Re-run TypeScript and frontend targeted tests**

Run:

```powershell
npx tsc -p tsconfig.json --noEmit
npm run test -- tests/browse-v2-interactions.test.tsx tests/action-menu.test.tsx tests/modal.test.tsx tests/i18n-coverage.test.ts tests/page-smoke.test.tsx
```

Expected: both commands pass.

### Task 3: Document Residual Scope Decision

**Files:**
- Modify: `docs/library-v2/PHASE8_BETA_READINESS_REVIEW.md`
- Modify if trash behavior changed materially: `docs/api/core-workbench.md`

- [x] **Step 1: Update trash note**

If the unique index is implemented, replace the prior concurrency caveat with a note that duplicate trash rows are blocked at schema level and duplicate API requests still return `ALREADY_TRASHED`.

- [x] **Step 2: Record the Add-to-collection decision**

Document that Browse v2 no longer exposes an add-to-collection menu item because collections are saved retrievals, not manual containers. This is an intentional P0 boundary, not an unfinished UI stub.

### Task 4: Final Verification

**Files:**
- No new files expected.

- [x] **Step 1: Run backend regression commands**

Run:

```powershell
python -m pytest tests/test_trash.py -q
python -m pytest tests/test_files_duplicates.py tests/test_library_v2_object_amendment_execute.py tests/test_library_v2_object_amendment_plan.py tests/test_library_v2_object_amendment_preflight.py -q
```

Expected: all selected tests pass.

- [x] **Step 2: Run frontend and desktop verification**

Run:

```powershell
npx tsc -p tsconfig.json --noEmit
npm run test -- tests/browse-v2-interactions.test.tsx tests/action-menu.test.tsx tests/modal.test.tsx tests/i18n-coverage.test.ts tests/page-smoke.test.tsx
npm run build
```

Then run from `apps/desktop`:

```powershell
npm run build
```

Expected: TypeScript, tests, frontend build, and desktop build pass. Existing Vite chunk-size warnings may remain.

- [x] **Step 3: Run hygiene checks**

Run: `git diff --check`

Expected: no whitespace errors. CRLF warnings are acceptable only if they match the existing repository line-ending behavior.

## Self-Review

- **Spec coverage:** The plan covers only the exposed residual risks: trash uniqueness, TypeScript closure, docs sync, and final validation. It does not add manual collection membership because that would require a product/API decision outside the current P0 task.
- **Placeholder scan:** No `TBD`, broad "handle edge cases", or hidden future implementation steps remain.
- **Type consistency:** File names and key paths match the currently referenced code. The frontend translator remains strongly typed.
