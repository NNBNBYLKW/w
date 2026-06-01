# Library as Foundation Feasibility Research

> Date: 2026-05-15 | Status: Research Report | Phase: Pre-decision

---

## 1. Executive Summary

**结论：方向可行，但需要实质性架构扩展。** 当前 Workbench 有大约 60% 的基础能力可以复用（文件扫描、分类、标签、组织计划、库根管理）。但三个关键能力完全缺失：**用户主动导入**、**操作日志与恢复**、**文件所有权生命周期管理**。建议在现有 beta 线上保持独立演进，将 "Library as Foundation" 作为 Phase 7/v2 进行设计，不做紧急切换。

## 2. Current Architecture Facts

### 2.1 当前数据流（source → scan → files → organize → managed root）

```
[用户添加 Source 目录]
     ↓
[POST /sources/{id}/scan] → ScannerWorker.scan_source()
     ↓
[os.scandir 遍历目录] → DiscoveredFileRecord → classify_file()
     ↓
[FileRepository.upsert_discovered_files] → files 表
     ↓
[用户手动操作] → tags/color tags/favorites/ratings/collections
     ↓
[Library Organize] → scan_candidates → generate_plan → execute → move 文件到 managed root
```

**源码证据：**
- Scanner: `apps/backend/app/workers/scanning/scanner.py:36` (scan_source)
- Classification: `apps/backend/app/core/classification.py:107` (classify_file)
- File upsert: `apps/backend/app/repositories/file/repository.py:54` (upsert_discovered_files)
- Organize execute: `apps/backend/app/services/library/organize.py:959` (shutil.move)

### 2.2 当前页面数据来源

| 页面 | 数据源 | 查询方式 |
|------|--------|----------|
| Search | `files` 表 | `LIKE '%query%'` on name + path, 按 file_type/kind/placement/color_tag 过滤 |
| Media | `files` 表 | `file_type="video"` 或按 placement 路由 |
| Games | `files` 表 | 按 `file_kind` + `auto_placement` 路由 |
| Software | `files` 表 | 同上 |
| Documents | `files` 表 | 同上 |
| Recent | `files` 表 | 按 `discovered_at` 排序 |
| Tags | `file_tags` 关联表 | JOIN files ← file_tags → tags |
| Collections | `collections` 表 | 手动保存的查询条件，无实时规则引擎 |
| Library Objects | `library_objects` 表 | 独立于 files 表的对象识别结果 |
| DetailsPanel | 跨表联合 | 一个文件对象关联到 File + FileUserMeta + FileMetadata 等多个表 |

**源码证据：**
- Search: `apps/backend/app/services/search/service.py:20` + `apps/backend/app/repositories/file/repository.py:179`
- Browse: `apps/backend/app/api/routes/library.py` (按 placement 路由到各垂直页面)

### 2.3 文件所有权现状

| 能力 | 当前状态 | 源码证据 |
|------|----------|----------|
| 用户导入文件 | **无** | 无 `POST /files/import` 端点；文件只能通过 source scan 进入 |
| 文件移动后 DB 更新 | **无** | organize.py `_execute_action` 只写 `before_path/after_path`，不更新 `files.path` |
| 文件所有权标记 | **无** | `files` 表无 `is_managed`/`ownership_status` 字段 |
| 操作日志 | **部分** | `organize_action_logs` 表有 organize 事件日志，但无通用文件变更日志 |
| 垃圾桶/撤销 | **无** | 无 trash 表、无 undo 机制 |
| 软删除 | **有** | `files.is_deleted` (Boolean, 默认 False) |
| 内容校验 | **部分** | `files.checksum_hint` 列存在但从未被填充（always None） |
| 原始路径保留 | **部分** | `before_path/after_path` 在 organize actions 中，但不在 files 表中 |

### 2.4 Inbox 概念

当前唯一与 "inbox" 相关的是 `organize.py:63` 的常量：

```python
INBOX_NAMES = {"00_inbox", "_to_sort", "inbox"}
```

这是纯目录命名约定——没有 inbox 数据表，没有 inbox API，没有自动处理。`_is_inbox_path()` 函数（`organize.py:1887`）仅用于区分 organize candidates 的类型（inbox_file vs loose_file）。

## 3. Proposed New Main Chain

