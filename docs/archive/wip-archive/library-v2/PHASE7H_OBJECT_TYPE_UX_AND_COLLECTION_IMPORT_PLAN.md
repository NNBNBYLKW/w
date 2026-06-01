# Phase 7H — Object Type UX and Multi-file Collection Import Plan

> 状态：方案增强稿 / `_wip`  
> 范围：只规划 Phase 7H，不实现代码。  
> Source of truth：当前仓库代码与 `docs/library-v2/` 正式文档优先；下载方案文档用于产品方向补充。  
> 产品边界：Workbench 是 Windows local-first 资产工作台，不是 Explorer 替代品、云 AI 平台、软件安装器或游戏启动器。

---

## 1. Purpose

Phase 7H 的目的不是重做 Library v2 架构，而是在 Phase 7A-7G 已验收基础上补齐两个用户体验缺口：

1. 让用户更容易理解 `final_object_type`，避免在一串近似技术枚举中做选择。
2. 增加“选择多个文件为合集”的导入模式，让用户无需先手动创建文件夹，也能把多个文件作为一个 object candidate 进入现有安全链路。

Phase 7H 必须做到：

- 优化用户看得懂的类型体系。
- 保持后端 enum / 数据语义清晰，API 仍传英文 value。
- 增加 `audio` / `asset_pack` 对象类型能力。
- 支持“选择多个文件为合集”。
- 让多文件合集复用现有 `Import -> Inbox -> Object Detection -> Review -> Organize Candidate -> Draft Plan -> Execute` 链路。
- 不破坏 Library v2 已完成的 copy-only、no-overwrite、人工确认、preflight、path sync、recovery 边界。

Do:

- 将近似类型在前端合并显示。
- 将真实后端 value 与用户 label 分离。
- 继续要求用户确认最终类型、对象名、目标 root。
- 继续让所有真实文件操作走 operation journal / path history。

Don't:

- 不把中文 label 写入后端。
- 不删除旧后端 value。
- 不让多文件合集绕过 review / draft plan / execute。
- 不让 AI 自动分类、自动写事实或执行移动。
- 不在本方案阶段实现代码。

---

## 2. Current Baseline

### 2.1 当前正式状态

当前正式文档入口是 `docs/library-v2/`。

| Fact | Evidence |
|---|---|
| Library v2 Phase 7A-7F 已完成，195 tests | `docs/library-v2/README.md`, `docs/library-v2/PHASE7_COMPLETION_REPORT.md` |
| README 已声明 Phase 7A-7G complete | `README.md` |
| 当前主链是 Import → Inbox → Object Detection → Review → Organize Candidate → Draft Plan → Execute → Managed Library → Browse/Search/Details → Recovery | `docs/library-v2/README.md`, `docs/library-v2/ARCHITECTURE.md` |
| Library v2 是 hybrid mode，source-scan beta 主线仍有效 | `docs/library-v2/README.md`, `docs/library-v2/ARCHITECTURE.md` |
| 正式 API route 文件没有 `/api` 前缀，Library v2 import routes 在 `/library/import` 下 | `docs/library-v2/API_REFERENCE.md`, `apps/backend/app/api/routes/importing.py` |
| `docs/library-v2/FINAL_ACCEPTANCE_SUMMARY.md` 当前不存在 | 只读检查 `Test-Path docs/library-v2/FINAL_ACCEPTANCE_SUMMARY.md` |

### 2.2 当前导入模式

| Mode | Current support | Evidence |
|---|---|---|
| File import | 已支持，`POST /library/import/batches/{id}/files`，每个文件成为独立 `inbox_item` | `apps/backend/app/api/routes/importing.py`, `apps/backend/app/services/importing/service.py`, `docs/library-v2/API_REFERENCE.md` |
| Folder as object | 已支持，`POST /library/import/batches/{id}/folders`，`mode="object"`，默认保留文件夹边界 | `apps/backend/app/api/routes/importing.py`, `apps/backend/app/services/importing/service.py` |
| Folder as loose files | 已支持，`mode="loose_files"`，显式拆散 | `apps/backend/app/api/routes/importing.py`, `LibraryInboxPanel.tsx` |
| Multi-file collection import | 未支持。当前多选文件会走 file import，成为多个独立 `inbox_item`，不会自动创建 synthetic object folder / `import_object_candidate` | `apps/frontend/src/services/api/importingApi.ts`, `apps/backend/app/api/routes/importing.py` |

### 2.3 当前 final_object_type / detected object type

当前前端下拉硬编码对象类型：

```text
movie
clip
course
anime
video_collection
clip_set
movie_collection
game
software
imgset
comic
photo_event
web_image_set
docset
```

Evidence：`apps/frontend/src/features/library/LibraryInboxPanel.tsx` 中 `OBJECT_TYPE_OPTIONS`。

当前 object boundary detection 可建议：

```text
software
game
imgset
comic
photo_event
course
anime
video_collection
unknown
```

Evidence：`apps/backend/app/services/importing/object_boundary.py`。

当前 loose-file import 的 `_detect_object_type()` 已可把 `file_kind="audio"` 映射成 `audio`，但这不是完整对象类型支持：

- `audio` 不在 `LibraryInboxPanel.tsx` 的 `OBJECT_TYPE_OPTIONS`。
- `audio` 不在 `PLAN_TARGET_DIRS`。
- `audio` 不在 `OBJECT_PREFIX`。
- `audio` 不在 `object_parser.py` 的 `SUPPORTED_OBJECT_TYPES`。

Evidence：`apps/backend/app/services/importing/service.py`, `apps/backend/app/services/library/organize.py`, `apps/backend/app/services/library/organize_template_renderer.py`, `apps/backend/app/services/library/object_parser.py`。

`asset_pack` 当前未在后端/前端对象类型链路中出现。

### 2.4 当前 PLAN_TARGET_DIRS

`apps/backend/app/services/library/organize.py` 中当前 `PLAN_TARGET_DIRS`：

| Type | Target dir |
|---|---|
| `movie` | `10_Movies_Anime/Movies` |
| `anime` | `10_Movies_Anime/Anime` |
| `game` | `20_Games` |
| `software` | `30_Software` |
| `course` | `40_Videos/Courses` |
| `imgset` | `30_Images/Image_Sets` |
| `docset` | `80_Documents/Docsets` |
| `clip` | `40_Videos/Clips` |
| `video_collection` | `40_Videos/Collections` |
| `clip_set` | `40_Videos/Clip_Sets` |
| `movie_collection` | `10_Movies_Anime/Collections` |
| `photo_event` | `30_Images/Photo_Events` |
| `web_image_set` | `30_Images/Web_Images` |

Missing for Phase 7H:

- `audio`
- `asset_pack`
- likely `comic` target path, unless current execution intentionally maps it through fallback or another route.

Current risk：`LibraryOrganizeService._target_dir()` 会把不在 `PLAN_TARGET_DIRS` 的类型 fallback 到 `clip`。

### 2.5 当前 OBJECT_PREFIX

