# Phase M3 — Feature Completion & Technical Debt Resolution Plan

> 日期：2026-05-23  
> 状态：已确认，执行中  
> 前置：M2-A 已完成（commit `e9bc012`）
> 确认：全部 6 点已由用户答复（2026-05-23）

---

## 1. 概述

M2-A 完成了信息架构重构。当前已无 Beta blocker。本轮目标：补齐开发中遗留的功能缺口，清理技术债。

基于 7 份文档交叉审计，共梳理出 **88 条待办项**。排除已完成的 M2-A 项、明确不做（design boundaries）的项、以及已暂停的过度硬化项后，实际可执行的待办项约 **35 条**。

---

## 2. 优先级分类

| 优先级 | 定义 | 数量 |
|--------|------|------|
| **P0** | 数据正确性 bug，必须修 | 2 |
| **P1** | 用户体验显著受损，应尽快修 | 8 |
| **P2** | 技术债，不阻塞使用但持续恶化 | 14 |
| **P3** | 锦上添花，beta 后慢慢做 | 11 |
| **不做** | 设计决策明确排除，或收益 < 代价 | — |

---

## 3. P0 — 数据正确性（立即执行）

### P0-01：修复 managed compose type_prefix 映射错误

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-05
- **问题**：`_finalize_managed_compose` 中 `OBJECT_PREFIX` 映射反转，大多数对象类型的 `type_prefix` 被错误写入为 `"OBJ"`
- **影响**：对象元数据不一致，对象根目录名与 type_prefix 不匹配
- **涉及**：`organize.py` `_finalize_managed_compose` 方法
- **改动量**：后端 ~10 行
- **测试**：验证各 object_type 的 type_prefix 正确映射
- **风险**：低（纯修复，不改 API）

### P0-02：修复 removed-member compose 资格检查

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-01
- **问题**：已移除成员（`member_status=removed`）的文件在 Browse v2 中显示为松散文件，但被 compose guard 拒绝，因为 guard 查询忽略了 `member_status`
- **影响**：已移除的文件无法被重新组合，违背了"removed = loose"的设计意图
- **涉及**：`organize.py` compose guard 查询
- **改动量**：后端 ~5 行
- **测试**：removed member file → managed compose → 成功
- **风险**：低（查询条件修改，已有 18d7831 的 active-only 查询模式可参考）

---

## 4. P1 — 用户体验显著改善（Beta 后尽快）

### P1-01：前端关键路径集成测试

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-10
- **问题**：Phase 8 UI 无任何自动化测试，回归全靠手工
- **方案**：Vitest + React Testing Library，优先覆盖 Browse v2 卡片渲染、对象详情、Compose 提交流程、Amendment 计划创建
- **改动量**：新增 ~20 测试文件
- **风险**：低（纯测试，不改功能）
- **预计工时**：4-6h 初始搭建 + 首批测试

### P1-02：GET endpoint 不应变更状态

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-04
- **问题**：`get_plan_detail` 在 GET 请求中调用 `_refresh_plan_conflicts` + `session.commit()`，违反 HTTP GET 语义
- **方案**：将冲突刷新移到 POST/PATCH 端点或定时任务
- **改动量**：后端 ~20 行
- **风险**：中（涉及 plan 状态流转，需确保不破坏 mark_ready 逻辑）

### P1-03：计划创建后操作反馈横幅

- **来源**：FILE_MANAGEMENT_UNIFICATION_ASSESSMENT 低风险修复 #45
- **问题**：用户在 Compose/Amendment 中创建计划后，只得到一闪而过的 toast。没有持久提示"文件尚未移动，去 Plans 执行"
- **方案**：创建计划成功后，在页面内显示持久横幅 + 一键跳转 Plans 按钮
- **改动量**：前端 ~30 行
- **风险**：低（纯 UI 增量）

### P1-04：原始 role 值替换为用户友好标签

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-09
- **问题**：对象详情中成员角色显示原始技术值（`primary`、`extra`、`unknown_child`），而非用户可理解的标签
- **方案**：添加 member role → i18n label 映射
- **改动量**：前端 i18n + 组件 ~15 行
- **风险**：低

### P1-05：Add-member modal 候选查询范围修正

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-08
- **问题**：Add-member modal 的松散文件查询默认 domain=media，导致 docs/apps/assets 域的松散文件不可见
- **方案**：移除 domain 默认限制，或改为动态读取当前对象的 domain
- **改动量**：前端 ~5 行
- **风险**：低

### P1-06：管理复合作流（Inbox / Roots / Plans）空状态引导

