# Phase 8 — Browse v2 and Object Management Manual

> 状态：Phase 8 执行操作手册草案  
> 输入方案：`G:\Windows\Downloads\PHASE8_BROWSE_V2_AND_OBJECT_MANAGEMENT_PLAN.md`  
> 当前仓库事实来源：`docs/library-v2/` 正式文档与当前工作区源码  
> 范围：只规划 Browse v2、对象级浏览、对象详情、散文件合成对象、对象 amendment plan  
> 非目标：不实现代码，不打包，不发布，不引入 AI 自动整理

---

## 1. Manual Purpose

这是一份 **Phase 8 工程执行操作手册**，不是愿景文档，也不是代码实现说明。

Phase 8 的目标是把 Workbench 浏览体系从当前的“文件平铺浏览”推进到“对象 + 散文件混合浏览”：

```text
Browse/Search/Media/Documents/Software/Games
  从 file cards only
  升级为 object cards + loose file cards
```

Phase 8 不是 beta package 阶段，不做发布打包，不做 UI 营销化改造，不扩展成 Explorer 替代品。它必须继续保护 Library v2 已建立的安全链路：

```text
Import -> Inbox -> Object Detection -> Review
-> Draft Plan -> Mark Ready -> Preflight -> Execute
-> Managed Library -> Browse/Search/Details -> Recovery
```

全阶段必须保持：

- import copy-only
- source preserved
- no overwrite
- no source cleanup
- no auto delete
- no auto execute
- plan / preflight / execute gate
- operation_journal
- file_path_history
- recovery diagnostics read-only

推荐执行顺序固定为：

```text
Phase 8A -> Phase 8B -> Phase 8C -> Phase 8D -> Phase 8E
```

不要一次性实现全部 Phase 8。

---

## 2. Current Baseline

### 2.1 Workspace Snapshot

本手册基于当前工作区事实编写。开始审查时 `git status --short --untracked-files=all` 显示已有未提交源码/测试改动：

```text
M apps/backend/app/api/routes/importing.py
M apps/backend/app/schemas/importing.py
M apps/backend/app/services/importing/object_boundary.py
M apps/backend/app/services/importing/service.py
M apps/backend/app/services/library/object_parser.py
M apps/backend/app/services/library/organize.py
M apps/backend/app/services/library/organize_template_renderer.py
M apps/frontend/src/features/library/LibraryInboxPanel.tsx
M apps/frontend/src/locales/en/features.ts
M apps/frontend/src/locales/zh-CN/features.ts
M apps/frontend/src/services/api/importingApi.ts
?? apps/backend/tests/test_library_v2_file_collection_import.py
?? apps/backend/tests/test_library_v2_object_type_ux.py
?? apps/frontend/src/features/library/objectTypeOptions.ts
```

这些文件不是本手册创建的改动。手册把它们作为“当前工作区源码事实”读取，但正式 docs 仍主要声明 Phase 7A–7F 完成。因此，涉及 Phase 7H 的能力需要在 Phase 8 开始前单独验收和落文档。

### 2.2 Baseline Fact Table