`apps/backend/app/services/library/organize_template_renderer.py` 中当前 `OBJECT_PREFIX`：

| Type | Prefix |
|---|---|
| `movie` | `MOVIE` |
| `anime` | `ANIME` |
| `game` | `GAME` |
| `software` | `SOFTWARE` |
| `course` | `COURSE` |
| `imgset` | `IMGSET` |
| `docset` | `DOCSET` |
| `clip` | `CLIP` |
| `video_collection` | `VIDEO_COLL` |
| `clip_set` | `CLIP_SET` |
| `movie_collection` | `MOVIE_COLL` |
| `photo_event` | `PHOTO_EVENT` |
| `web_image_set` | `WEB_IMAGE` |

Missing for Phase 7H:

- `audio`
- `asset_pack`
- likely `comic`, if comic should execute to a distinct managed object prefix.

### 2.6 当前 folder-as-object import 如何工作

Current facts:

- `ImportService.import_folder_to_batch()` 默认 `mode="object"`。
- 它 copy 整个文件夹到 `{managed_root}/00_Inbox/<batch_id>/<folder_name>/`。
- 它调用 `detect_object_type(inbox_folder.name, member_rel_paths)`。
- 它创建 `import_object_candidate`。
- 它为每个成员文件创建 `files` row、`inbox_item`、`import_object_member`。
- 它设置 `launch_file_id` / `primary_file_id`（如果 detection 给出）。
- 前端对象 candidate 展示 member groups，成员默认折叠在 object card 下。

Evidence：

- `apps/backend/app/services/importing/service.py`
- `apps/backend/app/services/importing/object_boundary.py`
- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- `docs/library-v2/MANUAL_ACCEPTANCE_GUIDE.md`

### 2.7 当前 loose file import 如何工作

Current facts:

- `POST /library/import/batches/{id}/files` 复制多个文件到 batch inbox。
- 每个文件成为独立 `inbox_item`。
- `ImportService._detect_object_type()` 按 `file_kind` 给 loose file 一个初步 type。
- 当前前端 default mapping 中 `audio` 被映射为 `clip`，`image` 被映射为 `image`，但 `image` 不是当前下拉对象类型之一，属于需要修正的现状。

Evidence：

- `apps/backend/app/services/importing/service.py`
- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`

### 2.8 当前 confirm / candidate / draft plan / execute / path sync 串联

Current chain:

```text
Inbox item or object candidate
-> confirm final_object_type + target_library_root_id
-> create OrganizeCandidate
-> generate draft OrganizePlan
-> mark-ready / preflight / execute via organize pipeline
-> successful move syncs files.path / storage_state / managed_root_id / managed_at
-> writes file_path_history + operation_journal
```

Object candidates generate one organize candidate; members are not split into independent organize candidates.

Evidence：

- `apps/backend/app/services/importing/service.py`
- `apps/backend/app/services/library/organize.py`
- `docs/library-v2/ARCHITECTURE.md`
- `docs/library-v2/PHASE7_COMPLETION_REPORT.md`

### 2.9 当前 final_object_type 下拉如何生成

Current facts:

- 前端 `LibraryInboxPanel.tsx` 使用本地常量 `OBJECT_TYPE_OPTIONS`。
- label 来自 `features.library.inbox.objectTypes.<type>`。
- 下拉未分组。
- `imgset` / `photo_event` / `web_image_set` 当前显示为不同选项。
- `clip` / `clip_set` 当前显示为不同选项。
- `audio` / `asset_pack` 当前不在下拉中。

Evidence：

- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- `apps/frontend/src/locales/en/features.ts`
- `apps/frontend/src/locales/zh-CN/features.ts`

### 2.10 当前图片 / 视频 / 软件 / 游戏 / 文档 / 脚本 detection

Current object boundary detection:

- Software：有可执行文件，且非游戏路径/游戏 DLL，或目录名含 tool/app/software/utility/中文软件提示。
- Game：有可执行文件并匹配 game dll/path/data dir signals。
- Image set：同目录图片数 `>= 5`，可进一步建议 `comic` / `photo_event` / `imgset`。
- Video collection：同目录视频数 `>= 2`，可进一步建议 `course` / `anime` / `video_collection`。
- Docs/config/dll/subtitle/cover 等作为 member roles，而不是独立对象。
- Script extensions (`bat/cmd/ps1/sh/py/rb/pl`) 在全局 classification 中是 `executable` / `software`。

Evidence：

- `apps/backend/app/services/importing/object_boundary.py`
- `apps/backend/app/core/classification.py`
- `docs/FILE_CLASSIFICATION_RULES.md`

### 2.11 Current limitations relevant to 7H

| Limitation | Evidence | Phase 7H implication |
|---|---|---|
| Duplicate/hash pipeline 未实现 | `docs/library-v2/KNOWN_LIMITATIONS.md` | 多文件合集不能依赖 hash 去命名或去重 |
| Detection rule-based，不是 AI | `docs/library-v2/KNOWN_LIMITATIONS.md`, `object_boundary.py` | Type suggestion 必须可被用户覆盖 |
| No app-level trash/delete | `docs/library-v2/KNOWN_LIMITATIONS.md` | 多文件合集失败处理不能自动删除源/目标 |
| No move import/source cleanup | `docs/library-v2/KNOWN_LIMITATIONS.md` | 7H 继续 copy-only |
| No persistent recovery findings | `docs/library-v2/KNOWN_LIMITATIONS.md` | 7H recovery 只复用现有 scan/retry |
| No strict SQL check constraint found for `final_object_type` | `apps/backend/app/db/models/importing.py` uses `String` | `audio` / `asset_pack` 可能不需 DB schema migration，但仍要检查 service/API validators and plan target maps |

---

## 3. Product Decisions

以下 10 个方向已由用户确认，本计划不重新争论，只记录 implementation implications。

| # | Decision | Implementation implication |
|---|---|---|
| 1 | `course` 不并入普通视频合集，但改名和重新定位为“课程 / 讲座资料” | 前端 label/help text 更新；后端 value 保持 `course` |
| 2 | `anime` 不并入电影合集 | `anime` 继续独立，强调 Series / Season / Episode |
| 3 | `imgset` / `photo_event` / `web_image_set` 用户侧合并显示为“图片合集 / 相册” | 前端 grouped option 或 alias display；旧值继续支持 |
| 4 | `clip` / `clip_set` 用户侧合并显示为“视频素材 / 片段” | 下拉降低区分成本；内部 value 可保留 |
| 5 | 新增 `audio` | 增加 label、target dir、prefix、allowed type、tests |
| 6 | 新增 `asset_pack` | 增加 label、target dir、prefix、detection/tests；不能自动吞掉全部 unknown |
| 7 | 新增“选择多个文件为合集” | 新 API / frontend modal / synthetic inbox object folder |
| 8 | 多选文件合集名称默认用公共前缀；无公共前缀用 `Collection YYYY-MM-DD HHmm`；用户可修改 | 前后端均需校验 sanitized `collection_name` |
| 9 | 多选多个视频默认建议 `video_collection` / “视频合集 / 系列视频” | detection suggestion，不是强制 final |
| 10 | `asset_pack` 可以包含任意文件类型 | 成员类型不限制；最终类型仍需用户确认 |

---

## 4. Revised User-facing Object Type System

### 4.1 User-facing table

| Group | 中文 label | English label | Backend value | Status | Notes |
|---|---|---|---|---|---|
| 视频 | 电影 / 长视频 | Movie / Long video | `movie` | Existing | 单个完整影视作品 |
| 视频 | 动漫 / 剧集 | Anime / Series | `anime` | Existing | Series / Season / Episode 结构 |
| 视频 | 课程 / 讲座资料 | Course / Lecture materials | `course` | Existing, relabeled | 带附件、资料、章节或记录属性的视频集合 |
| 视频 | 视频合集 / 系列视频 | Video collection / Series videos | `video_collection` | Existing | 多个相关视频，但非课程/剧集结构 |
| 视频 | 视频素材 / 片段 | Video clips / Footage | `clip` | Existing, merged display | 单个视频素材 |
| 视频 | 视频素材 / 片段 | Video clips / Footage | `clip_set` | Existing, merged display | 多个片段组成的素材集合 |
| 视频 | 电影合集 | Movie collection | `movie_collection` | Existing | 多部独立电影组成的 collection |
| 图片 | 图片合集 / 相册 | Image set / Album | `imgset` | Existing, merged display | 默认图片合集 value |
| 图片 | 图片合集 / 相册 | Image set / Album | `photo_event` | Existing, merged display | 旧数据/内部 value 保留 |
| 图片 | 图片合集 / 相册 | Image set / Album | `web_image_set` | Existing, merged display | 旧数据/内部 value 保留 |
| 图片 | 漫画 / 连续图片 | Comic / Sequential images | `comic` | Existing in frontend/detection | 顺序图片页 |
| 应用 | 软件 / 工具 | Software / Tool | `software` | Existing | 软件包、工具程序 |
| 应用 | 游戏 | Game | `game` | Existing | 游戏目录 |
| 文档 | 文档 / 资料包 | Document set / Materials | `docset` | Existing | 文档、PDF、资料包 |
| 音频 | 音频 / 录音 | Audio / Recording | `audio` | New object type | 不拆 music_album/recording/podcast/sound_effect |
| 素材 | 素材包 | Asset pack | `asset_pack` | New object type | 字体、音效、贴图、3D/2D 素材、混合项目素材 |

### 4.2 UI grouping recommendation

Recommendation for frontend dropdown:

```text
视频
  电影 / 长视频
  动漫 / 剧集
  课程 / 讲座资料
  视频合集 / 系列视频
  视频素材 / 片段
  电影合集

