# Library Organize Conflict Resolution Plan

> Date: 2026-05-14 | Type: Design Plan | Phase: Pre-implementation

---

## 1. Problem

After preflight, users encounter blocked/warning actions (target exists, path too long, classification wrong) with no in-app resolution path. The current workflow forces users to:

1. Leave the app
2. Open Windows Explorer
3. Manually rename/move/delete files
4. Return to the app
5. Re-scan sources
6. Re-generate the organize plan

This is friction-heavy and error-prone. The app should provide in-app conflict resolution for the most common preflight issues.

## 2. Current System Findings

### 2.1 Classification Rules — Where They Live

**File:** `apps/backend/app/core/classification.py` (149 lines)

This is the single authoritative file for all file extension → type mappings. It is entirely hardcoded Python — no config file, no database table, no user-editable mapping.

Extension sets defined:
| Set | Extensions |
|-----|-----------|
| `VIDEO_EXTENSIONS` | `avi, m4v, mkv, mov, mp4, mpeg, mpg, webm, wmv` |
| `AUDIO_EXTENSIONS` | `flac, mp3, ogg, wav` |
| `EXECUTABLE_EXTENSIONS` | `exe` |
| `INSTALLER_EXTENSIONS` | `appx, msi, msix` |
| `IMAGE_EXTENSIONS` | `bmp, gif, jpeg, jpg, png, svg, tif, tiff, webp` |
| `DOCUMENT_EXTENSIONS` | `csv, doc, docx, md, odp, ods, odt, ppt, pptx, rtf, txt, xls, xlsx` |
| `ARCHIVE_EXTENSIONS` | `7z, gz, rar, tar, zip` |

A separate file `apps/backend/app/services/library/object_parser.py` defines its own extension sets for object packaging (video, image, subtitle, document), used by `organize.py`'s `_detect_file_type` function.

### 2.2 Why .bat Is Classified as "video" (in user report)

In the current codebase, `.bat` is correctly classified as `"other"` in `classification.py` and `"unknown"` in `organize.py`'s `_detect_file_type`. If users see `.bat` classified as "video", the likely causes are:

- **(a) Data residue**: A prior code version had a bug where `.bat` was included in a video extensions set. If the database was not re-scanned after the fix, old `file_type: "video"` values persist.
- **(b) `_detect_file_type` fallback**: In `organize.py` line 1862, `_detect_file_type` uses its own extension sets (imported from `object_parser.py`). If a `.bat` file appears inside a directory that has other video files, it might be picked up by the folder-name-based object scanner rather than the extension-based classifier.
- **(c) No `.bat` entry exists in any classification set**: `.bat` falls through to `FILE_KIND_OTHER` in `classify_file()`, and to `"unknown"` in `_detect_file_type()`. The actual observed "video" classification must come from pre-existing database state or a now-fixed code path.

**Recommended short-term fix for .bat:**
Add `.bat` (and `.cmd`, `.ps1`, `.sh`, `.py`) explicitly to `classification.py` under a new or existing kind. The cleanest approach:
- Add `"bat", "cmd", "ps1", "sh", "py"` to a new `SCRIPT_EXTENSIONS` set
- Map `SCRIPT_EXTENSIONS` to `FILE_KIND_EXECUTABLE` or a new `FILE_KIND_SCRIPT`
- Map placement to `PLACEMENT_SOFTWARE`

This is a 5-line change in `classification.py` with zero schema impact.

### 2.3 Plan/Action Data Structures

**Current modify capabilities:**

| Action | Draft Plan | Ready Plan | Notes |
|--------|-----------|------------|-------|
| Modify `action.target_path` | YES (PATCH /actions/{id}) | NO | Only draft plans allow edits |
| Modify `action.payload_json` | YES | NO | |
| Cancel plan → candidates reset to pending | YES | YES | `cancel_plan` resets candidates |
| Regenerate plan | NO | NO | Must cancel + re-generate manually |
| Candidate overrides | NO | NO | No override fields exist on OrganizeCandidate |
| Update plan title/summary | YES (PATCH /plans/{id}) | NO | |

**Key limitation:** `update_action` only works on draft plans. Once a plan is `ready`, action edits are rejected with HTTP 400. Preflight results are cleared in the frontend (`setPreflightResult(null)`) on any action edit.

