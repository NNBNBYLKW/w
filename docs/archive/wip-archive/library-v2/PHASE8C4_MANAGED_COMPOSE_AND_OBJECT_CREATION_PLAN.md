# Phase 8C-4 — Managed Loose Files Compose and Object Creation Plan

> 状态：Phase 8C-4 方案 / 操作手册草案  
> 范围：只规划 managed loose files compose 与正式 object creation plan  
> 当前仓库事实：以 `main` 当前源码、`docs/library-v2/` 正式文档、Phase 8 `_wip` 手册为准  
> 明确非目标：不实现代码，不改 schema/API/test/package，不提交，不 push

---

## Current Facts Verified

### Current facts

| Question | Verified fact | Evidence |
|---|---|---|
| 当前是否已有 `library_objects` / `library_object_members` 表 | 已存在，并已有 SQLAlchemy model | `apps/backend/app/db/models/library_object.py` |
| 当前 `library_objects` 是否被 Browse v2 使用 | 已被 Browse v2 read model 读取并生成 managed object cards | `apps/backend/app/services/library/browse_v2.py` |
| 当前 managed loose file 如何表示 | `files.storage_state = "managed"`，且不属于 `library_object_members` / active `import_object_members` 的文件可作为 loose file | `apps/backend/app/db/models/file.py`, `apps/backend/app/services/library/browse_v2.py` |
| 当前如何判断 loose file | Browse v2 排除正式 object members 与 import object members 后，从 `files` 生成 loose file cards | `apps/backend/app/services/library/browse_v2.py` |
| 当前 managed 文件 path / root 如何存储 | `files.path` 是当前路径；`managed_root_id` 指向 managed root；`managed_at` 记录进入 managed 时间 | `apps/backend/app/db/models/file.py` |
| 当前 organize candidate / plan 模型 | `OrganizeCandidate` 有 `source_file_id/source_object_id`；`OrganizePlan` 有 `plan_kind/status/summary_json/target_library_root_id`；`OrganizeAction` 有 `action_type/source_path/target_path/payload_json/status` | `apps/backend/app/db/models/organize.py` |
| 当前 preflight / execute 如何移动文件 | `mark_ready -> preflight_plan -> execute_plan`；execute worker 对 `move/rename` 使用 `shutil.move`，且 preflight 阻止覆盖 | `apps/backend/app/services/library/organize.py`, `apps/backend/app/api/routes/library_organize.py` |
| 当前 `file_path_history` 是否存在 | 已存在，并在 Library v2 execute path sync 中写入 | `apps/backend/app/db/models/importing.py`, `apps/backend/app/services/library/organize.py`, `apps/backend/tests/test_library_v2_path_sync.py` |
| 当前 `operation_journal` 是否存在 | 已存在，import、retry、path sync、compose 等流程使用 | `apps/backend/app/db/models/importing.py`, `apps/backend/app/repositories/importing/repository.py` |
| 当前 recovery 如何识别 missing / orphan | Recovery scan 是只读诊断；检测 orphan inbox、missing inbox、missing managed、failed imports、incomplete journals 等 | `apps/backend/app/services/importing/recovery.py`, `apps/backend/tests/test_library_v2_recovery.py` |
| 当前 inbox compose 和 external compose 差异 | Inbox compose 只做 DB grouping；external compose copy-only 到 Inbox 后创建 object candidate；二者都不 draft plan / execute | `apps/backend/app/services/importing/service.py`, `apps/backend/app/api/routes/importing.py`, `docs/library-v2/API_REFERENCE.md` |
| 当前 no-overwrite / target path rendering 是否可复用 | no-overwrite preflight/execute 已存在；target dirs 和 prefixes 已存在 | `apps/backend/app/services/library/organize.py`, `apps/backend/app/services/library/organize_template_renderer.py` |
| 当前 managed loose files compose 是否需要正式 object model | 是。managed compose 的目标是正式对象创建，不应只停留在 `import_object_candidate` | `docs/library-v2/KNOWN_LIMITATIONS.md`, `apps/backend/app/db/models/library_object.py` |

### Safe assumptions

- Phase 8C-4 可以复用现有 `library_objects` / `library_object_members` 作为正式 object model，但必须由人类在实现前确认它们就是 canonical managed object model。
- 8C-4 的 planning / preflight / execute 应尽量复用现有 `OrganizePlan`、`OrganizeAction`、mark-ready、preflight、execute 流程，避免创建第二套文件操作系统。
- 当前 `_sync_import_paths_after_execute()` 只同步带 `inbox_item_id` 或 `import_object_candidate_id` 的 action；managed loose files 需要新的 object-creation finalize/path-sync 逻辑，不能假装已有。

