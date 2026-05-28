# Phase 8 Final Acceptance Checklist

## 1. Scope

### Phase 8 Completed
- Browse v2 (domain taxonomy, object/loose file cards, storage/card filters)
- Object Detail / Member View (read-only, paginated)
- Inbox compose (select inbox loose files → object candidate)
- External compose (copy-only external files → inbox → object candidate)
- Managed compose (draft → preflight → execute → formal object + members)
- Object Amendment add member (draft → preflight → execute → active member)
- Object Amendment remove member (draft → preflight → execute → removed status)
- Object detail plan-only UI (add/remove member buttons)
- member_status soft-deactivate (active/removed)
- Recovery diagnostics (read-only)
- File path history + operation journal for all operations

### Phase 8 NOT Included / Post-Phase 8 Partial
- Mixed add+remove amendment full execute/finalize. Current source accepts mixed draft creation, but finalization still only handles add-only and remove-only.
- Removed member history UI
- Direct preflight/execute UI from object detail
- Delete / trash / recycle bin UI or physical filesystem delete. Current source has backend-only soft trash metadata APIs.
- Source cleanup
- Automatic rollback
- Automatic recovery repair beyond the current safe subset
- Scraper / poster wall / AI

## 2. Acceptance Environment

- Windows local-first app
- Backend (FastAPI + SQLite) running locally
- Frontend (Vite/React) running in dev mode or built
- Desktop (Electron) in dev mode or packaged
- At least one managed library root configured
- Test data prepared per Section 3

## 3. Data Preparation Checklist

- [ ] At least one managed library root configured
- [ ] A set of managed loose files (for add-member testing)
- [ ] A set of inbox loose files (for inbox compose)
- [ ] A set of external loose files (for external compose)
- [ ] At least one formal library_object with members
- [ ] At least one managed loose file NOT in any object (add candidate)
- [ ] At least one active member (remove candidate)
- [ ] Files with duplicate basenames in different directories

## 4. Browse v2 Acceptance

- [ ] Domain buttons (media/documents/apps/assets) work
- [ ] Category tree shows correct items per domain
- [ ] Object cards display with namespaced ID, type badge, member count
- [ ] No raw technical values (import_object_candidate, needs_review, etc.)
- [ ] Loose file cards display with file kind, storage state, size
- [ ] Storage filter (all/external/inbox/managed) works
- [ ] Card kind filter (all/objects/files) works
- [ ] Click loose file → DetailsPanel opens
- [ ] Click object card → object detail loads
- [ ] Empty state message clear
- [ ] Error state message clear
- [ ] No raw i18n keys in Chinese

## 5. Object Detail Acceptance

- [ ] Object header shows display_title, object type, source
- [ ] Object metadata: status, member count, root path
- [ ] Active members listed with role, file kind, storage state badges
- [ ] "Add members" button visible for formal objects
- [ ] "Remove from object" button per member row
- [ ] Member pagination works if > page_size members
- [ ] Removed members not shown in default view
- [ ] Member count consistent with displayed members
- [ ] No stale technical raw values

## 6. Compose Acceptance

### Inbox compose
- [ ] Select inbox loose files via checkbox
- [ ] "Inbox files selected" label correct
- [ ] Compose modal: auto-suggested name/type
- [ ] Submit → object candidate created
- [ ] No file move
- [ ] Candidates appear in object section

### External compose
- [ ] Select external loose files via checkbox
- [ ] "External files selected" label correct
- [ ] Safety notice: "files will be copied to Inbox, source preserved"
- [ ] Submit → copies to Inbox, creates object candidate
- [ ] Source files still exist at original paths

### Managed compose
- [ ] Select managed loose files via checkbox
- [ ] "Managed files selected" label correct
- [ ] Safety notice: "draft plan only, files not moved"
- [ ] Submit → draft plan created, plan ID shown
- [ ] No file move

### General
- [ ] Inbox/external/managed cannot be mixed
- [ ] Selection clears on filter/page change
- [ ] No immediate unexpected file move

## 7. Managed Compose Execute Acceptance

- [ ] draft plan → mark ready
- [ ] preflight passes
- [ ] execute starts, plan status = completed
- [ ] Files moved to target object directory
- [ ] library_object created
- [ ] library_object_members created (active)
- [ ] Files no longer in loose browse
- [ ] Object detail shows new members
- [ ] file_path_history written
- [ ] operation_journal written
- [ ] completed_with_errors: no partial object created

## 8. Add Member Amendment Acceptance

- [ ] Object detail → "Add members" → modal shows managed loose candidates
- [ ] Select a managed loose file
- [ ] Submit → draft amendment plan created, Plan #ID shown
- [ ] "Files have not moved, membership has not changed" feedback
- [ ] No immediate member added to list
- [ ] mark ready → preflight → execute
- [ ] File moves into object directory
- [ ] Active library_object_member created
- [ ] Object detail now shows new member
- [ ] File no longer appears as managed loose
- [ ] file_path_history written
- [ ] operation_journal written

## 9. Remove Member Amendment Acceptance

- [ ] Object detail → member row → "移出对象"
- [ ] Modal wording: "不删除文件, 只创建草案计划"
- [ ] Modal wording: "remove from object, not delete"
- [ ] Submit → draft amendment plan created
- [ ] No immediate member removed from list
- [ ] mark ready → preflight → execute
- [ ] File moves to managed loose area
- [ ] member_status = removed
- [ ] Member no longer in default member list
- [ ] File now appears as managed loose
- [ ] Member row preserved in DB (soft-deactivate)
- [ ] file_path_history written
- [ ] operation_journal written

## 10. Safety Acceptance

- [ ] No delete button anywhere
- [ ] No source cleanup
- [ ] No hard delete of library_object_member
- [ ] completed_with_errors: no membership mutation
- [ ] Failed plan: no finalized state
- [ ] No automatic rollback UI
- [ ] Recovery safe repair is narrow; unsupported finding types remain manual

## 11. Build / Regression

- [ ] All amendment tests pass
- [ ] All managed compose tests pass
- [ ] All browse tests pass
- [ ] All path/recovery/storage tests pass
- [ ] All compose inbox/external tests pass
- [ ] Frontend build: npm run build
- [ ] Desktop build: tsc

## 12. Known Limitations for Beta

- Mixed add+remove amendment execute/finalize not supported
- Removed member history UI not implemented
- Direct preflight/execute UI from object detail not implemented
- Delete / trash UI and physical filesystem delete not implemented
- Source cleanup not implemented
- Automatic rollback not implemented
- Automatic recovery repair only supports the current safe subset
- Scraper / poster wall / AI not implemented

## 13. Pass / Fail Criteria

### Must-pass (blockers)
- [ ] Browse v2 renders without error
- [ ] Compose creates correct candidate/plan (test verified)
- [ ] Managed compose execute creates object + members
- [ ] Amendment execute finalizes membership correctly
- [ ] No hard delete of members
- [ ] completed_with_errors does not mutate membership
- [ ] All backend tests pass
- [ ] Frontend + desktop builds pass

### Acceptable limitations
- No mixed add/remove execute/finalize support
- No direct preflight/execute buttons in object detail
- No removed member history view
- No delete/trash UI or physical delete capability
