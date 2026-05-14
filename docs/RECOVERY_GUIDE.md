# Workbench Recovery Guide

This guide covers common problems and how to recover from them. It assumes you are running the beta version.

---

## 1. App Does Not Start

**Symptom**: The app window opens but stays blank, or the app does not open at all.

**What to do**:
1. **Desktop app**: Close and restart Workbench. The backend starts automatically.
2. **Check for error messages**: If the app shows a red error page, read the reason shown. Common causes: backend executable not found, data directory permissions.
3. **Check backend log**: The backend log is at `%APPDATA%/Workbench Beta/logs/backend.log` (desktop app) or the console output (dev mode).
4. **Dev mode**: Make sure the backend is running on `http://127.0.0.1:8000`. Run `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.

**Do NOT**: Edit the database directly. Do not delete the data directory without understanding the consequences.

---

## 2. Backend Unavailable

**Symptom**: The app shows "disconnected" status, or pages show loading states that never resolve.

**What to do**:
1. Wait a few seconds — the backend may be starting.
2. Check that no other process is using port 8000 (dev) or 8765 (desktop).
3. Restart the app.
4. If the problem persists, the backend process may have crashed. Check the backend log.

---

## 3. Source Folder Missing

**Symptom**: A source shows an error status, or scan fails with "path does not exist."

**What to do**:
1. The source folder may have been moved, renamed, or deleted outside Workbench.
2. Go to Settings → Sources → disable the source.
3. If the folder was moved, update the source path to the new location.
4. If the folder was permanently deleted, you can remove the source. Existing indexed files remain in the database but will show as "unavailable" in details.

---

## 4. Managed Root Rejected

**Symptom**: When trying to add a managed library root, the app shows an error: "Managed library root cannot be..."

**What to do**:
1. The folder you selected is a protected system or application directory.
2. Choose a different folder — one you created specifically for your library (e.g., `D:\MyLibrary`).
3. Do not try to use system folders like `C:\Windows`, `C:\Program Files`, or the Workbench installation directory.

---

## 5. Thumbnail Unavailable

**Symptom**: A file shows "Preview unavailable" instead of a thumbnail image.

**What to do**:
1. **Corrupted video files**: This is expected. The app cannot generate thumbnails for corrupted or unsupported video formats.
2. **Missing FFmpeg**: In dev mode, video thumbnails require FFmpeg. Install FFmpeg or use the desktop app which bundles it.
3. **Recent files**: Thumbnails are generated on demand. Newly discovered files may not have thumbnails yet.
4. **No action needed**: The app shows a placeholder message, not an error. This does not affect any other functionality.

---

## 6. Plan Preflight Failed

**Symptom**: When preflighting a plan, one or more actions are blocked. The execute button is disabled.

**What to do**:
1. Read the blocked action messages in the plan detail. Each blocked action explains why.
2. Common causes and fixes:

   | Message | Fix |
   |---------|-----|
   | "Target path is outside any enabled source or managed library root" | The action is trying to write to a location outside your sources or managed root. Edit the target path. |
   | "Target path already exists and would be overwritten" | A file already exists at the destination. Remove the conflicting file, or edit the target path. |
   | "Source path no longer exists" | The file to be moved has been deleted or moved. Remove the action from the plan or restore the file. |
   | "Target library root is missing or disabled" | The managed root for this plan is disabled. Go to Library → Managed Roots and enable it. |
   | "Source and target must stay inside the same enabled source" | In legacy mode, source and target must be in the same source root. |
3. After fixing, click "Mark Ready" again and re-run preflight.

---

## 7. Plan Execution Failed

**Symptom**: Plan status is `failed` or `completed_with_errors`. Some actions succeeded, some failed.

**What to do**:
1. Check the execution log in the plan detail to understand which actions failed and why.
2. **Copy Failed Actions**: In the Phase 5 section, click "Copy Failed Actions to New Plan." This creates a new draft plan with only the failed actions. You can then fix the issues and re-execute.
3. **Rollback**: You can generate a rollback plan to reverse the succeeded moves. The rollback is a draft plan — you must still mark ready, preflight, and execute it.
4. **Manual check**: Use Windows Explorer to check that the files that succeeded are correctly placed in the managed root.

**Do NOT**: Manually move files that were partially organized. The rollback plan relies on files being at their recorded target paths.

---

## 8. App Closed During Execution

**Symptom**: Workbench was closed (or crashed) while a plan was executing.

**What happens**:
1. When you restart Workbench, the plan is automatically marked as `failed` with the reason: "Interrupted on application startup."
2. You will see a `startup_recovery` log entry in the plan's action log.
3. The plan status is now `failed`.

**What to do**:
1. Check which actions succeeded before the interruption (look at the action log).
2. Some files may have been moved, some not. Check the managed root and source folders.
3. Use one of these recovery paths:
   - **Copy Failed Actions**: Creates a new draft plan with the remaining actions.
   - **Generate Rollback**: Reverses the succeeded moves.
   - **Re-generate**: Create a new organize plan from the same candidates.

---

## 9. Rollback Draft Generated

**Symptom**: You generated a rollback plan. It appears as a new plan with status `draft`.

**What to know**:
- The rollback plan **has not been executed**. It is only a draft.
- It reverses file moves: the rollback source is the original target, and the rollback target is the original source.
- `mkdir` and `asset.yaml` actions are not rollbacked.
- Only succeeded `move` and `rename` actions are included.
- Some actions may be blocked (e.g., the original source location already has a file, or the target file no longer exists).

**What to do**:
1. Review the rollback plan's actions carefully.
2. **Do not execute** unless you are sure you want to move files back to their original locations.
3. If you decide to proceed: Mark Ready → Preflight → Execute (with confirmation).
4. After execution, the files will be back at their original source paths.

---

## 10. Asset YAML Merge Conflict

**Symptom**: When generating an asset YAML merge, the plan shows field conflicts.

**What to know**:
- Workbench classifies fields into three categories:
  - **Safe additions**: Fields that can be safely added without affecting existing data (aliases, tags, notes).
  - **Confirmation fields**: Fields that require confirmation before merging (title, year, cover).
  - **Never modify fields**: Fields that are never changed by the merge (schema_version, type, original_title).
- The merge plan creates a backup of the current `asset.yaml` before updating.

**What to do**:
1. Review the field diff in the plan detail.
2. If you agree with the merge: Mark Ready → Preflight → Execute.
3. If you disagree: Do not execute. The current `asset.yaml` is unchanged.

---

## 11. What NOT to Do

- **Do not manually edit the database** (`workbench.db`) unless instructed by documentation. Incorrect edits can corrupt the database.
- **Do not move files that are part of an active plan.** Wait for execution to complete or mark the plan as cancelled first.
- **Do not use your real library for your first organize test.** Use a disposable test folder to understand the workflow.
- **Do not manually delete organized files** before generating a rollback plan. The rollback relies on the moved files existing at their target paths.
- **Do not register system folders** (C:\Windows, Program Files) as sources or managed roots. Workbench blocks this for managed roots but the restriction does not apply to sources.