**No candidate override fields exist.** The `OrganizeCandidate` model has `detected_type`, `display_name` but no `override_type`, `override_title` columns. Suggestions exist (`OrganizeSuggestion`) but are not consumed during action generation.

### 2.4 Path Handling

- `PATH_LENGTH_WARNING = 240` (organize.py:73) — warning-only, never blocks execute
- `_safe_title()` replaces Windows-illegal chars, collapses whitespace
- `_target_filename()` generates `Safe Title (2024).mkv` from display name + original extension
- **Templates control directory paths only** — filenames are always generated from display name
- Path containment is checked via `is_path_within()` at preflight time

## 3. Conflict Types

| Type | Severity | Example | Current Resolution |
|------|----------|---------|-------------------|
| **A1** — Target directory exists | warning | mkdir target already exists | Accept existing dir (non-blocking) |
| **A2** — Target file exists | blocked | move target exists | Must fix manually outside app |
| **A3** — asset.yaml exists | blocked | write_asset_yaml target exists | Must use merge flow or fix manually |
| **B** — Path too long | warning | ≥240 chars | No in-app shortening |
| **C** — Classification wrong | N/A (pre-plan) | .bat classified as video | Must manually classify, re-scan |
| **D** — Source missing | stale | Source file deleted | Must investigate outside app |

## 4. Same-name / Existing Target Handling

### A1. Target Directory Exists (warning)

Current: `"warning"` with message `"Target directory already exists."` Does not block execute.

**Recommendation:** Preserve current behavior. Show as warning. Let user proceed. This is a common case (re-organizing into an existing library tree). Add explanatory text: "This directory already exists. Files will be placed into it. This is usually safe."

### A2. Target File Exists (blocked)

Current: `"blocked"` with message `"Target path already exists and would be overwritten."` Blocks execute.

**Proposed resolution options (in-app):**

1. **Rename incoming** — Modify the target filename to include a suffix
   - Auto-suggest: `name (1).ext`, `name - copy.ext`
   - User can type custom name
   - Requires: ability to edit `target_path` on the action (currently only on draft plans)
   
2. **Choose different target folder** — Modify the target directory path
   - User picks a different subfolder within the managed root
   - Requires: ability to edit `target_path` on the action

3. **Skip this action** — Mark as cancelled
   - The action is cancelled; dependent actions (write_asset_yaml for same dir) would be dependency-skipped
   - **Risk**: Requires action exclude UX and dependency-scoped skip. Currently in frontend-only stage.

**Recommendation for Phase B:** Enable `target_path` editing on ready plans (relax the "draft only" guard to "draft or ready"), with mandatory re-preflight after any edit. This is the lowest-cost change.

### A3. asset.yaml Exists (blocked)

Current: `"blocked"` — will not overwrite.

**Resolution:** This is a special case. The user may:
- Use the existing `generate_asset_yaml_merge` flow (creates backup + merge plan)
- Accept that the yaml already exists (no-op — mkdir already handled, move already handled, yaml is final step)

**Recommendation:** Show an explicit "Use merge flow" button next to blocked asset.yaml actions. No new API needed — `generate_asset_yaml_merge` already exists.

## 5. Long Path Handling

### Current State

`PATH_LENGTH_WARNING = 240` characters. The check is `len(str(target)) >= 240` → `conflict_status = "warning"`. It never blocks execution. The actual Windows limit is 260 characters for the full path including drive letter.

### Proposed Resolution

**In the path preview, when a path is ≥240 chars:**

1. **Show path length** — Display "Path length: 248 / 240 chars (Windows limit: 260)"
2. **Offer shortening options:**
   - **Auto-shorten title**: Truncate `_safe_title` output to N chars (e.g., 40 chars max)
   - **Remove year suffix**: Drop ` (2024)` from folder/filename
   - **Use short prefix**: `[M]` instead of `[MOVIE]`
   - **Flatten hierarchy**: Skip intermediate directories if using template
3. **Let user manually edit** — Edit the target name inline

**Implementation approach:** 
- The auto-shorten logic would live in `_target_filename` or be a new utility
- Manual edit would use existing `PATCH /actions/{id}` (draft only currently)
- A "short name mode" template variant could be offered

**Recommendation:** Phase B — add path length display and manual edit. Phase C — add auto-shorten logic.

## 6. Classification Rule Handling

### Immediate Fix: .bat Classification

Add script extensions to `apps/backend/app/core/classification.py`:

