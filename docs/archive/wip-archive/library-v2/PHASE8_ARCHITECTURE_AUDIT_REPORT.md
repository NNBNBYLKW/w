# Phase 8 Architecture Audit Report

Generated: 2026-05-20  
Auditor: Codex  
Branch reviewed: main  
Reference commit observed: 826ca78 docs(library-v2): add phase 8 beta acceptance review

## 1. Executive Summary

### Overall verdict

Phase 8 has a coherent architecture and the main Browse v2 / Object model / Compose / Amendment chain is largely in place. The backend mostly keeps the intended route -> service -> repository boundary, the object/member model supports active vs removed membership, and all requested backend tests plus frontend and desktop builds pass.

However, the audit found one P0 data-consistency violation in the amendment finalization path and several P1 beta-readiness issues in the read model and remove-member flow. This means Phase 8 should not be treated as GREEN beta-ready until the P0 and P1 items are fixed or explicitly mitigated.

### Beta readiness

YELLOW.

The system is suitable for controlled local testing with disposable data and careful operator guidance, but not for broad beta testing yet.

### Issue counts

| Severity | Count |
|---|---:|
| P0 | 1 |
| P1 | 4 |
| P2 | 11 |
| P3 | 2 |

## 2. Scope Reviewed

### Docs

- README.md
- docs/README.md
- docs/library-v2/README.md
- docs/library-v2/ARCHITECTURE.md
- docs/library-v2/API_REFERENCE.md
- docs/library-v2/MANUAL_ACCEPTANCE_GUIDE.md
- docs/library-v2/BETA_TESTING_CHECKLIST.md
- docs/library-v2/KNOWN_LIMITATIONS.md
- docs/library-v2/PHASE8_FINAL_ACCEPTANCE_CHECKLIST.md
- docs/library-v2/PHASE8_BETA_READINESS_REVIEW.md
- docs/FILE_CLASSIFICATION_RULES.md
- docs/_wip/library-v2/PHASE8D_OBJECT_AMENDMENT_PLAN.md
- docs/_wip/library-v2/PHASE8C4_MANAGED_COMPOSE_AND_OBJECT_CREATION_PLAN.md
- docs/_wip/library-v2/PHASE8_BROWSE_V2_AND_OBJECT_MANAGEMENT_MANUAL.md

### Backend files

- Models: apps/backend/app/db/models/file.py, library_object.py, organize.py, importing.py
- Routes: apps/backend/app/api/routes/library.py, library_objects.py, library_organize.py, importing.py
- Schemas: apps/backend/app/schemas/browse_v2.py, library_organize.py, importing.py
- Services: apps/backend/app/services/library/browse_v2.py, organize.py, organize_template_renderer.py, apps/backend/app/services/importing/service.py, recovery.py
- Repositories: apps/backend/app/repositories/library_organize/repository.py, library_objects/repository.py, importing/repository.py
- Runtime / DB: apps/backend/app/db/session/engine.py, session.py, apps/backend/app/main.py
- Recovery/path searches: recovery, path_history, operation_journal, storage_scope, file_path_history, no_overwrite, shutil.move, copy2, completed_with_errors

### Frontend files

- apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx
- apps/frontend/src/features/browse-v2/ObjectCard.tsx
- apps/frontend/src/features/browse-v2/LooseFileCard.tsx
- apps/frontend/src/features/browse-v2/ComposeObjectModal.tsx
- apps/frontend/src/features/browse-v2/composeHelpers.ts
- apps/frontend/src/services/api/browseV2Api.ts
- apps/frontend/src/services/api/libraryOrganizeApi.ts
- apps/frontend/src/services/api/libraryObjectsApi.ts
- apps/frontend/src/services/api/importingApi.ts
- apps/frontend/src/locales/en/features.ts
- apps/frontend/src/locales/zh-CN/features.ts
- apps/frontend/src/app/styles/browse.css
- apps/frontend/src/app/styles/responsive.css

### Tests