### Open questions

- `OrganizeAction.payload_json` 是否足以承载 managed source `file_id/member_role`，还是需要给 `organize_actions` 增加专用 nullable trace 字段？
- 8C-4 是否允许跨 managed root 选择文件？
- 第一版是否保留原目录结构，还是只保留文件名？
- object creation plan 是否允许 `completed_with_errors` 后创建部分 object？本手册建议不允许。

### Deferred future work

- Object amendment add/remove member。
- Delete / app-level trash / source cleanup。
- AI 自动整理。
- scraper / poster wall / duplicate/hash。
- 自动 recovery repair。

---

## 1. Purpose

Phase 8C-4 的目的，是支持用户在 Browse v2 中把已经进入 managed library、但尚未属于任何正式对象的 loose files 合成为一个正式对象。

这与 Phase 8C-1 / 8C-2 / 8C-3 不同：

- Inbox loose files compose：只创建 `import_object_candidate`，不移动文件。
- External loose files compose：copy-only 到 Inbox，再创建 `import_object_candidate`，不移动 source。
- Managed loose files compose：目标文件已经在 managed library 内。合成对象需要把这些文件移动到新的 object directory，并创建正式 `library_object` / `library_object_members`。

因此 Phase 8C-4 必须走 plan-first：

```text
managed loose files
-> object creation plan
-> mark ready
-> preflight
-> execute
-> move files
-> create library_object
-> create library_object_members
-> sync files.path
-> write file_path_history
-> write operation_journal
```

Phase 8C-4 不允许：

- 直接移动文件。
- 直接创建正式 object。
- 直接写 members。
- 删除文件。
- source cleanup。
- auto execute。
- amendment add/remove member。

---

## 2. Current Baseline

| Area | Current fact | Implication for 8C-4 |
|---|---|---|
| Browse v2 | `GET /library/browse` 已返回 object cards 和 loose file cards | UI 可以在 loose file cards 上扩展 managed compose selection，但不能改 read model 语义 |
| Object detail | `GET /library/browse/object-detail` 已支持 `library_object` 和 `import_object_candidate` read-only detail/member list | 8C-4 execute 后应让新 object 出现在 object detail 中 |
| Inbox compose | `POST /library/import/compose` 从 inbox items 创建 `import_object_candidate`，不做 FS 操作 | 不能用于 managed files；managed compose 不应走 import candidate 作为最终模型 |
| External compose | `POST /library/import/compose/external-files` copy-only 到 Inbox，source preserved | external 仍不得 move；8C-4 只针对 managed loose files |
| Managed files | `files.storage_state="managed"`、`managed_root_id`、`path` 表示当前 managed 状态 | 8C-4 的 selected files 必须全部为 managed |
| Organize plan | `OrganizePlan.plan_kind` 可区分计划类型；actions 支持 `mkdir/move/rename/write_asset_yaml/...` | 可复用为 object creation plan，但需要新增 plan kind 和 finalize 语义 |
| Path sync | 现有 `_sync_import_paths_after_execute()` 只处理 inbox/import trace actions | 8C-4 需要 managed-object-specific path sync/finalize |
| File path history | `FilePathHistory` 已存在 | 每个成功移动的 managed file 都必须写 old_path/new_path |
| Operation journal | `OperationJournal` 已存在 | object creation plan、每个 path sync 或 finalization 应写审计记录 |
| Library object model | `library_objects` / `library_object_members` 已存在，并被 Browse v2 使用 | 推荐作为 canonical object model，而不是新建第二套对象表 |
| Import object model | `import_object_candidates` / `import_object_members` 是 import review 模型 | 不应用来表示 8C-4 的正式 managed object |
| Recovery | Recovery 是只读诊断，能检测 missing managed file；不自动修复 | 8C-4 后需要确保新 object members 的 managed paths 不被误报 |

---

## 3. Locked Decisions

1. Managed loose files compose 不直接创建 object。
2. Managed loose files compose 必须先生成 object creation plan。
3. Object creation plan 必须经过 preflight。
4. Object creation plan 必须经过 execute。
5. Execute 成功后才正式创建 `library_object` / `library_object_members`。
6. 不允许 delete。
7. 不允许 source cleanup。
8. 不允许 auto execute。
9. 不允许 AI 自动整理。
10. External source 文件仍然不能 move。
11. Managed files 可以移动，但只能在 plan execute 阶段移动。
12. Phase 8C-4 不做 object amendment plan 的完整 add/remove member 能力；只做“从 managed loose files 创建新对象”。

---

## 4. Core Product Flow