| Area | Current fact | Evidence | Implication for Phase 8 |
|---|---|---|---|
| Formal Library v2 status | 正式文档声明 Phase 7A–7F complete，195 tests；README 另称 7A–7G complete | `docs/library-v2/README.md`, `docs/library-v2/PHASE7_COMPLETION_REPORT.md`, `README.md` | Phase 8 手册应以 7A–7F 安全链路为稳定底座；7G/7H 要区分当前事实和待确认 |
| Phase 8 input plan location | 仓库 `_wip` 下未找到输入计划；下载目录存在方案 | `Test-Path docs/_wip/...PLAN.md = False`, `Test-Path G:\Windows\Downloads\...PLAN.md = True` | 本手册使用下载目录方案作为输入，不额外复制 plan 文件 |
| Formal object tables | 已存在 `library_objects`, `library_object_members`, `asset_metadata_cache` | `apps/backend/app/db/models/library_object.py`, `apps/backend/app/db/migrations/0001_initial_core.sql` | Phase 8B/8C 决策不是“是否建表”，而是是否把现有表升级为 managed object canonical model |
| Formal object API | 已有 `/library/objects/scan`, `/library/objects`, `/library/objects/{id}`, `/library/objects/{id}/members`, `/library/overview` | `apps/backend/app/api/routes/library_objects.py` | Phase 8A 可复用 object list/detail API，但它目前偏对象扫描 read model |
| Formal object service | `LibraryObjectScannerService` 扫描 `[TYPE]` 文件夹并写入 `library_objects` / members | `apps/backend/app/services/library/object_scanner.py` | 当前 object model 与导入执行链路尚未完全合并，需要 adapter 或同步策略 |
| Import object candidate model | `import_object_candidates` / `import_object_members` 已存在，含 candidate status、member role、launch/primary file | `apps/backend/app/db/models/importing.py` | 这是导入 review 阶段模型，不应直接当永久 browse object，除非 adapter 明确标注临时来源 |
| Object member roles | import members 有 `role`；library object members 有 `member_role` | `ImportObjectMember.role`, `LibraryObjectMember.member_role` | Browse v2 可展示 member role，但需要统一 role label 和 read model |
| Browse pages data source | Search/Media/Books/Games/Software 都从 `files` / `FileRepository` 查询 | `apps/backend/app/services/media/service.py`, `books/service.py`, `games/service.py`, `software/service.py`, `search/service.py` | 当前主要 browse surfaces 仍是 file-level flat list |
| Frontend browse API | `/library/media`, `/library/books`, `/library/games`, `/library/software`, `/search` | `apps/frontend/src/services/api/mediaLibraryApi.ts`, `booksApi.ts`, `gamesApi.ts`, `softwareApi.ts`, `searchApi.ts` | Phase 8A 需要新 browse v2 read model 或显式 mixed-card API |
| Library Objects UI | Library tab `objects` 使用 `listLibraryObjects()` / `getLibraryObject()` | `apps/frontend/src/features/library/LibraryObjectsPanel.tsx`, `libraryObjectsApi.ts` | 已有对象列表和页内对象详情，但不等于全 browse v2 |
| DetailsPanel | 统一右侧 DetailsPanel 当前只以 `file_id` 取 file details | `apps/backend/app/services/details/service.py`, `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx` | Phase 8B 如要对象 inspector，必须设计 object detail mode，不能 fork 页面专属 details center |
| Object detail page | 无独立 object route；Library Objects tab 内有 `ObjectDetail` aside | `LibraryObjectsPanel.tsx` | Phase 8B 可先增强页内 object detail，再评估统一 DetailsPanel object mode |
| Selection / bulk actions | Pending candidates 有多选生成 plan；普通 browse pages 主要是单击选择文件到 DetailsPanel | `LibraryPendingPanel.tsx`, `SearchFeature.tsx`, `MediaLibraryFeature.tsx` | Phase 8C 需要为 loose files 增加受控 selection model，不能默认跨分页批量 |
| Storage scope | Search/Media/Books/Games/Software 支持 `storage_state=external|inbox|managed`；默认 All | `routes/search.py`, `routes/library.py`, `test_library_v2_storage_scope.py` | Browse v2 必须保留 default All，不突然隐藏 external |
| Path history and journal | `operation_journal` / `file_path_history` 存在；execute path sync 写入 | `models/importing.py`, `organize.py`, `test_library_v2_path_sync.py` | Phase 8C/8D 任何真实文件变化必须继续写 journal/history |
| Recovery diagnostics | recovery scan 只读，retry failed import 是 copy-only | `apps/backend/app/services/importing/recovery.py`, `routes/importing.py`, `test_library_v2_recovery.py` | Phase 8 不能新增自动修复或自动清理 |
| Phase 7H artifacts | 当前工作区已有 `audio`, `asset_pack`, `/library/import/file-collections`, `objectTypeOptions.ts` | dirty source files listed above | 这些看起来已实现但未提交/未正式文档化；Phase 8 前必须验收并更新正式 docs |
| `audio` / `asset_pack` target dirs | 当前工作区 `PLAN_TARGET_DIRS` 包含 `audio -> 50_Audio`, `asset_pack -> 60_Assets`; `OBJECT_PREFIX` 包含 `AUDIO`, `ASSET` | `organize.py`, `organize_template_renderer.py` | Phase 8 taxonomy 可包含音频/素材，但实现前需确认 7H 已落地 |
| Multi-file collection import | 当前工作区已有 API/schema/service/frontend/tests 迹象 | `routes/importing.py`, `schemas/importing.py`, `service.py`, `LibraryInboxPanel.tsx`, `test_library_v2_file_collection_import.py` | Phase 8 可把它视作前置能力，但必须先跑 7H 验收 |
| Source-scan object parser | `SUPPORTED_OBJECT_TYPES` 当前含 MOVIE/ANIME/GAME/COURSE/IMGSET/DOCSET/CLIP/SOFTWARE/VIDEO_COLL/COMIC/AUDIO/ASSET 等 | `apps/backend/app/services/library/object_parser.py` | 可用于 formal object scan，但 role model 与 import members 仍需收敛 |
| Known limitations | app-level trash/delete、auto repair、persistent recovery findings、duplicate/hash、move import、source cleanup、AI classification 未实现 | `docs/library-v2/KNOWN_LIMITATIONS.md` | Phase 8 不能越界实现这些能力 |

### 2.3 Existing Capabilities

- 有正式 `library_objects` / `library_object_members` 表和 object scan API。
- 有导入阶段的 `import_object_candidates` / `import_object_members`。
- 有 storage_state：`external`, `inbox`, `managed`。
- 有 file-level Search / Media / Books / Games / Software browse。
- 有统一 file DetailsPanel，支持 storage section。
- 有 folder-as-object、成员折叠、review、draft plan、execute path sync、recovery diagnostics。
- 当前工作区看起来已有 Phase 7H 的 audio / asset_pack / multi-file collection import 代码，但需要单独确认。

### 2.4 Existing Gaps

- 主 browse pages 仍然平铺 `files`，没有 object + loose file mixed card read model。
- `library_objects` 是对象扫描模型，不一定代表导入 execute 后的 canonical managed object。
- `import_object_candidate` 是导入 review 模型，不适合作为长期正式对象模型。
- DetailsPanel 当前只支持 file detail，不支持 object detail。
- Browse pages 没有统一 loose-file selection/bulk compose workflow。
- 无 object creation/amendment plan 的正式 API/服务。
- 无对象扩容/缩容能力。
- 无物理删除、app trash、duplicate/hash、auto recovery repair，这些也不属于 Phase 8。

### 2.5 Source Mismatches / Needs Verification

| Item | Mismatch | Required handling |
|---|---|---|
| Phase 8 input plan says Phase 7H complete | 正式 `docs/library-v2/` 还停在 7A–7F；当前工作区有 7H 未提交代码迹象 | Phase 8A 前先完成 7H 验收、测试和正式 docs 更新 |
| Formal object table already exists | Phase 8 plan 写“8B/8C 前决定是否引入正式 library_objects” | 应改为“决定是否复用/扩展现有 `library_objects` 为 managed canonical object model” |
| `LibraryV2CapabilityResponse` still says import disabled | `schemas/importing.py` 与已实现导入能力不一致 | Phase 8 不处理，但作为 docs/source mismatch 记录 |
| `/library/import/file-collections` exists in dirty source | 输入计划把它当 Phase 7H 结果；它不在正式 API docs | Phase 8 手册可引用为当前工作区事实，但实现前需正式确认 |

---

## 3. Product Decisions Locked

以下决策来自 Phase 8 输入方案，本手册不重新争论方向，只转成执行约束：

1. 浏览导航按内容领域展开，不按“对象 / 散文件”拆成两个顶层入口。
2. 素材包作为一级“素材”领域。
3. 对象扩容 / 缩容必须生成 amendment plan。
4. 第一版不允许删除，只允许“移出对象”或解除成员关系。
5. 外部 source 文件合成对象时不允许 move，只能 copy-only 导入 Inbox。
6. 合成对象不直接创建正式 object，必须先生成 object creation / amendment plan，execute 后才正式创建 / 更新。
7. Phase 8A 可以先做 read model adapter。
8. Phase 8B / 8C 前必须决定如何复用/扩展正式 `library_objects` / `library_object_members`。
9. 散文件手动合成对象是 Phase 8C 核心能力。
10. Phase 8 执行顺序为 8A → 8B → 8C → 8D → 8E。