- apps/backend/tests/test_library_browse_v2_read_model.py
- apps/backend/tests/test_library_browse_v2_object_detail.py
- apps/backend/tests/test_library_v2_compose_inbox.py
- apps/backend/tests/test_library_v2_compose_external.py
- apps/backend/tests/test_library_v2_managed_compose_plan.py
- apps/backend/tests/test_library_v2_managed_compose_preflight.py
- apps/backend/tests/test_library_v2_managed_compose_execute.py
- apps/backend/tests/test_library_v2_object_member_status.py
- apps/backend/tests/test_library_v2_object_amendment_plan.py
- apps/backend/tests/test_library_v2_object_amendment_preflight.py
- apps/backend/tests/test_library_v2_object_amendment_execute.py
- apps/backend/tests/test_library_v2_path_sync.py
- apps/backend/tests/test_library_v2_recovery.py
- apps/backend/tests/test_library_v2_storage_scope.py

No frontend test or Playwright test directory was found for Browse v2 / Object Detail / Compose / Amendment.

## 3. Architecture Overview

### Main flows

```text
External source file
  -> external compose copies into 00_Inbox
  -> import_object_candidate pending_review

Inbox item
  -> inbox compose creates/updates import_object_candidate
  -> no file-system mutation

Managed loose file
  -> managed compose draft plan
  -> mark ready
  -> preflight
  -> execute move actions
  -> finalize library_object + active library_object_members

Formal library object
  -> object detail read model
  -> add-member amendment draft plan
  -> preflight / execute
  -> active member added

Formal library object
  -> remove-member amendment draft plan
  -> preflight / execute
  -> existing member_status becomes removed
  -> file moves back to managed loose area
```

### Core models

- files: file-system-backed fact table with storage_state, absolute_path, managed_root_id, inbox_item_id, original_path, managed_at.
- library_objects: formal object identity and object-level metadata.
- library_object_members: object membership rows with member_status active/removed.
- organize_plans: draft/ready/executing/completed/completed_with_errors/failed lifecycle container.
- organize_actions: mkdir/move action units with payload_json for object creation and amendment semantics.
- import_object_candidates and import_object_members: inbox-side object candidates before formal object creation.
- file_path_history: path transition audit trail.
- operation_journal: durable operation diagnostics.

### Lifecycle diagrams

```text
OrganizePlan:
draft
  -> mark_ready
ready
  -> preflight
ready
  -> execute
executing
  -> completed
  -> completed_with_errors
  -> failed
```

```text
LibraryObjectMember:
active
  -> remove amendment execute
removed
  -> hidden from object detail
  -> visible as managed loose if file remains managed and no active membership
```

```text
Execute worker:
preflight whole plan
  -> set plan executing
  -> for each action:
       cancelled => skipped
       ready => preflight action again => fs operation => action status
  -> sync paths
  -> finalize managed compose or amendment
  -> set plan status
```

## 4. Findings by Dimension

### 4.1 Architecture Layering

The backend mostly follows the intended architecture:

- Routes generally parse request parameters, call service functions, and return schemas.
- Services own business rules, validation, plan lifecycle, file-system operations, and cross-repository coordination.
- Repositories are mostly restrained data-access helpers.
- Browse v2 backend assembles stable view models rather than returning raw DB rows.

There are small deviations:

- apps/backend/app/api/routes/importing.py contains route-level workflow logic in update_object_candidate and retry_failed_import, including direct calls to private importing service helpers.
- apps/backend/app/api/routes/library.py contains inline SQL-style aggregation in the storage summary route.
- The frontend does not fabricate final business state, but BrowseV2Feature owns many distinct workflows at once.

Risk: P2.

### 4.2 Data Model Integrity

Acceptable points:

- files.storage_state is consistently used for external/inbox/managed separation.
- library_object_members.member_status is used by object detail and Browse v2 to distinguish active from removed members.
- Removed members are hidden from object detail and active-object membership views.
- Add/remove amendment creation rejects mixed add/remove in one plan.
- Hard delete is not used by Phase 8 amendment; removal is soft via member_status = removed.

Potential problems:

- The removed-member model and managed-compose eligibility are inconsistent: Browse v2 treats removed members as loose, while managed compose excludes any prior library_object_members row regardless of member_status.
- organize_plans.plan_kind is a free string and key relationships are often encoded inside summary_json or action payload_json.
- There are no explicit added_by_plan_id, removed_by_plan_id, or source_file_id columns for future forensic tracing.