```text
Browse v2
-> select managed loose files
-> Compose object
-> modal: object name / object type / target root
-> create object creation plan
-> user reviews plan
-> mark ready
-> preflight
-> execute
-> move files into object directory
-> create library_object
-> create library_object_members
-> update files.path
-> write file_path_history
-> write operation_journal
-> Browse v2 refreshes
```

Rules:

- 这是 managed compose，不是 inbox compose。
- 这是文件移动，因此必须 plan-first。
- 成功 execute 前不得改变正式 object 状态。
- 失败时不得留下半成品 object。
- 如果 execute 部分失败，默认不得创建正式 object；应保留 failed plan 状态和 audit trail，等待人类处理。
- Browse v2 刷新后，原文件不应再作为 managed loose files 出现；它们应折叠到新 object card 的 members 下。

---

## 5. Data Model Decision

### Option A — Reuse existing organize plan only

做法：

- 只创建 `OrganizePlan` / `OrganizeAction`。
- execute 只移动文件。
- 不创建正式 `library_object` / `library_object_members`。

优点：

- schema 改动少。
- 复用现有 preflight/execute。

缺点：

- execute 后 Browse v2 无正式 object 可读。
- 文件可能只是被移动到对象目录，但 DB 不知道成员关系。
- Object detail/member view 无法稳定展示新对象。
- 后续 amendment plan 没有 object anchor。

风险：

- 形成“文件系统看起来是对象，数据库仍是散文件”的不一致状态。

### Option B — Introduce / formalize `library_objects` + `library_object_members`

当前仓库已经存在：

- `apps/backend/app/db/models/library_object.py`
- `LibraryObject`
- `LibraryObjectMember`
- `LibraryObjectRepository`
- Browse v2 read model 对 `library_objects` 的读取

因此 Option B 在本项目里不是“从零新增表”，而是：

- 明确现有 `library_objects` / `library_object_members` 是 canonical managed object model。
- 让 object creation plan execute 后写入这些表。
- 让 Browse v2 / Object detail / Recovery 都围绕同一正式对象模型工作。

优点：

- 对象详情、成员列表、后续 amendment plan 有正式 anchor。
- Browse v2 可以稳定隐藏成员文件，显示 object card。
- 与 Phase 8B 已完成 object detail/member view 对齐。

缺点：

- 需要设计 execute finalization。
- 可能需要补字段或 migration，例如 `created_from_plan_id`、`managed_root_id`、`primary_file_id`、member active/status 等。
- 测试面比纯 move 更大。

### Recommended decision

推荐采用 Option B：

```text
Use existing library_objects + library_object_members as canonical object model.
Use OrganizePlan as the execution gate.
Create / update official object rows only after successful execute.
```

第一版最小策略：

- 不新增第二套 object 表。
- 不把 `import_object_candidate` 升级为正式对象。
- 使用 `OrganizePlan.plan_kind = "object_creation"` 或 `"object_creation_managed_compose"`。
- 在 `OrganizePlan.summary_json` 中存 object metadata 和 selected file ids。
- 在每个 move action 的 `payload_json` 中存 `file_id/member_role/relative_path`。
- execute 全部成功后，finalize 创建 `LibraryObject` 与 `LibraryObjectMember`。

Stop condition:

- 如果现有 `payload_json` 无法可靠追踪每个 source `file_id`，应停止并设计最小 migration，而不是滥用 `inbox_item_id` / `import_object_candidate_id`。

---

## 6. Object Creation Plan Model

### 6.1 Reuse or new table

推荐第一版复用 `OrganizePlan`，不要新增 `object_creation_plan` 表。

理由：

- 现有 mark-ready / preflight / execute / events / logs 都围绕 `OrganizePlan`。
- Phase 8C-4 仍然是文件移动计划。
- 新增第二套计划系统会增加 DB/FS 不一致风险。

### 6.2 Draft shape

Recommended draft:

```text
OrganizePlan
  plan_kind = "object_creation_managed_compose"
  status = "draft"
  target_library_root_id
  summary_json = {
    "plan_type": "object_creation",
    "object_name": "My Object",
    "object_type": "imgset",
    "target_object_dir": "...",
    "selected_file_ids": [1, 2, 3],
    "planned_members": [
      {"file_id": 1, "role": "image_member", "relative_path": "001.jpg"},
      {"file_id": 2, "role": "image_member", "relative_path": "002.jpg"}
    ],
    "finalize_policy": "all_or_nothing_object_creation"
  }
```

Recommended actions:

```text
OrganizeAction
  action_type = "mkdir"
  target_path = <target_object_dir>

OrganizeAction
  action_type = "move"
  source_path = <current managed file path>
  target_path = <target object dir>/<filename>
  payload_json = {
    "file_id": 1,
    "member_role": "image_member",
    "member_relative_path": "001.jpg",
    "object_creation_plan": true
  }
```

### 6.3 Plan status

Use existing plan statuses:

```text
draft -> ready -> executing -> completed
draft -> ready -> executing -> completed_with_errors
draft -> ready -> executing -> failed
draft/ready -> cancelled
```

8C-4 policy:

- `completed` may create official object.
- `completed_with_errors` should not create partial object in v1.
- `failed` must not create official object.
- If some files moved before failure, plan recovery must make the inconsistency visible through logs/recovery diagnostics.

### 6.4 Preflight status

Use existing preflight mechanics, with extra object-creation validation:

- all source files exist
- all source files are managed
- all source files are loose
- target root exists
- target object directory resolved
- no overwrite
- file ids in action payload match current DB paths

### 6.5 Execute status and finalization

Execute should:

1. Re-run preflight.
2. Execute `mkdir` and `move` actions.
3. If all object creation move actions succeed:
   - create `LibraryObject`
   - create `LibraryObjectMember` rows
   - update each `File.path`, `parent_path`, `name`, `managed_root_id`, `storage_state="managed"`
   - append `FilePathHistory`
   - append `OperationJournal`
4. Mark plan completed.

If any required move action fails:

- do not create `LibraryObject`
- do not create `LibraryObjectMember`
- write failed action status
- keep plan `failed` or `completed_with_errors`
- surface recovery/manual inspection path

### 6.6 Rollback / partial failure behavior

Phase 8C-4 does not implement automatic rollback execution.

Allowed:

- reuse existing rollback draft / copy failed actions documentation if available
- emit enough action logs for manual recovery
- recovery scan can report missing/changed managed paths

Forbidden:

- auto move files back
- auto delete created dirs
- auto mutate object members after partial failure

---

## 7. Target Path Rules

Phase 8C-4 must reuse:

- `PLAN_TARGET_DIRS` in `apps/backend/app/services/library/organize.py`
- `OBJECT_PREFIX` in `apps/backend/app/services/library/organize_template_renderer.py`
- existing safe title/path rendering
- existing no-overwrite preflight behavior

Examples:

```text
50_Audio/[AUDIO] Object Name/
60_Assets/[ASSET] Object Name/
30_Images/Image_Sets/[IMGSET] Object Name/
20_Videos/Collections/[VIDEO_COLL] Object Name/
```

Current target dirs include:

| Object type | Target directory |
|---|---|
| `movie` | `10_Movies_Anime/Movies` |
| `anime` | `10_Movies_Anime/Anime` |
| `movie_collection` | `10_Movies_Anime/Collections` |
| `game` | `20_Games` |
| `software` | `30_Software` |
| `imgset` | `30_Images/Image_Sets` |
| `photo_event` | `30_Images/Photo_Events` |
| `web_image_set` | `30_Images/Web_Images` |
| `comic` | `30_Images/Comics` |
| `course` | `40_Videos/Courses` |
| `clip` | `40_Videos/Clips` |
| `clip_set` | `40_Videos/Clip_Sets` |
| `video_collection` | `40_Videos/Collections` |
| `audio` | `50_Audio` |
| `asset_pack` | `60_Assets` |
| `docset` | `80_Documents/Docsets` |

Rules:

- `object_name` must be sanitized with the same rules as organize templates.
- Object directory conflict uses suffix, not overwrite.
- Member filename is preserved where possible.
- Same basename conflict inside object directory uses suffix.
- First version should not preserve nested relative directory structure unless explicitly decided.

Recommended first version:

```text
Only preserve filenames.
Do not preserve original directory hierarchy.
Use no-overwrite suffix for duplicate basenames.
```

Open question:

- If selected files come from different folders and have meaningful relative structure, should future versions allow “preserve relative folders”?

---

## 8. Backend API Draft

Current route style:

- Library read routes live under `/library/...`
- Import routes live under `/library/import/...`
- Organize plan routes live under `/library/organize/...` or existing library organize router paths

Managed compose is not import. It should not live under `/library/import`.

### Recommended endpoint

```text
POST /library/objects/creation-plans
```

Purpose:

- Validate selected managed loose files.
- Create draft object creation organize plan.
- Return plan summary.
- Do not move files.
- Do not create final object.

Request draft:

```json
{
  "file_ids": [1, 2, 3],
  "object_name": "My Object",
  "object_type": "imgset",
  "target_library_root_id": 1
}
```

Response draft:

```json
{
  "plan_id": 123,
  "plan_kind": "object_creation_managed_compose",
  "object_name": "My Object",
  "object_type": "imgset",
  "file_count": 3,
  "status": "draft",
  "target_object_dir": "G:/Managed/30_Images/Image_Sets/[IMGSET] My Object",
  "planned_moves": [
    {
      "file_id": 1,
      "source_path": "G:/Managed/Loose/a.jpg",
      "target_path": "G:/Managed/30_Images/Image_Sets/[IMGSET] My Object/a.jpg",
      "member_role": "image_member"
    }
  ]
}
```

Validation errors:

| Error | Status | Meaning |
|---|---:|---|
| `file_ids_required` | 400 | Empty selection |
| `not_managed_file` | 400 | One or more files are external/inbox |
| `not_loose_file` | 400 | One or more files already belong to object/import object |
| `missing_source_path` | 400 | DB path missing or source does not exist |
| `invalid_object_type` | 400 | Unsupported type |
| `invalid_target_root` | 400/404 | Target root missing/disabled |
| `path_conflict_unresolved` | 409 | Target path cannot be safely rendered |

### Preflight endpoint

Recommendation:

- Reuse existing organize preflight endpoint for `OrganizePlan`.
- Do not add a separate object creation preflight endpoint unless current router constraints force it.

### Execute endpoint

Recommendation:

- Reuse existing organize execute endpoint, but extend execution service to recognize `plan_kind="object_creation_managed_compose"` and run finalization.
- Do not execute from the creation-plan POST.

Forbidden:

- `POST /library/objects/creation-plans` must not move files.
- It must not create `library_objects`.
- It must not create `library_object_members`.
- It must not call execute internally.

---

## 9. Backend Implementation Plan

### 8C-4A — Planning-only backend

Goal:

- Create draft object creation plan from managed loose files.
- No filesystem operation.
- No object creation.

Files likely changed:

- `apps/backend/app/api/routes/library.py` or a new focused library object route file
- `apps/backend/app/schemas/browse_v2.py` or new schema module for object creation plan requests
- `apps/backend/app/services/library/organize.py`
- `apps/backend/app/services/library/organize_template_renderer.py`
- `apps/backend/app/repositories/library_organize/repository.py`
- `apps/backend/app/repositories/library_objects/repository.py`
- `apps/backend/tests/test_library_v2_managed_compose_plan.py`

Backend tasks:

1. Add request/response schemas for managed object creation plan.
2. Validate `file_ids` non-empty.
3. Load all files by id.
4. Reject missing file rows.
5. Reject non-managed files.
6. Reject files that are members of `library_object_members`.
7. Reject files that are active members of `import_object_members`.
8. Validate target root exists and is enabled.
9. Validate object type exists in `PLAN_TARGET_DIRS` / `OBJECT_PREFIX`.
10. Render target object dir.
11. Generate `mkdir` and `move` actions.
12. Store file trace in `payload_json`.
13. Create draft plan.
14. Return plan id and planned moves.

Acceptance criteria:

- Draft plan created.
- No file moved.
- No `library_object` created.
- No `library_object_member` created.
- Existing inbox/external compose APIs unchanged.

Stop conditions:

- The implementation needs to mutate `library_objects` before execute.
- The implementation tries to reuse `inbox_item_id` for managed files.
- Existing Phase 7 path sync tests fail because plan semantics changed globally.

### 8C-4B — Preflight

Goal:

- Ensure object creation plan is executable without overwrite or missing source.

Backend tasks:

1. Reuse existing `mark_ready`.
2. Reuse existing `preflight_plan`.
3. Add object creation specific validation before or inside preflight:
   - payload `file_id` matches a managed loose file
   - DB `files.path` matches action source path or reports stale plan
   - target root still valid
   - no target overwrite
   - target object dir either planned mkdir or safe existing warning state
4. Block stale plans.

Acceptance criteria:

- Missing source blocks preflight.
- Existing target file blocks preflight.
- Suffix-rendered safe target passes.
- Valid plan can be marked ready and preflighted.

Stop conditions:

- preflight ignores stale DB path changes.
- preflight allows overwrite.

### 8C-4C — Execute

Goal:

- Move managed loose files into object directory and finalize official object rows.

Backend tasks:

1. Reuse `execute_plan(confirm=True)`.
2. Execute move actions.
3. After all required moves succeed, create `LibraryObject`.
4. Create `LibraryObjectMember` for each moved file.
5. Update `File.path`, `parent_path`, `name`, `storage_state`, `managed_root_id`, `managed_at`.
6. Append `FilePathHistory` for each moved file.
7. Append `OperationJournal` entries for object creation and path sync.
8. Mark plan completed.
9. Refresh Browse v2 read model naturally from DB.

