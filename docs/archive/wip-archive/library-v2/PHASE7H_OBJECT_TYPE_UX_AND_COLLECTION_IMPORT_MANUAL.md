# Phase 7H — Object Type UX and Multi-file Collection Import Manual

> 状态：执行手册草案 / `_wip`  
> 输入方案：`docs/_wip/library-v2/PHASE7H_OBJECT_TYPE_UX_AND_COLLECTION_IMPORT_PLAN.md`  
> 目标读者：Codex / Claude / 人类开发者  
> 范围：Phase 7H 分阶段实现手册，不是代码实现。  
> Source of truth：当前仓库源码与 `docs/library-v2/` 正式文档优先，`docs/_wip/` 仅作为方案草案与操作手册。

---

## 1. Manual Purpose

这份文档用于指导 Phase 7H 的分阶段实现。它不是代码实现、不是 schema 变更、不是 API 已实现声明，也不是产品愿景文档。

Phase 7H 是 Library v2 的 UX / 类型体系 / 导入模式增强，目标是：

- 让 `final_object_type` 下拉对用户更可理解。
- 保持后端 value 清晰、稳定、英文 enum-like string。
- 补齐 `audio` 与 `asset_pack` 对象类型能力。
- 增加“选择多个文件为合集”的导入模式。
- 复用当前 Library v2 已完成的安全链路。

Phase 7H 必须分阶段执行：

1. Phase 7H-1 — Type Label UX
2. Phase 7H-2 — `audio` and `asset_pack` Types
3. Phase 7H-3 — Multi-file Collection Import

不建议一次性实现全部 7H。7H-1 是低风险前端 UX；7H-2 扩展类型能力；7H-3 涉及真实文件 copy、DB/FS 一致性、recovery 行为，风险最高，应最后实现。

任何阶段都不得破坏 Phase 7A-7G 已完成能力：

```text
Import -> Inbox -> Object Detection -> Review -> Organize Candidate
-> Draft Plan -> Mark Ready -> Preflight -> Execute
-> Managed Library -> Browse/Search/Details -> Recovery
```

---

## 2. Current Baseline Summary

### 2.1 Current facts

| Fact | Current state | Evidence |
|---|---|---|
| 产品定位 | Windows local-first asset workbench，不是 Explorer 替代品 | `README.md`, `AGENTS.md` |
| 正式 Library v2 文档入口 | `docs/library-v2/` | `docs/README.md`, `docs/library-v2/README.md` |
| `_wip` 文档定位 | 草案、临时材料、执行方案，通常被 git ignore | `docs/README.md` |
| Phase 7A-7F | 正式文档标记 complete，195 tests | `docs/library-v2/README.md`, `docs/library-v2/PHASE7_COMPLETION_REPORT.md` |
| Phase 7G | README 标记 Library v2 Phase 7A-7G complete | `README.md` |
| 当前 import 主链 | Import → Inbox → Object Detection → Review → Draft Plan → Execute → Managed Library → Browse/Search/Details → Recovery | `docs/library-v2/ARCHITECTURE.md` |
| 当前模式 | Hybrid mode，source scan 继续有效 | `docs/library-v2/README.md`, `docs/library-v2/ARCHITECTURE.md` |
| API prefix | route file 中为 `/library/import`，没有 in-file `/api` prefix | `docs/library-v2/API_REFERENCE.md`, `apps/backend/app/api/routes/importing.py` |
| object execute path sync | 成功 move 后同步 `files.path`、`storage_state=managed`、path history、journal | `docs/library-v2/PHASE7_COMPLETION_REPORT.md`, `apps/backend/app/services/library/organize.py` |

### 2.2 Existing capabilities

| Capability | Current support | Evidence |
|---|---|---|
| File import | 支持，`POST /library/import/batches/{id}/files`，多文件会变成多个 independent `inbox_item` | `apps/backend/app/api/routes/importing.py`, `apps/backend/app/services/importing/service.py` |
| Folder-as-object | 支持，`POST /library/import/batches/{id}/folders`，`mode="object"` | `apps/backend/app/api/routes/importing.py`, `apps/backend/app/services/importing/service.py` |
| Folder-as-loose-files | 支持，`mode="loose_files"` | `apps/backend/app/api/routes/importing.py`, `apps/frontend/src/features/library/LibraryInboxPanel.tsx` |
| Object candidate/member | 支持 `import_object_candidates` 和 `import_object_members` | `apps/backend/app/db/models/importing.py` |
| Member folded under object | 当前前端 object card 展示 member groups，不默认拆成独立 object candidate | `apps/frontend/src/features/library/LibraryInboxPanel.tsx`, `docs/library-v2/MANUAL_ACCEPTANCE_GUIDE.md` |
| Launch candidate override | 支持 `launch_file_id` update/confirm，且校验属于 object member | `apps/backend/app/api/routes/importing.py`, `apps/backend/app/services/importing/service.py` |
| Draft plan only | `generate_draft_plan_from_candidates()` 不 mark-ready、不 preflight、不 execute | `apps/backend/app/services/importing/service.py` |
| Recovery diagnostics | scan 检测 orphan/missing/failed/incomplete，除 retry 外不自动修复 | `apps/backend/app/services/importing/recovery.py` |

### 2.3 Existing gaps