图片
  图片合集 / 相册
  漫画 / 连续图片

应用
  软件 / 工具
  游戏

文档
  文档 / 资料包

音频
  音频 / 录音

素材
  素材包
```

Do:

- Use grouped labels and short helper text.
- Keep backend value in `<option value>`.
- Send only backend value to API.
- Allow blank / requires user confirmation for uncertain candidates.

Don't:

- Do not force users to distinguish `photo_event` vs `web_image_set` in the normal flow.
- Do not remove support for legacy values.
- Do not localize backend enum values.

---

## 5. Backend Value Mapping

| Backend value | User-facing label | Mapping rule |
|---|---|---|
| `movie` | 电影 / 长视频 | Direct |
| `anime` | 动漫 / 剧集 | Direct |
| `course` | 课程 / 讲座资料 | Relabel/reposition |
| `video_collection` | 视频合集 / 系列视频 | Direct |
| `clip` | 视频素材 / 片段 | Merged display |
| `clip_set` | 视频素材 / 片段 | Merged display |
| `movie_collection` | 电影合集 | Direct |
| `imgset` | 图片合集 / 相册 | Merged display default |
| `photo_event` | 图片合集 / 相册 | Merged display legacy/alias |
| `web_image_set` | 图片合集 / 相册 | Merged display legacy/alias |
| `comic` | 漫画 / 连续图片 | Direct |
| `software` | 软件 / 工具 | Direct |
| `game` | 游戏 | Direct |
| `docset` | 文档 / 资料包 | Direct |
| `audio` | 音频 / 录音 | New |
| `asset_pack` | 素材包 | New |

Rules:

- Frontend label 可以合并显示。
- Backend value 不应被中文污染。
- API 仍传英文 enum。
- 旧值不能直接删除，避免破坏旧数据、旧 plans、旧 object folders。
- If `object_parser.py` remains prefix-based, new/expanded values must have matching prefixes or explicit fallback behavior.

Current source mismatch to handle during implementation:

- `apps/backend/app/services/library/object_parser.py` 当前 `SUPPORTED_OBJECT_TYPES` 不包含 `software`, `video_collection`, `clip_set`, `movie_collection`, `photo_event`, `web_image_set`, `comic`, `audio`, `asset_pack` 等部分 Phase 7 object values。Phase 7H 实现时需确认这是 intentional legacy scanner limitation，还是需要补齐 managed object parsing。

---

## 6. Import UX Redesign

### 6.1 Proposed import entry layout

```text
导入散文件
  - 选择文件
  - 选择文件夹并拆散导入

导入为对象 / 合集
  - 选择文件夹为对象
  - 选择多个文件为合集
```

### 6.2 Import entry behavior

| Entry | User selects | Result | Best for | Creates inbox_item | Creates import_object_candidate | Creates import_object_members | Copy-only | User confirmation |
|---|---|---|---|---|---|---|---|---|
| 选择文件 | One or more files | Each file becomes independent inbox item | 零散文档、单图、单视频 | Yes | No | No | Yes | Per item before organize candidate |
| 选择文件夹并拆散导入 | One folder | Each file becomes independent inbox item | 用户明确要拆散目录 | Yes | No | No | Yes | Per item |
| 选择文件夹为对象 | One folder | Folder becomes one object candidate | 软件包、游戏包、图集、课程目录 | Yes, for members | Yes | Yes | Yes | Object type + root + launch candidate |
| 选择多个文件为合集 | Multiple files | Files copied into synthetic inbox object folder and become one object candidate | 用户不想先手动建文件夹的合集 | Yes, for members | Yes | Yes | Yes | Modal before copy + review before plan |

Do:

- Make “选择文件夹为对象” the recommended default for folder selection.
- Explain that software/game/image/video folders will not be split.
- Make “选择文件夹并拆散导入” explicit and lower priority.
- Make “选择多个文件为合集” visually distinct from ordinary file import.

Don't:

- Do not create batches on cancel.
- Do not execute organize plan from import UI.
- Do not imply selected files are moved; they are copied.

---

## 7. Multi-file Collection Import Design

### 7.1 Flow

```text
User clicks "选择多个文件为合集"
-> Electron / frontend file picker returns multiple file paths
-> Frontend opens "创建合集" confirmation modal
-> System generates collection_name
-> System suggests final_object_type
-> System suggests target root
-> User may edit name / type / root
-> Confirm import
-> Backend creates import_batch
-> Backend copies files into 00_Inbox/<batch_id>/<collection_name>/
-> Backend creates files rows
-> Backend creates inbox_items
-> Backend creates import_object_candidate
-> Backend creates import_object_members
-> Review / candidate / draft plan / execute reuse existing 7C/7D chain
```

### 7.2 Synthetic inbox object folder

Example input:

```text
Lesson 01.mp4
Lesson 02.mp4
Lesson 03.mp4
cover.jpg
materials.pdf
```

Backend target:

```text
00_Inbox/
  <batch_id>/
    Lesson/
      Lesson 01.mp4
      Lesson 02.mp4
      Lesson 03.mp4
      cover.jpg
      materials.pdf