```python
SCRIPT_EXTENSIONS = frozenset({"bat", "cmd", "ps1", "sh", "py", "rb", "pl"})
```

Map to `FILE_KIND_EXECUTABLE` with `PLACEMENT_SOFTWARE`. This is a one-file, backward-compatible change.

### Medium-term: User-Configurable Classification

**Option A — JSON config file**

```
config/file_classification_rules.json
```

```json
{
  "extensions": {
    ".bat": "software",
    ".cmd": "software", 
    ".ps1": "software",
    ".mkv": "video",
    ".mp4": "video"
  }
}
```

Priority: user config > hardcoded defaults.

**Option B — Database-backed**

A `classification_rules` table with `extension`, `file_kind`, `auto_placement` columns. Allows per-extension overrides. Needs a UI to manage.

**Option C — Inline inline editing in UI**

Allow changing `file_type` / `file_kind` on individual files via the DetailsPanel or a batch operation. No global rule change — just per-file overrides.

**Recommendation:**
- **Phase A**: Hardcode fix for `.bat` / `.cmd` / `.ps1` now
- **Phase C**: JSON config file with simple UI toggle
- **Phase D**: Database-backed with full rule editor

## 7. In-app Fix + Refresh Plan Workflow

### The Core Idea

```text
User sees blocked/warning in path preview
  → User applies fix in-app (rename, reclassify, etc.)
  → Plan refreshes affected actions
  → User re-runs preflight
  → Preflight passes → Execute
```

### Option A — Cancel + Regenerate (Current, Safe)

**Flow:** Cancel plan → candidates back to pending → fix classification/rules → regenerate

**Pros:** Safe, uses existing code paths. No new APIs needed.
**Cons:** Loses all manual action edits. User must re-select candidates. Multi-step.

**Verdict:** Already works. Frontend guidance can improve this ("Cancel & Regenerate" button with explanation).

### Option B — Edit Draft Actions (Needs Small Backend Change)

**Flow:** Stay in draft → edit action target_path → re-mark-ready → re-preflight

**What exists:** `PATCH /actions/{id}` already allows target_path edit on draft plans. Frontend already supports inline editing (editable when `plan.status === "draft"`).

**What's needed:** 
1. Relax `update_action` guard from `status != "draft"` to `status in {"draft", "ready"}` 
2. On ready plan edit: set plan.status back to "draft", clear confirmed_at
3. Frontend already clears preflightResult on edit — correct

**Safety:** Editing a ready plan's action must reset plan to draft and invalidate preflight. Mark-ready must run again before execute.

**Verdict:** Small backend change (1 guard relaxation + 1 status reset). High user value.

### Option C — Candidate Overrides + Regenerate Actions (Needs Schema)

**Flow:** User sets override on candidate → "Refresh Plan" regenerates actions for that candidate

**What's needed:**
- New `candidate_overrides` table or `override_json` column on `OrganizeCandidate`
- Override fields: `object_type`, `display_title`, `target_name`, `template_key`
- New endpoint: `POST /plans/{id}/refresh` that rebuilds actions from candidates, respecting overrides
- `_build_actions_for_plan` must read overrides when generating actions

**Pros:** Most architecturally clean. Preserves template generation logic. Overrides persist across plan generations.
**Cons:** Requires schema change + new endpoint. More implementation work.

**Verdict:** Defer to Phase D. Too much for beta.

### Option D — Rule Update + Re-scan (Systemic)

**Flow:** Update classification rules → re-scan sources → objects re-detected → generate new plan

**Verdict:** For systemic classification fixes (like adding `.bat` to software). Not for per-file conflicts.

### Recommended Phasing

| Phase | What | When |
|-------|------|------|
| **Phase A** | Hardcode `.bat`/`.cmd`/`.ps1` fix, preflight guidance text, copy path | Now |
| **Phase B** | Relax draft guard → edit target_path on ready plans, auto re-draft + mandatory re-preflight | Next |
| **Phase C** | JSON classification config, path auto-shorten, inline rename dialog | Mid-term |
| **Phase D** | Candidate overrides + refresh plan, database-backed rules, rule editor | Long-term |
| **Phase E** | Safe subset execution, action exclusion, conflict resolver dialog, operation journal | Future |

## 8. Short-term Plan (Phase A)

### 8.1 Fix .bat Classification