Risk: P2, except the skipped-action amendment finalization problem described in P0-01.

### 4.3 OrganizePlan Lifecycle

The intended lifecycle is clear:

```text
draft -> ready -> executing -> completed / completed_with_errors / failed
```

Managed compose, add-member amendment, and remove-member amendment all use the same plan-first structure. Draft creation does not immediately mutate the file system or object membership.

Lifecycle risks:

- execute_plan re-runs preflight before starting the worker, which is good.
- The worker re-runs per-action preflight, which reduces stale-path windows.
- The in-process BoundedSemaphore prevents concurrent worker execution inside one process.
- There is no durable plan lock, so cross-process execution protection is limited.
- Finalization relies on failed_count, not the full set of expected action outcomes.
- summary_json.finalized is written but not used as a hard finalization guard.

The largest lifecycle issue is P0-01: completed_with_errors can still be accompanied by membership mutation if some actions are skipped/cancelled and none fail.

Risk: P0/P1.

### 4.4 File System / DB Consistency

Current safety:

- External compose uses copy-only behavior and preserves source files.
- move actions use no-overwrite target generation.
- stale source path and target conflict checks happen at plan creation/mark-ready/preflight.
- target paths are checked to stay inside expected managed roots/object roots.
- source cleanup and delete are not implemented in Phase 8.
- failed_count > 0 prevents finalization.

Residual risk:

- File-system mutation and database updates are not atomic. A crash after a move but before finalization can leave the file system ahead of the DB.
- Recovery is diagnostic only and cannot automatically repair this class of mismatch.
- skipped/cancelled actions are not treated as finalization blockers for amendment finalization.
- Remove-member target directory creation is not represented as a plan action, so fresh remove-member plans can fail even when the logical move is valid.

Risk: P0/P1 due to amendment finalization and remove-target directory behavior; otherwise acceptable for local controlled testing.

### 4.5 Transaction Boundaries

Textual boundary map:

```text
Plan creation:
  DB session only -> commit

Preflight:
  DB reads + FS existence/conflict checks -> no intended mutation

Execute action:
  FS move/copy operation -> action DB status update -> commit

Finalization:
  DB object/member/path-history/journal updates -> commit

Failure:
  DB rollback only; FS rollback is not automatic
```

This is a reasonable local-first pattern, but the system should be explicit that FS rollback is not available. completed_with_errors is intended to mean no membership finalization, but the current skipped-action path violates that expectation for amendment plans.

Risk: P0/P1.

### 4.6 Browse v2 Read Model

Correct behavior:

- Object cards are sourced from formal library_objects and import candidates.
- Loose files exclude active library_object_members and active import_object_members.
- Removed library members are not treated as active members, so they can reappear as loose.
- storage_state, card_kind, domain, and category filters are present.
- Empty/loading/error states exist in the frontend.
- Object detail links are derived from object card identity.

Problems:

- Formal object card member_count is read from getattr(lo, "member_count", 0), but the LibraryObject model does not define member_count. Formal object cards can therefore show 0 members even when active members exist.
- The service paginates loose file rows before combining them with all object cards, then sorts and paginates the combined list again. This can create unstable totals, skipped loose files, or object-heavy pages that starve loose file results.
- Import candidate filtering uses suggested_object_type in the read model; candidates changed to a final type can be filtered unexpectedly.

Risk: P1 for member_count and pagination; P2 for candidate type-filter nuance.

### 4.7 Object Detail Read Model

Current state:

- Object detail returns active members only.
- Removed members are hidden, matching the explicit Phase 8 limitation that removed-member history UI is not implemented.
- member_id, file_id, role, absolute path, relative path, storage_state, and missing flag are available to the frontend.
- member_count is calculated from the returned active members.
- managed_root_id is available for amendment UI context.

Remaining risk:

- UI currently displays raw member role values directly, which can leak technical names into the product surface.
- Removed history is intentionally absent, but diagnostics may need this later.

Risk: P2.

### 4.8 Compose Flows

Flow boundaries are mostly clear:

| Flow | File-system behavior | Current boundary |
|---|---|---|
| Inbox compose | No FS mutation | Pure DB candidate composition |
| External compose | copy-only into inbox | Source preserved |
| Managed compose | draft plan only | No immediate object creation or file move |

Correct safeguards:

- Mixed storage-state selection is blocked.
- Inbox compose does not move files.
- External compose is copy-only.
- Managed compose is plan-first and does not create the object until execute/finalize.

Risks:

- Removed-member files are visible as loose but blocked from managed compose by queries that ignore member_status.
- The ComposeObjectModal description still has generic inbox/no-move wording that can be misleading in external/managed modes, although mode-specific text below is better.

Risk: P2, with user-confusion beta risk.

### 4.9 Amendment Flows

Current closed loop:

- Add-member draft creates move actions only; no immediate mutation.
- Remove-member draft creates move actions only; no immediate mutation.
- Mixed add/remove is rejected.
- Preflight validates active membership, object ownership, stale paths, target conflicts, and target root policy.
- Execute moves files first, then finalization creates active members or marks existing members removed.
- Remove is not delete. Source cleanup and hard delete are not implemented.

Critical risk:

- _finalize_object_amendment only checks failed_count > 0. It does not check skipped_count, cancelled actions, or "all required amendment actions succeeded" before mutating membership for succeeded actions. This allows completed_with_errors plus membership mutation.

Other risk:

- Remove-member plans target 90_Loose/Removed_<object_root> but do not create that directory as a mkdir action.

Risk: P0/P1.

### 4.10 Recovery / Diagnostic Behavior

Current recovery detects:

- Orphan inbox files.
- Missing inbox copies.
- Missing managed files from the File table.
- Failed import items.
- Incomplete batches.
- Incomplete journal operations.

Current recovery does not:

- Automatically repair anything.
- Reconcile library_object_members with File.path after amendment.
- Detect active member rows whose file has already been moved out of the object root.
- Detect removed member rows whose file did not return to loose storage.

The docs correctly describe recovery as diagnostic-only. This is acceptable for controlled beta, but it raises the importance of manual acceptance around compose/amendment.

Risk: P2.

### 4.11 Frontend State / UX Boundaries

Current state:

- BrowseV2Feature handles browsing, filtering, object detail, file detail selection, compose selection, compose modal state, add-member modal state, and remove-member modal state.
- Loose file clicks use the shared selectedItemId/details panel pattern; object detail is rendered as a local aside.
- Add/remove wording mostly avoids delete semantics.
- Success/error feedback exists for compose and amendment plan creation.

Risks:

- BrowseV2Feature is large and is now a maintenance hotspot.
- Add-member modal queries only managed loose files with default API filters; because the API default domain is media, candidate selection can omit docs/apps/assets.
- Raw member.role values appear in object detail.
- Locale copy still includes a Browse v2 read-only notice saying add/remove/compose belongs to a later phase, which is stale after Phase 8D.

Risk: P2.

### 4.12 API Consistency

Current quality:

- Endpoint naming is mostly stable and predictable.
- Response models are explicit Pydantic schemas.
- Managed compose lives under library_organize, matching plan ownership.
- Amendment plan creation lives under library_objects, matching object ownership.

Boundary concerns:

- Amendment creation is routed in library_objects.py but implemented by the organize service and consumed through libraryOrganizeApi.ts. This is understandable, but it blurs object vs organize boundaries.
- get_plan_detail refreshes conflicts and commits on a GET-style read. That makes a read endpoint perform state mutation.
- Error responses are service-dependent and not fully normalized.

Risk: P2.

### 4.13 i18n / Raw Key Risk

Current state:

- The duplicate "success" key issue from earlier phases is not present in the current locale files.
- English and zh-CN locale coverage exists for major Browse v2 / Compose / Amendment UI strings.

Risks:

- Raw technical member role values are rendered directly.
- A stale read-only notice remains in both locales.
- There are no frontend/i18n tests that would catch missing keys or raw key regressions.

Risk: P2.

### 4.14 Test Coverage

Current coverage is strong on backend happy paths and many validation paths. The requested backend suites all pass.