```
Import → Inbox → Classify/Review → Organize → Managed Library → Browse/Search
```

### 3.1 模块复用性分析

| 新链环节 | 可复用现有模块 | 需要新增/修改 |
|----------|---------------|--------------|
| **Import** | 文件扫描的 `classify_file()` 可用于自动分类导入文件 | 全新：用户文件选择 / 拖放 / 复制导入 → inbox 目录 |
| **Inbox** | 0% — 当前无 inbox 系统 | 全新：InboxItem 模型、状态机、UI 页面 |
| **Classify/Review** | `classification.py` 分类规则、`OrganizeSuggestion` 建议系统、`LibraryObject.needs_review` 审核标记 | 修改：支持 per-file classification override、用户确认 UI |
| **Organize** | `LibraryOrganizeService` 全套（plan generation/execution）复用度最高 | 修改：执行后更新 `files.path`、标记 managed 状态 |
| **Managed Library** | `LibraryRoot` CRUD、文件浏览页面 | 修改：区分 external/inbox/managed 文件来源；可能需要 `is_managed` 字段 |
| **Browse/Search** | 所有现有页面和过滤逻辑 | 修改：增加 managed/external 过滤维度 |

### 3.2 数据表影响

| 表名 | 状态 | 需要的变更 |
|------|------|-----------|
| `files` | 可复用 | 可能需要新增: `is_managed`, `managed_at`, `original_path`, `inbox_item_id` |
| `sources` | 可复用 | 无变更（source scan 模式保留） |
| `library_roots` | 可复用 | 无变更 |
| `organize_*` | 可复用 | 执行后同步更新 files 表 |
| `tags` / `file_tags` | 可复用 | 跨 inbox/managed 使用 |
| `collections` | 可复用 | 可能需要 managed 过滤 |
| **`inbox_items`** | **需要新增** | 全新表: id, source_file_path, target_inbox_path, import_method, status, classification, batch_id, error_message |
| **`operation_journal`** | **需要新增（推荐）** | 通用操作日志: timestamp, operation_type, entity_type, entity_id, before_state, after_state |
| **`file_path_history`** | **需要新增（推荐）** | 路径变更历史: file_id, old_path, new_path, changed_at, change_reason |
| **`import_batches`** | **需要新增** | 批量导入记录: id, created_at, status, source_type, file_count |

## 4. Reusable Existing Modules

| 模块 | 文件 | 复用度 | 说明 |
|------|------|--------|------|
| 文件分类引擎 | `classification.py` | 90% | 扩展名规则可直接用于 import inbox 分类 |
| Library Organize | `organize.py` | 85% | Plan/execute/preflight/reconcile 全套可复用 |
| 文件扫描器 | `scanner.py` | 70% | 遍历目录逻辑可复用，但需要新增 "import 专用入口" |
| 标签/评分/收藏 | `file_user_meta.py` | 100% | 无需变更，跨 inbox/managed 通用 |
| Library Root 管理 | `library_root.py` | 100% | 无需变更 |
| 搜索 | `search/service.py` | 80% | 需增加 inbox/managed 过滤维度 |
| 组织建议 | `OrganizeSuggestion` | 70% | provider 字段已支持扩展（当前仅 `rule_based`） |
| DetailsPanel | `DetailsPanelFeature.tsx` | 80% | 需增加文件来源标识 |

## 5. Required New Concepts

### 5.1 必须新增的核心概念

| 概念 | 模型/表 | 优先级 | 说明 |
|------|---------|--------|------|
| **Inbox Item** | `inbox_items` 表 | P0 | 导入文件的中间状态记录。track imported → classified → organized 全程 |
| **Import Batch** | `import_batches` 表 | P1 | 批量导入的批次记录。支持撤销整个批次 |
| **Managed File Flag** | `files.is_managed` 字段 | P0 | 标记此文件已由软件管理（已入库） |
| **Original Path** | `files.original_path` 字段 | P1 | 保留导入前的原始路径，用于恢复/审计 |
| **File Path History** | `file_path_history` 表 | P1 | 记录文件被 organize 移动的全部历史 |
| **Operation Journal** | `operation_journal` 表 | P1 | 通用操作日志。之前被 deferred，但在 "软件管理文件" 模式下变得必要 |

### 5.2 不应在当前阶段做的

