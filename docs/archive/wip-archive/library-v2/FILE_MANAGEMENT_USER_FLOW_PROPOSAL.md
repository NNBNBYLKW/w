# Proposed File Management User Flow

> Non-technical proposal for a future unified File Management experience.

## 1. First-Time Use

The first screen should ask one simple question:

```text
What do you want Workbench to do first?

1. See files I already have
2. Copy files into a managed library
3. Browse or search files already indexed
```

Recommended behavior:

- "See files I already have" opens Sources.
- "Copy files into a managed library" opens Managed Roots setup, then Inbox.
- "Browse or search" opens Browse or Search, with an empty-state explanation if no files exist yet.

## 2. Add Folders to Scan

User-facing name: **Scanned Folders / 扫描文件夹**

Flow:

```text
File Management > Sources
  -> Add Folder
  -> Run Scan
  -> Files appear in Search, Browse, and preset views
```

Plain-language explanation:

> Use this when you want Workbench to see files where they already are. Workbench indexes these files in place. It does not copy, move, or organize them.

Expected result:

- Files remain in the original folder.
- Workbench can search, inspect, tag, and browse them.
- Storage state appears as "Scanned" or "External".

## 3. Add a Managed Library Folder

User-facing name: **Managed Library Folder / 受管库文件夹**

Flow:

```text
File Management > Managed Roots
  -> Add Managed Library Folder
  -> Set as default
  -> Continue to Inbox
```

Plain-language explanation:

> Use this when you want Workbench to keep organized copies of files. A managed library folder is a destination, not a scanned source. Adding it does not scan existing files inside it.

Expected result:

- The folder becomes available for import and organize plans.
- No existing files are scanned automatically.
- The next recommended step is importing files into Inbox.

## 4. Import Files

User-facing name: **Import / 导入**

Flow:

```text
File Management > Inbox
  -> Import Files or Import Folder
  -> Workbench copies files into Inbox
  -> Review detected type
  -> Create draft plan
```

Plain-language explanation:

> Import copies files into the managed library's Inbox. Your original files are preserved. Imported files are waiting for review until you create and execute a plan.

Expected result:

- Source files are untouched.
- Inbox copies are visible.
- Object candidates can be reviewed.
- Draft plans can be generated.

## 5. Browse Files

User-facing name: **Browse / 浏览**

Flow:

```text
File Management > Browse
  -> Choose domain or preset
  -> Filter by Scanned / Inbox / Managed
  -> Open object detail or inspect a file
```

Plain-language explanation:

> Browse shows organized objects and files that are not inside an object yet. It can show scanned files, imported Inbox files, and managed files.

Expected result:

- Object cards show grouped works/packages.
- Ungrouped file cards show files that can be composed or added to objects.
- Clicking a file opens shared details.

## 6. Create an Object

User-facing name: **Create Object / Create Package / 创建对象**

Flow:

```text
Browse
  -> Select managed ungrouped files
  -> Create Object
  -> Draft plan created
  -> Open Plans
  -> Preflight and Execute
```

Plain-language explanation:

> Creating an object from managed files creates a pending plan first. Files do not move until you execute the plan.

Expected result:

- Before execute: files stay where they are.
- After execute: Workbench creates the object and links active members.

## 7. Add Files to an Object

Flow:

```text
Browse
  -> Open object
  -> Add Files
  -> Select managed ungrouped files
  -> Draft amendment plan created
  -> Execute from Plans
```

Plain-language explanation:

> Adding files to an object is also plan-based. The selected files are not moved into the object until the plan executes successfully.

Expected result:

- Added files become object members after execute.
- The object member count increases.

## 8. Move Files Out of an Object

Flow:

```text
Browse
  -> Open object
  -> Remove from Object
  -> Draft amendment plan created
  -> Execute from Plans
```

Plain-language explanation:

> Removing a file from an object does not delete it. It moves the file back to the managed ungrouped area after the plan executes.

Expected result:

- File is no longer shown as an active member.
- File appears as a managed ungrouped file.
- No hard delete happens.

## 9. Execute Plans

User-facing name: **Pending Plans / 待执行计划**

Flow:

```text
File Management > Plans
  -> Select draft plan
  -> Mark Ready
  -> Preflight
  -> Execute
  -> Review result
```

Plain-language explanation:

> Plans are pending file operations. Workbench uses them so you can review what will happen before files move.

Expected result:

- `draft`: not ready yet.
- `ready`: can be checked.
- `preflight`: verifies paths and conflicts.
- `execute`: performs the planned operations.
- `completed`: done.
- `completed_with_errors` or `failed`: review diagnostics; do not assume all files moved.

## 10. View Problems

User-facing name: **Diagnostics / 问题诊断**

Flow:

```text
File Management > Recovery
  -> Run diagnostics
  -> Review findings
  -> Retry safe import cases where available
```

Plain-language explanation:

> Diagnostics show possible mismatches between Workbench records and files on disk. Workbench does not automatically delete, repair, or rewrite your files.

Expected result:

- User can see orphan Inbox files, missing files, or path mismatches.
- Automatic repair is not implied.
- Retry remains copy-only where supported.

## Future User Mental Model

```text
Sources = scan files in place.
Managed Roots = where organized files live.
Inbox = copied files waiting for review.
Browse = objects and ungrouped files.
Plans = pending file operations.
Recovery = diagnostics, not automatic repair.
```
