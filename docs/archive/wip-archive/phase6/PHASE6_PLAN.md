# Workbench Phase 6 Plan

> Date: 2026-05-14 | Status: Planning — no implementation yet

---

## 1. Current Baseline

**Core chain** (find → inspect → tag → refind → browse): fully functional.

| Capability | Status | Test Coverage |
|-----------|--------|---------------|
| Source scanning + file indexing | Complete | Phase 1A/B, Phase 2D |
| Metadata extraction | Complete | Phase 2A |
| Search with filters | Complete | Phase 2A, 2C |
| File details (thumbnail, preview, metadata) | Complete | Phase 2B |
| Tags + color tags CRUD | Complete | Phase 3A, 3B, 6B |
| Collections | Complete | Phase 2E |
| Recent / recent-tagged / recent-color-tagged | Complete | Phase 5B, 7C |
| Media library browse | Complete | Phase 5A |
| Books library browse | Complete | Phase 3A |
| Software library browse | Complete | Phase 3B |
| Games library browse | Complete | Batch 1, 3 |
| Library objects scan + list | Complete | Phase 2 objects |
| Library organize (candidates, suggestions, plans) | Complete | Phase 3, 5D |
| Plan execution (mkdir, move, rename, asset.yaml) | Complete | Phase 5A-D |
| Reconcile / rollback / copy failed / asset merge | Complete | Phase 5A-D |
| Managed library roots | Complete | H1 (hardened) |
| Rule-based suggestions | Complete | Phase 5D-3 |
| Built-in templates | Complete | Phase 5D-2 |
| Batch organize (tag, color, placement) | Complete | Phase 7A |
| User meta (favorite, rating, placement) | Complete | Phase 7B |
| Tools (video merge) | Complete | Tools plan |
| Settings (language, theme, system status) | Complete | — |
| Electron desktop shell | Complete | Packaging configured |
| Frontend design rewrite | Complete | design.pen merged |
| Frontend architecture cleanup | Complete | Library/DetailsPanel/CSS split |
| Query invalidation helpers | Complete | Centralized |
| Backend hardening H1-H4 | Complete | +31 safety tests |
| Onboarding page | Route exists | Unknown implementation status |

**Test totals**: 40 backend test files (~200+ tests), 0 frontend tests.

---

## 2. Phase 6 Goal

**Beta stabilization — make Workbench safe and usable for real personal media libraries.**

Phase 6 is not about building new features. It is about hardening what exists so that a beta user can:

1. Install and launch the app without manual setup
2. Register their media folders as sources without confusion
3. Browse, search, tag, and organize files without crashes or data loss
4. Understand what the app is doing and what it will NOT do
5. Report bugs with enough context for us to triage

---

## 3. Recommended Phase 6 Scope

### 3.1 Beta Stabilization (Priority: P0)

**Why**: The app has never been tested by anyone outside development. Edge cases in real libraries (huge folders, mixed content, broken files, unusual paths) will surface immediately.

**Tasks**:
- Create a manual QA checklist covering all 15 pages + all organize phases
- Run a large-library smoke test (10K+ files, mixed types, nested directories)
- Classify all known `# TODO`, `FIXME`, and bare exception handlers
- Review all error states: what does the user see when things fail?
- Add frontend error boundaries for unexpected crashes
- Verify light mode is usable (development focused on dark theme)

**Affected files**: tests/smoke, frontend error boundaries, logging

**Risk**: Low — no behavioral changes, just verification and triage

**Acceptance**: QA checklist with 100% pass rate on a clean Windows machine

### 3.2 Large Library Performance (Priority: P1)

**Why**: Current testing uses small temp directories. Real libraries have 10K-100K files. Slow scans, UI freezes, and memory issues will be the first thing beta users notice.

**Tasks**:
- Profile source scan on a 50K-file directory tree
- Profile search/list with pagination on 10K+ results
- Check frontend rendering with many rows (virtualization if needed)
- Check thumbnail warmup behavior with many video files
- Verify SQLite query plans for hot paths (file list, search, recent)
- Add basic SQLite indexes if EXPLAIN QUERY PLAN shows missing ones

**Affected files**: scanning service, search routes, file repository, thumbnail service, frontend list components

**Risk**: Medium — performance changes could affect correctness

**Acceptance**: 50K-file source scan completes in < 60s, search results render in < 2s

### 3.3 UX Polish (Priority: P1)

**Why**: The design.pen rewrite gave the app a unified visual language, but some states and transitions are rough. Beta users will judge the app on fit-and-finish.

**Tasks**:
- Empty-state consistency: all list pages show the same EmptyState pattern
- Loading-state consistency: skeleton or spinner, not raw "Loading..." text
- Error-state consistency: actionable error messages, not stack traces
- Light/dark mode: audit all pages for contrast and readability
- First-run experience: what does the user see with zero sources, zero files?
- Thumbnail fallbacks: corrupted video → placeholder, not broken image icon
- Path display: truncation, tooltips, copy-to-clipboard
- Navigation: active state preservation, back-button behavior