**File:** `apps/backend/app/core/classification.py`

Add script extensions and map them to `FILE_KIND_EXECUTABLE` / `PLACEMENT_SOFTWARE`:

```python
SCRIPT_EXTENSIONS = frozenset({"bat", "cmd", "ps1", "sh", "py", "rb", "pl"})

# In classify_file(), after the shortcut check, before the document check:
if ext in SCRIPT_EXTENSIONS:
    return FILE_KIND_EXECUTABLE, PLACEMENT_SOFTWARE
```

Also update `_detect_file_type` in `organize.py` to handle scripts:

```python
if extension in {".bat", ".cmd", ".ps1", ".sh", ".py"}:
    return "software", "low", "Detected as script/executable file."
```

### 8.2 Preflight Guidance Text

In the preflight notice bar (already enhanced in the UX implementation):
- For `target_exists` blocked actions: suggest "Rename target, choose different folder, or cancel and re-generate"
- For `source_missing` stale actions: suggest "Source file may have been moved or deleted. Verify in Explorer."
- For path length warnings: suggest "Consider shortening the title or using a flatter directory structure"

### 8.3 Copy Path Buttons

Add "Copy source path" and "Copy target path" buttons to action rows (next to existing path display). Use `navigator.clipboard.writeText()` — no backend needed. This lets users quickly copy paths for use in Explorer.

## 9. Medium-term Plan (Phase B/C)

### 9.1 Enable target_path Editing on Ready Plans

**Backend change** in `organize.py` `update_action`:
```python
# Before:
if plan.status != "draft": raise HTTPException(400, "Only draft plan actions can be edited.")

# After:
if plan.status not in {"draft", "ready"}: raise HTTPException(400, "Only draft or ready plan actions can be edited.")
```

**Additional:** If plan is `ready` and an action is edited:
- Set plan.status back to `"draft"`
- Clear `plan.confirmed_at`
- The plan must go through `mark_ready` → `preflight` again before execute

**Frontend:** Already supports inline editing when `editable={detail.plan.status === "draft"}` (PlanDetailPanel.tsx line 50). Change to `editable={["draft", "ready"].includes(detail.plan.status)}`.

**Safety:** The `_refresh_action_conflict` is already called on every edit, which checks path containment, target exists, and path length. The plan reverts to draft, so re-preflight is mandatory.

### 9.2 Path Length Display and Auto-shorten

**Frontend:** In PlanActionRow, when `conflict_status === "warning"` and message mentions path length:
- Show `Math.max(0, 260 - path.length)` as "chars remaining"
- Show a color bar (green > 20, amber 10-20, red < 10)

**Backend:** New utility `_shorten_target_path()`:
```python
def _shorten_target_path(target: Path, max_len: int = 220) -> Path:
    """Shorten each component of a path to fit within max_len total."""
    parts = list(target.parts)
    # Strategy: truncate the last component (filename/foldername) first
    # Keep directory structure intact, only shorten the leaf
    ...
```

### 9.3 Manual Classification Override

**Frontend:** In candidate list or PlanDetail, add a dropdown to change `detected_type` for a candidate. Options: movie, anime, game, course, imgset, docset, clip, software, other.

**Backend:** Extend `update_action` or add a new `PATCH /candidates/{id}` endpoint to allow `detected_type` override. Store in a new `override_detected_type` column or reuse the suggestion system.

## 10. Deferred Advanced Features (Phase D/E)

| Feature | Phase | Notes |
|---------|-------|-------|
| Candidate overrides table | D | `candidate_overrides` table with `object_type`, `display_title`, `target_name`, `template_key` |
| Refresh plan endpoint | D | `POST /plans/{id}/refresh` — regenerates actions for one or all candidates |
| DB-backed classification rules | D | `classification_rules` table + CRUD UI |
| Rule editor UI | D | Settings page with extension-to-type mapping |
| Safe subset execution | E | Execute only non-blocked actions, skip blocked |
| Action exclusion toggle | E | Per-action enable/disable |
| Conflict resolver dialog | E | Interactive wizard for each conflict type |
| Operation journal | E | Full multi-plan operation history |

## 11. Backend/API Impact

