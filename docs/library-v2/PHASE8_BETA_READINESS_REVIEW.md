# Phase 8 Beta Readiness Review

## 1. Executive Summary

Phase 8 is **beta-ready for controlled local testing after audit P0/P1 stabilization**. The Browse v2, object detail, compose (inbox/external/managed), and object amendment (add/remove) chains are complete end-to-end. The application is not ready for destructive production use without backups.

**Current recommendation**: GREEN for controlled local beta after audit P0/P1 fixes, using disposable test data first.

## 2. Completed Capabilities

| Capability | Status |
|---|---|
| Browse v2 taxonomy navigation | Complete |
| Object cards + loose file cards | Complete |
| Object detail with paginated member list | Complete |
| Inbox compose (file selection → object candidate) | Complete |
| External compose (copy-only → inbox → candidate) | Complete |
| Managed compose (draft → preflight → execute → formal object) | Complete |
| Object amendment add member (draft → preflight → execute) | Complete |
| Object amendment remove member (draft → preflight → execute) | Complete |
| Object detail plan-only UI (add/remove buttons) | Complete |
| member_status soft-deactivate | Complete |
| file_path_history for all operations | Complete |
| operation_journal for all operations | Complete |
| Recovery diagnostics | Complete |
| Narrow recovery safe repair (post-Phase 8 source update) | Partial: `path_mismatch` and `import_failed_retryable` only |

## 3. Beta Testing Focus

Priority test areas:
1. **Real data import flows**: Import files via source → inbox → review → organize → execute
2. **Object creation**: Managed compose full chain with real files
3. **Add/remove member**: Amendment cycle on real formal objects
4. **Path movement correctness**: Verify file locations after execute
5. **UI clarity**: No raw i18n keys, labels clear in Chinese
6. **Failure handling**: completed_with_errors, stale path, target conflict

## 4. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Path move failure during execute | Medium | completed_with_errors prevents partial mutation; action logs preserved |
| Amendment skipped/cancelled action | Low | Audit fix requires all amendment move actions to succeed and prevents duplicate finalization |
| Removed-member recompose confusion | Low | Audit fix treats only active memberships as compose/amendment blockers |
| Browse card count/pagination drift | Low | Audit fix applies stable combined pagination and active-member counts |
| User misunderstanding plan-only UI | Medium | Plan-only feedback messages explicit: "files not moved yet" |
| No direct preflight/execute UI from object detail | Low | Users must navigate to Library > Plans to execute amendment plans |
| Removed member hidden by default | Low | Soft-delete preserves DB row; member can be inspected directly |
| No automatic rollback | Low | Failed plans leave files in place; manual recovery needed |
| No delete/trash model | Low | Documented as deferred; users warned not to rely on app for deletion |
| Recovery repair is intentionally narrow | Low | Current source only repairs `path_mismatch` and `import_failed_retryable`; all other findings stay manual |

## 5. Recommended Beta Rules

1. Use a **disposable test library** first — not your only copy of data
2. **Backup** before testing amendment and execute operations
3. Do not test on sole copy of valuable files
4. Avoid huge batch operations (100+ files at once)
5. Record before/after screenshots or paths
6. Save logs if anything fails

## 6. Suggested Test Dataset

Prepare:
- 10 images (various formats: jpg, png, webp)
- 5 videos (mp4, mkv)
- 3 documents (pdf, docx, txt)
- Duplicate filenames: `cover.jpg` in two directories
- External source files in a non-managed directory
- Managed loose files in managed root
- A formal object with 5+ members
- One extra managed loose file (add candidate)

## 7. Manual Test Sessions

### Session 1: Browse v2
- Open /browse-v2
- Switch domains (media/documents/apps/assets)
- Verify object cards and loose file cards
- Filter by storage state
- Click loose file → DetailsPanel opens
- Click object → detail loads
- Check Chinese labels

### Session 2: Compose Object
- Inbox: select 3 inbox files → compose → verify candidate created
- External: select 2 external files → compose → verify copy + candidate
- Managed: select 2 managed files → compose → verify draft plan

### Session 3: Managed Compose Execute
- From managed compose draft plan: mark ready → preflight → execute
- Verify: files moved, formal object created, members visible
- Verify: no source deletion, no cleanup

### Session 4: Add Member
- Object detail → Add members → select managed loose file
- Create plan → mark ready → preflight → execute
- Verify: file moved into object, new active member appears

### Session 5: Remove Member
- Object detail → Remove from object
- Create plan → mark ready → preflight → execute
- Verify: file moved to loose area, member_status = removed, no hard delete

### Session 6: Error / Conflict
- Create plan → change file path → preflight should reject
- Create plan → make file a member of another object → preflight should reject
- Create plan → create target conflict → preflight should reject

## 8. Release Decision

### Green criteria (all met after audit P0/P1 fixes)
- [x] All backend tests pass (151+ tests)
- [x] Frontend build passes
- [x] Desktop build passes
- [x] No raw i18n keys
- [x] No hard delete of members
- [x] completed_with_errors prevents partial mutation
- [x] Phase 8 audit P0/P1 regression tests pass

### Yellow criteria (acceptable for beta)
- [x] Manual data-present smoke not yet performed

### Red criteria (none triggered)
- No crashing paths identified
- No data loss paths identified
- No security issues identified

### Current status: **GREEN for controlled local beta testing after audit P0/P1 fixes**
