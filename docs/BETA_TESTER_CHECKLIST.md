# Workbench Beta Tester Checklist

Use this checklist when testing Workbench. Run the entire checklist on a **test folder with disposable files** first. Do not use your real library for the organize steps.

---

## 1. Test Environment

| Item | Value |
|------|-------|
| Windows version | |
| Install method (installer / unpacked / dev) | |
| App version or git commit | |
| Test source path | |
| Managed root path | |
| Approximate file count in source | |

---

## 2. Installation / Launch

- [ ] App installs without errors (or dev server starts)
- [ ] App launches to a non-blank page
- [ ] Open Settings → system status shows `database: ok`
- [ ] No JavaScript errors in console
- [ ] Sidebar shows 12 navigation items
- [ ] DetailsPanel shows "Select an item to load its shared details"

---

## 3. Source Setup

- [ ] Add a source folder (Settings → Sources)
- [ ] Source appears in the source list with "Enabled" status
- [ ] Click "Scan" — scan starts
- [ ] Scan completes (check status in Settings or system status)
- [ ] File count increases after scan (check in Search)
- [ ] No crash during or after scan

---

## 4. Find / Inspect

- [ ] Search page loads
- [ ] Search results show files from the scanned source
- [ ] Filter by file type (e.g., image, video) narrows results
- [ ] Click a file — DetailsPanel shows file info
- [ ] Path, size, type, timestamps are displayed
- [ ] Preview/thumbnail shows (or shows a fallback message for unsupported files)
- [ ] Metadata section shows (or shows "No extracted metadata available")
- [ ] Click a different file — DetailsPanel updates

---

## 5. Tag / Refind

- [ ] Add a tag to a file (DetailsPanel → Tags section)
- [ ] Tag appears in the file's tag list
- [ ] Remove the tag
- [ ] Add a color tag (red, yellow, green, blue, or purple)
- [ ] Color tag changes are reflected
- [ ] Clear the color tag
- [ ] Mark file as favorite
- [ ] Set a rating (1-5)
- [ ] Clear the rating
- [ ] Go to Recent — file appears in recent list
- [ ] Go to Tags — tag browser shows files by tag
- [ ] Go to Collections — collections page loads (may be empty if no collections match)

---

## 6. Library Organize (TEST FOLDER ONLY)

**WARNING**: The following steps move files on disk. Use only a disposable test folder.

### Prepare
- [ ] Go to Library → Managed Roots
- [ ] Create a managed root (select a test output folder)
- [ ] Go to Library → Pending
- [ ] Click "Scan Candidates"
- [ ] Candidates appear in the list
- [ ] Select one or more candidates

### Generate & Review
- [ ] Click "Generate Plan"
- [ ] Plan appears in the plan list (Library → Plans)
- [ ] Select the plan — plan detail shows
- [ ] Check actions: source_path, target_path, action_type
- [ ] Confirm no unexpected actions

### Preflight & Execute
- [ ] Click "Mark Ready"
- [ ] Click "Preflight"
- [ ] Preflight shows `can_execute: true`
- [ ] If blocked: read the reason, fix the issue (e.g., target exists), re-mark ready and preflight
- [ ] Click "Execute" and confirm
- [ ] Plan status changes from "executing" to "completed"
- [ ] Verify files moved to managed root (check in Windows Explorer)
- [ ] Verify original files no longer in source

### Reconcile & Rollback
- [ ] Click "Reconcile"
- [ ] Reconcile shows status for each action (matched, target_missing, etc.)
- [ ] Click "Generate Rollback" (in the Phase 5 section)
- [ ] A new draft rollback plan appears
- [ ] Rollback plan status is "draft" — has NOT been executed
- [ ] Source plan is unchanged

---

## 7. Visual / UX

- [ ] Light mode: text readable, buttons visible, select/input styled
- [ ] Dark mode: text readable, buttons visible, select/input styled
- [ ] Sidebar: active page highlighted, hover states work
- [ ] DetailsPanel: all sections render without overflow or truncation
- [ ] Empty states: pages with no data show clear messages (not blank)
- [ ] Error states: error messages are readable (not raw stack traces)
- [ ] Navigation: clicking sidebar items loads the correct page

---

## 8. Multi-Page Smoke

- [ ] Home — loads, no errors
- [ ] Search — loads, filters work
- [ ] Library Overview — loads
- [ ] Library Managed Roots — loads, add form works
- [ ] Library Objects — loads
- [ ] Library Pending — loads, scan works
- [ ] Library Plans — loads, plan list and detail work
- [ ] Documents / Books — loads
- [ ] Media — loads, grid/table toggle works
- [ ] Games — loads
- [ ] Software — loads
- [ ] Recent — loads
- [ ] Tags — loads
- [ ] Collections — loads
- [ ] Tools — loads
- [ ] Settings — loads, system status works
- [ ] Onboarding — loads

---

## 9. Bug Report Template

Copy this for each bug found:

```
**Severity**: P0 (data loss/crash) / P1 (feature broken) / P2 (UX issue) / P3 (cosmetic)

**Page**: (e.g., Search, Library Plans, DetailsPanel)

**Steps to reproduce**:
1.
2.
3.

**Expected**:

**Actual**:

**Screenshot / log**:

**Test folder or real folder**:

**Was file operation executed?** (yes / no)

**Additional notes**:
```