| Change | New API? | Schema Change? | Migration? |
|--------|----------|----------------|------------|
| Fix .bat classification | No | No | No (re-scan needed for existing data) |
| Relax draft guard for action edit | No | No | No |
| Auto-draft on ready action edit | No | No | No |
| candidate_overrides table (Phase D) | Yes (CRUD) | Yes (new table) | Yes (Alembic) |
| refresh-plan endpoint (Phase D) | Yes (POST) | No | No |
| Classification rules config (Phase C) | No (file-based) | No | No |
| DB classification rules (Phase D) | Yes (CRUD) | Yes (new table) | Yes (Alembic) |

**Phase A requires zero backend changes beyond the .bat fix.**

## 12. Frontend Impact

| Change | Files | Complexity |
|--------|-------|------------|
| Copy path buttons | PlanDetailPanel.tsx | Low (1 component per path) |
| Path length meter | PlanDetailPanel.tsx + library.css | Low |
| Editable target_path on ready | PlanDetailPanel.tsx (1 line change) | Low |
| Rename dialog | PlanDetailPanel.tsx (new modal/input) | Medium |
| Classification dropdown | PlanDetailPanel.tsx or LibraryPendingPanel.tsx | Medium |
| Refresh plan button | PlanDetailPanel.tsx | Medium (needs backend endpoint) |
| Rule editor | New Settings sub-page | High (Phase D) |

## 13. Safety Rules

All proposals must preserve:

| Rule | Phase A | Phase B | Phase C+ |
|------|---------|---------|----------|
| No overwrite without user intent | ✅ | ✅ | ✅ |
| No delete | ✅ | ✅ | ✅ |
| No auto-move | ✅ | ✅ | ✅ |
| No auto-retry | ✅ | ✅ | ✅ |
| No auto-rollback | ✅ | ✅ | ✅ |
| No skip preflight for blocked | ✅ | ✅ | ✅ |
| Warning-only can execute with notice | ✅ | ✅ | ✅ |
| All user edits → mandatory re-preflight | N/A | ✅ | ✅ |
| Path containment check on all edits | N/A | ✅ | ✅ |
| Path length check on all edits | N/A | ✅ | ✅ |
| Target exists check on all edits | N/A | ✅ | ✅ |
| No plan execution while draft | ✅ | ✅ | ✅ |

## 14. Test Strategy

### Backend Tests (Phase A)

- `test_bat_classified_as_executable_not_video` — `.bat` file → `file_kind = "executable"`
- `test_cmd_ps1_also_executable` — `.cmd`, `.ps1` → executable
- `test_target_exists_blocked_remains` — existing target → preflight still blocked
- `test_path_length_warning_stays_warning` — long path → warning, not blocked

### Backend Tests (Phase B)

- `test_edit_ready_action_resets_plan_to_draft` — edit target_path on ready plan → plan becomes draft
- `test_edited_action_outside_root_rejected` — target_path outside managed root → blocked
- `test_edited_action_target_exists_blocked` — target already exists → blocked by conflict refresh
- `test_edit_draft_action_target_path_persists` — draft plan edit → target_path updated

### Frontend Tests (Phase B)

- `blocked action shows rename/edit button`
- `edit target_path clears preflight result`
- `path length meter updates on edit`
- `execute disabled while plan is draft`
- `copy path button works`

### Manual Smoke

1. Create `.bat` file in source → scan → verify classified as software/executable
2. Create conflicting same-name file → generate plan → preflight → see blocked
3. Edit target_path → plan reverts to draft → mark ready → preflight → execute
4. Long filename → preflight shows path length warning with count

## 15. Recommendation

### Must-fix before next manual acceptance (Phase A)

1. **Fix `.bat`/`.cmd`/`.ps1` classification** in `classification.py` — 5-line change
2. **Update `_detect_file_type`** in `organize.py` to handle script extensions — 3-line change

### Recommended for next development sprint (Phase B)

1. **Relax `update_action` guard** to allow edits on ready plans → auto-draft on edit
2. **Enable inline target_path editing in frontend** for ready plans
3. **Add copy path buttons** to action rows
4. **Add path length display** with remaining char count

### Should not implement now

- Safe subset execution
- Action exclusion
- Candidate overrides table + refresh plan endpoint
- Rule editor
- Operation journal

### Why no schema changes needed for Phase A/B

- Classification fix is a code-only change (new extension in existing set)
- Relaxing the draft guard is a code-only change (one guard condition)
- Copy path buttons are pure frontend (no API call)
- Path length display is pure frontend (data already in action)