| Gap | Current evidence | Phase 7H impact |
|---|---|---|
| Multi-file collection import 不存在 | 没有 `/library/import/file-collections` 或 batch file-collection endpoint；`LibraryInboxPanel` 的 file mode 直接调用 `importFilesToBatch()` | 7H-3 新增 |
| 类型下拉偏技术枚举 | `LibraryInboxPanel.tsx` 中 `OBJECT_TYPE_OPTIONS` 是 flat array，未分组 | 7H-1 优化 |
| `imgset/photo_event/web_image_set` 分开显示 | locale 中分别为 Image set / Photo event / Web image set；中文为图集/摄影合集/网图合集 | 7H-1 合并显示 |
| `clip/clip_set` 分开显示 | locale 中分别为 Clip / Clip set；中文为片段/片段合集 | 7H-1 合并显示 |
| `audio` 未完整接入 object type | `ImportService._detect_object_type()` 可返回 `audio`，但前端下拉、`PLAN_TARGET_DIRS`、`OBJECT_PREFIX`、object parser 均未补齐 | 7H-2 补齐 |
| `asset_pack` 不存在 | 未在 grep 中出现 | 7H-2 新增 |
| `comic` 目标目录/prefix 不明确 | detection/frontend 有 `comic`，但 `PLAN_TARGET_DIRS` / `OBJECT_PREFIX` 未包含 | Open question |
| `object_parser.py` 支持类型落后 | `SUPPORTED_OBJECT_TYPES` 只含 MOVIE/ANIME/COLLECTION/GAME/COURSE/IMGSET/DOCSET/PROJECT/CLIP | 7H-2 需确认是否补齐 |
| frontend audio 默认映射错误 | `defaultObjectType()` 中 `audio -> clip` | 7H-2 修正 |
| frontend image 默认映射可能无效 | `defaultObjectType()` 中 `image -> image`，但下拉没有 `image` value | 7H-1 或 7H-2 修正为 `imgset` 或 blank |

### 2.4 Source mismatches

| Mismatch | Source | Required handling |
|---|---|---|
| 正式 docs 标记 7A-7F complete，README 标记 7A-7G complete | `docs/library-v2/README.md`, `README.md` | 手册按用户背景承认 7G 已完成，但正式细节以 `docs/library-v2/` 为准 |
| `LibraryV2Capability` 仍返回 `status="data_foundation"` / flags false | `apps/backend/app/services/importing/service.py`, `apps/backend/app/schemas/importing.py` | Phase 7H 不处理，除非后续实现触及 capability UI |
| `ImportService._FILE_KIND_TO_TYPE` 有 `audio`，但 frontend 默认把 audio 设为 `clip` | `service.py`, `LibraryInboxPanel.tsx` | 7H-2 必须修正 |
| `object_boundary.py` 检测 `comic`，但 plan target/prefix 缺 `comic` | `object_boundary.py`, `organize.py`, `organize_template_renderer.py` | 7H-2 前需人类确认 |
| `object_parser.py` prefix 支持不覆盖所有 Phase 7 values | `object_parser.py` | 7H-2 实现时验证 managed object scan 是否需要补齐 |

### 2.5 Assumptions

- Phase 7H 不改变 source-scan beta 主线。
- Phase 7H 不需要新增 DB 表，除非实现时发现 strict check constraint 或现有模型无法表达必要状态。
- `import_object_candidates` / `import_object_members` 是多文件合集应复用的数据结构。
- File picker bridge 当前已有 `selectFiles()` / `selectFolder()`，但需要验证多选文件语义是否足够稳定。
- `docs/_wip` 可能被 git ignore；文档存在不一定出现在 `git status` 中。

---

## 3. Global Safety Invariants

所有 Phase 7H 阶段都必须遵守：

- import 必须 copy-only。
- source files / source folders 必须保留。
- 不允许 source cleanup。
- 不允许自动删除。
- 不允许覆盖已有文件。
- 发生同名冲突必须使用 no-overwrite suffix。
- 不允许绕过 Review。
- 不允许绕过 Draft Plan。
- 不允许绕过 Mark Ready / Preflight / Execute。
- 不允许自动 execute。
- 不允许 AI 自动分类为正式事实。
- 不允许 AI 执行文件操作。
- path sync 只能发生在 successful move 后。
- partial failure 只能同步成功 move 的文件。
- recovery scan 只能检测和报告，不自动修复、删除或移动。
- 前端 label 不得污染后端 enum value。
- API 必须继续使用英文 backend value。
- 旧 backend value 不能直接删除。
- 不确定分类必须允许用户确认或保持空。
- 成员文件可以有 `files` row / `inbox_item`，但用户整理流程默认按 object candidate 展示。
- 多文件合集必须创建 object candidate，而不是直接创建 organize plan 或 managed library object。

---

## 4. Global Prohibited Actions

### 4.1 禁止的文件操作

- 禁止删除 source 文件。
- 禁止移动 source 文件。
- 禁止自动清理 source folder。
- 禁止自动清理 `00_Inbox`。
- 禁止自动清理 orphan 文件。
- 禁止覆盖目标文件。
- 禁止未通过 preflight 执行 move。
- 禁止在 import API 中直接执行 managed move。
- 禁止在 recovery scan 中执行文件修复。

### 4.2 禁止的架构行为

- 禁止重写 Library v2 主链。
- 禁止新建第二套 object candidate 系统。
- 禁止绕过 `import_object_candidates` / `import_object_members`。
- 禁止绕过 `OrganizeCandidate` / `OrganizePlan`。
- 禁止把 multi-file collection 做成独立孤岛逻辑。
- 禁止新增复杂插件系统。
- 禁止新增 AI agent 自动整理平台。
- 禁止新增云同步、多用户、复杂权限。
- 禁止把 Workbench 改成 Explorer 替代品。

### 4.3 禁止的 UI 行为

- 禁止隐藏用户确认步骤。
- 禁止让“生成草稿计划”看起来像“已经移动文件”。
- 禁止把 legacy value 从 UI 中彻底隐藏到用户无法处理旧数据。
- 禁止把中文 label 当成后端 value 发给 API。
- 禁止默认跨分页批量处理。
- 禁止将 object members 默认渲染为一堆独立待整理对象。
- 禁止在 cancel 后创建空 batch。
- 禁止 empty selection 创建 batch。