---

## 4. Global Safety Invariants

所有 Phase 8 子阶段都必须遵守：

- 不删除物理文件。
- 不移动 external source 文件。
- 不做 source cleanup。
- 不自动清理 orphan。
- 不自动 execute。
- 不绕过 draft plan。
- 不绕过 mark-ready / preflight / execute。
- 不绕过 operation_journal。
- 不绕过 file_path_history。
- 不让 AI 写正式类型。
- 不让 AI 执行文件操作。
- 不未经 plan 直接改对象成员关系。
- 不把 `import_object_candidate` 当成永久正式 object 模型，除非 read model adapter 明确标注为临时派生。
- 不让 Browse v2 隐藏默认 external 文件；默认仍为 All。
- 不破坏 file-level DetailsPanel、single click select、double click open。

---

## 5. Global Prohibited Actions

### File-system prohibited actions

- 禁止删除文件。
- 禁止移动 external source。
- 禁止覆盖文件。
- 禁止自动清理 `00_Inbox`。
- 禁止自动清理 orphan。
- 禁止自动修复 missing files。
- 禁止未通过 preflight 执行 move。

### Data-model prohibited actions

- 禁止未经 plan 直接创建正式 object。
- 禁止未经 execute 直接改 object members。
- 禁止把 temporary candidate 当正式 object 写死。
- 禁止破坏 `storage_state` 语义。
- 禁止绕过 `file_path_history` / `operation_journal`。
- 禁止为了 Browse v2 修改既有 API response 语义而不保留兼容。

### UI prohibited actions

- 禁止把导航拆成“对象 / 散文件”两个顶层入口。
- 禁止让“生成 plan”看起来像“已经移动文件”。
- 禁止提供物理删除按钮。
- 禁止提供自动修复按钮。
- 禁止提供一键 execute 大量对象按钮。
- 禁止默认跨分页批量处理。
- 禁止让对象成员像普通 loose file 一样被视觉拆散。

### Scope prohibited actions

- 不做 metadata scraper。
- 不做 poster wall。
- 不做 AI classification。
- 不做 audio transcription。
- 不做 EXIF timeline / photo map。
- 不做 duplicate/hash pipeline。
- 不做 app-level trash。
- 不做 beta package。

---

## 6. Target Browse Taxonomy

Phase 8 的导航按内容领域组织。对象和散文件的差异由主面板 card badge 表示，而不是用两个独立导航入口表示。

```text
媒体
  媒体总览
  电影
  剧集 / 动漫
  课程 / 讲座资料
  视频合集
  视频素材
  图片 / 相册
  漫画
  音频 / 录音

文档
  文档 / 资料包

应用
  软件 / 工具
  游戏

素材
  素材包
```

### Type Mapping

| Domain | User label | Backend values | Card query group |
|---|---|---|---|
| 媒体 | 电影 / 长视频 | `movie` | `media.movie` |
| 媒体 | 剧集 / 动漫 | `anime` | `media.series` |
| 媒体 | 课程 / 讲座资料 | `course` | `media.course` |
| 媒体 | 视频合集 / 系列视频 | `video_collection` | `media.video_collection` |
| 媒体 | 视频素材 / 片段 | `clip`, `clip_set` | `media.clip` |
| 媒体 | 图片 / 相册 | `imgset`, `photo_event`, `web_image_set` | `media.image_set` |
| 媒体 | 漫画 | `comic` | `media.comic` |
| 媒体 | 音频 / 录音 | `audio` | `media.audio` |
| 文档 | 文档 / 资料包 | `docset` | `documents.docset` |
| 应用 | 软件 / 工具 | `software` | `apps.software` |
| 应用 | 游戏 | `game` | `apps.game` |
| 素材 | 素材包 | `asset_pack` | `assets.asset_pack` |

### Do

- 保留旧 backend value，前端做合并显示。
- browse filter 传英文 backend value 或 query group，不传中文 label。
- 默认显示对象和散文件混合结果。

### Don’t

- 不删除 legacy value。
- 不把 `photo_event` / `web_image_set` 数据变成不可见。
- 不把素材包塞进软件/工具下面。

---

## 7. Browse v2 Read Model

Phase 8A 推荐先创建 read model adapter，而不是立即大改表结构。

### 7.1 Card Types

```ts
type BrowseV2Card =
  | BrowseV2ObjectCard
  | BrowseV2LooseFileCard;
```

#### Object Card Draft

| Field | Meaning |
|---|---|
| `card_kind: "object"` | card 类型 |
| `object_id` | 正式 `library_objects.id`，或 adapter 临时 id |
| `object_source` | `library_object` / `import_object_candidate` / `derived` |
| `object_type` | backend value |
| `display_title` | 用户显示名 |
| `members_count` | 成员数量 |
| `storage_state` | `inbox` / `managed` / mixed |
| `root_path` | 对象根路径 |
| `cover_file_id` / `cover_path` | 可选封面 |
| `primary_file_id` / `launch_file_id` | 可选主文件 |
| `needs_review` | 是否需要用户检查 |
| `warning_flags` | missing/member_mismatch/recovery_warning |

#### Loose File Card Draft

| Field | Meaning |
|---|---|
| `card_kind: "loose_file"` | card 类型 |
| `file_id` | `files.id` |
| `name` | 文件名 |
| `file_kind` | image/video/audio/document/etc |
| `storage_state` | external/inbox/managed |
| `path` | 当前路径 |
| `size_bytes` | 文件大小 |
| `modified_at` | 修改时间 |
| `can_compose_object` | 是否可合成对象 |
| `blocked_reason` | 不能合成原因 |

### 7.2 Adapter Sources

| Source | Use in Phase 8A | Caveat |
|---|---|---|
| `library_objects` | 正式 object card 的首选来源 | 当前来自 `[TYPE]` 目录扫描，不一定覆盖所有 managed imports |
| `import_object_candidates` | 可显示 Inbox / pending object candidates | 必须标记为 `object_source=import_object_candidate`，不能冒充正式 object |
| `files` | loose file card 来源 | 要排除已归属正式 object 的成员，避免视觉拆散 |
| `library_object_members` | 排除或展开正式对象成员 | 当前 roles 与 import roles 名称不完全一致 |
| `import_object_members` | 折叠 import object candidate members | 默认不作为 loose item 展示 |