```

This synthetic folder is an import-time object boundary. It is not a user-created source folder, but it should behave like folder-as-object after copy.

### 7.3 Collection name generation

Algorithm draft:

1. Strip extensions from selected basenames.
2. Normalize separators (`_`, `-`, `.`, repeated spaces) to spaces.
3. Find longest common prefix across normalized basenames.
4. Trim trailing numeric/episode tokens if they are sequence-only.
5. If prefix length is meaningful, use it.
6. Else fallback to `Collection YYYY-MM-DD HHmm`.
7. Sanitize with the same Windows-safe logic used for organize folder names.
8. If target folder conflicts, apply no-overwrite suffix.
9. User can override before batch creation.

Examples:

| Selected files | Suggested collection_name |
|---|---|
| `Lesson 01.mp4`, `Lesson 02.mp4`, `Lesson 03.mp4` | `Lesson` |
| `S01E01.mkv`, `S01E02.mkv`, `S01E03.mkv` | `S01` or user-edit prompt; avoid finalizing poor names silently |
| `IMG_0001.jpg`, `IMG_0002.jpg` | `IMG` if acceptable, otherwise user-edit prompt |
| `dog.jpg`, `run.mp4`, `notes.pdf` | `Collection 2026-05-15 2158` |

Implementation note:

- If common prefix is too generic (`IMG`, `VID`, `DSC`, `S01`) the modal should show a warning/helper and encourage user editing.

### 7.4 Type suggestion rules for selected files

| Selected file set | Suggested type | Notes |
|---|---|---|
| Multiple videos | `video_collection` | Default for Phase 7H |
| Videos + PDF/PPT/DOC/ZIP/notes/projects | `course` | “课程 / 讲座资料” |
| Multiple images | `imgset` | User label “图片合集 / 相册” |
| Numbered images / comic keywords | `comic` | Suggest only |
| Multiple audio files | `audio` | New object type |
| Mixed creative assets | `asset_pack` | Suggest only; do not swallow all unknown |
| Software/game folder-like selected members | Usually `asset_pack` or require confirmation | Multi-file selection lacks folder hierarchy; be conservative |
| Uncertain mix | Blank / requires user confirmation | Must not force final |

### 7.5 Safety behavior

Required:

- copy-only
- no source delete
- no source move
- no overwrite
- temporary copy + atomic replace pattern where applicable
- cancel creates no batch
- empty selection rejected
- invalid/non-file paths rejected or recorded as failed
- source files preserved even if partial copy fails
- object confirm does not execute
- create-candidate does not execute
- draft plan still requires organize mark-ready/preflight/execute

### 7.6 API shape recommendation

Current route style uses `/library/import` router prefix and batch-oriented file/folder endpoints.

Recommended endpoint:

```text
POST /library/import/file-collections
```

Reason:

- It can create its own import batch only after user confirms the modal.
- It keeps cancel/no-batch behavior simple.
- It avoids requiring the frontend to create an empty batch before the user decides name/type/root.
- It matches the product action: “import these files as one collection”.

Alternative if implementation prefers explicit batch ownership:

```text
POST /library/import/batches/{id}/file-collection
```

Use only if the existing UI explicitly creates a batch before import. Otherwise prefer the single action endpoint.

---

## 8. Type Detection Rules

### 8.1 Current backend location

Object-level detection should be centered in:

```text
apps/backend/app/services/importing/object_boundary.py
```

This file is already pure, side-effect-free, and used by folder-as-object import.

Frontend can pre-compute display suggestions for the modal, but backend must re-detect or validate. Frontend suggestions are UX hints only.

### 8.2 Video rules

| Signal | Suggested type | Notes |
|---|---|---|
| Multiple video files | `video_collection` | Default generic collection |
| Filenames contain `S01E01`, `E01`, `EP01` | `anime` or `video_collection` depending context | If folder/name has anime/season signal, prefer `anime` |
| Consecutive lesson/chapter names | `course` | Especially with lesson/tutorial/course terms |
| Directory/name contains course/tutorial/lesson/lecture/课程/教程 | `course` | Repositioned as “课程 / 讲座资料” |
| Video + documents/slides/notes/project attachments | `course` | Strong Phase 7H addition |
| Directory/name contains anime/season/动漫/番剧 | `anime` | Series/season/episode structure |
| Subtitles present | Supporting role `subtitle` | Does not alone determine type |
| Cover/poster image present | Role `cover` | Does not alone determine type |

Do not auto-finalize; these are suggestions.

### 8.3 Image rules

| Signal | Suggested type | Notes |
|---|---|---|
| Image count threshold (`>=5` current) | `imgset` | Current hard-coded threshold exists |
| Sequential image names (`001`, `002`, pages) | `comic` | Suggest if sequence is strong |
| Folder/name contains comic/manga/漫画 | `comic` | Strong signal |
| Folder/name contains album/photo/相册/照片 | `imgset` or legacy `photo_event` | User label remains “图片合集 / 相册” |
| Cover/preview file | Role `cover` | Member role, not final type alone |
| Similar dimensions/ratio | Future | Do not implement in Phase 7H unless separate scope |

### 8.4 Audio rules

Initial object type:

```text
audio
```

Candidate extensions:

```text
mp3, wav, flac, ogg, m4a, aac, opus
```

Current source mismatch:

- `classification.py` currently includes `flac`, `mp3`, `ogg`, `wav`.
- Phase 7H should decide whether `m4a`, `aac`, `opus` are added now or deferred.

Do not split into:

- `music_album`
- `recording`
- `podcast`
- `sound_effect`

Use tags later for those distinctions.

### 8.5 Asset pack rules

Suggested type:

```text
asset_pack
```

Signals:

- Mixed creative files: `psd`, `ai`, `blend`, `fbx`, `obj`, `glb`, `gltf`, fonts, textures, sounds, references.
- Directory names: `assets`, `resources`, `textures`, `fonts`, `materials`, `references`, `samples`, `pack`.
- Multiple unrelated file kinds where none of video/image/doc/software/game dominates.

Important:

- `asset_pack` can contain any file type.
- It must not become an automatic bucket for all unknown files.
- If confidence is low, leave final type blank and require user confirmation.

### 8.6 Software/game rules

Current rules are a good baseline:

- `.exe`, `.bat`, `.cmd`, `.ps1`, `.sh`, `.py`, `.rb`, `.pl` can be launch candidates.
- `setup`, `install`, `installer`, `uninstall`, `update`, `patch`, `redist`, `crash_reporter`, `launcher_update` should be excluded or downgraded as main launch candidate.
- `.dll`, configs, assets, plugins, resources are members.
- Game signals include `UnityPlayer.dll`, `*_Data`, `Engine`, `Binaries`, `Content`, `Mods`, Steam/GOG/Epic path hints.

Phase 7H must preserve:

- `launch_file_id` is a suggestion.
- User can change launch candidate in review panel.
- Organize plan moves object root, not scattered component files.

### 8.7 Rules that must not auto-force final type

Never automatically finalize:

- `asset_pack` for arbitrary unknown folder
- `course` from a single video plus one unrelated doc without clear signal
- `game` solely from folder name without executable/data signals
- `audio` when selection contains mixed audio plus many unrelated project files

Uncertain result should be:

```text
suggested_object_type = null or "unknown"
final_object_type = null
requires user confirmation
```

---

## 9. Backend Implementation Plan

### 9.1 Files likely changed

Expected backend files for later implementation:

- `apps/backend/app/services/importing/object_boundary.py`
- `apps/backend/app/services/importing/service.py`
- `apps/backend/app/services/importing/recovery.py` (likely no behavior change; verify synthetic folders are not false positives)
- `apps/backend/app/api/routes/importing.py`
- `apps/backend/app/schemas/importing.py`
- `apps/backend/app/repositories/importing/repository.py` (only if new query/create helpers are needed)
- `apps/backend/app/services/library/organize.py`
- `apps/backend/app/services/library/organize_template_renderer.py`
- `apps/backend/app/services/library/object_parser.py` (verify/extend managed object parser support)
- `apps/backend/app/core/classification.py` (only if adding audio extensions or asset file-kind hints)
- `apps/backend/tests/test_library_v2_object_type_ux.py` (new)
- `apps/backend/tests/test_library_v2_file_collection_import.py` (new)

### 9.2 Object type validation / allowed values

Current source does not show a central strict enum validator for `final_object_type`; confirm/creation mainly requires non-empty string and target root checks.

Phase 7H should introduce or document a central allowed-object-type list before expanding values. Recommended location:

```text
apps/backend/app/services/importing/object_types.py
```

or if avoiding a new file:

```text
apps/backend/app/services/importing/service.py
```

Recommended constants:

```text
CANONICAL_OBJECT_TYPES
LEGACY_OBJECT_TYPES
USER_VISIBLE_OBJECT_GROUPS
```

Do not put frontend labels in backend constants.

### 9.3 PLAN_TARGET_DIRS updates

Add:

```text
audio -> 50_Audio
asset_pack -> 60_Assets
comic -> 30_Images/Comics
```

Needs verification:

- Whether `comic` should get its own target path in Phase 7H or remain a display/detection value that maps into `imgset`-like image directories.
- Whether numbering `50_Audio` and `60_Assets` conflicts with current library template conventions.

### 9.4 OBJECT_PREFIX updates

Add:

```text
audio -> AUDIO
asset_pack -> ASSET
comic -> COMIC
```

Needs verification:

- Whether `VIDEO_COLL`, `MOVIE_COLL`, `WEB_IMAGE` naming should remain as-is or be normalized in a later non-breaking migration. Do not rename existing prefixes in Phase 7H.

### 9.5 ImportService updates

Add a new service method, for example:

```text
import_file_collection(
  session,
  *,
  paths: list[str],
  collection_name: str,
  final_object_type: str | None,
  target_library_root_id: int | None,
)
```

Recommended behavior:

1. Reject empty path list.
2. Validate all paths are files.
3. Sanitize `collection_name`.
4. Create import batch only after validation and user confirmation.
5. Create `00_Inbox/<batch_id>/<collection_name>/` with no-overwrite suffix.
6. Copy selected files into the synthetic folder.
7. Register each file into `files`.
8. Create member `inbox_items`.
9. Create one `import_object_candidate`.
10. Create `import_object_members`.
11. Set candidate `suggested_object_type` from backend detection.
12. If request includes user-confirmed `final_object_type`, set it only as confirmed/draft per chosen API semantics.

Important:

- If modal confirmation includes `final_object_type`, backend may set `final_object_type` but should still require explicit confirm action unless API contract says this endpoint both imports and confirms. Safer default: import creates pending_review candidate with suggestion; user confirms in existing review panel.

### 9.6 ImportRecoveryService impact

Expected:

- No major recovery architecture change.
- Synthetic collection folders should behave like folder-as-object folders.
- Verify orphan detection does not treat synthetic object folder contents as loose orphan files.
- Verify retry failed import handles collection member failures without deleting source or partial target.

### 9.7 object_boundary.py updates

Add:

- Audio extension set and detection.
- Asset pack signal detection.
- Multi-file collection detection helper that can operate on selected basenames without original folder path.
- Video + document attachment -> `course`.
- Mixed creative assets -> `asset_pack` or blank/unknown if low confidence.

Keep:

- Pure function.
- No DB access.
- No filesystem writes.
- Rule-based only.

### 9.8 Route endpoint recommendation

Recommended new route:

```text
POST /library/import/file-collections
```

Request draft:

```json
{
  "paths": ["C:/source/Lesson 01.mp4", "C:/source/Lesson 02.mp4"],
  "collection_name": "Lesson",
  "suggested_object_type": "video_collection",
  "target_library_root_id": 1
}
```

Response draft:

```json
{
  "batch": { "id": 123, "status": "completed" },
  "object_candidate": {
    "id": 456,
    "suggested_object_type": "video_collection",
    "final_object_type": null,
    "member_count": 2
  },
  "members": [
    { "inbox_item_id": 1, "file_id": 10, "role": "episode_video" }
  ],
  "failed_items": []
}
```

Validation:

- `paths` non-empty.
- Each path exists and is file.
- No directories accepted in this endpoint.
- `collection_name` required after frontend confirmation.
- `collection_name` sanitized and length-limited.
- `target_library_root_id`, if provided, must be enabled.
- `suggested_object_type`, if provided, must be known or ignored as frontend hint.

Errors:

- 400 for empty selection.
- 400 for invalid path / directory path.
- 400 for disabled target root.
- 400/207-like structured response for partial copy failures, following existing import API style.

Safety:

- copy-only.
- source preserved.
- no overwrite.
- cancel creates no batch.
- create object candidate only; no organize execution.

### 9.9 Path sync reuse

Expected reuse:

- A synthetic object candidate should create an `OrganizeCandidate` with `source_path=oc.inbox_root_path`.
- Existing object execute path sync should move the synthetic root and sync member relative paths.

Must test:

- `files.path` updates for all selected member files.
- `file_path_history` written for all member files.
- `operation_journal` entries identify collection import and execute sync.

---

## 10. Frontend Implementation Plan

### 10.1 Files likely changed

Expected frontend files for later implementation:

- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- `apps/frontend/src/services/api/importingApi.ts`
- `apps/frontend/src/services/desktop/filePicker.ts`
- `apps/frontend/src/locales/en/features.ts`
- `apps/frontend/src/locales/zh-CN/features.ts`
- `apps/frontend/src/entities/file/types.ts` (only if object type typing is introduced there)
- `apps/frontend/src/entities/media/types.ts` (likely no change unless audio browse label impacted)

### 10.2 Type dropdown UX

Phase 7H-1 should refactor the type dropdown into a reusable data structure:

```text
ObjectTypeGroup[]
  groupLabelKey
  options[]
    value
    labelKey
    descriptionKey
    displayAliasGroup?