- **来源**：FILE_MANAGEMENT_UNIFICATION_ASSESSMENT 低风险修复 #46
- **问题**：Plans 为空时无引导文字；Inbox 为空时无"先添加受管库"提示
- **方案**：添加各 tab 的空状态引导组件
- **改动量**：前端 i18n + 组件 ~40 行
- **风险**：低

### P1-07：import 后跨链接引导

- **来源**：FILE_MANAGEMENT_UNIFICATION_ASSESSMENT 低风险修复 #49
- **问题**：用户添加完 Managed Root 后不知道下一步该导入文件
- **方案**：在 Roots 页面添加 Managed Root 后显示"下一步：导入文件到 Inbox"
- **改动量**：前端 ~15 行
- **风险**：低

### P1-08：移除过时 Phase 文案

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-09（stale notices）
- **问题**：locale 中仍有 "Phase 2 只读"、"add/remove 后续阶段实现"等过时文案
- **方案**：审查并更新所有 locale 文件中引用 Phase 1/2/alpha 的过时文案
- **改动量**：i18n 文件 ~20 处
- **风险**：低

---

## 5. P2 — 技术债清理（持续进行）

### P2-01：datetime.utcnow() 废弃警告批量替换

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P3-02
- **问题**：~900 处 `datetime.utcnow()` 调用，Python 3.12+ 已标记废弃
- **方案**：创建项目内 `utcnow()` helper 函数，全局替换
- **改动量**：后端全局（机械替换）
- **风险**：低（但需要全量测试通过）

### P2-02：BrowseV2Feature 组件拆分

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-07
- **问题**：组件仍混合卡片列表、详情面板、Compose 模态框、Amendment 模态框等多种职责
- **方案**：提取 `useBrowseCards`、`useBrowseSelection`、`AmendObjectModal`（已有部分）
- **改动量**：前端 ~300 行重构
- **风险**：中（需前端测试先到位）

### P2-03：代码分割（React.lazy）

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P3-01
- **问题**：单 chunk 848 KB，首屏加载可优化
- **方案**：路由级 lazy loading：`BrowseV2Page`、`LibraryPage`、`SearchPage` 等
- **改动量**：前端 Router ~20 行
- **风险**：低

### P2-04：数据库自动备份

- **来源**：M2 评审 P2-04
- **问题**：SQLite DB 无自动备份，用户数据损坏后无法恢复
- **方案**：应用启动时复制 DB 到 `data/backups/`，保留最近 3 个
- **改动量**：后端 + Electron ~30 行
- **风险**：低

### P2-05：日志轮转

- **来源**：M2 评审 P2-05
- **问题**：`backend.log` 无限增长
- **方案**：Python `RotatingFileHandler`，5MB × 5 文件
- **改动量**：后端 ~10 行
- **风险**：低

### P2-06：Route 层逻辑提取到 Service

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-03
- **问题**：`importing.py` route 中有内联 workflow/SQL 逻辑；`library.py` 有内联聚合
- **方案**：提取到对应的 Service 方法
- **改动量**：后端 ~50 行重构
- **风险**：中（需保持行为完全一致）

### P2-07：CSS 文件按组件拆分

- **来源**：M2 评审 P2-03
- **问题**：`components.css` 600+ 行，`shell.css` 1100+ 行
- **方案**：拆分为 `button.css`、`badge.css`、`card.css`、`sidebar.css`、`breadcrumb.css` 等，在 `global.css` 中按依赖顺序导入
- **改动量**：纯文件拆分，无逻辑变更
- **风险**：低（需验证导入顺序不破坏层叠）

### P2-08：数据库迁移版本管理

- **来源**：KNOWN_LIMITATIONS.md
- **问题**：当前使用 `_ensure_*()` 辅助函数，无版本号追踪
- **方案**：添加 `schema_version` 表 + 版本常量；不引入 Alembic
- **改动量**：后端 `engine.py` ~20 行
- **风险**：低

### P2-09：恢复功能增强（持久化发现 + 对象成员感知）

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-06 + KNOWN_LIMITATIONS
- **问题**：Recovery 发现不持久化；不检查活跃成员路径/对象根不匹配；不检查 removed 成员松散状态不匹配
- **方案**：添加 `recovery_findings` 表持久化发现结果；添加 member-object-root 一致性检查
- **改动量**：后端 ~80 行 + 新 migration
- **风险**：中（新表 + migration）

### P2-10：plan_kind 枚举化

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-02
- **问题**：`plan_kind` 是自由字符串，依赖 `payload_json` 携带工作流语义
- **方案**：不改变 DB schema，但在 Service 层添加常量枚举 + 校验
- **改动量**：后端 ~15 行
- **风险**：低

### P2-11：操作历史面板