**Affected files**: frontend CSS, feature components, EmptyState/Skeleton shared components

**Risk**: Low — visual-only changes

**Acceptance**: All 15 pages pass a manual UX checklist in both light and dark modes

### 3.4 Packaging / Release Readiness (Priority: P1)

**Why**: The electron-builder pipeline exists but has never been exercised for a release. Beta users need a one-click install.

**Tasks**:
- Verify `npm run package:win` produces a working NSIS installer
- Verify the packaged app starts, creates data directory, and reaches the home page
- Verify FFmpeg bundling works in the packaged app (needed for video thumbnails)
- Set safe defaults: data directory, allowed origins, log level
- Remove dev artifacts from packaged build (source maps, dev-only deps)
- Add version display in Settings or titlebar
- Create a first-run wizard or onboarding page if the current one is incomplete

**Affected files**: desktop package.json, electron-builder config, main.ts, preload.ts, settings

**Risk**: Medium — packaging bugs can produce non-functional builds

**Acceptance**: Installer runs on clean Windows machine, app launches and indexes a test folder

### 3.5 Documentation (Priority: P2)

**Why**: Beta testers need to know what the app does, what it doesn't do, and how to recover from problems.

**Tasks**:
- User guide: what is a source, a managed root, an organize plan?
- Beta tester checklist: step-by-step walkthrough of the core chain
- Known limitations: what file types, path patterns, and workflows are unsupported
- Recovery instructions: how to handle a crashed plan, a corrupted thumbnail, a missing file
- Scope document: what Phase 6 will NOT do (no AI, no cloud, no media player, etc.)

**Affected files**: docs/

**Risk**: None — documentation only

**Acceptance**: Beta tester can complete the core chain using only the documentation

---

## 4. Explicit Non-goals

- **No Explorer replacement**: Workbench is a library organizer, not a file manager
- **No game platform / launcher**: Game status tracking only; no launching, no Steam integration
- **No document reader / editor**: Books/software metadata only; no EPUB reader, no PDF editor
- **No software installer**: Software metadata only; no .exe/.msi execution
- **No real AI auto-classification**: Rule-based suggestions only; no LLM, no cloud AI, no training
- **No cloud / provider / LLM platform**: Fully local; no API keys, no network services
- **No plugin system**: No extension points, no third-party integrations
- **No operation journal**: Not needed at current risk level (see H5 assessment)
- **No full organize.py decomposition**: Remaining extraction is diminishing returns (see H4 status review)
- **No complex permission system**: Single-user local app; no auth, no roles, no multi-tenancy
- **No Phase 5 business logic rewrite**: organize workflow, suggestions, templates are stable
- **No new features outside the core chain**: find → inspect → tag → refind → browse

---

## 5. Candidate Workstreams (Detail)

### A. Beta Stabilization

| Task | Effort | Files |
|------|--------|-------|
| Manual QA checklist | 1 day | New doc |
| Error boundary audit | 1 day | Frontend features |
| Light mode audit | 0.5 day | CSS tokens, components |
| Logging review | 0.5 day | Backend routes, services |
| First-run smoke test | 0.5 day | Full stack |

### B. Large Library Performance

| Task | Effort | Files |
|------|--------|-------|
| Scan profiling | 1 day | Scanning service |
| SQLite index review | 0.5 day | Models, migrations |
| List pagination stress test | 0.5 day | File repository, frontend lists |
| Thumbnail warmup profiling | 0.5 day | Thumbnail service, warmup hook |

### C. UX Polish

| Task | Effort | Files |
|------|--------|-------|
| Empty/loading/error state pass | 2 days | All feature components, shared EmptyState |
| Light/dark consistency | 1 day | CSS tokens, shell, components |
| Thumbnail fallback hardening | 0.5 day | useRetryingThumbnail, DetailsPanel |
| Path display improvements | 0.5 day | KeyValueRow, FileRow, DetailsPanel |
| Navigation polish | 0.5 day | AppSidebar, router |

### D. Packaging / Release Readiness

| Task | Effort | Files |
|------|--------|-------|
| Release build verification | 1 day | Desktop package.json, electron-builder |
| Safe defaults audit | 0.5 day | Settings, main.ts |
| Dev artifact cleanup | 0.5 day | Build config |
| Onboarding page completion | 1 day | OnboardingFeature (if incomplete) |

### E. Documentation

| Task | Effort | Files |
|------|--------|-------|
| User guide | 1 day | New docs |
| Beta tester checklist | 0.5 day | New docs |
| Known limitations | 0.5 day | New docs |
| Recovery instructions | 0.5 day | New docs |

---

## 6. Recommended Implementation Order

### Step 1: Beta Stabilization Foundation (2 days)

**Task**: Create QA checklist, audit error states, verify build

**Scope**: Read-only — no code changes. Run the app end-to-end. Document what works and what doesn't.

**Files**: New docs, smoke test script

**Tests**: `python -m unittest discover -s tests -v` (all backend), `npm run build` (frontend)