```

Requirements:

- `audio` and `asset_pack` can be added without scattered arrays.
- `imgset/photo_event/web_image_set` display under one user-facing group or one default visible option plus “advanced legacy values”.
- `clip/clip_set` display as one user-facing concept.
- Backend value remains exact.
- If backend record has legacy value, display the merged label but preserve value on update unless user changes it.

Do:

- Use helper text for `course`, `anime`, `asset_pack`.
- Allow blank type for uncertain candidates.

Don't:

- Do not hide current value if an existing candidate uses legacy value.
- Do not send display label to API.

### 10.3 Import mode UI

Current mode picker supports:

```text
files
folder-as-object
folder-as-loose
```

Add:

```text
file-collection
```

Recommended display:

```text
导入散文件
  [选择文件]
  [选择文件夹并拆散导入]

导入为对象 / 合集
  [选择文件夹为对象]
  [选择多个文件为合集]
```

### 10.4 Desktop file picker bridge

Current frontend uses:

- `selectImportFiles()`
- `selectImportFolder()`

Needs verification:

- Whether `selectImportFiles()` already supports multi-select reliably through Electron bridge.
- Whether manual path fallback can distinguish “file collection” from ordinary file import.

If bridge already returns multiple paths, no desktop API change may be needed.

If not, add a narrow file-picker bridge method for multi-select files only. Do not add broad filesystem management APIs.

### 10.5 Collection creation modal

Fields:

- `collection_name`
- `final_object_type` or suggested type
- `target_library_root_id`
- selected file count
- file preview list
- source-preserved safety copy

States:

- empty selection rejected before modal.
- invalid collection name blocks confirm.
- disabled root blocks confirm.
- cancel closes modal and creates no batch.
- import button disabled while importing.
- partial failures visible after API response.

### 10.6 Object candidate review panel updates

Add/ensure:

- suggested type label + confidence.
- reason/signals if available.
- member count.
- launch candidate selector remains editable.
- cover candidate display if available.
- member preview groups:
  - Launch
  - Videos
  - Images
  - Audio
  - Documents
  - Components
  - Assets
  - Unknown

Rule:

- Members can have `files` rows and `inbox_items`, but UI default must show the object candidate as the unit of review.
- Members must remain folded under the object candidate unless the user explicitly chooses loose-file import or a future explicit “split object” action.

### 10.7 i18n

Add/update keys in:

- `apps/frontend/src/locales/en/features.ts`
- `apps/frontend/src/locales/zh-CN/features.ts`

Required labels:

- 课程 / 讲座资料
- 动漫 / 剧集
- 视频合集 / 系列视频
- 视频素材 / 片段
- 图片合集 / 相册
- 音频 / 录音
- 素材包
- 选择多个文件为合集
- 创建合集
- 合集名称
- 原文件不会移动或删除
- 不确定，稍后选择

---

## 11. Data Model Impact

### 11.1 Expected schema impact

Current models use `String` fields for:

- `InboxItem.final_object_type`
- `ImportObjectCandidate.suggested_object_type`
- `ImportObjectCandidate.final_object_type`
- `ImportObjectMember.role`

Evidence：`apps/backend/app/db/models/importing.py`。

Therefore:

- Adding `audio` / `asset_pack` as values likely does not require a DB schema migration.
- Multi-file collection can reuse `import_batches`, `inbox_items`, `import_object_candidates`, `import_object_members`.
- New table is not required for Phase 7H-3.

Needs verification:

- `apps/backend/app/db/migrations/0002_library_v2.sql` has no strict check constraints for object type.
- Any hidden service validators or tests may still reject new values.
- Existing ensure helpers may need no-op update only if a central allowed list is introduced.

### 11.2 Data model reuse

| Concept | Reuse |
|---|---|
| Collection import batch | `import_batches` |
| Synthetic object folder | `import_object_candidates.inbox_root_path` |
| Original selected source files | `inbox_items.source_path`, `files.original_path` |
| Copied inbox member paths | `inbox_items.inbox_path`, `files.path` while `storage_state=inbox` |
| Member relationship | `import_object_members` |
| Final user type | `ImportObjectCandidate.final_object_type` |
| Target root | `ImportObjectCandidate.target_library_root_id` |
| Execute traceability | `organize_actions.import_object_candidate_id` |
| Path sync | `file_path_history` |
| Operation audit | `operation_journal` |

### 11.3 No schema change by default

Phase 7H should prefer no schema/migration unless implementation discovers:

- strict enum/check constraints,
- missing required fields for synthetic collection naming,
- inability to record necessary operation identity,
- recovery needs a persisted collection-specific marker.

If such a need appears, stop and update the plan before implementation.

---

## 12. API Reference Draft

### 12.1 Multi-file collection import

| Field | Draft |
|---|---|
| Method | `POST` |
| Path | `/library/import/file-collections` |
| Purpose | Copy selected files into a synthetic inbox object folder and create one `import_object_candidate` |

Request:

```json
{
  "paths": [
    "C:/Temp/Lesson 01.mp4",
    "C:/Temp/Lesson 02.mp4"
  ],
  "collection_name": "Lesson",
  "suggested_object_type": "video_collection",
  "target_library_root_id": 1
}
```

Response:

```json
{
  "batch_id": 12,
  "object_candidate_id": 34,
  "suggested_object_type": "video_collection",
  "confidence": "medium",
  "member_count": 2,
  "members": [
    {
      "relative_path": "Lesson 01.mp4",
      "file_id": 101,
      "inbox_item_id": 201,
      "role": "episode_video"
    }
  ],
  "failed_items": []
}
```

Validation:

- `paths` required and non-empty.
- All `paths` must be files, not directories.
- `collection_name` required and sanitized.
- Invalid Windows path characters are removed/replaced.
- Target root must exist and be enabled if supplied.
- Suggested type may be absent; backend can re-detect.

Safety notes:

- copy-only.
- no source delete.
- no overwrite.
- cancel creates no batch.
- endpoint creates object candidate, not organize candidate unless explicitly designed otherwise.
- endpoint does not generate plan or execute.

### 12.2 Confirm API impact

Existing endpoints:

```text
POST /library/import/inbox/items/{id}/confirm
POST /library/import/object-candidates/{id}/confirm
```

Phase 7H impact:

- Allowed type list, if introduced, must include `audio` and `asset_pack`.
- `final_object_type` can remain blank until user confirms; uncertain candidates should not be auto-finalized.
- `launch_file_id` remains editable for software/game object candidates.

### 12.3 Draft plan generation impact

Existing endpoint:

```text
POST /library/import/organize-plans
```

Phase 7H impact:

- Must accept candidates whose `detected_type` is `audio` or `asset_pack`.
- Must target correct directories instead of falling back to `clip`.
- Must preserve existing draft-only behavior.

---

## 13. Test Plan

### 13.1 Phase 7H-1 tests — Type Label UX

Frontend-oriented validation:

- type dropdown renders grouped labels.
- `imgset`, `photo_event`, `web_image_set` display as 图片合集 / 相册 aliases.
- `clip`, `clip_set` display as 视频素材 / 片段 aliases.
- backend values remain unchanged in option values.
- existing legacy candidate value remains visible and selectable.
- blank/uncertain option is available.
- i18n keys exist for English and Chinese.

Suggested test/build:

- `npm --prefix apps/frontend run build`
- targeted component smoke if existing frontend test harness is available.

### 13.2 Phase 7H-2 tests — audio and asset_pack Types

Suggested new backend test file:

```text
apps/backend/tests/test_library_v2_object_type_ux.py
```

Cases:

- `test_audio_type_accepted_for_inbox_confirm`
- `test_asset_pack_type_accepted_for_object_candidate_confirm`
- `test_audio_target_path_uses_audio_dir`
- `test_asset_pack_target_path_uses_assets_dir`
- `test_audio_object_prefix_is_audio`
- `test_asset_pack_object_prefix_is_asset`
- `test_audio_path_sync_after_execute`
- `test_asset_pack_path_sync_after_execute`
- `test_old_values_photo_event_web_image_set_still_supported`
- `test_unknown_type_does_not_silently_fallback_to_clip_without_signal`

### 13.3 Phase 7H-3 tests — Multi-file Collection Import

Suggested new backend test file:

```text
apps/backend/tests/test_library_v2_file_collection_import.py
```

Cases:

- `test_multi_file_collection_creates_object_candidate`
- `test_collection_name_common_prefix`
- `test_collection_name_timestamp_fallback`
- `test_user_override_collection_name`
- `test_copy_selected_files_into_synthetic_inbox_folder`
- `test_source_files_preserved`
- `test_no_overwrite_suffix_for_collection_folder`
- `test_selected_files_same_basename_get_no_overwrite_suffix`
- `test_multiple_videos_default_video_collection`
- `test_video_plus_documents_default_course`
- `test_multiple_images_default_imgset`
- `test_comic_numbered_images_default_comic`
- `test_multiple_audio_default_audio`
- `test_mixed_assets_default_asset_pack_or_requires_confirmation`
- `test_empty_selection_rejected`
- `test_cancel_creates_no_batch` (frontend/service-level as applicable)
- `test_partial_copy_failure_marks_failed_without_deleting_source`
- `test_subsequent_review_plan_execute_works_for_file_collection`
- `test_recovery_scan_handles_synthetic_collection_folder`

### 13.4 Regression tests

Must keep passing:

- `apps/backend/tests/test_library_v2_data_foundation.py`
- `apps/backend/tests/test_library_v2_import.py`
- `apps/backend/tests/test_library_v2_folder_import.py`
- `apps/backend/tests/test_library_v2_object_boundary.py`
- `apps/backend/tests/test_library_v2_inbox_review.py`
- `apps/backend/tests/test_library_v2_path_sync.py`
- `apps/backend/tests/test_library_v2_storage_scope.py`
- `apps/backend/tests/test_library_v2_recovery.py`

---

## 14. Manual Acceptance Plan

### 14.1 Type label smoke

Setup:

- Start frontend/backend in dev mode.
- Configure managed root.
- Open Library > Inbox.

Steps:

1. Open final object type dropdown for an inbox item.
2. Verify grouped labels.
3. Verify 图片合集 / 相册 is not shown as three confusing top-level concepts.
4. Verify 视频素材 / 片段 hides the clip vs clip_set distinction from normal user flow.
5. Verify backend value remains English when confirming.

Expected:

- User-facing labels are clear.
- Old values remain supported.

### 14.2 audio import smoke

Setup:

```text
source/
  Meeting Recording.wav