### 7.3 Loose File Definition

一个 file 只有在满足以下条件时才是 Browse v2 loose file：

- 不属于正式 `library_object_members`，或 member inactive。
- 不属于 active `import_object_members` 的默认折叠对象候选。
- 没有被当前 draft/amendment plan 占用。
- `is_deleted=false`。

Recommendation: Phase 8A 先用 conservative loose-file query，宁可少显示可合成项，也不要把对象成员误显示成散文件。

---

## 8. Data Model Strategy

### 8.1 Current Model Reality

当前已经有：

- `library_objects`
- `library_object_members`
- `asset_metadata_cache`
- `import_object_candidates`
- `import_object_members`
- `organize_candidates.source_object_id`
- `organize_plans.plan_kind`
- `organize_actions.inbox_item_id`
- `organize_actions.import_object_candidate_id`

### 8.2 Phase 8 Decision Gate

在 Phase 8B / 8C 前，必须明确以下决策：

| Decision | Option A | Option B | Recommendation |
|---|---|---|---|
| 正式 object source of truth | 复用并扩展 `library_objects` | 新建 v2 object 表 | 优先复用现有表，除非字段语义无法承载 managed import |
| 导入 execute 后 object 创建 | execute 后立即写 `library_objects` | execute 后等待 object scan | Phase 8B 前建议设计 execute sync，避免 Browse v2 缺对象 |
| import candidate 生命周期 | 保留 review/audit | 升级为正式 object | 保留 review/audit，不升级为正式模型 |
| object amendment | 扩展 organize plan | 新建 amendment plan 系统 | 优先扩展 `OrganizePlan.plan_kind`，避免第二套执行系统 |

### 8.3 Schema Change Rule

Phase 8A 不应需要 schema/migration。Phase 8B/8C/8D 可能需要字段扩展，例如：

- `library_objects.storage_state`
- `library_objects.managed_root_id`
- `library_objects.primary_file_id`
- `library_objects.cover_file_id`
- `library_object_members.active`
- `library_object_members.role` alias or mapping
- `library_object_members.created_from_plan_id`

任何 schema 变化必须单独阶段实现并添加 migration/ensure helper/tests。

---

## 9. Phase 8A Manual — Browse Taxonomy and Read Model Adapter

### Goal

建立 Browse v2 的内容领域导航、对象/散文件混合 read model、基础卡片和安全筛选。Phase 8A 只读，不做对象合成/扩容/缩容。

### Allowed Changes

- 新增 read-only browse v2 backend service/repository/schema/API。
- 新增 frontend Browse v2 页面或替换现有 browse surfaces 的展示层。
- 新增 domain taxonomy、card badges、object/loose file mixed list。
- 复用 `library_objects`, `import_object_candidates`, `files`。
- 保留现有 `/search`, `/library/media`, `/books`, `/software`, `/library/games` API。

### Forbidden Changes

- 不改真实文件。
- 不执行 plan。
- 不创建/amend object。
- 不新增删除/修复。
- 不改 source scan 行为。
- 不默认隐藏 external。
- 不把 import candidate 写成正式 object。

### Files Likely Changed

Backend:

- `apps/backend/app/api/routes/library.py` 或新增 `apps/backend/app/api/routes/browse_v2.py`
- `apps/backend/app/services/library/browse_v2.py`（建议新增）
- `apps/backend/app/repositories/file/repository.py`
- `apps/backend/app/repositories/library_objects/repository.py`
- `apps/backend/app/schemas/browse_v2.py`（建议新增）
- `apps/backend/app/main.py`（如新增 route）

Frontend:

- `apps/frontend/src/services/api/browseV2Api.ts`（建议新增）
- `apps/frontend/src/entities/library/types.ts` 或新增 `entities/browse-v2/types.ts`
- `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`
- `apps/frontend/src/features/books/BooksFeature.tsx`
- `apps/frontend/src/features/software/SoftwareFeature.tsx`
- `apps/frontend/src/features/games/GamesFeature.tsx`
- `apps/frontend/src/features/search/SearchFeature.tsx`（只接入 card mode，不破坏原 search）
- `apps/frontend/src/locales/en/features.ts`
- `apps/frontend/src/locales/zh-CN/features.ts`

### Backend Tasks

1. 定义 `BrowseV2Card` response schema，区分 `object` / `loose_file`。
2. 实现 `LibraryBrowseV2Service.list_cards(domain, object_type_group, storage_state, query, page, page_size)`。
3. 从 `library_objects` 生成正式 object cards。
4. 从 `import_object_candidates` 生成 Inbox/pending object cards，并标记临时来源。
5. 从 `files` 生成 loose file cards。
6. 在 loose file query 中排除 object members，避免视觉拆散。
7. 保留 storage_state 默认 All。
8. 添加只读 API，例如：

```text
GET /library/browse-v2/cards
```

建议 query：

```text
domain=media|documents|apps|assets
type=movie|anime|course|video_collection|image_set|...
storage_state=external|inbox|managed
card_kind=all|object|loose_file
query=
page=
page_size=
```

### Frontend Tasks

1. 增加 Browse v2 taxonomy data，不硬编码中文值到 API。
2. 建立 object card / loose file card 两种 presentational components。
3. 在 Media/Books/Games/Software/Search 中先接入 read-only mixed-card result frame。
4. loose file 单击仍调用现有 selected file flow，打开 DetailsPanel。
5. object card 单击进入对象详情占位或选中 object card，不调用 file DetailsPanel。
6. 加 badge：Object / Loose file / External / Inbox / Managed / Missing。
7. 空/loading/error 状态沿用当前设计系统。

### Tests

建议新增：

- `apps/backend/tests/test_phase8a_browse_v2_read_model.py`
- `apps/backend/tests/test_phase8a_browse_v2_storage_scope.py`

测试用例：