**Acceptance**: QA checklist with known issues categorized by severity

### Step 2: Packaging Verification (1 day)

**Task**: Verify `npm run package:win` produces a working installer. Fix packaging bugs.

**Scope**: Desktop/Electron only. No backend/frontend logic changes.

**Files**: `apps/desktop/package.json`, `electron-builder.yml`, `main.ts`, `preload.ts`

**Tests**: Install on clean machine, launch, register a test source, verify core chain

**Acceptance**: Packaged app starts, scans, browses, and organizes without errors

### Step 3: Large Library Performance (2 days)

**Task**: Profile and fix the biggest performance issues for 50K-file libraries.

**Scope**: Backend scanning + query optimization. Frontend rendering only if profiling shows issues.

**Files**: Scanning service, file repository, search routes, SQLite (indexes only if needed)

**Tests**: Existing backend tests must pass. New performance smoke test with 50K temp files.

**Acceptance**: 50K-file scan < 60s, search < 2s, browse < 1s per page

### Step 4: UX Polish — Empty/Loading/Error States (1.5 days)

**Task**: Consistent empty/loading/error states across all 15 pages.

**Scope**: Frontend CSS + components only. No backend changes.

**Files**: Shared EmptyState, feature components, components.css

**Tests**: `npm run build`, visual smoke test on all pages

**Acceptance**: Every page shows a consistent state for: no data, loading, error, and normal data

### Step 5: UX Polish — Light/Dark + Thumbnail + Navigation (1 day)

**Task**: Light mode audit, thumbnail fallback hardening, navigation polish.

**Scope**: Frontend CSS + thumbnail hook + sidebar only.

**Files**: CSS tokens, shell.css, components.css, useRetryingThumbnail, AppSidebar

**Tests**: Visual smoke test in both themes

**Acceptance**: All pages readable in light mode. Corrupted video shows placeholder, not crash.

### Step 6: Documentation (1.5 days)

**Task**: Write user guide, beta tester checklist, known limitations.

**Scope**: Docs only.

**Files**: New docs under `docs/` or `docs/_wip/phase6/`

**Acceptance**: A new user can complete the core chain using only the documentation

---

## 7. Testing Strategy

### Backend
```bash
cd apps/backend
python -m unittest discover -s tests -v
```
All ~200+ backend tests must pass. No regressions.

### Frontend
```bash
cd apps/frontend
npm run build
```
Build must succeed with zero errors. CSS size monitored for unexpected growth.

### Smoke Tests
- All 15 pages load without JavaScript errors
- Core chain: create source → scan → search → select file → add tag → add color tag → set favorite → Library → scan candidates → generate plan → preflight → execute → reconcile
- Light + dark mode on Home, Search, Library, Settings
- Error states: invalid file ID, missing source, disabled root, corrupted video thumbnail

### Large Library Test
- Create temp directory with 50K files (mixed types: video, image, document, archive, other)
- Register as source, scan, verify all files discovered
- Search with filters, verify pagination works
- Library organize: scan candidates, generate plan, preflight (no execute needed)

### File Operation Safety
- Verify organize execution creates no orphan files
- Verify rollback plan generation does not modify filesystem
- Verify asset YAML merge creates backup before update
- Verify startup recovery marks stale plans but does not touch files

---

## 8. Risk Register

| Risk | Severity | Phase 6 Must Fix? | Notes |
|------|----------|-------------------|-------|
| Cross-volume move atomicity | Low | No | Edge case; defer to post-Phase 6 |
| Huge source scan performance | Medium | **Yes** | First thing beta users do is scan |
| Thumbnail corrupted media | Medium | **Yes** | Already handled (404, not crash); verify in QA |
| Electron open/show in folder | Low | No | Works on dev machine; verify in packaging |
| Organize execution interruption | Low | No | H2 handles stale plans; preflight + confirm gate |
| UI regressions from design rewrite | Low | **Yes** | Audit in Step 4/5 |
| Onboarding page incomplete | Medium | Check in Step 2 | Route exists; verify implementation |
| First-run with zero sources | Low | **Yes** | Empty states audit in Step 4 |
| Light mode contrast | Low | **Yes** | Audit in Step 5 |
| Frontend no test infrastructure | Medium | No | Accept for beta; add vitest post-Phase 6 |

---

## 9. Final Recommendation

**Phase 6 should start from Workstream A: Beta Stabilization.**

The first concrete task: create a manual QA checklist by running the full core chain end-to-end and documenting every step, every state, and every edge case. No code changes — pure observation.

**Do NOT do H4-Step3 or H5 before Phase 6.** They are low-risk deferrals. The current organize.py state is stable and well-tested. Move atomicity is an edge case. Neither blocks beta stabilization.

**Phase 6 can enter implementation immediately.** The plan is a guide, not a gate. Start with Step 1 (QA checklist) today. All P0 hardening is complete.

**Phase 6 estimated total**: ~9 days of focused work across all 6 steps.