Transaction / FS consistency rules:

- DB finalization should occur only after FS moves succeed.
- If DB finalization fails after FS moves, write plan failure logs and expose recovery need.
- If FS move partially fails, do not create official object in v1.
- Do not mark file moved in DB before the corresponding FS move succeeds.

Acceptance criteria:

- Files physically moved.
- `library_object` exists.
- Members exist.
- Old file paths no longer used in `files.path`.
- Browse v2 shows object card.
- Loose file cards no longer show the member files.
- Details/object detail shows members.

Stop conditions:

- `completed_with_errors` creates partial official object.
- DB claims moved file while FS source remains unmoved or target missing.
- journal/history missing.

### 8C-4D — Recovery integration

Goal:

- Ensure recovery diagnostics understand objects created through managed compose.

Backend tasks:

1. Verify recovery clean state after successful managed compose.
2. Verify missing moved member is reported.
3. Avoid false orphan reports for new object folders.
4. Ensure old loose paths are not reported as missing if DB path already synced.
5. Document manual recovery limitation.

Acceptance criteria:

- Recovery summary clean after successful compose.
- Manually deleting a member triggers missing managed file / object member diagnostic.
- Recovery does not auto repair.

Stop conditions:

- recovery auto moves/deletes files.
- recovery reports old paths as missing after successful path sync.

---

## 10. Frontend Implementation Plan

This section is design only. Do not implement in this planning pass.

### Browse v2 behavior

- Managed loose files can show compose checkboxes only when they are truly loose and selectable.
- Inbox, external, and managed compose modes must be separated.
- Mixed mode selection is blocked.
- Object cards are not selectable for managed compose.
- Object members are not selectable as loose files.
- Managed compose submit creates an object creation plan, not an object.
- After plan creation, route user to plan review / organize plan detail if a route exists; otherwise show a link to the plan.

### Compose modal

Mode-specific safety copy for managed:

Chinese:

```text
这些已入库散文件将通过整理计划移动到新的对象目录。
提交后只会生成计划，不会立即移动文件。
```

English:

```text
These managed loose files will be moved into a new object directory through an organize plan.
Submitting creates a plan only and does not move files immediately.
```

Fields:

- object name
- object type
- target root
- selected files summary
- planned target preview

Forbidden UI:

- no execute button in modal
- no delete
- no source cleanup
- no amendment add/remove controls
- no one-click bulk across pages

Files likely changed later:

- `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`
- `apps/frontend/src/features/browse-v2/LooseFileCard.tsx`
- `apps/frontend/src/features/browse-v2/ComposeObjectModal.tsx`
- `apps/frontend/src/features/browse-v2/composeHelpers.ts`
- `apps/frontend/src/services/api/browseV2Api.ts`
- potential new `apps/frontend/src/services/api/libraryObjectPlansApi.ts`
- locale files under `apps/frontend/src/locales/en/` and `apps/frontend/src/locales/zh-CN/`

---

## 11. Validation Rules

Backend request validation:

- `file_ids` non-empty.
- All ids resolve to `files` rows.
- All files exist on disk.
- All files have `storage_state = "managed"`.
- All files are loose, not formal object members.
- All files are not active import object members.
- All files are under a valid managed root.
- `target_library_root_id` exists and is enabled.
- `object_name` non-empty after trim.
- `object_name` is Windows-safe after sanitization.
- `object_type` is allowed by target rendering.
- No mixed storage_state.
- No directory rows, unless future file model explicitly supports directories.
- No missing source path.
- No already planned locked items, if plan lock is implemented.

Plan validation:

- planned source paths match current DB file paths.
- planned target paths are inside target managed root.
- no target overwrite.
- same basename conflicts are suffix-resolved.
- all required move actions have `payload_json.file_id`.

Frontend validation:

- cannot submit empty selection.
- cannot mix inbox/external/managed selections.
- cannot select object cards.
- cannot select managed object members.
- managed safety copy visible.

---

## 12. Safety Invariants

- No delete.
- No source cleanup.
- No auto execute.
- No direct object creation before execute.
- No direct member mutation before execute.
- No external source move.
- No inbox compose behavior mixed into managed compose.
- Plan must be reviewable.
- Preflight required before execute.
- Execute must write `file_path_history`.
- Execute must write `operation_journal`.
- Partial failure must not leave DB claiming moved files that were not moved.
- `completed_with_errors` must not create a misleading complete object in v1.
- Object creation must be all-or-nothing at the official object model level in v1.

---

## 13. Test Plan

### 8C-4A tests

Suggested file:

```text
apps/backend/tests/test_library_v2_managed_compose_plan.py
```