- **来源**：M2 评审 Post-05
- **问题**：用户无法回溯操作历史（导入、计划执行、修正）
- **方案**：Home 页面添加"最近活动"模块，读取 `operation_journal` 表
- **改动量**：后端新 API + 前端面板 ~150 行
- **风险**：中

### P2-12：版本号统一管理

- **来源**：M2 评审
- **问题**：多个 `package.json` / `pyproject.toml` 中版本号不一致
- **方案**：统一为 `0.2.0`，构建脚本注入 git commit hash
- **改动量**：配置文件 ~5 处
- **风险**：低

### P2-13：CI/CD 流水线

- **来源**：M2 评审
- **问题**：无自动测试/构建流水线
- **方案**：GitHub Actions：lint → backend test → frontend build → electron build
- **改动量**：新增 `.github/workflows/ci.yml`
- **风险**：低

### P2-14：前端构建 chunk 警告

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P3-01
- **问题**：Single chunk > 500 KB
- **方案**：路由级 lazy loading（与 P2-03 重叠）
- **改动量**：前端 Router ~20 行
- **风险**：低

---

## 6. P3 — Post-Beta 增强（可延后）

### P3-01：v2 Premium 视觉对齐（不含字体）

- **来源**：M2 评审 Post-01
- **方案**：收紧圆角 ~30%，调整间距和表面层次
- **改动量**：CSS tokens ~50 行

### P3-02：对象详情一键预检+执行

- **来源**：M2 评审 Post-04 + PHASE8_FINAL_ACCEPTANCE_CHECKLIST
- **方案**：需独立设计：确认弹窗 + 动作预览 + 安全边界。前端串联 create plan → preflight → execute 三步
- **改动量**：前端 ~200 行
- **注意**：需先通过安全设计评审

### P3-03：混合 add+remove amendment

- **来源**：KNOWN_LIMITATIONS.md + PHASE8_FINAL_ACCEPTANCE_CHECKLIST
- **方案**：后端支持单一计划中同时添加和移除成员
- **改动量**：后端 ~100 行

### P3-04：duplicate / hash 检测

- **来源**：KNOWN_LIMITATIONS.md
- **问题**：`files.checksum_hint` 列存在但未填充
- **方案**：导入时计算 SHA-256，在导入流程中警告重复文件
- **改动量**：后端 ~60 行

### P3-05：Removed member 历史 UI

- **来源**：KNOWN_LIMITATIONS.md
- **方案**：对象详情中添加"已移除成员"折叠区域
- **改动量**：前端 ~50 行

### P3-06：导入后跨 batch 组合

- **来源**：KNOWN_LIMITATIONS.md
- **方案**：允许从不同 import batch 中选择文件进行 compose
- **改动量**：后端 ~30 行

### P3-07：Recovery 自动修复（受限）

- **来源**：KNOWN_LIMITATIONS.md
- **方案**：仅限安全场景（重试失败导入、修复路径不一致），始终需用户确认
- **改动量**：后端 ~100 行

### P3-08：前端 e2e 测试（Playwright）

- **方案**：关键路径：Browse → 对象详情 → 添加成员 → 创建计划
- **改动量**：新测试 ~10 用例

### P3-09：Browse 存储状态图例

- **来源**：FILE_MANAGEMENT_UNIFICATION_ASSESSMENT 低风险修复 #44
- **方案**：在 Browse 页面添加 external / inbox / managed 状态说明 tooltip
- **改动量**：前端 ~15 行

### P3-10：跨链接完善（Roots→Inbox, Inbox→Plans）

- **来源**：FILE_MANAGEMENT_UNIFICATION_ASSESSMENT 低风险修复
- **方案**：在 Roots 页面添加"下一步：导入"、在 Inbox 添加"下一步：创建计划"
- **改动量**：前端 ~20 行

### P3-11：docs 更新同步

- **来源**：PHASE8_ARCHITECTURE_AUDIT_REPORT P2-11
- **方案**：更新 ARCHITECTURE.md（Phase 8 计划/成员生命周期）、KNOWN_LIMITATIONS（修正过时 statement）、README
- **改动量**：docs ~100 行

---

## 7. 明确不做

以下项目已被明确排除，不纳入任何阶段：

- ❌ delete / trash / recycle bin（设计决策，非遗漏）
- ❌ source cleanup（设计决策，不删除原始文件）
- ❌ AI 自动分类（产品边界）
- ❌ 移动导入（保持 copy-only 安全模型）
- ❌ Alembic 迁移（`_ensure_*()` 模式满足当前需求）
- ❌ organize.py 深度拆分 H4-Step4~8（收益递减，暂停）
- ❌ Managed Root 自动扫描（设计决策）
- ❌ Source 和 Managed Root 数据模型合并（架构决策）
- ❌ DM Sans / IBM Plex Sans 字体替换（性能影响待评估）

