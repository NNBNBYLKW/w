# Phase 2A：Metadata Extraction Baseline（可执行计划）

## 1. 任务目标

当前项目已经完成 Phase 1 / MVP 主链收口：

- source onboarding
- scan / delete-sync
- search
- shared details panel
- normal tags / color tags
- files / media / recent / tags retrieval
- desktop open actions
- Home / Settings / Tags 主入口

下一阶段不应直接扩成重垂类库，也不应立刻进入 AI / OCR / semantic search。

因此，Phase 2A 的唯一核心目标定义为：

> **正式激活 `file_metadata`，为当前工作台引入第一批稳定、可消费、可展示的基础元数据。**

这一阶段的定位是：
- 不是重做索引系统
- 不是重做媒体页
- 不是重做详情系统
- 而是在现有主链上增加“文件内容特征层”

---

## 2. 本阶段只做什么

Phase 2A 只做以下内容：

1. **扫描后补充最小 metadata 提取**
2. **把 metadata 写入现有 `file_metadata` 表**
3. **在 `GET /files/{id}` 中返回最小 metadata 区块**
4. **在共享详情侧栏中展示 metadata 区块**
5. **metadata 只在共享详情侧栏中消费，默认不改 MediaLibrary UI**

---

## 3. 本阶段明确不做什么

以下内容明确不进入 Phase 2A：

- thumbnail generation
- preview URL
- hover/play
- OCR
- AI tagging
- semantic search
- embeddings
- 游戏 / 电子书 / 软件库页
- library_items
- thumbnails 表 / 模型 / route
- 批量 metadata 重建系统
- 复杂后台任务平台
- 实时 watcher
- 文件内容 hash / 去重系统
- Search / Files / Recent 的 metadata filter
- 任何 page-specific details system
- 任何 open actions 行为变更

---

## 4. 推荐的最小 metadata 范围

为了保持 Phase 2A 克制，metadata 仅按当前 file_type 做最小支持：

### 4.1 image
提取：
- `width`
- `height`

### 4.2 video
本阶段不提取。

要求：
- `duration_ms` 只保留在 detail wire shape 中
- 当前返回值显式为 `null`

### 4.3 document
本阶段不提取。

要求：
- `page_count` 只保留在 detail wire shape 中
- 当前返回值显式为 `null`

### 4.4 other / archive
不做 metadata 提取。

### 4.5 title / author / extra_json
Phase 2A 一律不主动激活：
- `title`
- `author`
- `extra_json`

这些字段虽然表中存在，但当前先不正式进入主流程。

---

## 5. 数据语义要求

### 5.1 `file_metadata` 的定位
`file_metadata` 在 Phase 2A 中定义为：

> **基于当前索引文件做出的最小派生元数据层**

它不是事实层，不替代 `files`，也不应改变 `files` 的现有语义。

### 5.2 写入规则
- 每个 `file_id` 最多对应一条 `file_metadata`
- 若 metadata 成功提取：
  - upsert `file_metadata`
- 若 metadata 当前无法提取：
  - 不报整次 scan 失败
  - 对该文件允许没有 metadata row，或按实现选择保留空值 row