Key gaps:

- No test for amendment execution where one action is cancelled/skipped and another succeeds.
- No test asserting completed_with_errors never mutates membership for skipped/cancelled amendment plans.
- No test for remove-member draft/preflight against a fresh missing Removed_<object_root> target directory.
- No test for Browse v2 formal object member_count.
- No test for combined object + loose pagination stability.
- No test for removed-member file re-entry into managed compose eligibility.
- No frontend component, Playwright, or i18n raw-key tests were found.

Risk: P1 for critical backend gaps, P2 for frontend/E2E gaps.

### 4.15 Documentation Consistency

Consistent:

- Phase 8 final acceptance and beta readiness docs accurately describe the intended completed scope.
- API_REFERENCE documents the new Browse v2, compose, and amendment surfaces.
- Manual and beta docs correctly emphasize diagnostic recovery and no auto-repair.

Stale or incomplete:

- KNOWN_LIMITATIONS.md still contains an object amendment limitation indicating add/remove members are deferred, which conflicts with Phase 8D completion.
- ARCHITECTURE.md does not fully document Phase 8 plan kinds, managed compose finalization, amendment finalization, or the member_status lifecycle.
- Some broader docs still read like Phase 7-era state while Phase 8 is complete.

Risk: P2.

## 5. Issue Register