### 4.4 禁止的文档行为

- 禁止把未实现 API 写成已实现。
- 禁止把 future work 写成当前能力。
- 禁止把 `_wip` 草案当成正式 source of truth。
- 禁止在实现前更新正式 docs 宣称能力完成。

---

## 5. Out-of-Scope Matrix

| Item | Status | Reason |
|---|---|---|
| AI 自动分类并写入正式类型 | Out of scope | AI 只能建议，不能写事实 |
| 自动 execute plan | Out of scope | 必须走 ready/preflight/execute |
| app-level trash/delete cleanup | Out of scope | 属于未来 recovery/trash 设计 |
| duplicate/hash pipeline | Out of scope | 独立复杂能力，当前 `checksum_hint` 未填充 |
| persistent recovery findings table | Out of scope | 7F 已定义 computed diagnostics |
| movie metadata scraper | Out of scope | 后续影视刮削阶段 |
| poster wall / movie wall | Out of scope | 后续展示层 |
| course progress tracking | Out of scope | 后续课程功能 |
| EXIF timeline / photo map | Out of scope | 后续图片/相册功能 |
| audio transcription | Out of scope | 后续 audio 能力 |
| music album / podcast / sound effect 细分 | Out of scope | Phase 7H 只做一个 `audio` |
| advanced asset manager | Out of scope | 后续素材库能力 |
| package/beta release | Out of scope | 7H 完成后再考虑 |
| schema migration framework 重做 | Out of scope | 当前 docs 说明仍为 idempotent SQL + ensure helpers |
| source cleanup / delete original | Out of scope | 当前安全边界禁止 |

---

## 6. Final Product Decisions

用户已确认以下决策，后续实现不得重新争论方向：

1. `course` 不并入 `video_collection`，但改名为“课程 / 讲座资料”方向。
2. `anime` 不并入 `movie_collection`。
3. `imgset` / `photo_event` / `web_image_set` 用户侧合并显示为“图片合集 / 相册”。
4. `clip` / `clip_set` 用户侧合并显示为“视频素材 / 片段”。
5. 新增 `audio`，只做一个类型，不拆 `music_album` / `recording` / `podcast` / `sound_effect`。
6. 新增 `asset_pack`。
7. 新增“选择多个文件为合集”。
8. 多文件合集名默认用公共前缀，无公共前缀用 `Collection YYYY-MM-DD HHmm`，用户可修改。
9. 多选多个视频默认 `video_collection`。
10. `asset_pack` 可以包含任意文件类型，但不能自动吞掉全部 unknown。

---

## 7. Revised Object Type System

| Group | Backend value | 中文 label | English label | Current/New | Display rule | 说明 |
|---|---|---|---|---|---|---|
| 视频 | `movie` | 电影 / 长视频 | Movie / Long video | Existing | Direct | 单个完整影视作品 |
| 视频 | `anime` | 动漫 / 剧集 | Anime / Series | Existing | Direct | Series / Season / Episode 结构 |
| 视频 | `course` | 课程 / 讲座资料 | Course / Lecture materials | Existing, relabeled | Direct | 带附件、资料、章节或记录属性的视频集合 |
| 视频 | `video_collection` | 视频合集 / 系列视频 | Video collection / Series videos | Existing | Direct | 普通多视频合集 |
| 视频 | `clip` | 视频素材 / 片段 | Video clips / Footage | Existing | Merged display | 单个视频素材 |
| 视频 | `clip_set` | 视频素材 / 片段 | Video clips / Footage | Existing | Merged display / legacy visible | 多个片段合集 |
| 视频 | `movie_collection` | 电影合集 | Movie collection | Existing | Direct | 多部独立电影 |
| 图片 | `imgset` | 图片合集 / 相册 | Image set / Album | Existing | Merged display default | 默认图片合集 value |
| 图片 | `photo_event` | 图片合集 / 相册 | Image set / Album | Existing | Merged display / legacy visible | 旧数据保留 |
| 图片 | `web_image_set` | 图片合集 / 相册 | Image set / Album | Existing | Merged display / legacy visible | 旧数据保留 |
| 图片 | `comic` | 漫画 / 连续图片 | Comic / Sequential images | Existing in detection/frontend | Direct, target open | 连续页图片 |
| 应用 | `software` | 软件 / 工具 | Software / Tool | Existing | Direct | 软件包、工具程序 |
| 应用 | `game` | 游戏 | Game | Existing | Direct | 游戏目录 |
| 文档 | `docset` | 文档 / 资料包 | Document set / Materials | Existing | Direct | 文档、PDF、资料包 |
| 音频 | `audio` | 音频 / 录音 | Audio / Recording | New object type | Direct | 音乐、录音、会议音频、采访等 |
| 素材 | `asset_pack` | 素材包 | Asset pack | New object type | Direct | 字体、音效、贴图、3D/2D 素材、混合项目素材 |

Implementation note:

- `image` / `document` / `archive` 是 file-level kind 或当前 loose import fallback，不应直接作为 Phase 7H final object type 下拉主选项，除非实现前明确设计。
- 当前 `LibraryInboxPanel.tsx` 的 `defaultObjectType()` 中 `image -> image`、`audio -> clip` 是需要修正的现状。

---

## 8. Value / Label Separation Rules

Rules:

- backend value 是英文 enum-like string，例如 `video_collection`。
- frontend label 是本地化显示，例如“视频合集 / 系列视频”。
- 合并显示不等于删除 value。
- API 永远发送 backend value。
- 旧数据中的 `photo_event` / `web_image_set` / `clip_set` 必须可显示、可处理。
- 如果用户不改旧 value，不应强制迁移。
- 如果用户重新选择图片合集默认 value，建议映射到 `imgset`。
- 如果用户重新选择视频素材默认 value，建议映射到 `clip` 或按 UI 场景选择 `clip_set`；这个选择应在实现前明确。
- `audio` / `asset_pack` 是新增 backend values，不是中文 label。
- Uncertain / unknown 应允许保持 blank，直到用户确认。

Implementation requirement:

- 建议创建前端本地 option map，例如 `OBJECT_TYPE_GROUPS`，但不要在 7H-1 引入 backend behavior。
- 如果后端引入 centralized allowed list，必须只包含 backend values，不包含 label。

---

## 9. Phase 7H-1 Manual — Type Label UX

### Goal

只优化类型下拉显示、分组、说明文本。7H-1 不改变后端行为、不增加新 API、不新增真实类型能力。

### Allowed Changes

- frontend labels
- dropdown grouping
- help text
- i18n
- local object type option map
- `LibraryInboxPanel.tsx` 内部的 presentation-only dropdown structure

### Forbidden Changes

- 不改后端。
- 不改 API。
- 不改 schema。
- 不新增 `audio` / `asset_pack` 后端能力。
- 不新增 multi-file collection import。
- 不改 detection 规则。
- 不改 execute/path sync。
- 不改 import service。
- 不改 tests 以外的行为假设。

### Files Likely Changed

- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- `apps/frontend/src/locales/en/features.ts`
- `apps/frontend/src/locales/zh-CN/features.ts`
- Optional: `apps/frontend/src/features/library/objectTypeOptions.ts` 或 feature-local helper

Do not touch:

- `apps/backend/**`
- `apps/backend/tests/**`
- `apps/backend/app/db/**`
- `apps/backend/app/api/**`

### Step-by-step Tasks

1. Read current `OBJECT_TYPE_OPTIONS` in `LibraryInboxPanel.tsx`.
2. Create a local option map with fields:
   - `group`
   - `value`
   - `labelKey`
   - `descriptionKey` if needed
   - `isLegacyAlias` if needed
3. Define groups:
   - 视频
   - 图片
   - 应用
   - 文档
4. Keep current backend values only:
   - `movie`, `anime`, `course`, `video_collection`, `clip`, `clip_set`, `movie_collection`, `imgset`, `photo_event`, `web_image_set`, `comic`, `software`, `game`, `docset`
5. Update labels:
   - `course` -> 课程 / 讲座资料
   - `anime` -> 动漫 / 剧集
   - `video_collection` -> 视频合集 / 系列视频
   - `clip` / `clip_set` -> 视频素材 / 片段
   - `imgset` / `photo_event` / `web_image_set` -> 图片合集 / 相册
6. Ensure option `value` remains the backend value.
7. Ensure existing candidate with `photo_event`, `web_image_set`, or `clip_set` still renders and can be saved.
8. Add short helper text explaining:
   - detection is suggestion only
   - final type is user-confirmed
   - source files are not moved by review
9. Confirm no new API calls are introduced.
10. Run validation commands for this phase only.

### Acceptance Criteria

- 用户看得懂下拉。
- 下拉按语义分组。
- 中文无 raw key。
- English locale has equivalent labels.
- Option value remains backend value.
- `photo_event` / `web_image_set` / `clip_set` old values do not disappear.
- Existing confirm / reject / create candidate / generate draft plan still works.
- Frontend build passes.

### Stop Conditions

- 中文 label 被发给后端。
- 旧 candidate value 无法显示。
- Confirm failed because option value changed.
- 下拉无法保存原 value。
- 7H-1 需要 backend change 才能完成。
- Type grouping causes uncontrolled React select state or blanking existing value.

### Tests / Validation

Run:

```powershell
npm --prefix apps/frontend run build
```

Manual smoke:

1. Open Library > Inbox.
2. Expand an object candidate.
3. Open final object type dropdown.
4. Verify grouped labels.
5. Select a legacy alias value if present.
6. Confirm candidate with disposable data.
7. Verify network payload uses backend value.

Recommended commit message:

```text
feat(library-v2): improve object type labels
```

---

## 10. Phase 7H-2 Manual — audio and asset_pack Types

### Goal

完整支持 `audio` / `asset_pack` 对象类型，使它们能走：

```text
confirm -> create candidate -> generate draft plan -> execute -> path sync
```

且不能 fallback 到 `clip`。

### Allowed Changes

- backend allowed object types
- `PLAN_TARGET_DIRS`
- `OBJECT_PREFIX`
- object detection
- object parser support if needed
- frontend labels
- backend tests
- frontend labels/tests/build
- formal docs after implementation

### Forbidden Changes

- 不做 multi-file collection import。
- 不改 schema，除非发现 strict check constraint。
- 不新增复杂 audio transcription。
- 不新增 advanced asset manager。
- 不自动把所有 unknown 变 `asset_pack`。
- 不破坏旧类型。
- 不让 `audio` / `asset_pack` fallback 到 `clip`。
- 不删除 `photo_event` / `web_image_set` / `clip_set`。
- 不改变 source-scan 文件分类主线，除非明确添加 audio 扩展名。

### Files Likely Changed

Backend:

- `apps/backend/app/services/library/organize.py`
- `apps/backend/app/services/library/organize_template_renderer.py`
- `apps/backend/app/services/library/object_parser.py`
- `apps/backend/app/services/importing/object_boundary.py`
- `apps/backend/app/services/importing/service.py`
- `apps/backend/app/core/classification.py` only if adding audio extensions
- `apps/backend/tests/test_library_v2_object_type_ux.py` new
- existing `apps/backend/tests/test_library_v2_*.py` if expected assertions need extension

Frontend:

- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- `apps/frontend/src/locales/en/features.ts`
- `apps/frontend/src/locales/zh-CN/features.ts`

Docs after implementation:

- `docs/library-v2/README.md`
- `docs/library-v2/ARCHITECTURE.md`
- `docs/library-v2/API_REFERENCE.md`
- `docs/library-v2/MANUAL_ACCEPTANCE_GUIDE.md`
- `docs/library-v2/BETA_TESTING_CHECKLIST.md`
- `docs/library-v2/KNOWN_LIMITATIONS.md`
- `docs/FILE_CLASSIFICATION_RULES.md`

### Step-by-step Tasks

1. Confirm no strict enum/check constraint exists for object type.
   - Inspect `apps/backend/app/db/models/importing.py`.
   - Inspect `apps/backend/app/db/migrations/0002_library_v2.sql`.
   - If a DB-level constraint exists, stop and create a migration plan first.
2. Establish or update an allowed object type list.
   - Prefer central backend constant over scattered hard-coded strings.
   - Include existing values and new values.
3. Add `audio` and `asset_pack` to backend allowed values.
4. Update `PLAN_TARGET_DIRS` in `apps/backend/app/services/library/organize.py`.
   - Proposed:
     - `audio -> ("50_Audio",)`
     - `asset_pack -> ("60_Assets",)`
   - Do not finalize `comic` target without resolving open question.
5. Update `OBJECT_PREFIX` in `apps/backend/app/services/library/organize_template_renderer.py`.
   - Proposed:
     - `audio -> AUDIO`
     - `asset_pack -> ASSET`
6. Confirm whether `comic` needs target dir/prefix now.
   - If yes, add `comic -> ("30_Images", "Comics")` and `comic -> COMIC`.
   - If no, add tests documenting current fallback/alias behavior or block `comic` execute until resolved.
7. Update `object_boundary.py`.
   - Add audio extension set if object-level folder detection should detect audio collections.
   - Add `asset_pack` signal rules.
   - Keep detection pure and side-effect-free.
8. Update `object_parser.py` if managed object scan should recognize new prefixes.
   - Add `AUDIO`, `ASSET`, and any missing Phase 7 prefixes only if required by current object scan behavior.
9. Update `ImportService._detect_object_type()` if loose file defaults should map:
   - `audio -> audio`
   - image default should be reviewed (`imgset` or blank), because current `image` value is not in object type options.
10. Update frontend dropdown / labels to include `audio` and `asset_pack`.
11. Fix `LibraryInboxPanel.tsx` default object type mapping:
   - `audio -> audio`
   - `image -> imgset` or blank, based on UX decision.
12. Add backend tests.
13. Run backend tests for new file and existing v2 suite.
14. Run frontend build.
15. Update formal docs only after implementation passes.

### Acceptance Criteria

- `audio` can confirm/create candidate/generate plan/execute.
- `asset_pack` can confirm/create candidate/generate plan/execute.
- `audio` target path does not fallback to `clip`.
- `asset_pack` target path does not fallback to `clip`.
- `OBJECT_PREFIX` generates correct managed folder prefix.
- Path sync works for `audio` and `asset_pack`.
- Source files remain preserved.
- Existing Phase 7 tests pass.
- Formal docs are updated after code is complete.

### Stop Conditions

- Need DB migration and impact is unclear.
- `audio` / `asset_pack` execute into `40_Videos/Clips`.
- Recovery scan reports many false positives after managed execute.
- Old tests fail due to type list restrictions.
- `object_parser.py` cannot handle new prefixes and object scan behavior becomes unstable.
- Implementation attempts to add audio transcription, asset catalog, scraper, or AI behavior.

### Tests / Validation

Create:

```text
apps/backend/tests/test_library_v2_object_type_ux.py
```

Recommended tests:

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

Run:

```powershell
cd apps/backend
python -m pytest tests/test_library_v2_object_type_ux.py -v
python -m pytest tests/test_library_v2_*.py -v
cd ..\..
npm --prefix apps/frontend run build
```

Recommended commit message:

```text
feat(library-v2): add audio and asset pack object types
```

---

## 11. Phase 7H-3 Manual — Multi-file Collection Import

### Goal

支持用户选择多个文件作为一个合集对象导入，创建一个 synthetic inbox object folder 和一个 `import_object_candidate`，后续复用 7C/7D 链路。

### Allowed Changes

- new import API
- import service method
- synthetic inbox object folder
- object candidate/member creation
- frontend file picker flow
- collection modal
- collection name suggestion helper
- tests
- docs

### Forbidden Changes

- 不移动 source。
- 不删除 source。
- 不覆盖 target。
- 不自动 execute。
- 不绕过 Review。
- 不跳过 Draft Plan。
- 不创建第二套 object 系统。
- 不直接把 selected files 散成多个 candidate。
- 不允许 cancel 后创建空 batch。
- 不允许 empty selection 创建 batch。
- 不允许 partial copy failure 静默成功。
- 不允许未记录 failed items。
- 不允许 import endpoint 直接生成 organize plan。
- 不允许 file collection API 接收目录路径。

### Files Likely Changed

Backend:

- `apps/backend/app/api/routes/importing.py`
- `apps/backend/app/schemas/importing.py`
- `apps/backend/app/services/importing/service.py`
- `apps/backend/app/services/importing/object_boundary.py`
- `apps/backend/app/repositories/importing/repository.py` if helper needed
- `apps/backend/tests/test_library_v2_file_collection_import.py` new

Frontend:

- `apps/frontend/src/features/library/LibraryInboxPanel.tsx`
- `apps/frontend/src/services/api/importingApi.ts`
- `apps/frontend/src/services/desktop/filePicker.ts` if bridge needs extension
- `apps/frontend/src/locales/en/features.ts`
- `apps/frontend/src/locales/zh-CN/features.ts`
- Optional: `apps/frontend/src/features/library/CollectionImportModal.tsx`