Cases:

- `test_creates_object_creation_plan_from_managed_loose_files`
- `test_rejects_empty_file_ids`
- `test_rejects_inbox_files`
- `test_rejects_external_files`
- `test_rejects_files_already_library_object_members`
- `test_rejects_files_already_import_object_members`
- `test_rejects_missing_files`
- `test_rejects_invalid_target_root`
- `test_rejects_invalid_object_type`
- `test_managed_compose_plan_does_not_move_files`
- `test_managed_compose_plan_does_not_create_library_object`
- `test_managed_compose_plan_does_not_create_members`

### 8C-4B tests

Suggested file:

```text
apps/backend/tests/test_library_v2_managed_compose_preflight.py
```

Cases:

- `test_preflight_detects_missing_source`
- `test_preflight_detects_target_conflict`
- `test_preflight_computes_no_overwrite_suffix`
- `test_preflight_validates_target_root`
- `test_preflight_detects_stale_source_path`
- `test_preflight_passes_valid_object_creation_plan`

### 8C-4C tests

Suggested file:

```text
apps/backend/tests/test_library_v2_managed_compose_execute.py
```

Cases:

- `test_execute_moves_files`
- `test_execute_creates_library_object`
- `test_execute_creates_library_object_members`
- `test_execute_updates_files_path`
- `test_execute_writes_file_path_history`
- `test_execute_writes_operation_journal`
- `test_execute_handles_same_basename_conflict`
- `test_execute_failure_does_not_create_false_object`
- `test_completed_with_errors_does_not_create_partial_object`
- `test_browse_v2_hides_members_after_execute`

### 8C-4D tests

Suggested file:

```text
apps/backend/tests/test_library_v2_managed_compose_recovery.py
```

Cases:

- `test_recovery_sees_moved_members_as_valid`
- `test_recovery_detects_missing_object_member`
- `test_recovery_does_not_mark_old_loose_path_as_orphan`
- `test_recovery_does_not_auto_repair_managed_compose`

### Regression tests

Run after implementation:

```powershell
cd apps/backend
python -m pytest tests/test_library_v2_compose_inbox.py tests/test_library_v2_compose_external.py -v
python -m pytest tests/test_library_browse_v2_read_model.py tests/test_library_browse_v2_object_detail.py -v
python -m pytest tests/test_library_v2_path_sync.py tests/test_library_v2_recovery.py tests/test_library_v2_storage_scope.py -v
```

Frontend:

```powershell
cd apps/frontend
npm run build
```

Desktop:

```powershell
cd apps/desktop
npm run build
```

---

## 14. Manual Acceptance Plan

Use disposable managed roots and disposable files only.

1. Prepare managed loose files.
2. Open Browse v2.
3. Filter to `storage_state=managed`.
4. Confirm managed loose files are visible and object members are not selectable as loose items.
5. Select managed loose files.
6. Open compose modal.
7. Confirm safety text says plan only.
8. Enter object name, object type, target root.
9. Submit.
10. Verify plan created.
11. Verify no file moved after submit.
12. Verify no `library_object` exists yet.
13. Open plan detail.
14. Mark ready.
15. Run preflight.
16. Execute.
17. Verify files moved to object directory.
18. Verify `files.path` now points to the new target paths.
19. Verify `file_path_history` rows exist.
20. Verify `operation_journal` rows exist.
21. Verify Browse v2 shows a new object card.
22. Verify old loose file cards disappear from loose file results.
23. Open object detail.
24. Verify members show correctly.
25. Run recovery scan.
26. Verify clean state for this fixture.
27. Confirm no delete/source cleanup occurred.

Failure symptoms:

- Object appears before execute.
- Files move before execute.
- Old paths remain in `files.path` after execute.
- Members still appear as loose files.
- Recovery reports old loose path missing after successful sync.
- Any delete/rmdir operation appears in plan actions.

Stop condition:

- Stop testing immediately if any source/managed file outside disposable fixture is moved or deleted.

---

## 15. Risk Register