- `test_browse_v2_returns_object_and_loose_file_cards`
- `test_browse_v2_does_not_show_object_members_as_loose_files`
- `test_browse_v2_default_all_includes_external_inbox_managed`
- `test_browse_v2_storage_state_filter`
- `test_browse_v2_import_candidate_marked_temporary`
- `test_browse_v2_legacy_file_apis_unchanged`

### Manual QA

- Media browse 显示对象卡片和散文件卡片。
- 点击散文件仍打开右侧 DetailsPanel。
- 点击对象不触发 file details 错误。
- storage filter 默认 All。
- external 文件仍可见。
- 对象成员不以散文件重复出现。

### Acceptance Criteria

- Browse v2 read model 是只读。
- 主面板能同时展示 object + loose file。
- 旧 browse API 和旧页面行为未破坏。
- 没有真实文件操作。
- 没有 schema 变更，除非明确单独提交。

### Stop Conditions

- 对象成员被当作 loose file 显示。
- external 默认被隐藏。
- object card 点击导致 DetailsPanel file fetch 404。
- Browse v2 API 开始创建/修改数据。
- 旧 Media/Books/Games/Software/Search 测试失败且原因不是测试预期更新。

---

## 10. Phase 8B Manual — Object Detail and Member View

### Goal

用户能打开对象并查看成员、角色、主文件/封面/启动文件、storage state、missing 状态和 path history 摘要。

### Allowed Changes

- 增强现有 `/library/objects/{id}` 或新增 Browse v2 object detail endpoint。
- 增强 `LibraryObjectsPanel` 或建立共享 `ObjectDetailPanel`。
- 增加 object detail mode 的 UI，但不复制 file DetailsPanel 业务逻辑。
- 展示 members、roles、missing/recovery warning。

### Forbidden Changes

- 不添加成员。
- 不移出成员。
- 不删除成员。
- 不自动修复 missing。
- 不在 detail 页直接改正式 object members。
- 不把对象详情做成新的独立产品竖线。

### Files Likely Changed

Backend:

- `apps/backend/app/services/library/object_scanner.py`
- `apps/backend/app/repositories/library_objects/repository.py`
- `apps/backend/app/api/routes/library_objects.py`
- `apps/backend/app/schemas/library_objects.py`
- possibly `apps/backend/app/services/importing/recovery.py` for read-only warnings only

Frontend:

- `apps/frontend/src/features/library/LibraryObjectsPanel.tsx`
- `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`（仅当决定支持 object mode）
- `apps/frontend/src/features/details-panel/sections/*`（仅新增 object-safe sections）
- `apps/frontend/src/services/api/libraryObjectsApi.ts`
- locale files

### Backend Tasks

1. 决定 object detail 来源：正式 `library_objects` only，还是 adapter 包含 import candidates。
2. 为 detail response 添加 member role summary。
3. 提供 primary/cover/launch candidates。
4. 提供 missing flags，但不自动修复。
5. 如果需要 path history 摘要，新增只读 query，不改 history 语义。
6. 保持 pagination，避免大对象一次返回全部成员。

### Frontend Tasks

1. 建立 ObjectDetailPanel：identity、facts、members、warnings、paths、actions placeholder。
2. 成员列表按 role 分组：Launch/Main/Cover/Videos/Images/Documents/Components/Unknown。
3. 成员 file_id 可点击时进入 file DetailsPanel 或打开 file detail drawer，但不能破坏 object context。
4. 对 missing member 显示 warning badge。
5. “添加成员/移出成员”只显示 disabled placeholder，直到 Phase 8D。

### Tests

- `apps/backend/tests/test_phase8b_object_detail.py`

测试用例：

- `test_object_detail_returns_members_paginated`
- `test_object_detail_includes_role_summary`
- `test_object_detail_does_not_modify_members`
- `test_object_detail_missing_members_are_reported_read_only`
- `test_object_detail_404_for_missing_object`

### Manual QA

- 打开对象卡片，看到成员列表。
- 大对象成员分页可用。
- missing warning 可读。
- 文件成员点击仍可查看 file details。
- 页面无“删除/自动修复/execute”入口。

### Acceptance Criteria

- 对象详情只读。
- 成员角色清晰。
- object detail 不 fork 全局 DetailsPanel 的 file organization controls。
- 无真实文件操作。

### Stop Conditions

- detail 请求会写 DB。
- detail 页面直接移除/新增成员。
- missing 文件被自动修复或隐藏。
- 大对象导致一次性返回过多成员。

---

## 11. Phase 8C Manual — Compose Object from Loose Files

### Goal

允许用户从 Browse/Search/Pending 中选择已被系统看到的 loose files，安全合成为对象。

### Scope Split

推荐拆为三步：

```text
8C-1 inbox loose -> import_object_candidate
8C-2 external loose -> copy-only import to Inbox synthetic object folder
8C-3 managed loose -> object creation plan
```

### Allowed Changes

- controlled selection model for loose file cards。
- compose object modal。
- preview API。
- object creation plan / import candidate creation。
- existing organize plan pipeline integration。
- copy-only flow for external loose files。

### Forbidden Changes

- 不移动 external source。
- 不删除 source。
- 不直接创建正式 object。
- 不自动 execute。
- 不绕过 review。
- 不跨分页默认选择。
- 不把 object members 当 loose files 再合成。

### Files Likely Changed

Backend:

- `apps/backend/app/api/routes/library.py` or `browse_v2.py`
- `apps/backend/app/services/library/browse_v2.py`
- `apps/backend/app/services/importing/service.py`
- `apps/backend/app/services/library/organize.py`
- `apps/backend/app/db/models/organize.py`（仅如需 plan_kind/action trace 扩展）
- `apps/backend/app/schemas/browse_v2.py`

Frontend:

- Browse v2 result components
- `apps/frontend/src/services/api/browseV2Api.ts`
- `LibraryInboxPanel.tsx` only if reusing candidate review links
- selection toolbar/modal components
- locale files

### Backend Tasks