Docs after implementation:

- `docs/library-v2/API_REFERENCE.md`
- `docs/library-v2/ARCHITECTURE.md`
- `docs/library-v2/MANUAL_ACCEPTANCE_GUIDE.md`
- `docs/library-v2/BETA_TESTING_CHECKLIST.md`
- `docs/library-v2/KNOWN_LIMITATIONS.md`

### Step-by-step Tasks

1. Confirm existing file picker behavior.
   - `apps/frontend/src/services/desktop/filePicker.ts` calls `window.assetWorkbench.selectFiles()`.
   - Verify Electron bridge already returns multiple file paths.
   - If not, add only a narrow multi-file picker bridge; do not add broad filesystem APIs.
2. Design frontend modal state.
   - selected paths
   - generated collection name
   - suggested object type
   - target root
   - file count and preview
   - confirm/cancel state
3. Implement collection name suggestion helper.
4. Add backend schema.
   - Example: `ImportFileCollectionRequest`
   - fields: `paths`, `collection_name`, `suggested_object_type`, `target_library_root_id`
5. Add endpoint.
   - Recommended path: `POST /library/import/file-collections`
   - Reason: cancel creates no batch; endpoint creates batch only after modal confirm.
6. Implement service method.
   - Example: `ImportService.import_file_collection(...)`
7. Validate request.
   - reject empty `paths`
   - reject directory paths
   - reject missing files
   - sanitize `collection_name`
   - validate root if provided
8. Create `import_batch` only after validation enough to proceed.
9. Create synthetic inbox folder:
   - `{managed_root}/00_Inbox/<batch_id>/<collection_name>/`
10. Copy selected files with no-overwrite suffix.
11. If selected files share basename, suffix target filenames inside synthetic folder.
12. Create `files` rows.
13. Create `inbox_items`.
14. Create one `import_object_candidate`.
15. Create `import_object_members`.
16. Return summary:
   - batch id
   - object candidate id
   - suggested type
   - member count
   - failed items
17. Add frontend API function in `importingApi.ts`.
18. Add import mode to `LibraryInboxPanel.tsx`.
19. Add modal and wire confirm to API.
20. Ensure object candidate list refreshes after import.
21. Ensure cancel does not call API.
22. Ensure empty selection does not call API.
23. Verify review/plan/execute reuses current object candidate flow.
24. Verify recovery scan on synthetic folder.
25. Update formal docs after implementation.

### Collection Name Rules

Executable algorithm:

1. Start with selected basenames.
2. Strip extensions.
3. Normalize separators:
   - `_`, `-`, `.`, repeated spaces -> single space.
4. Compute longest common prefix across normalized names.
5. Trim trailing sequence tokens:
   - `01`, `001`, `S01E01`, `EP01`, `Part 01`, `Lesson 01`.
6. Reject prefix if:
   - length less than 3 after trim,
   - only generic camera prefix such as `IMG`, `DSC`, `VID`,
   - only season token such as `S01`,
   - only punctuation/number.
7. If rejected, fallback:
   - `Collection YYYY-MM-DD HHmm`.
8. Sanitize Windows path characters:
   - replace `\ / : * ? " < > |` with space.
   - trim trailing dots/spaces.
9. Limit length to avoid long path risk.
10. Apply no-overwrite suffix if synthetic folder exists.
11. User must be able to override before import.

### Type Suggestion Rules

| Input signal | Suggested object type |
|---|---|
| multiple videos | `video_collection` |
| multiple images | `imgset` |
| multiple audio | `audio` |
| video + docs/slides/notes/zip/project files | `course` |
| numbered images / comic keywords | `comic` |
| mixed creative assets | `asset_pack` or blank |
| uncertain | blank / requires user confirmation |

Rules:

- Frontend may suggest for UX, but backend must re-check or validate.
- Suggestions are not final facts.
- User confirmation remains required before organize candidate creation unless user explicitly confirms final type in existing review flow.

### API Draft

Method:

```text
POST /library/import/file-collections
```

Request:

```json
{
  "paths": ["C:/Temp/Lesson 01.mp4", "C:/Temp/Lesson 02.mp4"],
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

- `paths` required.
- `paths.length > 0`.
- every path must be an existing file.
- no directory paths.
- `collection_name` required after modal confirm.
- sanitized collection name must be non-empty.
- target root must exist/enabled if provided.
- suggested type must be known or ignored as frontend hint.

Safety:

- copy-only.
- no source delete.
- no overwrite.
- batch created only after confirm.
- object candidate only, no execute.
- no direct organize plan generation.

### Acceptance Criteria

- 多文件可作为一个 object candidate。
- Source files preserved.
- No overwrite.
- `collection_name` 可改。
- Cancel creates no batch.
- Empty selection rejected.
- Same basename collision safely suffixed.
- Object candidate members correct.
- Members are folded under candidate, not independent review items.
- Review/plan/execute works.
- Path sync works for all members.
- Recovery does not false-positive synthetic folders.

### Stop Conditions

- Source 被 move/delete。
- Cancel 后有 batch。
- Execute 被自动触发。
- Object members 被拆散为独立 candidate。
- Synthetic folder 无法被 recovery 正确理解。
- Partial copy 造成 DB/FS mismatch。
- API returns success while silently dropping failed files.
- Implementation tries to add hash/dedup/trash/source cleanup.

### Tests / Validation

Create:

```text
apps/backend/tests/test_library_v2_file_collection_import.py
```

Recommended backend tests:

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
- `test_partial_copy_failure_marks_failed_without_deleting_source`
- `test_subsequent_review_plan_execute_works_for_file_collection`
- `test_recovery_scan_handles_synthetic_collection_folder`

Frontend validation:

```powershell
npm --prefix apps/frontend run build
```

Backend validation:

```powershell
cd apps/backend
python -m pytest tests/test_library_v2_file_collection_import.py -v
python -m pytest tests/test_library_v2_*.py -v
```

Recommended commit message:

```text
feat(library-v2): import selected files as collection
```

---

## 12. Manual QA Playbooks

### Playbook 1 — Type label smoke

Fixture:

- Any existing inbox item or object candidate.

Steps:

1. Open Library > Inbox.
2. Expand item/object candidate review controls.
3. Open final object type dropdown.
4. Switch language if possible.
5. Select `imgset`/`photo_event`/`web_image_set` if available.
6. Select `clip`/`clip_set` if available.

Expected result:

- Labels are grouped and readable.
- No raw locale keys.
- Existing backend value remains selectable.
- Confirm sends backend value.

Failure conditions:

- Chinese label appears in API payload.
- Existing value appears blank unexpectedly.
- Confirm fails due label/value mismatch.

### Playbook 2 — audio import

Fixture:

```text
C:\Temp\Workbench7H\source\Meeting Recording.wav
C:\Temp\Workbench7H\managed\
```

Steps:

1. Configure managed root.
2. Import `Meeting Recording.wav`.
3. Set final type to `audio`.
4. Confirm, create candidate, generate draft plan.
5. Mark ready, preflight, execute on disposable fixture.
6. Search file and open DetailsPanel.

Expected result:

- Source file still exists.
- Managed path uses audio directory/prefix.
- DetailsPanel storage state is managed.
- Path history and journal are written.

Failure conditions:

- Target path is `40_Videos/Clips`.
- Source deleted/moved.
- Path sync missing.

### Playbook 3 — asset_pack import

Fixture:

```text
Asset Pack\
  textures\wall.png
  sounds\click.wav
  fonts\demo.ttf
  readme.txt