- **Trash / Recycle Bin**：复杂度高，可以通过 "标记为不活跃 + 保留原始路径" 先替代
- **Content Hash / Dedup**：性能开销大，先不引入。`checksum_hint` 可以后续按需填充
- **AI Auto-Classification**：保持 rule_based，AI 只作为 suggestion layer
- **Full MIME Detection**：保持 extension-based，后续按需添加

## 6. Database Impact

### 6.1 建议新增字段（最小方案）

**`files` 表扩展：**

```sql
ALTER TABLE files ADD COLUMN is_managed BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE files ADD COLUMN managed_at DATETIME NULL;
ALTER TABLE files ADD COLUMN original_path TEXT NULL;
ALTER TABLE files ADD COLUMN inbox_item_id INTEGER NULL REFERENCES inbox_items(id) ON DELETE SET NULL;
```

### 6.2 建议新增表

**`inbox_items`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `source_file_path` | TEXT NOT NULL | 用户选择的原始文件路径 |
| `target_inbox_path` | TEXT NOT NULL | 复制/移动到 inbox 后的实际路径 |
| `import_method` | TEXT NOT NULL | 'copy' / 'move' / 'link' |
| `import_batch_id` | INTEGER FK | |
| `status` | TEXT NOT NULL | 'imported' / 'classified' / 'planned' / 'organized' / 'rejected' / 'failed' |
| `detected_type` | TEXT NULL | 自动检测的对象类型 |
| `user_classification` | TEXT NULL | 用户手动覆盖的分类 |
| `error_message` | TEXT NULL | |
| `created_at` | DATETIME NOT NULL | |
| `updated_at` | DATETIME NOT NULL | |

**`operation_journal`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `operation_type` | TEXT NOT NULL | 'import' / 'classify' / 'move' / 'organize' / 'delete' / 'restore' |
| `entity_type` | TEXT NOT NULL | 'file' / 'inbox_item' / 'plan' |
| `entity_id` | INTEGER NOT NULL | |
| `summary` | TEXT NOT NULL | 人类可读的操作摘要 |
| `details_json` | TEXT NULL | 结构化详情 |
| `created_at` | DATETIME NOT NULL | |

## 7. File Operation Safety

### 7.1 Import 方式比较

| 方式 | 安全 | Local-first | 原子性 | 建议 |
|------|------|-------------|--------|------|
| **copy** | 最高 — 原文件不变 | 中等 — 占用双倍空间 | 中等 — 需在 copy 成功后提交 DB | ✅ 推荐作为默认 |
| **move** | 低 — 原文件消失 | 中等 — 节省空间 | 低 — DB 失败后源文件已不在 | ⚠️ 不推荐 |
| **link** | 中等 — 不可跨盘 | 最高 — 零拷贝 | 高 — 只需 DB 操作 | ⚠️ 仅限同盘 |

**建议：默认 copy，可选 move（用户明确选择时）。** 这避免了 DB 写入失败后文件丢失的问题。

### 7.2 原子性问题

当前 organize 的执行没有 DB/FS 两阶段提交：

- `_execute_action` 先做 `shutil.move`，后写 DB action status
- 如果 move 成功但 DB commit 失败 → 文件已移动但记录未更新
- 如果 DB commit 成功但 move 失败 → action status = "failed"，记录在 error_message

**改进方向（非当前实现）：**
- Organize 执行应改为：先记录 executing 状态 → 执行 FS 操作 → 更新 DB 记录
- Import 应改为：先 copy 文件到 inbox → 写入 inbox_items + files 记录 → 标记导入完成

### 7.3 当前缺失的安全能力

| 能力 | 当前状态 | 缺口 |
|------|----------|------|
| 避免覆盖 | ✅ preflight checks target_exists → blocked | 已有，充足 |
| 跨盘移动 | ⚠️ `shutil.move` 非原子 | 需增加操作日志 |
| 同名冲突处理 | ⚠️ preflight blocked，无自动重命名 | 需增加 rename-imported 选项 |
| 文件完整性校验 | ❌ checksum_hint 为空 | 可后续按需填充 |
| 操作回滚 | ⚠️ rollback plan 是草稿，需手动执行 | 短期可接受 |
| 垃圾桶 | ❌ 无 | 先不做 |