1. 实现 `POST /library/browse-v2/compose/preview`（只读）。
2. preview 根据 selected file ids 判断 storage_state 分流。
3. 对 mixed storage_state selection 返回 blocked，要求用户分批处理。
4. `inbox` loose files：创建 `import_object_candidate` + members，不复制文件。
5. `external` loose files：copy-only 到 Inbox synthetic object folder，再创建 candidate/members。
6. `managed` loose files：生成 object creation plan，不直接创建正式 object。
7. 所有真实文件变更都只在 execute 中发生。
8. 不确定类型只写 suggestion，用户必须确认 final type。

### Frontend Tasks

1. Browse v2 card list 增加 selection mode。
2. 只允许选择 loose file card。
3. 显示 selected count，不跨分页默认选择。
4. 打开 Compose Object modal。
5. modal 字段：object name、object type、target root、member preview、target structure preview。
6. storage_state 混合时显示阻止原因。
7. 提交后根据后端 response 显示 candidate/plan 链接。

### Tests

- `apps/backend/tests/test_phase8c_compose_object.py`
- `apps/backend/tests/test_phase8c_compose_external_copy.py`
- `apps/backend/tests/test_phase8c_compose_managed_plan.py`

测试用例：

- `test_compose_inbox_loose_files_creates_object_candidate`
- `test_compose_external_files_copies_to_inbox_preserving_source`
- `test_compose_managed_files_creates_object_creation_plan_only`
- `test_compose_rejects_object_members`
- `test_compose_rejects_cross_page_implicit_selection`
- `test_compose_mixed_storage_state_requires_explicit_split`
- `test_compose_does_not_execute`
- `test_compose_cancel_creates_nothing`

### Manual QA

- 从 Inbox loose files 合成对象，生成 candidate。
- 从 External loose files 合成对象，source 保留，Inbox 有 copy。
- 从 Managed loose files 合成对象，只生成 plan。
- 取消 modal 不产生 batch/candidate/plan。
- 选中 object member 时不可合成。

### Acceptance Criteria

- 合成对象不直接创建正式 object。
- external copy-only。
- managed 走 plan。
- candidate/plan 后续可走 Review → Draft Plan → Execute。
- 所有失败有可见状态。

### Stop Conditions

- source 被 move/delete。
- 取消后创建 batch/candidate。
- 直接写正式 object。
- 自动 execute。
- partial copy 后 DB/FS 不一致且无 failed 状态。

---

## 12. Phase 8D Manual — Object Amendment Plan

### Goal

支持对象扩容/缩容，但所有成员变化必须通过 amendment plan。

### Allowed Changes

- 新增 `plan_kind=object_amendment` 或等价 plan origin。
- 添加成员、移出成员、移动到另一个对象的 draft plan。
- execute 后更新 members/files/path history/journal。
- UI 显示 amendment preview。

### Forbidden Changes

- 不物理删除。
- 不 source cleanup。
- 不直接拖拽写 DB。
- 不绕过 preflight。
- 不自动 repair。

### Files Likely Changed

Backend:

- `apps/backend/app/services/library/organize.py`
- `apps/backend/app/services/library/object_amendment.py`（建议新增）
- `apps/backend/app/repositories/library_objects/repository.py`
- `apps/backend/app/repositories/importing/repository.py`
- `apps/backend/app/db/models/organize.py`（如需新 action trace）
- tests

Frontend:

- Object detail panel
- member selection controls
- amendment modal
- plan detail labels/i18n

### Backend Tasks

1. 设计 amendment action types，例如 `add_member`, `remove_member_relation`, `move_member_to_object`, `move_into_object_root`。
2. preflight 校验路径、冲突、object membership、source containment。
3. execute 成功后写 member relationship。
4. 如果文件路径变化，写 `files.path`、`file_path_history`、`operation_journal`。
5. 如果只是解除成员关系但不移动文件，也必须写 audit log。
6. partial failure 只同步成功 action。

### Tests

- `apps/backend/tests/test_phase8d_object_amendment_plan.py`

测试用例：

- `test_add_member_generates_draft_amendment_plan`
- `test_remove_member_does_not_delete_file`
- `test_move_member_to_another_object_requires_preflight`
- `test_execute_amendment_updates_members_and_path_history`
- `test_failed_amendment_does_not_partially_hide_member`

### Manual QA

- 添加文件到对象，生成 amendment plan。
- 从对象移出成员，文件不删除。
- 移动成员到另一个对象，preflight 阻止冲突。
- execute 后成员关系和 path history 可见。

### Acceptance Criteria

- 无删除。
- 所有变更可预检、可追踪。
- object detail 更新后与文件系统一致。

### Stop Conditions

- member relation 直接被 UI 改写。
- 物理文件被删除。
- external source 被移动。
- path history/journal 缺失。

---

## 13. Phase 8E Manual — Domain-specific Cards

### Goal

在 Browse v2 read model 稳定后，为不同对象类型提供更适合的卡片表达。

### Allowed Changes

- 类型专属 card presentation。
- cover/poster/mosaic/launch file/member summary。
- 不影响数据语义。

### Forbidden Changes

- 不做 scraper。
- 不做 poster wall。
- 不做播放器/阅读器/launcher。
- 不新增自动 metadata fetching。

### Card Enhancements

| Object type | Enhancement |
|---|---|
| `movie` | poster/cover, year, duration if known |
| `anime` | episode count, season hint |
| `course` | video count, attachment count |
| `video_collection` | clip/episode count |
| `clip`, `clip_set` | duration/format summary |
| `imgset`, `photo_event`, `web_image_set` | cover/mosaic, image count |
| `comic` | page count, cover |
| `audio` | duration if known, count |
| `docset` | document count |
| `software` | launch executable, file count |
| `game` | launch executable, mod/component count |
| `asset_pack` | member type summary |

### Tests

- frontend build
- browse card smoke
- no object-specific card can change backend value

### Acceptance Criteria

- Cards are richer but still dense workbench UI.
- No new business behavior.
- No external metadata scraping.

---

## 14. API Reference Draft

All paths follow current backend style: route files do **not** include `/api` prefix.

### GET `/library/browse-v2/cards`

Purpose: return mixed object + loose file cards for a domain/type scope.

Request query:

```text
domain=media|documents|apps|assets
type=movie|anime|course|video_collection|clip|image_set|comic|audio|docset|software|game|asset_pack
storage_state=external|inbox|managed
card_kind=all|object|loose_file
query=
page=1
page_size=50
sort_by=updated_at|title|modified_at
sort_order=asc|desc
```