managed/
```

Steps:

1. Import file.
2. Set final type to 音频 / 录音 (`audio`).
3. Select root and confirm.
4. Create candidate.
5. Generate draft plan.
6. Execute only on disposable fixture.

Expected:

- Source preserved.
- Managed target uses audio path/prefix.
- Search/details show managed file after execute.

### 14.3 asset_pack import smoke

Setup:

```text
Asset Pack/
  textures/wall.png
  sounds/click.wav
  fonts/demo.ttf
  readme.txt
```

Steps:

1. Import folder as object.
2. Set final type to 素材包 (`asset_pack`).
3. Confirm root and create candidate.
4. Generate draft plan.
5. Execute on disposable fixture.

Expected:

- Members remain folded.
- Target path uses asset pack path/prefix.
- No member becomes independent review item by default.

### 14.4 Multiple videos as collection

Setup:

```text
Lesson 01.mp4
Lesson 02.mp4
Lesson 03.mp4
cover.jpg
```

Steps:

1. Click “选择多个文件为合集”.
2. Select all files.
3. Verify modal name suggestion.
4. Verify suggested type = 视频合集 / 系列视频 or 课程 / 讲座资料 if lesson signals are strong.
5. Edit name.
6. Confirm import.
7. Verify object candidate appears.
8. Confirm/review/generate plan.

Expected:

- Synthetic inbox folder created.
- Source files preserved.
- Object candidate members grouped.

### 14.5 Multiple images as collection

Setup:

```text
001.jpg
002.jpg
003.jpg
004.jpg
cover.jpg
```

Expected:

- Suggested type is 图片合集 / 相册 or 漫画 / 连续图片 depending sequence signal.
- User can override final type.

### 14.6 Mixed assets as collection

Setup:

```text
texture.png
click.wav
reference.pdf
model.fbx
readme.txt
```

Expected:

- Suggested type is 素材包 or blank requiring confirmation.
- No automatic execute.

### 14.7 Recovery after collection import

Steps:

1. Create multi-file collection import.
2. Manually delete one inbox copy in disposable fixture.
3. Run recovery scan.

Expected:

- Missing inbox finding appears.
- Recovery does not delete, move, or auto-repair files.

---

## 15. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Frontend label/value mismatch | P1 | Central object type option map; tests ensure option value remains backend enum |
| Old data using `photo_event` / `web_image_set` displays oddly | P2 | Alias display preserves backend value and legacy support |
| `asset_pack` becomes too broad | P1 | Use as suggestion only; low-confidence mixed files require user confirmation |
| Collection name collision | P1 | Use no-overwrite suffix for synthetic inbox folder |
| Selected files from different folders confuse source context | P2 | Modal shows source list; collection object uses synthetic folder; original paths preserved per member |
| Selected files with same basename collide | P1 | Per-file no-overwrite suffix inside synthetic folder |
| Large multi-file copy UX stalls | P1 | Progress/busy state; defer recursive folder-like large copy improvements if needed |
| Partial copy failure | P1 | Failed items returned; source preserved; batch status completed_with_errors or failed per existing style |
| API cancel creating empty batch | P1 | Prefer endpoint that creates batch only on confirmed import |
| Path sync for synthetic object folder wrong | P0 | Tests for all member relative paths after execute |
| Recovery detects synthetic folders incorrectly | P1 | Recovery test for synthetic collection folder |
| `audio`/`asset_pack` fallback to `clip` path | P1 | Add PLAN_TARGET_DIRS + OBJECT_PREFIX tests |
| `comic` value has no target mapping | P2/P1 | Decide whether Phase 7H adds comic target path; test no silent fallback |
| Frontend default maps audio to clip | P1 | Update `LibraryInboxPanel.tsx` default object type logic in implementation |
| Software/game launch candidate wrong | P1 | Keep editable launch selector; exclude setup/uninstall/update helpers |
| Multi-file collection bypasses review | P0 | API creates pending object candidate; organize still requires confirm/draft/preflight/execute |
| Source file accidentally moved/deleted | P0 | Copy-only implementation; tests assert source preserved |
| Object members visually split into independent review items | P1 | UI default shows object candidate as review unit; members folded under candidate |

---

## 16. Implementation Phases

### Phase 7H-1 — Type Label UX

Goal:

- Make object type selection understandable without changing backend behavior.

Scope:

- Frontend labels.
- Dropdown grouping.
- Help text.
- Alias display for merged types.

Likely files:

- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- `apps/frontend/src/locales/en/features.ts`
- `apps/frontend/src/locales/zh-CN/features.ts`

Acceptance criteria:

- Dropdown shows user-facing grouped labels.
- `imgset/photo_event/web_image_set` are visually unified as 图片合集 / 相册.
- `clip/clip_set` are visually unified as 视频素材 / 片段.
- Existing backend values are still submitted unchanged.
- No backend/API/schema changes.

Stop conditions:

- Existing candidate with legacy value disappears from UI.
- Confirm sends Chinese label instead of backend value.
- Existing import/review actions break.

### Phase 7H-2 — audio and asset_pack Types

Goal:

- Add full backend/frontend support for `audio` and `asset_pack` object types.

Scope:

- Backend allowed type handling.
- Target directories.
- Object prefixes.
- Detection suggestions.
- Frontend labels/dropdown.
- Tests.
- Formal docs update during implementation.

Likely files:

- `apps/backend/app/services/library/organize.py`
- `apps/backend/app/services/library/organize_template_renderer.py`
- `apps/backend/app/services/library/object_parser.py`
- `apps/backend/app/services/importing/object_boundary.py`
- `apps/backend/app/services/importing/service.py`
- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- locale files
- backend tests

Acceptance criteria:

- `audio` confirm/candidate/plan/execute works.
- `asset_pack` confirm/candidate/plan/execute works.
- Neither type falls back to `clip`.
- Source files remain preserved.
- Existing Phase 7 tests pass.

Stop conditions:

- Schema check constraint blocks values unexpectedly.
- New types require a migration larger than expected.
- Path sync fails for either new type.

### Phase 7H-3 — Multi-file Collection Import

Goal:

- Add “选择多个文件为合集” import mode.

Scope:

- New API endpoint.
- Service method for synthetic inbox object folder.
- Frontend modal and file picker flow.
- Detection/name suggestion.
- Tests and manual QA docs.

Likely files:

- `apps/backend/app/api/routes/importing.py`
- `apps/backend/app/schemas/importing.py`
- `apps/backend/app/services/importing/service.py`
- `apps/backend/app/services/importing/object_boundary.py`
- `apps/backend/app/repositories/importing/repository.py` if helper needed
- `apps/frontend/src/services/api/importingApi.ts`
- `apps/frontend/src/services/desktop/filePicker.ts` if bridge needs extension
- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- locale files
- new backend tests

Acceptance criteria:

- User can select multiple files and import as one object candidate.
- Cancel creates no batch.
- Empty selection rejected.
- Collection name generated and editable.
- Copy target is `00_Inbox/<batch_id>/<collection_name>/`.
- Source files preserved.
- Members folded under one object candidate.
- Review/candidate/draft/execute path works.
- Recovery scan handles synthetic folders.

Stop conditions:

- Multi-file import creates independent review items by default.
- Partial failure loses files or creates inconsistent DB/FS state.
- Endpoint directly generates plan or executes.
- Large copy blocks UI with no feedback.

---

## 17. Documentation Updates

During later implementation, update formal docs:

- `docs/library-v2/README.md`
- `docs/library-v2/ARCHITECTURE.md`
- `docs/library-v2/API_REFERENCE.md`
- `docs/library-v2/MANUAL_ACCEPTANCE_GUIDE.md`
- `docs/library-v2/KNOWN_LIMITATIONS.md`
- `docs/library-v2/BETA_TESTING_CHECKLIST.md`
- `docs/FILE_CLASSIFICATION_RULES.md`

Update content:

- New user-facing object type labels.
- `audio` and `asset_pack` object types.
- Target directories and prefixes.
- Multi-file collection import endpoint and UX.
- Manual acceptance playbooks.
- Recovery limitations for synthetic folders if any.
- Updated known limitations if `asset_pack`/audio detection remains simple.

Do not update formal docs until implementation exists.

---

## 18. Final Recommendation

Recommended order:

1. Phase 7H-1 — Type Label UX.
2. Phase 7H-2 — `audio` and `asset_pack` types.
3. Phase 7H-3 — Multi-file Collection Import.

Rationale:

- 7H-1 is lowest risk and immediately improves current review UX.
- 7H-2 expands the type system and must be correct before collection import can suggest `audio` / `asset_pack`.
- 7H-3 changes import behavior and has the highest DB/FS consistency risk, so it should come last.

Final direction:

- Proceed with Phase 7H as an additive improvement.
- Do not implement all three steps in one batch.
- Keep copy-only import, source preservation, no-overwrite, manual review, draft plan, preflight, execute, path sync, journal, and recovery invariants.
- Treat all detection as rule-based suggestion.
- Keep final object type and launch candidate user-confirmed.
- Keep current beta/source-scan behavior valid and visible.

Open questions for human decision before implementation:

1. Should `comic` receive a first-class target directory/prefix in 7H-2, or remain under image-set handling?
2. Should `m4a`, `aac`, `opus` be added to global audio classification now?
3. Should `asset_pack` target directory be `60_Assets`, `70_Assets`, or align with an existing managed library numbering convention?
4. Should multi-file collection import set `final_object_type` immediately from modal, or only set `suggested_object_type` and require the existing Review confirm step?
5. Should frontend expose legacy values (`photo_event`, `web_image_set`, `clip_set`) in an advanced chooser, or only display them when existing data uses them?
6. Should `asset_pack` be suggested for unknown mixed files, or should unknown mixed files default to blank and require selection?
7. Should selected files from many different source folders show a stronger warning in the collection modal?
8. Should collection import preserve relative folder structure if file picker can return directories in future, or keep 7H strictly file-only?