```

Steps:

1. Import folder as object.
2. Set final type to `asset_pack`.
3. Confirm root and launch/primary fields as applicable.
4. Create candidate and draft plan.
5. Execute on disposable fixture.

Expected result:

- Folder boundary preserved.
- Members folded.
- Target path uses asset directory/prefix.

Failure conditions:

- Files split into unrelated review items.
- Target falls back to clip.

### Playbook 4 — multiple videos as collection

Fixture:

```text
Lesson 01.mp4
Lesson 02.mp4
Lesson 03.mp4
cover.jpg
```

Steps:

1. Click “选择多个文件为合集”.
2. Select all files.
3. Review collection modal.
4. Verify suggested name and type.
5. Edit name.
6. Confirm import.
7. Expand object candidate.

Expected result:

- One object candidate.
- Members grouped under candidate.
- Source files preserved.

Failure conditions:

- Multiple independent candidates created.
- Cancel path creates batch.
- Empty selection accepted.

### Playbook 5 — multiple images as collection

Fixture:

```text
001.jpg
002.jpg
003.jpg
004.jpg
cover.jpg
```

Expected result:

- Suggested `imgset` or `comic` depending sequence.
- User can override.
- Members folded.

### Playbook 6 — mixed assets as collection

Fixture:

```text
texture.png
click.wav
reference.pdf
model.fbx
readme.txt
```

Expected result:

- Suggested `asset_pack` or blank requiring confirmation.
- No automatic execute.

### Playbook 7 — collection execute path sync

Steps:

1. Import multi-file collection.
2. Confirm final type.
3. Create candidate and draft plan.
4. Execute.
5. Search all member files.
6. Inspect DetailsPanel storage section.

Expected result:

- Every member `files.path` maps under managed object root.
- Every member storage state becomes managed.
- Path history exists per member.

### Playbook 8 — recovery after collection import

Steps:

1. Import multi-file collection.
2. Manually delete one inbox member copy before execute.
3. Run recovery scan.

Expected result:

- Missing inbox copy reported.
- No auto-delete or auto-repair.

### Playbook 9 — cancel and empty selection safety

Steps:

1. Open collection import picker and cancel.
2. Verify no batch created.
3. Trigger empty manual selection/path fallback if available.
4. Verify no batch created.

Expected result:

- No empty `import_batch`.

### Playbook 10 — same basename conflict safety

Fixture:

```text
FolderA\cover.jpg
FolderB\cover.jpg
```

Steps:

1. Select both as one collection if picker allows cross-folder selection.
2. Confirm import.

Expected result:

- Both copied with no-overwrite suffix.
- Both represented as members.
- Source files preserved.

---

## 13. Risk Register

| Risk | Trigger | Severity | Detection | Mitigation | Stop condition |
|---|---|---|---|---|---|
| label/value mismatch | Dropdown refactor sends label | P1 | Inspect network payload / API error | Keep `value` as backend enum; tests | Chinese label reaches backend |
| legacy value display failure | Candidate uses `photo_event`/`web_image_set`/`clip_set` | P2 | UI smoke with seeded legacy values | Preserve aliases | Existing value becomes blank/unusable |
| `asset_pack` too broad | Unknown mixed files auto-finalized | P1 | Review detection tests | Low confidence -> blank | All unknown becomes `asset_pack` |
| collection name collision | Same generated name exists | P1 | File system fixture | No-overwrite suffix | Existing folder overwritten |
| same basename collision | Selected files from different folders share name | P1 | Cross-folder fixture | Per-file no-overwrite suffix | One file overwrites another |
| selected files from different folders confuse source context | Multi-folder selection | P2 | Modal preview | Show full source paths | User cannot see origins |
| large copy stalls | Many/large files | P1 | Manual test | Busy/progress state; future progress enhancement | UI appears frozen/no feedback |
| partial copy failure | One copy fails mid-import | P1 | Backend test | Failed items + journal + source preserved | Success response hides failure |
| cancel creates empty batch | Frontend creates batch before modal confirm | P1 | Cancel QA | Prefer single endpoint after confirm | Empty batch after cancel |
| path sync wrong | Synthetic root relative mapping wrong | P0 | Execute test | Reuse object candidate member sync | Member paths corrupt/missing |
| recovery false positive | Synthetic folders not recognized | P1 | Recovery QA | Known paths include oc root and member paths | Recovery reports valid members orphan |
| fallback to clip | New type missing target dir | P1 | Target path tests | Add `PLAN_TARGET_DIRS` and `OBJECT_PREFIX` | `audio`/`asset_pack` in clip dir |
| comic target dir unresolved | `comic` detected but no plan target | P2/P1 | Plan target tests | Human decision before 7H-2 | Comic executes to wrong category |
| file picker bridge mismatch | `selectFiles()` not true multi-select | P2 | Desktop smoke | Add narrow bridge only if needed | Cannot select multiple files |
| source file accidentally moved | Wrong FS op | P0 | Source preservation tests | Copy-only helpers | Source missing after import |
| API partial success ambiguity | Failed items not explicit | P1 | Response contract tests | Structured `failed_items` | Client cannot tell failure |
| object members visually split | UI lists members as independent review items | P1 | UI smoke | Candidate-first display | dll/config/images become separate objects |
| old tests fail due type list | Added validator too strict | P1 | Existing v2 suite | Include legacy values | Existing Phase 7 tests fail |

---

## 14. Open Questions Before Implementation

Human decisions required:

1. Should `comic` receive a first-class target directory/prefix in 7H-2, or remain under image-set handling?
2. Should `m4a`, `aac`, `opus` be added to global audio classification now?
3. Should `asset_pack` target directory be `60_Assets`, `70_Assets`, or align with another existing numbering convention?
4. Should multi-file collection import set `final_object_type` immediately from modal, or only set `suggested_object_type` and require Review confirm?
5. Should legacy values (`photo_event`, `web_image_set`, `clip_set`) be exposed in advanced options, or only displayed when existing data uses them?
6. Should `asset_pack` be suggested for unknown mixed files, or should unknown mixed files default to blank?
7. Should selected files from many folders show a stronger warning?
8. Should future collection import preserve relative folder structure, or keep 7H strictly file-only?
9. Should frontend default image loose-file import map to `imgset` or remain blank for user confirmation?
10. Should a central backend object type registry be added in 7H-2, or keep constants local to reduce scope?
11. Should `LibraryV2Capability` stale `data_foundation` values be corrected in Phase 7H, or left for a separate cleanup?
12. Should `object_parser.py` managed scan support all Phase 7 prefixes now, or only new `audio` / `asset_pack`?

Do not proceed with 7H-2/7H-3 if questions 1, 3, 4, or 6 block target path or API behavior.

---

## 15. Implementation Order and Commit Strategy

Recommended order:

1. Implement 7H-1, validate, commit.
2. Implement 7H-2, validate, commit.
3. Implement 7H-3, validate, commit.

Rules:

- Each phase must be a separate branch or at least a separate commit.
- Do not mix 7H-1 label work with backend type support.
- Do not mix 7H-2 type support with multi-file collection import.
- Do not update formal docs before each phase implementation is verified.
- Do not include generated build/dist/cache/runtime files.

Suggested commit messages:

```text
feat(library-v2): improve object type labels
feat(library-v2): add audio and asset pack object types
feat(library-v2): import selected files as collection
```

Recommended per-phase report:

- What changed
- Files changed
- Safety boundary confirmation
- Tests run
- Manual QA run
- Docs updated
- What remains intentionally not done

---

## 16. Documentation Update Checklist

### 7H-1 documentation

Update after implementation:

- `docs/library-v2/MANUAL_ACCEPTANCE_GUIDE.md`
- `docs/library-v2/BETA_TESTING_CHECKLIST.md`

Update only if the visible UX changes should be documented:

- `docs/library-v2/README.md`

### 7H-2 documentation

Update after implementation:

- `docs/library-v2/ARCHITECTURE.md`
- `docs/library-v2/API_REFERENCE.md`
- `docs/library-v2/MANUAL_ACCEPTANCE_GUIDE.md`
- `docs/library-v2/BETA_TESTING_CHECKLIST.md`
- `docs/library-v2/KNOWN_LIMITATIONS.md`
- `docs/FILE_CLASSIFICATION_RULES.md`

Must document:

- `audio`
- `asset_pack`
- target dirs
- prefixes
- detection limitations
- any audio extension additions

### 7H-3 documentation

Update after implementation:

- `docs/library-v2/API_REFERENCE.md`
- `docs/library-v2/ARCHITECTURE.md`
- `docs/library-v2/MANUAL_ACCEPTANCE_GUIDE.md`
- `docs/library-v2/BETA_TESTING_CHECKLIST.md`
- `docs/library-v2/KNOWN_LIMITATIONS.md`

Must document:

- new endpoint
- collection import UX
- synthetic inbox object folder
- cancel/no-batch behavior
- recovery behavior
- manual acceptance playbooks

---

## 17. Final Recommendation

Proceed in this order:

1. 7H-1 first.
2. 7H-2 after 7H-1 is accepted.
3. 7H-3 last.

Do not implement 7H-1/2/3 in one pass.

Reasoning:

- 7H-1 improves current UX without backend risk.
- 7H-2 expands type capability and must settle target path/prefix behavior.
- 7H-3 touches real copy flow and DB/FS consistency; it has the highest risk.

After 7H completes and passes manual QA, consider beta package work separately. Do not bundle packaging with Phase 7H implementation.