## 8. Inbox Design Questions

### 8.1 Inbox 状态机

```
imported → classified (用户选择类别)
        → planned (已生成 organize plan)
        → organized (plan 执行完成)
        → rejected (用户忽略/删除)
        → failed (导入或处理过程出错)
```

### 8.2 关键设计决策

| 问题 | 建议 | 原因 |
|------|------|------|
| 物理文件夹 vs DB 状态 | **两者都有** | inbox 目录存放实际文件，inbox_items 表追踪状态 |
| Inbox 文件是否进入 Search | **是，但默认不搜索 inbox 中的文件** | 用户可以切换 "包括 Inbox" |
| Inbox 文件是否允许 tags | **是** | tags 系统已在 files 表级别，自动支持 |
| 是否与 Library Pending 合并 | **是** | 当前 pending candidates 实际上是 inbox 文件的对象识别结果 |
| 是否保存原始路径 | **是** | `original_path` 字段 |
| 是否保留 import batch | **是** | `import_batches` 表支持批量撤销 |

### 8.3 与当前 Organize Candidates 的关系

当前 organize candidates 机制可以复用为 inbox → organize 的桥梁：

- **当前**：candidate scan 从 source 目录中查找需要整理的文件
- **新设计**：inbox 中的文件自动成为 candidate（跳过 source scan 中的 inbox 过滤步骤）
- **复用**：candidate 的 `status` 字段（pending → added_to_plan → resolved）直接对应 inbox 状态机的一部分

## 9. Classification and Rule Management

### 9.1 当前规则能力评估

| 能力 | 当前 | 对 Inbox Import 的适用性 |
|------|------|-------------------------|
| Extension-based | ✅ 完全 | ✅ 够用——导入时已知扩展名 |
| MIME-based | ❌ 无 | ⚠️ 扩展名可能被改或缺失 |
| 用户覆盖 | ❌ 无 per-file override | ❌ 关键缺口——用户必须在导入时修正错误分类 |
| 规则配置 | ❌ 硬编码 | ❌ 需要 JSON config 或 DB rules |
| AI 建议 | ❌ 无 | ⚠️ 后续可选，不应是 blocker |

### 9.2 Inbox 分类的最小扩展路径

1. **Per-file override**：在 `inbox_items.user_classification` 或 `FileUserMeta` 中增加分类覆盖
2. **Per-extension config**：Phase C 的 JSON 配置文件
3. **AI suggestion**：复用 `OrganizeSuggestion` 表，增加 `provider="ai_suggestion"`

**优先级：用户手动覆盖 > 扩展名规则默认 > 回退 other**

## 10. Managed Library File Structure Options

### Option 1: Flat by type
```
ManagedLibrary/
  Inbox/
  Media/          ← 整理后的文件按类别放在这里
  Books/
  Games/
  Software/
```

**优点：** 简单，用户一眼能看懂。**缺点：** 与 organize templates 的 `10_Movies_Anime/Movies/[MOVIE] Title (Year)` 结构不一致。**Windows 路径风险：** 低（短路径）。**数据库映射：** 简单。

### Option 2: Object-organized
```
ManagedLibrary/
  Inbox/
  Objects/
    10_Movies_Anime/Movies/[MOVIE] Title (Year)/  ← 与当前 organize 模板一致
    20_Games/PC_Portable/[GAME] Title (Year)/
  80_Documents/Docsets/[DOCSET] Title (Year)/
```

**优点：** 与现有 organize templates 100% 兼容。**缺点：** 用户可读性一般（深层目录）。**Windows 路径风险：** 中等（需注意路径长度）。**数据库映射：** 中等。

### Option 3: Hybrid with meta
```
ManagedLibrary/
  Inbox/
  ByType/         ← 按对象类型组织
  ByCollection/   ← 按用户集合组织（可选）
  _meta/          ← 软件内部元数据
  _trash/         ← 垃圾桶（Phase D+）
```

**优点：** 灵活，支持多维度访问。**缺点：** 最复杂。**数据库映射：** 最难（需要路径 → 类型的双向映射）。

### 推荐

**Option 2** 作为默认——与当前 organize 模板 100% 兼容，零迁移成本。Option 3 的 ByCollection 可以后续通过软链接或 DB 视图实现，不需要物理文件移动。

