# Library v2 Manual Acceptance Guide

## Prerequisites

- Disposable test directory (e.g., `C:\Temp\WorkbenchV2Smoke\`)
- Managed root configured in Library > Roots
- At least one test file and one test folder with software-like contents

## Smoke Fixture Suggestions

```
C:\Temp\WorkbenchV2Smoke\
  source\
    sample.txt
    photo.jpg
  software_fixture\
    MyTool.exe
    config.json
    plugins\plugin.dll
    assets\icon.png
    readme.txt
  managed\          ← set as managed library root
```

## 7B — Copy-only File Import

1. Open Library > 导入 (Import)
2. Click "Choose files to import" → select `source\sample.txt`
3. Verify: batch created, file copied to `managed\00_Inbox\{batch_id}\sample.txt`
4. Verify: `source\sample.txt` still exists with original content
5. Import the same file again → verify `sample (1).txt` suffix, no overwrite

**Pass criteria:** Source preserved, inbox copy exists, no overwrite, batch + item visible in UI.

## 7B+ — Folder-as-Object Import

1. Select "Import folder as object" mode
2. Click "Choose files to import" → select `software_fixture\`
3. Verify: object candidate created, suggested type = software
4. Expand object card → verify members grouped (Launch, Documents, Components)
5. Verify: launch candidate = MyTool.exe (not setup/uninstall)
6. Verify: config.json, plugin.dll, icon.png, readme.txt not shown as independent items

**Pass criteria:** Object boundary preserved, member roles detected, no splitting.

## 7C — Inbox Review and Draft Plan

1. Select imported `sample.txt` → set final_object_type = docset
2. Select target root → Confirm
3. Create OrganizeCandidate
4. Generate Draft Plan
5. Verify: plan status = draft, "Draft plan only" notice shown
6. Verify: no files moved, source still exists, inbox copy still exists

**Pass criteria:** Review flow complete, draft plan generated, no execute.

## 7D — Execute and Path Sync

1. Open the draft plan from 7C in Plans tab
2. Mark ready → Preflight → Execute
3. Verify: plan completes (or completes with errors)
4. Verify: `source\sample.txt` still exists
5. Search for the file → verify it appears under managed target path
6. Open DetailsPanel → verify storage_state = Managed, managed root shown
7. Check Library > 导入 → verify inbox item status = organized

**Pass criteria:** Source preserved, file moved to managed target, DB synced, path_history + journal written.

## 7E — Storage Scope Filters

1. Search page: default All → see both external and managed files
2. Switch to External → only source-scanned files
3. Switch to Managed → only organized files
4. Media/Books/Games/Software pages: verify storage scope dropdown exists
5. DetailsPanel: verify storage section shows state badge + path info
6. Library Overview: verify storage summary counts

**Pass criteria:** Filters work, default All, no white screen, details show storage info.

## 7F — Recovery Diagnostics

1. Create orphan: manually add file to `managed\00_Inbox\orphan.txt`
2. Call recovery summary → verify orphan_inbox_count > 0
3. Verify orphan file not deleted by scan
4. Create failed import (import non-existent path)
5. Verify failed item visible in recovery
6. Restore source path → retry → verify status = imported

**Pass criteria:** Detection works, no auto-delete, retry succeeds, source preserved.

## Stop Conditions

Stop acceptance testing if any of these occur:
- Source file deleted or moved during import
- Target file overwritten without suffix
- Plan executes without going through mark-ready/preflight
- DB path not synced after successful execute
- External files hidden by default
- Recovery scan deletes or moves files