| ID | Severity | Area | Finding | Evidence | Impact | Recommendation |
|---|---|---|---|---|---|---|
| P0-01 | P0 | Amendment lifecycle | Amendment finalization can mutate membership even when final plan status is completed_with_errors if actions are skipped/cancelled but none fail. | apps/backend/app/services/library/organize.py worker increments skipped for cancelled actions, sets completed_with_errors when skipped > 0, but _finalize_object_amendment gates only on failed_count > 0 and then finalizes succeeded move actions. | Violates the required rule that completed_with_errors must not mutate membership; can produce partial object membership changes. | Block amendment finalization unless every required amendment action succeeded; treat skipped/cancelled as finalization blockers; add regression tests. |
| P1-01 | P1 | Remove amendment | Remove-member plans target 90_Loose/Removed_<object_root> but do not create that directory as a mkdir action. | create_amendment_plan builds remove move actions to Removed_<root>; _preflight_action requires target.parent to exist or be planned; tests pre-create the directory. | Fresh real remove-member flows can fail preflight/mark-ready even when logically valid. | Add a planned mkdir action for the remove target directory or target an existing loose directory; add a fresh-directory test. |
| P1-02 | P1 | Browse v2 read model | Combined pagination is unstable because loose files are paginated before object cards are combined and paginated again. | apps/backend/app/services/library/browse_v2.py applies offset/limit to file query, then sorts and slices object+file cards in memory. | Cards can be skipped/duplicated across pages and totals can be misleading. | Use a stable combined pagination strategy or separate object/file pagination counts; add pagination tests. |
| P1-03 | P1 | Browse v2 read model | Formal object cards can show member_count = 0 because member_count is read from a field not present on LibraryObject. | browse_v2.py uses getattr(lo, "member_count", 0); LibraryObject has no member_count column/property. | Object card counts are visibly wrong and can undermine acceptance testing. | Aggregate active member counts in the query or service mapping; add formal object member_count tests. |
| P1-04 | P1 | Tests | Critical P0/P1 paths lack tests. | Current suites cover normal amendment execution, but not skipped/cancelled action finalization, fresh remove target directory, formal object member_count, or mixed object+file pagination. | High-risk regressions can pass the current test suite. | Add targeted backend tests before broad beta. |
| P2-01 | P2 | Data model / compose | Removed members reappear as loose but are blocked from managed compose by LOM queries that ignore member_status. | create_managed_compose_plan and _validate_object_creation_move exclude any LibraryObjectMember.file_id, not only active rows. | A file that appears loose may be rejected as "already a member." | Decide policy; if removed means loose, filter only active memberships in compose guards. |
| P2-02 | P2 | Data model | plan_kind and payload_json carry important workflow semantics as free strings/opaque JSON. | organize_plans.plan_kind is String; object creation/amendment dispatch depends on payload_json flags. | Harder to validate, migrate, and diagnose as plan types grow. | Add typed constraints or future explicit relation fields such as source_file_id, added_by_plan_id, removed_by_plan_id. |
| P2-03 | P2 | Layering | Some routes contain workflow or SQL-like logic. | importing.py retry_failed_import calls private service helpers; update_object_candidate loops validation inline; library.py storage summary performs inline aggregation. | Route/service boundaries can drift and become harder to test. | Move orchestration and aggregation into services. |
| P2-04 | P2 | API semantics | get_plan_detail refreshes conflicts and commits during a read. | organize service refresh path updates action conflicts and commits when reading plan details. | GET/read behavior can mutate server state unexpectedly. | Split conflict refresh into explicit command or document this as a refresh endpoint. |
| P2-05 | P2 | Metadata | Managed compose writes type_prefix as OBJ for most object types because the OBJECT_PREFIX map is reversed incorrectly. | _finalize_managed_compose builds prefix_map = {v: k for k, v in OBJECT_PREFIX.items()} then looks up object_type. | Object metadata is less useful and inconsistent with naming intent. | Use OBJECT_PREFIX.get(object_type, "OBJ"). |
| P2-06 | P2 | Recovery | Recovery is not object-member-aware enough for amendment diagnostics. | Recovery covers File-table missing managed files, but not active member path/object-root mismatches or removed member loose-state mismatches. | Post-amendment inconsistencies may require manual DB/FS inspection. | Add diagnostic checks for library_object_members vs files and object roots. |
| P2-07 | P2 | Frontend maintainability | BrowseV2Feature owns too many responsibilities. | One component manages browse filters, pagination, object detail, file detail, selection, compose, add-member, and remove-member state. | Future changes risk regressions and stale UI state. | Split into object detail panel, compose controller, amendment modals, and browse grid subcomponents. |
| P2-08 | P2 | Frontend UX | Add-member modal candidate query is too narrow. | It calls listBrowseCards with storage_state=managed and card_kind=loose_file only; API defaults domain to media. | Users may not see valid docs/apps/assets loose files for add-member. | Query all supported domains or add a dedicated add-member candidate endpoint. |
| P2-09 | P2 | i18n / UX | Raw technical role values and stale copy can appear in UI. | Object detail renders member.role directly; overview readOnlyNotice still says add/remove/compose is later-phase work. | UI can confuse beta testers and suggests incomplete functionality. | Add role label mapping and update stale locale copy. |
| P2-10 | P2 | Frontend tests | No frontend/Playwright/i18n tests were found for Phase 8 UI flows. | No relevant apps/frontend tests directory was present. | UI regressions and raw key regressions may pass CI. | Add smoke tests for browse, object detail, compose modal, amendment modals, and raw key checks. |
| P2-11 | P2 | Documentation | Formal docs contain stale Phase 8 statements. | KNOWN_LIMITATIONS says object amendment add/remove is deferred; ARCHITECTURE lacks Phase 8 plan/member lifecycle details. | Reviewers may misunderstand current capabilities and risks. | Update formal docs after P0/P1 fixes. |
| P3-01 | P3 | Build / performance | Frontend build emits a large chunk warning. | npm run build reports JS chunk over 500 kB. | No current functional failure, but startup performance can degrade. | Consider route-level or vendor code splitting later. |
| P3-02 | P3 | Runtime hygiene | Tests emit deprecation warnings. | pytest reports datetime.utcnow and FastAPI coroutine deprecation warnings. | No current failure; future Python/FastAPI versions may break. | Schedule warning cleanup after beta blockers. |

## 6. P0 / P1 Action Plan

### P0-01: Prevent amendment finalization on skipped/cancelled actions

Required outcome:

- completed_with_errors must not create new members, mark members removed, or update membership-related file state.

Recommended implementation direction:

- Track required amendment move action IDs.
- Finalize amendment only when every required amendment move action is succeeded.
- Treat cancelled/skipped amendment actions as finalization blockers.
- Add tests for one succeeded action plus one cancelled/skipped action.

### P1-01: Make remove-member target directory lifecycle explicit

Required outcome:

- A remove-member plan should work on a fresh object without manually pre-creating Removed_<object_root>.

Recommended implementation direction:

- Add mkdir action for 90_Loose/Removed_<object_root>, or use an already guaranteed existing managed loose directory.
- Add preflight and execute tests where the directory does not exist before plan creation.

### P1-02 and P1-03: Fix Browse v2 card count and pagination correctness

Required outcome:

- Formal object cards show accurate active member_count.
- Browse pages are stable across mixed formal objects, import candidates, and loose files.

Recommended implementation direction:

- Add active member aggregation for library_objects.
- Rework combined pagination or expose separate sections/counts.
- Add tests with many objects and many loose files.

### P1-04: Add critical regression tests

Required outcome:

- The current P0/P1 risks are covered before broad beta.

Recommended tests:

- Amendment skipped/cancelled action does not mutate membership.
- Remove-member plan works when target directory is absent.
- Formal object card member_count reflects active members.
- Mixed object+loose pagination is stable.

## 7. P2 / P3 Improvement Backlog

- Clarify removed-member recompose policy and align compose guards with Browse v2 loose behavior.
- Reduce JSON/free-string reliance for plan semantics as Phase 9 planning begins.
- Move remaining route-level workflow logic into services.
- Make plan-detail reads pure or clearly rename them as refresh operations.
- Fix managed compose type_prefix metadata.
- Add object-member-aware recovery diagnostics.
- Split BrowseV2Feature into smaller feature components.
- Broaden add-member candidate discovery beyond default media domain.
- Add role label mapping and remove stale read-only locale text.
- Add frontend smoke/i18n tests.
- Address frontend chunk size and Python/FastAPI deprecation warnings after beta blockers.

## 8. Test Coverage Matrix

| Flow | Current tests | Coverage | Gap | Priority |
|---|---|---|---|---|
| Browse v2 | test_library_browse_v2_read_model.py | Filters, card kinds, storage state, loose/member exclusion | Formal object member_count and mixed pagination stability | P1 |
| Object detail | test_library_browse_v2_object_detail.py | Active members, metadata fields, not-found behavior | Raw role label presentation not tested | P2 |
| Inbox compose | test_library_v2_compose_inbox.py | Pure DB compose, validation, no FS mutation | Frontend UX not tested | P2 |
| External compose | test_library_v2_compose_external.py | Copy-only, source preservation, rollback, no-overwrite | Removed-member recompose policy not covered | P2 |
| Managed compose plan | test_library_v2_managed_compose_plan.py | Draft creation and validation | Removed-member eligibility mismatch | P2 |
| Managed compose preflight | test_library_v2_managed_compose_preflight.py | Stale path, conflict, member checks | Pagination/count unrelated | -- |
| Managed compose execute | test_library_v2_managed_compose_execute.py | Object creation, path sync, history, journal | type_prefix metadata assertion | P2 |
| Object member status | test_library_v2_object_member_status.py | Active vs removed read model behavior | Removed-member compose eligibility | P2 |
| Amendment plan | test_library_v2_object_amendment_plan.py | Add/remove draft validation, mixed rejection | Remove target dir fresh lifecycle | P1 |
| Amendment preflight | test_library_v2_object_amendment_preflight.py | Add/remove conflicts, stale paths, membership checks | Tests pre-create remove target directory | P1 |
| Amendment execute | test_library_v2_object_amendment_execute.py | Move, add/remove membership, history, no delete | skipped/cancelled action finalization | P0 |
| Path sync | test_library_v2_path_sync.py | Existing path-sync behavior | Object-member-specific recovery | P2 |
| Recovery | test_library_v2_recovery.py | Diagnostic-only import/file checks | Amendment/member diagnostics | P2 |
| Storage scope | test_library_v2_storage_scope.py | Storage filters and summary | Route-level aggregation layering | P2 |
| Frontend build | npm run build | TypeScript/Vite build passes | Component/interaction/raw-key tests missing | P2 |
| Desktop build | npm run build | TypeScript build passes | No desktop E2E around Phase 8 | P2 |

## 9. Data Safety Assessment

### File move