## 11. UX and Page Architecture Impact

### 11.1 页面架构变更

| 问题 | 建议 | 原因 |
|------|------|------|
| Library 是否成为主入口 | **否** — 保持多入口 | 用户习惯不同；Search 和 Library 应并列 |
| 是否需要 Import 页面 | **是** — Library 下的 Inbox 子页 | 与 Pending 合并，不新建顶层导航 |
| Inbox 独立导航 vs Library 子页 | **Library 子页** | 当前 Library 已有 Pending/Objects/Plans 标签；Inbox 可作为新标签 |
| Media/Games/Software 是否只展示正式库 | **默认是，可切换到 "全部文件"** | 需要 `is_managed` 过滤 |
| Search 搜索范围 | **默认全部（可过滤）** | 增加 "仅搜索已管理文件" 选项 |
| DetailsPanel 区分来源 | **显示 Inbox / Managed / External 标签** | 三个 state 的视觉区分 |
| Tags/Collections 跨区使用 | **是** | tags 已在 files 表级别，天然支持跨区 |

### 11.2 新链的用户可见流程

```
1. 用户点击 "导入文件" 
2. 选择文件/文件夹 → 文件复制到 ManagedLibrary/Inbox/
3. Inbox 页面显示待分类文件
4. 用户逐个或批量分类 → 确认 detected_type / 修改错误分类
5. 点击 "生成整理计划" → 从 inbox items 生成 organize plan
6. Preflight → Execute → 文件移动到最终位置
7. 文件出现在 Media/Games/Software 等正式浏览页面
```

## 12. AI Collaboration Boundary

### 12.1 当前 AI 能力

**零。** 没有 LLM、没有 ML 模型、没有 OpenAI/Anthropic 导入。`OrganizeSuggestion` 的 provider 字段当前只有 `"rule_based"`。

### 12.2 AI 接入边界

**原则：AI 只能做 suggestion，不能直接写正式文件事实或执行文件移动。**

```
AI Suggestion 层
  ↓ (suggestion → OrganizeSuggestion 表)
User Confirmation 层  
  ↓ (accept/reject → 更新 inbox_item.user_classification)
Rule Engine 层
  ↓ (生成 organize plan actions)
Execution 层
  ↓ (用户在 preflight 后手动 execute)
```

**AI 对文件的读取边界：**
- ✅ 读取文件名、扩展名、路径结构
- ✅ 读取已有 metadata（asset.yaml）
- ✅ 读取缩略图/预览帧（如有）
- ❌ 读取完整文件内容（除非用户明确授权）
- ❌ 直接修改文件系统
- ❌ 直接执行 organize plan

### 12.3 AI 结果存储

复用现有 `organize_suggestions` 表，增加 provider 值：
- `"rule_based"` — 现有
- `"ai_extension_guess"` — AI 基于扩展名的分类建议
- `"ai_content_analysis"` — AI 基于内容分析的分类建议
- `"ai_metadata_match"` — AI 基于在线元数据的匹配建议

## 13. Migration Strategy

### 13.1 最安全的过渡路径

**双模式并存，渐进切换：**

1. **Phase 7A**：新增 `files.is_managed` 和 `files.original_path` 字段（nullable，默认 NULL = not managed）
2. **Phase 7B**：新增 Import → Inbox 流程。现有 source scan 模式不受影响
3. **Phase 7C**：Inbox → Organize 全链路贯通。Organize 执行后更新 `files.is_managed = True`
4. **Phase 7D**：Media/Games/Software 等页面增加 managed 视图切换
5. **Phase 7E**：评估是否可以 deprecate source scan 模式（或保留作为 "链接外部目录" 模式）

### 13.2 不会破坏 beta 用户数据

| 现有数据 | 迁移方式 | 风险 |
|----------|----------|------|
| `files` 表现有记录 | `is_managed` 默认 NULL，现有的 source scan 文件不受影响 | 极低 |
| `file_user_meta` (tags/ratings/etc) | 不变，跨区通用 | 极低 |
| `library_objects` | 现有 organize plans 历史保留 | 极低 |
| `organize_plans` | 历史 plan 保留，新 plan 可选中 inbox items 作为 candidate | 低 |

### 13.3 是否需要 feature flag