### 5.3 推荐语义
建议采用更克制的语义：
- **只有成功提取到至少一个 metadata 字段时才创建/更新 `file_metadata` row`**
- 不强制给每个 file 写一条空 metadata row

### 5.4 失败语义
- 单文件 metadata 提取失败：跳过该文件 metadata，不让整次 scan 失败
- metadata 提取失败不应改变 `files` 的 scan 成功/失败判定逻辑
- metadata 提取是 scan 成功后的附加 enrich step，而不是新的主成功条件
- 不做历史 metadata backfill job；已有 indexed files 只有在 source 再次 scan 后才会获得 metadata

### 5.5 再次扫描时的更新语义
若同一路径文件再次被扫描：
- metadata 可按当前扫描结果覆盖更新
- 不需要额外保存 metadata 历史版本

---

## 6. 推荐实现策略

## 6.1 扫描调用链建议
当前 scan 主链已经成立，因此 Phase 2A 应尽量复用现有链路：

1. `POST /sources/{id}/scan`
2. `SourceManagementService.trigger_scan(...)`
3. `ScanningService.run_source_scan_inline(...)`
4. `ScannerWorker.scan_source(...)`
5. `FileRepository.upsert_discovered_files(...)`
6. **新增：对本次 seen 文件做最小 metadata extraction + persistence**
7. success/failure 收口保持原有 scan 语义

### 关键原则
- 不能把 metadata extraction 做成另一个独立大系统
- 不能破坏当前 scan / delete-sync 行为
- 不能让 metadata 失败把整个 source scan 判成 failed

---

## 6.2 提取执行位置建议
建议新增：
- `apps/backend/app/services/metadata/service.py`
- `apps/backend/app/workers/metadata/extractor.py`
- `apps/backend/app/repositories/file_metadata/repository.py`

推荐分工：

### extractor
只负责：
- 输入 file row 或最小 file payload
- 读取真实文件路径
- 尝试提取最小 metadata
- 返回标准化结果

### metadata service
只负责：
- 协调一批文件的 metadata enrich
- 调 extractor
- 调 repository upsert
- 控制失败隔离策略

### repository
只负责：
- `get_by_file_id(...)`
- `upsert_metadata(...)`
- 或批量 upsert helper

---

## 7. Exact Files To Change

### Backend
建议允许修改：

- `apps/backend/app/services/scanning/service.py`
- `apps/backend/app/services/details/service.py`
- `apps/backend/app/api/schemas/file.py`
- `apps/backend/app/repositories/file/repository.py`（仅在确有必要时，为 metadata 读取辅助方法做极小补充）
- `apps/backend/app/db/models/file_metadata.py`（如当前模型需要最小修正）
- `apps/backend/app/services/metadata/service.py`（new）
- `apps/backend/app/workers/metadata/extractor.py`（new）
- `apps/backend/app/repositories/file_metadata/repository.py`（new）
- `apps/backend/tests/test_phase2a_metadata_extraction.py`（new）
- `apps/backend/tests/test_phase2b_file_details.py`（update）
- `apps/backend/tests/test_phase5a_media_library.py`（仅在 media list 实际消费 metadata 时 update）

### Frontend
建议允许修改：

- `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`
- `apps/frontend/src/entities/file/types.ts`
- `apps/frontend/src/app/styles/global.css`

### Docs
建议允许修改：

- `plans/README.md`
- `plans/phase-2a-metadata-extraction.md`（new）
- `docs/windows本地资产管理工作台_数据库schema与api草案_v_1.md`
- `docs/windows本地资产管理工作台_开发任务拆解文档_v_1.md`
- 如有需要，再更新：`docs/current-project-status-dossier.md`

---

## 8. Exact Files Not To Touch

以下文件/区域本阶段原则上不应修改：

### Backend
- `apps/backend/app/api/routes/search.py`
- `apps/backend/app/api/routes/files.py`（除非 `GET /files/{id}` schema 变动确实需要最小 route 适配）
- `apps/backend/app/api/routes/library.py`（除非 media list 本阶段确实消费 metadata）
- `apps/backend/app/api/routes/recent.py`
- `apps/backend/app/api/routes/tags.py`
- `apps/backend/app/services/tags/service.py`
- `apps/backend/app/services/color_tags/service.py`
- `apps/backend/app/services/files/service.py`
- `apps/backend/app/services/recent/service.py`
- `apps/backend/app/services/media/service.py`
- `apps/backend/app/workers/scanning/scanner.py`（除非为了向 metadata service 提供必要输入做极小改动）
- 所有 CORS / desktop action / source root validation 逻辑

### Frontend
- `apps/frontend/src/pages/search/SearchPage.tsx`
- `apps/frontend/src/pages/files/FilesPage.tsx`
- `apps/frontend/src/pages/recent/RecentImportsPage.tsx`
- `apps/frontend/src/pages/tags/TagsPage.tsx`
- `apps/frontend/src/pages/settings/SettingsPage.tsx`
- `apps/frontend/src/pages/home/HomePage.tsx`
- `apps/frontend/src/services/desktop/openActions.ts`
- `apps/frontend/src/features/source-management/SourceManagementFeature.tsx`
- `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`

### Desktop
- `apps/desktop/**`

### Data / product scope
- 不新增新页面
- 不新增新主导航
- 不新增新全局 store
- 不改 Search / Files / Media / Recent 的查询语义
- 不做 thumbnail / preview / hover 播放

---

## 9. API / Response 变更要求

## 9.1 `GET /files/{id}`
Phase 2A 最推荐的外部变化是：

在当前 detail payload 中新增：

```json
{
  "item": {
    "id": 1,
    "name": "cover.png",
    "path": "D:\\Assets\\cover.png",
    "file_type": "image",
    "size_bytes": 12345,
    "created_at_fs": "2026-04-16T09:00:00",
    "modified_at_fs": "2026-04-16T10:00:00",
    "discovered_at": "2026-04-16T10:30:00",
    "last_seen_at": "2026-04-16T11:00:00",
    "is_deleted": false,
    "source_id": 1,
    "tags": [],
    "color_tag": null,
    "metadata": {
      "width": 1920,
      "height": 1080,
      "duration_ms": null,
      "page_count": null
    }
  }
}
```

### 语义要求
- `metadata` 可以为 `null`
- 若存在 `metadata`，总是固定包含：
  - `width`
  - `height`
  - `duration_ms`
  - `page_count`
- 当前 inactive 字段显式返回 `null`
- 不返回 `title` / `author` / `extra_json`

---

## 9.2 `/library/media`
默认建议：
- **不改 response shape**
- MediaLibrary 继续走当前最小 list shape

若实现非常轻量且不增加复杂度，可允许在前端只通过详情侧栏看到 metadata，而不是直接在 media list 项里加字段。

也就是说：

> Phase 2A 的最小成功标准不依赖 `/library/media` shape 变化。

---

## 10. 前端展示规则

## 10.1 DetailsPanelFeature
在当前详情面板中新增一个轻量 `Metadata` 区块：

### 当 `metadata` 为 null
显示：
- `No extracted metadata available yet.`
或等价中文文案

### 当 `metadata` 有值
按 file_type 做最小显示：

#### image
- Width
- Height

#### video
- Width
- Height
- Duration

#### document
- Page count（如果本阶段已支持）

### 状态要求
- metadata 展示是 detail query 的一部分
- 不新增单独 metadata query
- 不新增 metadata mutation
- metadata 区块的展示不能破坏当前 tags / color tags / open actions 区块

---

## 10.2 MediaLibraryFeature
本阶段默认不改 MediaLibrary UI。

metadata 消费全部放在共享 DetailsPanel。

---

## 11. 错误处理规则

### 11.1 metadata 提取失败
- 单文件失败不影响整次 scan success
- 不应把 source scan 标成 failed
- 只跳过该文件 metadata enrich

### 11.2 文件已不存在
如果 scan 与 metadata enrich 之间文件被移除：
- 该文件 metadata enrich 可跳过
- 不影响本轮 scan 的主成功语义

### 11.3 不支持的格式
- 视为 no metadata
- 不报错
- 不写 failure 状态给用户

### 11.4 前端 detail 展示
- `metadata = null` 不是错误
- 只是一种正常的“当前无 metadata”状态

---

## 12. 测试计划

## 12.1 Backend tests
新增：
- `tests.test_phase2a_metadata_extraction`

至少覆盖：

### `extracts_image_dimensions_and_persists_file_metadata`
- 创建 image 文件
- scan 后验证 `file_metadata.width/height`

### `does_not_backfill_existing_files_without_rescan`
- 已有 indexed files 在未重新 scan 前不会自动获得 metadata

### `metadata_failure_does_not_fail_source_scan`
- patch extractor 抛 deterministic exception
- scan 仍成功
- file row 存在
- metadata row 缺失或不更新

### `file_details_returns_metadata_block_when_present`
- `/files/{id}` 返回 metadata

### `file_details_returns_metadata_null_when_absent`
- `/files/{id}` 正常返回 `metadata: null`

### `rescan_updates_metadata_when_file_changes`
- 若实现成本合理，可覆盖再次扫描后 metadata 更新
- 若不稳，可留到后续阶段

---

## 12.2 Regression
至少回归：

```powershell
cd apps/backend
python -m unittest
```

并重点确认以下旧能力不回退：
- source scan
- delete sync
- search
- file details
- tags
- color tags
- files list/browse
- media library
- recent imports
- tag files retrieval

---

## 12.3 Frontend validation
至少完成：

```powershell
cd apps/frontend
npm run build
```

并手工确认：
- 选中 image 文件后，DetailsPanel 出现 metadata 区块
- `metadata` 非空时固定四字段都可见，inactive 字段显示为 unavailable / null 对应展示
- 无 metadata 的文件不会把 panel 弄成 error
- tags / color tags / open actions 继续正常工作

---

## 13. Manual acceptance path

最小手工验收路径：

1. 在 Settings 添加 source
2. 触发 scan
3. 在 Search 找到一个 image 文件
4. 打开共享详情侧栏
5. 确认看到 image metadata（至少 width / height）
6. 给该文件添加 tag / color tag，确认未受影响
7. 对一个旧 indexed file 在未重新 scan 前查看 detail，确认不会自动出现 metadata
8. 重新 scan 对应 source 后，再查看同一 image 文件，确认 metadata 出现
9. 执行 `Open file` / `Open containing folder`，确认未受影响

---

## 14. Done When

只有同时满足以下条件，Phase 2A 才算完成：

### Backend
- scan 成功后可对 image（至少）写入 `file_metadata`
- `GET /files/{id}` 返回 `metadata` 区块或 `metadata: null`
- metadata 提取失败不会导致整次 scan failed
- 不存在历史 metadata backfill job
- 全量 backend unittest 通过

### Frontend
- `DetailsPanelFeature` 正常展示 metadata 区块
- metadata 缺失时表现为正常 empty state，而不是错误
- MediaLibrary UI 默认未改
- frontend build 通过

### Scope discipline
- 没有顺手引入 thumbnail / preview / AI / 新页面
- 没有改变 Search / Files / Media / Recent 的产品边界
- 没有新增 page-specific details system

### Docs
- `plans/phase-2a-metadata-extraction.md` 已新增
- schema/API 文档已同步当前 detail payload 的 metadata 变化
- 如有必要，current project status dossier 已补充当前 metadata 激活状态

---

## 15. 交付输出要求（给 Codex）

实现后必须输出：

1. `What changed`
2. `Files changed`
3. `How to verify manually`
4. `Validation`
5. `What remains intentionally not implemented`
6. `Docs updated`

并明确说明：
- 是否只先支持 image metadata
- video / document 哪些字段本轮真正进入主流程
- 哪些字段仍然只是 schema 占位未激活

---

## 16. 当前建议结论

Phase 2A 的最佳切入点不是新页面，也不是新垂类库，而是：

> **激活 `file_metadata`，让现有工作台第一次拥有真正可消费的内容特征层。**

这一步完成后，后续 Phase 2B（thumbnail / preview）、Phase 2C（retrieval loop expansion）和更远的轻量垂类库，都会更自然也更稳。