Move operations are plan-driven and protected by preflight checks, stale-path checks, target root checks, and no-overwrite target generation. The residual risk is that FS moves and DB updates are not transactional as a unit.

### Source preservation

External compose is copy-only and uses source preservation. Source cleanup is not implemented. Delete is not implemented in Phase 8 amendment.

### No delete

No Phase 8 amendment path hard-deletes member files. Remove-member marks library_object_members.member_status as removed and moves the file out of the object area.

### Recovery

Recovery is diagnostic-only and covers common File/inbox/import inconsistencies. It does not automatically repair and is not yet deep enough for object-member-specific amendment inconsistencies.

### Rollback limits

DB rollback cannot reverse file-system moves. If a process crashes after FS mutation but before DB finalization, recovery/manual inspection is required. This limit is documented and acceptable for controlled beta only when testers use disposable data.

### completed_with_errors limit

The intended contract is that completed_with_errors does not mutate final object membership. Current amendment code violates this when skipped/cancelled actions exist without failed actions. This is the highest-priority data safety issue.

## 10. Beta Readiness Decision

Decision: YELLOW.

### Conditions

- Fix P0-01 before any broad beta.
- Fix or explicitly mitigate P1-01, P1-02, and P1-03 before external beta users rely on Phase 8 flows.
- Add P1 regression tests before declaring Phase 8 GREEN.
- Continue using disposable local data until recovery and manual acceptance have been re-run after fixes.

### Forbidden during beta

- Do not enable delete.
- Do not enable source cleanup.
- Do not enable mixed add/remove.
- Do not enable automatic rollback/repair.
- Do not add direct preflight/execute UI shortcuts from object detail.
- Do not start scraper/poster wall/AI work before stabilizing Phase 8.

### Tester guidance

- Use disposable files and a disposable managed root.
- Do not manually cancel individual amendment actions in DB or tooling.
- Treat recovery results as diagnostics, not repair instructions.
- Verify object card counts, object detail membership, and loose-file reappearance after every execute.
- For remove-member flows, watch for preflight failure around missing Removed_<object_root> target folders until P1-01 is fixed.

## 11. Recommended Next Steps

1. Fix P0-01 and add the skipped/cancelled amendment finalization regression test.
2. Fix P1 remove-member target directory handling and Browse v2 member_count/pagination correctness.
3. Re-run the Phase 8 backend suites plus frontend and desktop builds.
4. Run the Phase 8 final acceptance checklist manually with disposable data.
5. Update stale formal docs after the code fixes, then hold new feature work until Phase 8 is GREEN.

## Appendix A. Validation Results

Backend validation:

| Command | Result |
|---|---|
| python -m pytest tests/test_library_v2_object_member_status.py -v | 3 passed |
| python -m pytest tests/test_library_v2_object_amendment_plan.py -v | 14 passed |
| python -m pytest tests/test_library_v2_object_amendment_preflight.py -v | 11 passed |
| python -m pytest tests/test_library_v2_object_amendment_execute.py -v | 13 passed |
| python -m pytest tests/test_library_v2_managed_compose_plan.py tests/test_library_v2_managed_compose_preflight.py tests/test_library_v2_managed_compose_execute.py -v | 29 passed |
| python -m pytest tests/test_library_browse_v2_read_model.py tests/test_library_browse_v2_object_detail.py -v | 16 passed |
| python -m pytest tests/test_library_v2_path_sync.py tests/test_library_v2_recovery.py tests/test_library_v2_storage_scope.py -v | 43 passed |
| python -m pytest tests/test_library_v2_compose_inbox.py tests/test_library_v2_compose_external.py -v | 22 passed |

Total specified backend tests: 151 passed.

Build validation:

| Command | Result |
|---|---|
| cd apps/frontend; npm run build | Passed; Vite emitted a chunk-size warning for a JS bundle over 500 kB |
| cd apps/desktop; npm run build | Passed |

Warnings observed:

- Python/FastAPI deprecation warnings during backend tests.
- Vite chunk-size warning during frontend build.

## Appendix B. Scope Confirmation

- No business code changed.
- No test code changed.
- No schema or migration changed.
- No frontend/backend logic changed.
- No formal docs changed.
- No commit created.
- No push performed.