**建议是。** 新增 `isManagedLibraryEnabled` 配置项或环境变量，默认 false。在 beta 阶段逐步开启。

## 14. Performance and Scale

### 14.1 当前性能基线

| 操作 | 指标 | 来源 |
|------|------|------|
| 10K 文件扫描 | 271.6s (36.8 files/s) | PHASE6_SUMMARY.md |
| 50 thumbnails | ~5.7s | PHASE6_SUMMARY.md |
| 查询端点 | all sub-35ms | PHASE6_SUMMARY.md |
| 数据库大小 | 72 MB per 10K files | KNOWN_LIMITATIONS.md |

### 14.2 Import 场景新增性能考虑

| 考虑 | 评估 |
|------|------|
| Import copy 开销 | 与文件大小成正比。大文件（4K 视频、游戏 ISO）copy 可能耗时数分钟 |
| Content hash | 对大文件计算 SHA-256 会很慢。如需 hash，应在后台异步队列中执行 |
| 后台任务队列 | 当前无任务队列。`tasks` 表存在但无 worker pool。需要新增 |
| 进度条 | 当前无进度上报机制。需要在 import service 中增加回调或 WebSocket |
| SQLite 是否够用 | 对于单用户 local 应用，完全够用。不需要 PostgreSQL |
| UI 卡死 | 当前 organize 执行在 daemon 线程中，UI 不阻塞。Import 应采用同样模式 |

## 15. Risk Matrix

### P0 — 数据丢失风险

| 风险 | 当前防护 | 缺口 | 建议措施 |
|------|---------|------|----------|
| 文件被覆盖 | ✅ preflight target_exists → blocked | 已有 | 保持 |
| 文件被意外删除 | ✅ organize 只有 mkdir/move/write，无 delete | 已有 | 保持 |
| DB/FS 不一致（move 成功但 DB 未更新） | ⚠️ `_execute_action` 单次 commit，无两阶段提交 | 缺少操作日志 | 增加 operation_journal + reconcile 自动修复 |
| 导入 copy 失败 | ❌ 暂无导入功能 | 全新 | copy → verify → DB write 的原子性需要设计 |

### P1 — 可用性风险

| 风险 | 当前防护 | 缺口 | 建议措施 |
|------|---------|------|----------|
| 分类错误导致文件放错位置 | ⚠️ extension-based 分类可能不准 | 缺少 per-file override | 增加 Inbox 分类确认步骤 |
| 导入中断 | ❌ 无导入功能 | 缺少断点续传 | 批次级别的状态追踪 |
| 同名文件冲突 | ⚠️ preflight blocked，但无自动重命名 | 缺少 rename-on-import | 提供 rename / skip / replace 选项 |
| 跨盘移动失败 | ⚠️ `shutil.move` 在跨盘时非原子 | 已有已知限制 | 操作日志中记录，提供重试 |

### P2 — 体验风险

| 风险 | 当前防护 | 缺口 | 建议措施 |
|------|---------|------|----------|
| 大文件导入慢 | ❌ 同步 copy | 缺少异步导入队列 | 后台线程 + 进度条 |
| UX 复杂 | N/A | Inbox → Classify → Organize 链路步骤多 | UI 引导 + 默认值 |
| 规则难懂 | extension-based 对用户透明 | 缺少规则说明入口 | 帮助文档 + 分类结果说明 |

## 16. Recommended Research Conclusions

### Top 10 Findings

1. **60% 的基础模块可复用** — `classification.py`、`organize.py`、`scanner.py`、标签/评分/收藏系统、LibraryRoot 管理
2. **文件导入完全是空白** — 没有 import API、没有 inbox 系统、没有导入 UI
3. **操作日志和恢复是关键缺口** — 当前 "没有操作日志" 是有意设计（beta 阶段简单化），但在 "软件管理文件" 模型下变得必要
4. **Organize 不更新 files.path** — 执行 move 后 DB 记录保持旧路径，直到下次 source scan
5. **分类系统已足够支撑 import inbox** — extension-based + 用户手动覆盖可以解决 90%+ 的分类需求
6. **现有 safety invariants 良好** — preflight 不覆盖、不删除、不自动执行。这些应原封保留
7. **没有 AI、没有 MIME** — 当前 zero。AI 应作为 suggestion 层，不能直接移动文件
8. **SQLite 完全够用** — 单用户 local 应用不需要迁移数据库
9. **Beta 用户数据不会受损** — 所有新字段都可以 nullable，双模式并存
10. **Migration 可以通过 feature flag 安全进行** — 不需要破坏性切换