Response draft:

```json
{
  "items": [
    { "card_kind": "object", "object_id": 1, "object_type": "imgset", "display_title": "Trip", "members_count": 245 },
    { "card_kind": "loose_file", "file_id": 10, "file_kind": "image", "name": "wallpaper.jpg", "storage_state": "external" }
  ],
  "total": 2,
  "page": 1,
  "page_size": 50
}
```

Safety:

- read-only
- no filesystem access except optional existence checks already supported by services
- default All storage scope

### GET `/library/browse-v2/objects/{id}`

Purpose: object detail + members for Browse v2.

May wrap existing `/library/objects/{id}` if formal object model is chosen.

### POST `/library/browse-v2/compose/preview`

Purpose: read-only preview for selected loose files.

Safety:

- no DB write
- no file operation
- returns blocked reasons

### POST `/library/browse-v2/compose`

Purpose: create candidate or draft plan from selected loose files depending on storage_state.

Safety:

- no execute
- external path copy only to Inbox
- managed path creates plan only
- inbox path creates candidate only

### POST `/library/browse-v2/objects/{id}/amendments`

Purpose: create object amendment draft plan.

Safety:

- draft only
- mark-ready/preflight/execute still required
- no delete action type in Phase 8

---

## 15. Frontend Reference Draft

### Browse v2 Page Structure

```text
Masthead
Domain rail / type rail
Toolbar: storage scope, query, card kind, sort
Result frame
  ObjectCard
  LooseFileCard
Selection toolbar (only loose files)
Object detail / DetailsPanel integration
```

### ObjectCard

Shows:

- object type label
- title
- members count
- storage state badge
- root path short form
- needs_review / missing warnings

Click behavior:

- single click selects object / opens object detail panel
- double click may open object root only if existing desktop bridge behavior supports it and user intent is clear

### LooseFileCard

Shows:

- file name
- file_kind
- storage_state
- path
- size/modified time
- tags/favorite/rating if available

Click behavior:

- single click selects file and opens unified DetailsPanel
- double click keeps existing open file behavior where supported

### Selection Toolbar

Only visible when selected loose files > 0.

Actions:

- Compose object
- Clear selection

Do not include:

- Delete
- Execute
- Auto fix
- Cross-page select all

---

## 16. Test Matrix

### Backend Unit / Service Tests

| Phase | Test file | Must cover |
|---|---|---|
| 8A | `apps/backend/tests/test_phase8a_browse_v2_read_model.py` | mixed cards, object/loose distinction, storage scope |
| 8A | `apps/backend/tests/test_phase8a_browse_v2_no_member_split.py` | members folded under objects |
| 8B | `apps/backend/tests/test_phase8b_object_detail.py` | detail, members, roles, pagination |
| 8C | `apps/backend/tests/test_phase8c_compose_object.py` | inbox/external/managed compose paths |
| 8C | `apps/backend/tests/test_phase8c_compose_safety.py` | no source move/delete, cancel no-op, no auto execute |
| 8D | `apps/backend/tests/test_phase8d_object_amendment_plan.py` | add/remove/move member via plan |
| 8E | no backend required unless card data changes | presentation-only if no API changes |

### Regression Tests

Run after implementation phases:

- `apps/backend/tests/test_library_v2_*.py`
- `apps/backend/tests/test_library_phase*.py`
- `apps/backend/tests/test_phase2a_search.py`
- `apps/backend/tests/test_phase2c_search_filters.py`
- `apps/backend/tests/test_phase3a_books_library.py`
- `apps/backend/tests/test_phase3b_software_library.py`
- `apps/backend/tests/test_phase5a_media_library.py`
- `apps/backend/tests/test_games_library_batch*.py`
- `apps/backend/tests/test_file_classification_documents.py`

### Frontend Validation

- `npm --prefix apps/frontend run build`
- smoke routes:
  - `/search`
  - `/library`
  - `/library?tab=objects`
  - `/library/media`
  - `/books`
  - `/software`
  - `/library/games`

---

## 17. Manual QA Playbooks

### Playbook A — Existing Beta Regression

Fixture: existing source scan files plus managed root.

Steps:

1. Search default All.
2. Open Media/Books/Games/Software.
3. Click file rows.
4. Verify DetailsPanel loads file details.
5. Double-click supported files.

Expected:

- No external files hidden.
- DetailsPanel unchanged for files.
- No object feature affects file open.

Stop:

- file details fail
- external missing by default
- old browse endpoints broken

### Playbook B — Browse v2 Mixed Cards

Fixture: one scanned library object plus loose files.

Steps:

1. Run object scan if needed.
2. Open Browse v2 media domain.
3. Confirm object card and loose file card both appear.
4. Verify object members do not appear as loose cards.

Expected:

- object badge visible
- loose file badge visible
- storage badges visible

### Playbook C — Object Detail

Fixture: object with members.

Steps:

1. Click object card.
2. Open detail.
3. Inspect role groups and paths.
4. Click a member with `file_id`.

Expected:

- members are visible
- member click can inspect file
- no delete/amend action until Phase 8D

### Playbook D — Compose Inbox Loose Files

Fixture: imported loose files in Inbox.

Steps:

1. Select loose files.
2. Click Compose object.
3. Confirm name/type/root.
4. Create object candidate.
5. Continue review/draft plan.

Expected:

- no execute
- object candidate created
- members folded

### Playbook E — Compose External Loose Files

Fixture: source-scanned external files.

Steps:

1. Select external loose files.
2. Compose object.
3. Confirm source files still exist.
4. Confirm Inbox synthetic folder contains copies.

Expected:

- copy-only
- source preserved
- no direct managed object

### Playbook F — Object Amendment

Fixture: managed object with members.

Steps:

1. Open object detail.
2. Add member or move member out.
3. Generate amendment plan.
4. Mark ready → preflight → execute on disposable fixture.

Expected:

- no delete
- path history/journal written
- member relationship updated only after execute

---

## 18. Risk Register