---

## 8. 推荐执行顺序

### 第一轮：P0 + 低风险 P1（1-2 周）

```
P0-01 type_prefix fix ──┐
P0-02 compose guard fix ─┤ 后端 3 文件 ~20 行
P1-02 GET fix          ─┘
P1-04 role labels      ──┐
P1-05 add-member query ──┤
P1-08 stale copy       ──┤ 前端 i18n/组件 ~50 行
P1-06 empty states     ──┤
P1-07 cross-link       ──┘
P1-03 plan banner      ─── 前端组件 ~30 行
```

### 第二轮：测试基础 + 中等重构（2-4 周）

```
P1-01 frontend tests   ─── Vitest + RTL 基础设施 + 首批 15 测试
P2-01 utcnow replace   ─── 后端全局机械替换
P2-02 BrowseV2 split   ─── 依赖 P1-01（测试保护）
P2-03 code splitting   ─── React.lazy
P2-06 route→service    ─── 提取内联逻辑
P2-07 CSS split        ─── 纯文件拆分
P2-08 migration versioning ── schema_version 表
```

### 第三轮：功能增强 + 运维（4-6 周）

```
P2-04 DB auto-backup   ──┐
P2-05 log rotation     ──┤ 运维改进
P2-12 version numbers  ──┤
P2-13 CI/CD            ──┘
P2-09 recovery enhance ─── 新表 + migration
P2-10 plan_kind enum   ─── 常量化
P2-11 operation history ── 新 API + 面板
```

### 第四轮：P3 增强（6+ 周，按需）

```
P3-01 visual polish
P3-02 direct execute（需安全设计先）
P3-03 mixed amendment
P3-04 hash detection
P3-05 removed member history
P3-08 e2e tests
P3-11 docs sync
```

---

## 9. 每轮验收标准

### 第一轮验收
- [ ] P0-01：所有 object_type 的 type_prefix 正确映射
- [ ] P0-02：removed member file → compose → 成功
- [ ] P1-02：GET plan detail 不触发 commit
- [ ] P1-03：创建计划后显示横幅 + 跳转按钮
- [ ] P1-04~08：无 raw role 值、无过时文案、空状态引导正确
- [ ] `npm run build` 通过
- [ ] 全部后端测试通过

### 第二轮验收
- [ ] 前端关键路径集成测试 ≥ 15 个，全部通过
- [ ] `datetime.utcnow()` 调用数 = 0
- [ ] BrowseV2Feature 拆分为 ≤ 300 行主组件
- [ ] 路由级 lazy loading 正常工作
- [ ] CSS 文件拆分无视觉回归

### 第三轮验收
- [ ] 数据库启动备份正常
- [ ] 日志自动轮转
- [ ] 操作历史面板显示最近 10 条操作
- [ ] schema_version 表记录当前版本
- [ ] CI 流水线 green

---

## 10. 风险矩阵

| 风险 | 关联项 | 缓解 |
|------|--------|------|
| P0 修复引入回归 | P0-01, P0-02 | 每项配 2+ 测试；全量后端测试 |
| 前端测试基础设施搭建超时 | P1-01 | 先最小可用（Vitest + 5 测试），再增量 |
| BrowseV2 拆分破坏 M2 URL 参数流 | P2-02 | M2 URL 参数化已完成，拆分时不改状态管理 |
| Recovery 增强需要新 migration | P2-09 | `_ensure_*()` 模式，幂等迁移 |
| CI/CD 配置需要 GitHub Secrets | P2-13 | 不依赖 secrets（纯公开仓库） |
| 重构量过大导致合并冲突 | P2-02, P2-06, P2-07 | 分 PR 提交，每 PR 独立可合并 |

---

## 11. 问题确认（2026-05-23）

| # | 问题 | 决策 |
|---|------|------|
| 1 | P0-01 type_prefix fix | ✅ 先只读确认，若真实存在则最小修复+回归测试；若已修复则只补验证报告 |
| 2 | 前端测试框架 | ✅ Vitest + React Testing Library，Playwright 后置 P3 |
| 3 | GET mutation fix | ✅ 刷新移到 `POST /plans/{id}/refresh-conflicts`；mark_ready/preflight 内部仍可刷新 |
| 4 | datetime.utcnow() | ✅ 创建 `app.core.time.utcnow()` helper；P2 单独批次，不与 P0/P1 混 |
| 5 | 操作历史面板 | ✅ 第一版最近 10 条 operation_journal 列表；不聚合、不撤销、不恢复 |
| 6 | P3-02 direct execute | ✅ 不纳入 M3；保留 P3 future design；当前保持三步语义 |