### Biggest Blockers

1. **没有操作日志和恢复机制** — 这是 "软件管理文件" 的前提条件。没有日志就无法审计、无法回滚、无法排查问题
2. **没有导入基础设施** — inbox 表、import API、文件选择 UI 全部需要新建
3. **Organize 不更新 files.path** — 导致 organize 后的文件和 DB 记录不同步，需要 source re-scan 来修复

### What Can Be Reused (最高复用价值)

| 模块 | 复用度 |
|------|--------|
| `organize.py` 全套 (plan/execute/preflight/reconcile) | 85% |
| `classification.py` | 90% |
| `scanner.py` 文件发现逻辑 | 70% |
| Tags / Color Tags / Favorites / Ratings | 100% |
| Library Root CRUD | 100% |
| DetailsPanel | 80% |
| Search + Browse 页面 | 80% |

### What Must Be Newly Designed

1. **Inbox 系统** — `inbox_items` 表 + Import API + Inbox UI 页面
2. **操作日志** — `operation_journal` 表
3. **文件路径历史** — `file_path_history` 表
4. **Import 批量管理** — `import_batches` 表 + 批量撤销
5. **文件所有权标记** — `files.is_managed` / `files.original_path`
6. **Import 专用文件选择 UI** — 拖放 / 文件对话框 / 批量导入

## 17. Open Questions for Human Decision

1. **是否应该将 "Library as Foundation" 作为 Phase 7 / v2 进行，而不是在当前 beta 中紧急切换？**
   - 建议：Phase 7 / v2。当前 beta 保持现有 scan-based 模式，新链作为并行开发分支。

2. **Import 默认使用 copy 还是 move？**
   - 建议：默认 copy，可选 move。避免 DB 失败后文件丢失。

3. **操作日志是否要在 Phase 7A 最先实施？**
   - 建议：是。没有日志的 "软件管理文件" 是不可靠的。

4. **是否需要 content hash？**
   - 建议：暂不需要。`checksum_hint` 可以后续按需启用，但导入时计算 hash 会显著拖慢大文件导入。

5. **Inbox 是否应作为 Library 的新标签，还是独立顶层导航？**
   - 建议：Library 的新标签。保持导航简洁，与 Pending / Objects / Plans 并列。

6. **现有 organize candidates 是否应该与 inbox items 合并为一个表？**
   - 建议：先不合并。candidates 是 organize 的内部概念，inbox items 是面向用户的概念。可以通过 candidate.source_file_id 引用 inbox_item_id 来关联，但不共享一个表。

7. **AI 分类建议是否在 Phase 7 中引入？**
   - 建议：先不引入。Phase 7 专注于基础导入和文件管理链路。AI 作为 Phase 8+ 的可选增强。

8. **是否需要 migration baseline？**
   - 建议：是。在 Phase 7 首次提交前，做一次数据库快照 + `Alembic` 迁移基线。

---

## 附录：涉及的关键源文件

| 文件 | 角色 |
|------|------|
| `apps/backend/app/core/classification.py` | 文件分类规则（file_kind + placement） |
| `apps/backend/app/workers/scanning/scanner.py` | 文件扫描 worker |
| `apps/backend/app/repositories/file/repository.py` | 文件 CRUD + upsert_discovered_files |
| `apps/backend/app/services/library/organize.py` | Organize 全套（scan/generate/execute/reconcile） |
| `apps/backend/app/db/models/file.py` | File 模型（path, is_deleted, checksum_hint） |
| `apps/backend/app/db/models/organize.py` | Organize 模型（candidate, plan, action, suggestion） |
| `apps/backend/app/db/models/library_object.py` | LibraryObject + member + asset cache |
| `apps/backend/app/db/models/file_user_meta.py` | 用户元数据（manual_placement, color_tag, rating, is_favorite） |
| `apps/backend/app/api/routes/search.py` | 搜索路由 |
| `apps/backend/app/api/routes/files.py` | 文件 API 路由 |
| `apps/frontend/src/features/library/` | 前端 Library 模块 |