| Risk | Trigger | Severity | Detection | Mitigation | Stop condition |
|---|---|---|---|---|---|
| Object members visually split into loose files | Adapter does not exclude members | P0 | Browse v2 mixed list QA | Conservative exclusion query; test no-member-split | Any member appears as independent loose card |
| Formal object vs import candidate confusion | Adapter hides source kind | P1 | UI badges / API source field | Add `object_source` | Temporary candidate shown as permanent managed object |
| External source moved | Compose external path reuses managed move logic | P0 | file fixture check | External compose must copy-only to Inbox | Source path missing after compose |
| Direct object creation before execute | Compose managed writes `library_objects` immediately | P0 | DB assertions | Draft plan only before execute | Object exists before execute |
| Missing path history/journal | Amendment execute skips audit | P0 | tests inspect journal/history | Reuse organize execution audit path | Successful path change without history |
| Default browse hides external | storage filter defaults managed | P1 | Search/Browse smoke | Default All | External absent by default |
| Object detail mutates data | detail endpoint does sync/repair | P1 | service tests | detail read-only | GET changes DB or FS |
| Cross-page bulk action | select all silently spans pages | P1 | UI QA | current page only | Hidden files included in action |
| Delete scope creep | shrink action maps to physical delete | P0 | action list / UI | Phase 8D remove relation only | Any delete/rmdir action added |
| Recovery false positive | synthetic object folders treated orphan | P1 | recovery smoke | update recovery read model carefully | clean state reports high severity |
| Duplicate official object models | new table duplicates `library_objects` | P1 | schema review | reuse/extend existing table unless proven impossible | two competing object APIs |
| DetailsPanel fork | page-specific details diverge | P2 | frontend review | shared object detail primitives | copied file details logic |
| Performance regression | mixed card API joins too broadly | P2 | 10k/50k smoke | pagination, indexed filters | browse timeout/large memory |
| Legacy object values hidden | merged labels remove old values | P2 | old data QA | aliases remain displayable | old objects cannot be selected/opened |

---

## 19. Open Questions Before Implementation

1. Phase 7H 当前未提交代码是否已经人工验收并准备进入正式 docs？
2. Browse v2 是否应直接使用当前 `library_objects` 作为 canonical object model，还是先保守 adapter？
3. 导入 execute 后是否应立即创建/更新 `library_objects`，还是继续依赖 object scan？
4. `library_object_members.hidden_from_global` 是否应成为 loose-file exclusion 的权威依据？
5. object detail 是否进入右侧 unified DetailsPanel，还是 Phase 8B 先保留页内 detail？
6. `collection` / `project` 这类旧 object_parser 类型是否纳入 Phase 8 taxonomy？
7. Phase 8A 是否替换现有 Media/Books/Games/Software 页面，还是先以 feature flag 并存？
8. managed loose files 的定义是否包含 `hidden_from_global=false` 的 object members？
9. object amendment action type 是否扩展 `organize_actions.action_type`，还是新增 amendment payload？
10. 需要显示 object missing 状态时，是否读取 recovery diagnostics 即时计算，还是只显示 object scan 状态？
11. `audio` / `asset_pack` 若当前工作区代码未合并，Phase 8 是否阻塞等待 7H？
12. 大对象成员上限是否继续沿用 `MAX_MEMBERS_PER_OBJECT=500`？

---

## 20. Implementation Order and Commit Strategy

### Recommended Order

1. Confirm Phase 7H current working tree and docs status.
2. Phase 8A — Browse taxonomy + read model adapter.
3. Phase 8B decision gate — formal object model sync strategy.
4. Phase 8B — Object detail + member view.
5. Phase 8C — Compose object from loose files.
6. Phase 8D — Object amendment plan.
7. Phase 8E — Domain-specific cards.

### Commit Strategy

Keep phases separate:

- `feat(library-v2): add browse v2 read model`
- `feat(library-v2): add object detail member view`
- `feat(library-v2): compose objects from loose files`
- `feat(library-v2): add object amendment plans`
- `style(frontend): add domain-specific object cards`

Do not mix:

- schema changes with frontend cards
- compose object with amendment execution
- recovery repair with browse UI
- metadata scraper with object cards

---

## 21. Documentation Update Checklist

When Phase 8 implementation lands, update formal docs as needed:

| Phase | Docs to update |
|---|---|
| 8A | `docs/library-v2/README.md`, `ARCHITECTURE.md`, `API_REFERENCE.md`, `MANUAL_ACCEPTANCE_GUIDE.md`, `BETA_TESTING_CHECKLIST.md` |
| 8B | `ARCHITECTURE.md`, `API_REFERENCE.md`, `MANUAL_ACCEPTANCE_GUIDE.md` |
| 8C | `ARCHITECTURE.md`, `API_REFERENCE.md`, `MANUAL_ACCEPTANCE_GUIDE.md`, `KNOWN_LIMITATIONS.md` |
| 8D | `ARCHITECTURE.md`, `API_REFERENCE.md`, `RECOVERY` notes if any, `KNOWN_LIMITATIONS.md` |
| 8E | `MANUAL_ACCEPTANCE_GUIDE.md`, `BETA_TESTING_CHECKLIST.md` |

Also check:

- `README.md` if project status or main chain wording changes.
- `docs/README.md` if formal doc index changes.
- `docs/FILE_CLASSIFICATION_RULES.md` only if classification/type rules change.

---

## 22. Final Recommendation

Phase 8 should proceed, but only after the current Phase 7H working tree is either merged and documented or explicitly excluded from the Phase 8 baseline.

Recommended approach:

1. Do **Phase 8A first** as read-only Browse v2 adapter.
2. Do **not** start 8C/8D before object detail and object model strategy are clear.
3. Reuse current `library_objects` where possible, but do not pretend import candidates are permanent objects.
4. Keep Browse v2 domain navigation content-oriented, not object-vs-file oriented.
5. Keep all mutating object management behind draft plan → ready → preflight → execute.
6. Do not implement deletion, trash, auto repair, metadata scraping, AI classification, poster wall, audio transcription, duplicate/hash, or package release as part of Phase 8.

The safest Phase 8 minimum viable slice is:

```text
8A read-only mixed browse cards
  + object/loose distinction
  + storage scope
  + no member visual splitting
  + file DetailsPanel preserved
```

Only after that should object detail, compose object, and amendment plans be implemented.