| Risk | Severity | Trigger | Mitigation | Stop condition |
|---|---|---|---|---|
| Moving managed files is destructive if plan wrong | P0 | Wrong target root/path/type | Draft review + preflight + no overwrite + disposable QA | Target outside managed root or unexpected path |
| Object model not ready | P0 | Execute moves files but cannot create stable object | Adopt existing `library_objects` as canonical or stop for migration design | No stable object/member rows after execute |
| Organize plan cannot express object metadata | P1 | `summary_json`/payload not enough | Add minimal schema only after design review | Need to abuse inbox/import IDs |
| Path history mismatch | P0 | DB path sync incomplete | Per-file history assertions | Moved file lacks history |
| Operation journal missing | P0 | Finalize path not journaled | Append journal in finalization | Move/object creation without journal |
| Recovery false orphan | P1 | New object folder not recognized | Recovery tests after execute | Clean fixture reports high severity |
| Partial FS move + DB rollback mismatch | P0 | Exception after some moves | All-or-nothing official object creation; action logs | DB claims moved file that did not move |
| Duplicate filenames | P1 | Selected files share basename | Suffix target filenames in plan | Overwrite or dropped file |
| Mixed roots | P1 | Files from multiple managed roots selected | Decide policy; reject in v1 if uncertain | Cross-root plan renders ambiguous target |
| Selected files already object members | P0 | Read model/selection bug | Backend validation rejects | Existing object loses hidden member |
| Target root invalid | P1 | Disabled/missing root | Validate target root before plan/preflight | Plan points to missing root |
| Frontend implies immediate move | P1 | Modal copy is wrong | Managed safety text and plan-only response | User thinks files already moved |
| Confusion between inbox/external/managed compose | P1 | Shared modal hides mode | Mode-specific validation and copy | Wrong endpoint called |
| Scope creep into amendment plan | P2 | Add/remove existing object members added early | Keep 8C-4 to new object from loose files | UI offers member amendment |
| Plan lock missing | P1 | Same file used in two draft plans | Add validation or plan lock before execute | Two plans move same file |
| Completed_with_errors creates partial object | P0 | Finalize despite failed moves | Require all required moves succeed | Partial object appears official |

---

## 16. Out of Scope

Phase 8C-4 does not implement:

- object amendment add/remove existing object members
- delete
- app-level trash
- source cleanup
- external source move
- AI auto organization
- scraper / poster wall
- duplicate/hash pipeline
- automatic recovery repair
- advanced collection/franchise/series model
- object cover/primary file automation beyond minimal optional role inference
- managed root migration
- beta packaging/release

---

## 17. Recommended Execution Breakdown

Do not implement Phase 8C-4 in one pass.

Recommended sequence:

```text
8C-4A: backend object creation plan draft
8C-4B: backend preflight validation
8C-4C: backend execute + object creation finalize
8C-4D: frontend managed compose to plan
8C-4E: recovery integration / docs / acceptance
```

### 8C-4A — Backend object creation plan draft

- Add request/response schemas.
- Add endpoint.
- Validate managed loose files.
- Render target paths.
- Create draft plan/actions.
- No FS operation.
- No object creation.

### 8C-4B — Backend preflight validation

- Mark ready.
- Preflight object creation plan.
- Block stale source paths and conflicts.
- Verify all action payload file ids.

### 8C-4C — Backend execute + object creation finalize

- Reuse execute worker.
- Add finalization for `plan_kind=object_creation_managed_compose`.
- Create `library_object`/members only after all required moves succeed.
- Update paths/history/journal.

### 8C-4D — Frontend managed compose to plan

- Enable managed loose selection.
- Add mode-specific modal text.
- Submit to creation-plan endpoint.
- Navigate/link to plan review.
- No execute from modal.

### 8C-4E — Recovery integration / docs / acceptance

- Add recovery smoke coverage.
- Update formal docs after implementation.
- Run manual acceptance on disposable fixture.

---

## 18. Open Questions

1. 是否正式采用 `library_objects` / `library_object_members` 作为 canonical object model？本手册建议是。
2. object creation plan 是否复用 `OrganizePlan`？本手册建议复用，并设置新 `plan_kind`。
3. managed compose 是否允许跨 managed root？第一版建议拒绝或强警告；需要人类确认。
4. 是否保留原目录结构？第一版建议不保留，只保留文件名并 suffix 冲突；需要人类确认。
5. object member role 第一版如何定义？建议先使用 `member` / `primary` / type-derived roles，避免复杂推断。
6. execute 后是否从 loose file view 隐藏原 file？建议是：成员不再显示为 loose file。
7. 是否需要 plan lock，防止同一 file 被多个 plan 同时使用？建议在 8C-4A 或 8C-4B 前确认。
8. recovery 对 object member missing 的显示方式是什么？建议作为 managed missing file + object member context。
9. 是否需要 object cover / primary file 在 8C-4 建立？建议 optional，不能阻塞基础 object creation。
10. `completed_with_errors` 是否绝对禁止创建 partial object？本手册建议禁止。
11. 如果 `payload_json.file_id` 不够可靠，是否接受新增 `organize_actions.source_file_id` migration？
12. managed compose target root 与 selected files 原 managed root 不一致时，是否允许跨 root 移动？

