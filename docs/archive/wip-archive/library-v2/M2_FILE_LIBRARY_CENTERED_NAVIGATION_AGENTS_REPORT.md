# M2 File Library Centered Navigation — Agents Team Report

> 评审日期：2026-05-22  
> 评审类型：规划/架构评审（不实现代码）  
> 基于：Phase 8 Beta 完成 + M1 文案完成 + FILE_MANAGEMENT_UNIFICATION_ASSESSMENT.md

---

## 1. Executive Summary

### 是否建议执行？
**是。强烈建议在 Beta 后执行 M2 导航重构。**

### 推荐方案一句话
将 Browse v2 的领域分类导航提升为全局左侧导航的核心部分，以"文件库"（File Library）为管理中心，消除当前"Source 线"和"Library 线"的信息架构割裂，同时保持后端数据模型完全不动。

### Beta 前做什么？
**Beta 前不做 M2。** 当前 Beta 包（`Workbench_Phase8_Beta_Portable_20260522_1333.zip`）的导航和信息架构保持现状。M2 仅在 Beta 反馈收集后进行。

### Beta 后做什么？
按 M2-A → M2-B → M2-C → M2-D → M2-E 五阶段执行（详见第 11 节）。

---

## 2. Current Navigation Assessment

### 2.1 当前问题

1. **Source 线和 Library 线割裂**：用户在 Settings 管理 Source（扫描外部目录），在 Library 管理 Managed Root（受管库），在两个不同的顶层页面操作同属"文件管理"的功能。

2. **左侧导航和 Browse 内部导航重复**：侧边栏有 Media、Documents、Games、Software 四个一级入口，Browse v2 页面内部又有完全相同的领域分类（media/documents/apps/assets + 子分类）。用户不知道应该用侧边栏的 Media 还是 Browse 里的 Media。

3. **Browse v2 内部分类导航被埋藏**：Browse v2 的分类树（domain → category group → category）设计良好，但它只存在于 Browse v2 页面内部，用户需要先点击侧边栏的"Browse"才能看到。

4. **Library 页面信息过载**：7 个标签页（Overview、Roots、Path、Pending、Objects、Plans、Inbox）功能齐全但入口拥挤，新用户难以理解从哪里开始。

5. **旧版子集页面（Books/Media/Games/Software）地位模糊**：M1 文案已将它们标注为"预筛选视图"，但它们仍占据一级导航位置。

### 2.2 当前左侧一级导航

来自 `AppSidebar.tsx`：

```
操作（Operate）
  Home              /home
  Search            /search
  Library           /library

浏览（Browse）
  Browse            /browse-v2
  Media             /library/media
  Documents         /books
  Software          /software
  Games             /library/games

再找回（Refind）
  Recent            /recent
  Tags              /tags
  Collections       /collections

系统（System）
  Tools             /tools
  Settings          /settings
```

### 2.3 Browse v2 内部分类导航

来自 `BrowseV2Feature.tsx` 的 `CATEGORY_TREE`：

```
媒体（Media）
  视频
    电影 / 长视频
    剧集 / 动漫
    课程 / 讲座资料
    视频合集
    视频素材 / 片段
  图片
    图片 / 相册
    漫画
  音频
    音频 / 录音

文档（Documents）
  全部
    文档 / 资料包

应用（Apps）
  全部
    软件 / 工具
    游戏

素材（Assets）
  全部
    素材包
```

### 2.4 File Library / Library 页面当前 Tabs

来自 `LibraryFeature.tsx`：

| Tab | 中文 | 功能 |
|-----|------|------|
| overview | 总览 | 对象统计 + 存储摘要 |
| roots | 受管库 | 管理受管库根目录 |
| path | 路径浏览 | 按精确目录浏览文件 |
| pending | 待整理 | 候选对象扫描和审查 |
| objects | 对象 | 正式对象列表 |
| plans | 整理计划 | 计划管理（mark ready / preflight / execute） |
| inbox | 导入 | 导入批次和文件导入 |

### 2.5 Source Management 当前位置

- **Settings 页面**（`/settings`）：以 `SourceManagementFeature` 组件嵌入
- **Onboarding 页面**（`/onboarding`）：以 `SourceManagementFeature` 组件独立页面

### 2.6 必须保留兼容的路由

全部现有路由（15 个）必须保留：

`/`, `/home`, `/onboarding`, `/search`, `/library`, `/files`, `/books`, `/software`, `/library/games`, `/browse-v2`, `/library/media`, `/tools`, `/recent`, `/tags`, `/collections`, `/settings`

### 2.7 可仅通过 nav / i18n / page composition 调整的

- 侧边栏分组标签（i18n `shell.sidebar.groups.*`）
- 侧边栏项目标签（i18n `navigation.items.*`）
- 侧边栏项目排序和分组（`navGroups` 数组，纯静态数据）
- 页面描述文案（i18n `pages.*`）
- 组件复用（`SourceManagementFeature` 可在多处渲染）

### 2.8 会触及业务逻辑需要避免的

- 修改路由路径
- 修改 `CATEGORY_TREE` 和 `DOMAIN_TYPE_MAP`（影响 API 查询参数）
- 修改 library tabs 的 `value` 字段（影响 `?tab=` URL 参数）
- 修改 `StartupRedirect` 逻辑
- 修改后端 API 语义

---

## 3. Product Principle

### 3.1 核心原则

1. **文件库为中心**：所有文件操作（扫描、导入、整理、浏览）汇聚到一个以"文件库"命名的信息架构节点下
2. **信息架构合并，数据模型不合并**：Source 和 Managed Root 在 UI 中并列展示，但在后端保持完全独立的数据模型
3. **分类导航提升到全局**：Browse v2 内部分类树成为左侧导航的核心"浏览分类"部分
4. **管理操作汇聚**：Source 管理、Managed Root 管理、导入、计划执行汇聚到"管理"区域
5. **旧入口兼容**：所有旧路由保留，但可通过重定向或导航权重降低过渡

### 3.2 最终用户心智模型

```
文件库 = 一切文件操作的中心
├── 浏览分类 = 按内容类型查看已组织的文件和对象
├── 管理 = 添加源、添加受管库、导入、执行计划
└── 再找回 = 搜索、标签、集合、最近

系统 = 应用设置和工具
```

---

## 4. Proposed Sidebar Model

### 4.1 推荐左侧导航结构

```
资产工作台
├── 首页                    /home
├── 文件库                  (section header, not a link)
│   ├── 总览                /library?tab=overview
│   ├── 浏览全部            /browse-v2?category=all
│   │
│   ├── 浏览分类            (subsection header)
│   │   ├── 媒体            /browse-v2?domain=media
│   │   │   ├── 全部        /browse-v2?domain=media&category=all
│   │   │   ├── 电影/长视频 /browse-v2?domain=media&category=movie
│   │   │   ├── 剧集/动漫   /browse-v2?domain=media&category=series_anime
│   │   │   ├── 课程/讲座   /browse-v2?domain=media&category=course
│   │   │   ├── 视频合集    /browse-v2?domain=media&category=video_collection
│   │   │   ├── 视频素材    /browse-v2?domain=media&category=video_clip
│   │   │   ├── 图片/相册   /browse-v2?domain=media&category=image_album
│   │   │   ├── 漫画        /browse-v2?domain=media&category=comic
│   │   │   └── 音频/录音   /browse-v2?domain=media&category=audio
│   │   ├── 文档            /browse-v2?domain=documents
│   │   ├── 应用            /browse-v2?domain=apps
│   │   └── 素材            /browse-v2?domain=assets
│   │
│   ├── 管理                (subsection header)
│   │   ├── 扫描文件夹      /library?tab=sources    (new — Source Management)
│   │   ├── 受管库文件夹    /library?tab=roots
│   │   ├── 导入暂存        /library?tab=inbox
│   │   ├── 待执行计划      /library?tab=plans
│   │   └── 问题诊断        /library?tab=recovery   (new)
│   │
│   └── 再找回              (subsection header)
│       ├── 搜索            /search
│       ├── 最近            /recent
│       ├── 标签            /tags
│       └── 集合            /collections
│
└── 系统
    ├── 工具                /tools
    └── 设置                /settings
```

### 4.2 默认展开/折叠

| 区域 | 默认状态 | 理由 |
|------|---------|------|
| 浏览分类 > 媒体子分类 | **折叠** | 分类项多（9 项），默认折叠避免导航过长 |
| 浏览分类 > 文档/应用/素材 | **展开**（单层） | 子项少（1-2 项），展开不占空间 |
| 管理 | **展开** | 常用操作入口，需要始终可见 |
| 再找回 | **展开** | 项目少（4 项） |

### 4.3 Badge 建议

| 导航项 | Badge 内容 | 触发条件 |
|--------|-----------|---------|
| 待执行计划 | 数字（ready + draft 计划数） | > 0 时显示 |
| 导入暂存 | 数字（pending inbox items） | > 0 时显示 |
| 问题诊断 | 黄点 | 有未查看的诊断发现时显示 |

### 4.4 Tooltip 建议

- **扫描文件夹**："添加要索引的文件夹。Workbench 只读索引，不会修改原文件。"
- **受管库文件夹**："添加文件整理的目标文件夹。受管库文件夹不会被自动扫描。"
- **导入暂存**："从受管库文件夹导入文件到暂存区，等待分类和整理。"

---

## 5. File Library Overview Design

### 5.1 "从这里开始" 卡片

Library Overview（`/library?tab=overview`）应重构为"文件库总览"，包含以下卡片：

```
┌─────────────────────────────────────────────────────┐
│  文件库总览                                          │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 扫描已有文件夹 │  │ 添加受管库    │  │ 浏览文件和  │ │
│  │              │  │ 文件夹       │  │ 对象       │ │
│  │ 索引现有文件  │  │ 设定整理目标  │  │ 按分类查看  │ │
│  │ 不修改原文件  │  │ 目录         │  │ 已组织内容  │ │
│  │              │  │              │  │            │ │
│  │ [前往扫描]   │  │ [添加受管库]  │  │ [开始浏览]  │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │ 导入文件      │  │ 执行待处理    │                 │
│  │              │  │ 计划         │                 │
│  │ 从受管库导入  │  │ 预检并执行   │                 │
│  │ 文件到暂存区  │  │ 整理计划     │                 │
│  │              │  │              │                 │
│  │ [打开导入]   │  │ [查看计划]    │                 │
│  └──────────────┘  └──────────────┘                 │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │ 快速状态                                      │   │
│  │ 已索引文件: 1,234  受管文件: 567              │   │
│  │ 待处理计划: 3     活跃对象: 42               │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 5.2 预筛选视图入口

在 Overview 底部提供现有子集页面的快捷入口（作为卡片行，而非一级导航）：

```
快速浏览：
[📷 媒体] [📄 文档] [🎮 游戏] [💻 软件]
```

### 5.3 需要新增的内容

| 内容 | 类型 | 是否阻塞 M2 | 备注 |
|------|------|-----------|------|
| "从这里开始" 引导卡片 | 静态 i18n + 链接 | 否 | M2-A 纯前端 |
| 快速状态摘要 | 需要新增 API | 否 | 可先显示已有 `/library/overview` 数据 |
| 预筛选视图入口卡片行 | 纯链接 | 否 | 链接到现有旧路由 |

---

## 6. Browse Page Redesign Direction

### 6.1 当前状态

Browse v2 页面（`/browse-v2`）内部有一个左侧分类导航面板（taxonomy panel），包含：
- 4 个领域按钮（media / documents / apps / assets）
- 动态分类树（根据所选领域展开）
- 存储状态筛选器
- 卡片类型筛选器

### 6.2 M2 后的变化

如果全局侧边栏已经包含完整的分类导航，Browse v2 页面内部应：

| 元素 | 处理方式 |
|------|---------|
| 领域按钮 | **移除**（全局侧边栏已提供） |
| 分类树 | **移除**（全局侧边栏已提供） |
| 存储状态筛选器 | **保留**，改为顶部水平 filter bar |
| 卡片类型筛选器 | **保留**，改为顶部水平 filter bar |
| 内容区（卡片网格 + 详情面板） | **保留**，作为主要内容区 |

### 6.3 Browse 页面新布局

```
┌──────────────────────────────────────────────────┐
│ 面包屑：文件库 > 媒体 > 电影/长视频               │
│                                                   │
│ [存储: 全部 ▾] [类型: 全部 ▾] [排序: 最近 ▾]     │
│                                                   │
│ ┌──────────────────────┐ ┌──────────────────────┐ │
│ │ 对象卡片              │ │ 右侧详情面板          │ │
│ │ (卡片网格)            │ │ (选中对象/文件时显示)  │ │
│ │                      │ │                      │ │
│ └──────────────────────┘ └──────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### 6.4 如果 M2-C 前不移除内部分类导航

在 M2-A 和 M2-B 阶段，全局侧边栏已添加分类导航但 Browse 页面内部仍保留分类面板时：
- 侧边栏分类导航和页面内部分类面板会**双重显示**
- 这是**可接受的过渡状态**，因为两个分类面板指向相同的 URL 参数
- 在 M2-C 阶段移除页面内部分类面板后，双重导航消失

---

## 7. Source / Managed Root Relationship

### 7.1 用户侧怎么解释

| 概念 | 用户友好名称 | 一句话解释 |
|------|------------|-----------|
| Source | 扫描文件夹 | "告诉 Workbench 去哪里找文件。只读索引，不修改原文件。" |
| Managed Root | 受管库文件夹 | "Workbench 整理文件的目标位置。文件会被复制到这里进行组织。" |
| Source Scan | 扫描 | "让 Workbench 读取文件夹中的文件信息。" |
| Managed Import | 导入 | "将文件复制到受管库的暂存区，等待分类和整理。" |

### 7.2 后端模型为什么不合并

1. **Source** 代表"输入"——文件从哪里来。Source 有扫描策略、文件发现机制。
2. **Managed Root** 代表"输出"——文件到哪里去。Managed Root 是整理目标，不自动扫描。
3. **storage_state** 标记文件在生命周期中的位置：`external`（源）→ `inbox`（暂存）→ `managed`（已整理）。
4. 合并这两个模型会模糊文件生命周期，让用户误以为"添加受管库 = 自动扫描"。

### 7.3 UI 中如何并列展示

在"文件库 > 管理"区域，两者作为同级入口：

```
管理
├── 扫描文件夹     → /library?tab=sources    (Source Management)
├── 受管库文件夹    → /library?tab=roots      (Managed Roots)
├── 导入暂存       → /library?tab=inbox      (Inbox)
├── 待执行计划     → /library?tab=plans      (Plans)
└── 问题诊断       → /library?tab=recovery   (Recovery)
```

两者并列，但视觉上明确区分为"输入"和"输出"。

---

## 8. Old Pages / Route Compatibility

### 8.1 旧子集页面处理策略

| 页面 | 路由 | M2-A 处理 | M2-D 处理 |
|------|------|----------|----------|
| Books/Documents | `/books` | 保留路由，从侧边栏移除，在 Overview 添加快捷卡片 | 重定向到 `/browse-v2?domain=documents` |
| Media | `/library/media` | 保留路由，从侧边栏移除 | 重定向到 `/browse-v2?domain=media` |
| Games | `/library/games` | 保留路由，从侧边栏移除 | 重定向到 `/browse-v2?domain=apps&category=game` |
| Software | `/software` | 保留路由，从侧边栏移除 | 重定向到 `/browse-v2?domain=apps&category=software` |
| Recent | `/recent` | 保留路由，移入"再找回"子区 | 保留 |
| Files | `/files` | 保留（已重定向到 `/library?tab=path`） | 保留 |

### 8.2 旧路由处理原则

1. **不删除任何路由**
2. **M2-A/B 阶段**：旧路由保留完整功能，仅从侧边栏移除导航项
3. **M2-D 阶段**：旧路由可改为重定向到 Browse/Overview 预设参数
4. **直接 URL 访问**：始终有效

---

## 9. Agents Review Notes

### 9.1 Product Lead

**Current concern：** 用户心智模型碎片化。Source 在 Settings，Managed Root 在 Library，Browse 独立一页——用户无法建立"文件库"的统一概念。

**Recommended approach：** 以"文件库"为一级概念，将扫描、导入、整理、浏览汇聚。不做功能删减，只做信息架构重组。M2-A 先在 Library Overview 添加"从这里开始"引导卡片，然后逐步将 Source 移入 Library。

**Risks：** 如果只改导航标签不改底层页面组织，用户仍会在点击后跳转到"感觉是另一个应用"的页面。

**What not to do：** 不要新增顶层页面；不要在 Library 以外创建第二个"文件管理中心"。

**Acceptance criteria：** 新用户能在 30 秒内理解"扫描已有文件"和"导入到受管库"是两个不同操作，知道各自去哪里执行。

### 9.2 UX / Information Architecture Lead

**Current concern：** 侧边栏 14 个项目 + Browse 内部 4 领域 × N 子分类 = 双层导航冲突。分类导航设计优秀但被埋没。

**Recommended approach：** 将 Browse v2 分类树提升为全局侧边栏的"浏览分类"区域。侧边栏分为三大区：（1）文件库（浏览分类 + 管理），（2）再找回，（3）系统。确保分类导航在侧边栏折叠时显示为图标+tooltip。

**Risks：** 侧边栏可能变得很长（媒体有 9 个子分类）。需要默认折叠子分类、手风琴展开。

**What not to do：** 不要同时保留侧边栏分类导航和 Browse 页面内部分类导航（M2-C 前可接受过渡，M2-C 后必须移除内部面板）。

**Acceptance criteria：** 用户可以从侧边栏直接导航到"媒体 > 电影/长视频"，无需先打开 Browse 页面。

### 9.3 Frontend Architect

**Current concern：** `AppSidebar.tsx` 当前是静态的 `navGroups` 数组，不支持嵌套子项和手风琴展开。需要扩展侧边栏组件以支持可展开的分类子导航。

**Recommended approach：** M2-A 阶段保持 `navGroups` 结构不变，仅调整分组和标签。M2-B 阶段为侧边栏添加可折叠子导航组件（`CollapsibleNavGroup`），支持嵌套的 `NavLink` 子项。M2-C 阶段移除 `BrowseV2Feature` 内部的 taxonomy panel，仅保留 filter bar。

**Risks：** 侧边栏组件改动影响所有页面；分类导航子项通过 URL 参数（`?domain=media&category=movie`）传递，需要确保 `NavLink` 的 `to` 属性正确构建。

**What not to do：** 不要重写整个 AppSidebar。渐进增强，不要替换。

**Acceptance criteria：** `npm run build` 通过；所有现有路由仍可访问；侧边栏折叠/展开正常工作。

### 9.4 Backend Architect

**Current concern：** M2 导航重构可能让前端开发者误以为需要"统一 Source 和 Managed Root 的 API"。必须明确：导航合并 ≠ 数据模型合并。

**Recommended approach：** 后端零改动。所有 M2 阶段仅涉及前端导航、i18n、路由组织和组件复用。`GET /library/overview` 已有足够数据支持 Overview 状态卡片。如果需要"待处理事项计数"的聚合 API，M2 后期可新增一个轻量只读端点。

**Risks：** 如果前端开始在 Library 页面内渲染 SourceManagementFeature 并尝试调用 `/sources` API，后端已经支持——`/sources` 端点无页面归属限制。

**What not to do：** 不创建"统一文件管理"API 端点；不合并 `sources` 和 `library_roots` 表；不给 Managed Root 添加 `scan` 端点。

**Acceptance criteria：** 所有现有 API 端点不变；没有新的数据库迁移。

### 9.5 QA / Test Lead

**Current concern：** 导航重构的回归风险集中在：路由重定向是否正确、旧 URL 是否仍可访问、侧边栏链接是否指向正确页面。

**Recommended approach：** 每个 M2 阶段配一套手动验收清单：
- M2-A：检查侧边栏分组和标签是否正确；Library Overview 引导卡片链接是否有效
- M2-B：检查 SourceManagementFeature 在 Library 内是否正常工作（添加源、扫描）
- M2-C：检查 Browse 页面分类导航移除后，URL 参数是否仍正确驱动内容过滤
- M2-D：检查旧路由重定向是否正确；直接访问旧 URL 是否跳转到预期目标

**Risks：** 路由重定向可能产生重定向循环（如 `/books` → `/browse-v2?domain=documents`，但 `/browse-v2` 内部又有逻辑跳回 `/books`）。

**What not to do：** 不要假设"改了导航标签就算完成"——每个链接必须实际点击验证。

**Acceptance criteria：** 每个 M2 阶段的验收清单全部通过；`npm run build` 无新增错误。

### 9.6 Release / Beta Lead

**Current concern：** M2 导航重构不应该进入当前的 Beta 包。Beta 测试者的反馈应该基于当前稳定的导航结构。

**Recommended approach：** 当前 Beta 包保持 M1 文案状态（`d4ea296`）。M2 全部阶段在 Beta 反馈收集后进行。Beta 期间可以收集用户对导航的困惑反馈，用于验证 M2 方案。

**Risks：** 如果 Beta 测试者强烈反馈"找不到功能"，可能需要加速 M2-A（低风险文案和引导卡片）作为 Beta 包的热修复。

**What not to do：** 不要在 Beta 包中包含任何 M2 代码变更。

**Acceptance criteria：** Beta 包和 M2 分支完全独立。

### 9.7 User Support Reviewer

**Current concern：** 当前用户最大的困惑点是"为什么扫描了文件夹但 Browse 里看不到"——因为他们没有理解 Source Scan（只读索引）和 Managed Import（复制+整理）的区别。

**Recommended approach：** M2-A 的 Library Overview "从这里开始"引导卡片是最关键的改进。它用非技术语言解释："扫描 = 告诉 Workbench 文件在哪（不修改）"，"导入 = 复制文件到受管库准备整理"。

**Risks：** 如果引导文字太长，用户跳过不读。需要简洁、带图标的卡片布局。

**What not to do：** 不要用"Source""Managed Root""Storage State"等开发术语。用"扫描文件夹""受管库文件夹""文件状态"。

**Acceptance criteria：** 非技术测试者能在不看文档的情况下理解扫描和导入的区别。

### 9.8 Security / Data Safety Reviewer

**Current concern：** 如果把 Source Management 从 Settings 移到 Library，用户可能误以为"在 Library 里添加的文件夹会被 Workbench 修改"。必须在 UI 中明确标注：扫描文件夹 = 只读，受管库文件夹 = 文件会被复制到这里。

**Recommended approach：** 在"扫描文件夹"旁添加信息图标 + tooltip："Workbench 只读取文件信息，不会修改或移动原文件。"在"受管库文件夹"旁添加："导入的文件会被复制到此目录。原文件不会被删除。"

**Risks：** 如果 tooltip 不够显眼，用户可能跳过。建议在 Library Overview "从这里开始"卡片中再次强调安全边界。

**What not to do：** 不要暗示 Workbench 会"自动管理""自动整理""自动清理"——所有操作都是用户手动触发的。

**Acceptance criteria：** 用户能在 UI 中明确区分"只读操作"和"会修改文件系统的操作"。

### 9.9 Project Scope Guardian

**Current concern：** M2 方案可能被误解为"把 Workbench 变成 Windows Explorer 替代品"。必须反复强调：Workbench 是元数据和组织层，不是文件管理器。

**Recommended approach：** M2 导航以"浏览分类"（按内容类型查看）为核心，不是"目录树浏览"（按文件夹路径查看）。保留 Path Browser 作为低层级诊断工具，但不放在主导航。

**Risks：** 如果侧边栏分类树太长，用户可能要求"自定义分类""创建新分类"→ 这是功能膨胀的信号，必须拒绝。

**What not to do：**
- 不添加文件夹树导航（tree view）
- 不让用户自定义分类（分类来自后端 `object_type` 枚举）
- 不做 Explorer 替代品
- 不做游戏启动器
- 不做软件安装管理器
- 不做 AI 自动分类

**Acceptance criteria：** M2 完成后，软件的核心定位"本地资产元数据和组织工作台"不变。

---

## 10. Cross-Examination and Resolutions

### Challenge 1
- **Challenge:** UX Lead 建议将 9 个媒体子分类放入侧边栏——侧边栏会变得非常长，在小屏幕上不可用。
- **Raised by:** Frontend Architect
- **Target:** UX / IA Lead
- **Response:** 媒体子分类默认折叠，用户点击"媒体"后才展开。侧边栏可用 `overflow-y: auto` 处理。小屏幕（笔记本）上侧边栏可折叠为图标模式，子分类在图标模式下显示为 tooltip。
- **Resolution:** 接受。媒体子分类默认折叠，手风琴展开。侧边栏折叠为图标模式时不显示子分类。

### Challenge 2
- **Challenge:** 把 Source Management 从 Settings 移到 Library 会让 Settings 失去一个重要功能，Settings 变成"只有主题和语言"的空壳页面。
- **Raised by:** Product Lead
- **Target:** UX / IA Lead
- **Response:** Settings 保留 Source Management 的"兼容入口"（一个链接指向 Library > Sources）。Settings 未来的定位是"应用偏好"（主题、语言、数据目录、日志、关于），不需要承载文件管理功能。
- **Resolution:** M2-B 阶段在 Library 添加 Sources tab，Settings 保留指向它的链接。M2-D 阶段可考虑从 Settings 移除 SourceManagementFeature 组件（但保留链接）。

### Challenge 3
- **Challenge:** 如果 Browse v2 内部分类导航被移除，用户如何知道当前在浏览哪个分类？
- **Raised by:** User Support Reviewer
- **Target:** UX / IA Lead
- **Response:** 通过面包屑导航 + 页面标题显示当前分类。例如：`文件库 > 媒体 > 电影/长视频`。侧边栏当前激活的分类项高亮显示。两者结合提供清晰的当前位置指示。
- **Resolution:** 接受。M2-C 必须实现面包屑或等效的当前位置指示。

### Challenge 4
- **Challenge:** "文件库"这个概念是否会让用户误以为 Workbench 是文件管理器？
- **Raised by:** Project Scope Guardian
- **Target:** Product Lead
- **Response:** "文件库"（File Library）强调的是"库"（Library）——一个经过组织的集合，而不是"文件夹"（Folder）——原始磁盘目录。Library v2 的核心理念就是"从文件到库"的转变。UI 中始终保持"浏览分类"（按内容类型）优先于"路径浏览"（按目录）。
- **Resolution:** 接受。"文件库"作为用户友好名称可以保留。但需要确保 UI 中强调分类浏览而非目录树浏览。

### Challenge 5
- **Challenge:** M2 方案没有提到 DetailsPanel 如何适配——当前 DetailsPanel 在 Browse v2、Search、Library 等页面共享。如果导航大改，DetailsPanel 的行为需要确认不受影响。
- **Raised by:** Frontend Architect
- **Target:** UX / IA Lead
- **Response:** DetailsPanel 通过 `useUIStore.selectedItemId` 驱动，与页面路由无关。无论在哪个页面，选中一个文件/对象后 DetailsPanel 都会显示。M2 不改变这个机制。唯一需要注意的是：如果 Browse v2 页面内部布局改变，需要确保右侧面板的预留空间仍然正确。
- **Resolution:** 接受。DetailsPanel 机制不变。M2-C 的 Browse 页面重布局需要保留 344px 右侧面板空间。

### Challenge 6
- **Challenge:** M2 导航中"再找回"（Refind）分组包含 Search、Recent、Tags、Collections——但 Search 是最常用的功能之一，放在子区可能降低可发现性。
- **Raised by:** User Support Reviewer
- **Target:** UX / IA Lead
- **Response:** Search 可以保持在顶层（不与"再找回"分组），或作为"再找回"的第一个项目并默认高亮。考虑到 M1 的用户习惯和 Search 的全局搜索属性，建议 Search 与 Home 并列作为顶层项目。
- **Resolution:** 调整方案：Search 提升为顶层（与 Home、文件库、系统并列）。Recent、Tags、Collections 留在"再找回"子区。

### Challenge 7
- **Challenge:** 在 Library 页面嵌入 SourceManagementFeature 是否意味着 `/library?tab=sources` 的 tab 需要新增？——这需要修改 `LibraryFeature.tsx` 的 `libraryTabs` 数组和第 86-93 行的 tab panel 渲染逻辑，触及业务逻辑。
- **Raised by:** Frontend Architect
- **Target:** Product Lead
- **Response:** 是的，添加 `sources` tab 需要修改 `libraryTabs` 数组和条件渲染。但变更范围很小（增加一个 tab 值 + 一个条件渲染分支，复用已有的 `SourceManagementFeature` 组件）。不涉及 API、不涉及数据模型。风险可控。
- **Resolution:** 接受。M2-B 阶段在 `LibraryFeature.tsx` 中添加 `sources` tab，复用现有 `SourceManagementFeature` 组件。

### Challenge 8
- **Challenge:** 404 页面、错误状态、加载状态——如果在侧边栏做大幅改动，这些状态页面是否会因为路由变更而受到影响？
- **Raised by:** QA / Test Lead
- **Target:** Frontend Architect
- **Response:** M2 不新增/删除路由，只调整侧边栏哪些项目可见。404 行为不变。加载/错误状态由各 Feature 组件内部管理，不受侧边栏影响。
- **Resolution:** 接受。不需要额外的状态处理。

---

## 11. Recommended M2 Roadmap

### M2-Plan（当前阶段）
- **目标**：Agents Team 评审，输出本报告
- **输出**：本文件
- **不改代码**

### M2-A：侧边栏信息架构 + File Library Overview 引导卡片
- **范围**：
  - 调整 `AppSidebar.tsx` 的 `navGroups` 结构（重组分组，不新增路由）
  - 重写 `LibraryOverviewPanel` 为"从这里开始"引导卡片布局
  - 更新 i18n 文案（`shell.ts`、`navigation.ts`、`features.ts`、`pages.ts`）
  - Search 提升为顶层导航项
- **不改**：不新增路由、不修改 `BrowseV2Feature` 内部分类面板、不移动 Source Management
- **风险**：低
- **验收**：侧边栏分组正确；引导卡片链接有效；`npm run build` 通过

### M2-B：Source Management 移入 File Library
- **范围**：
  - 在 `LibraryFeature.tsx` 添加 `sources` tab
  - `libraryTabs` 数组增加 `{ value: "sources", labelKey: "..." }`
  - Tab panel 渲染中添加 `<SourceManagementFeature />`
  - Settings 页面保留 Source Management 的兼容链接
  - 添加 i18n keys
- **不改**：不修改 `SourceManagementFeature` 业务逻辑；不修改 `/sources` API
- **风险**：低-中（触及 `LibraryFeature.tsx` 的 tab 逻辑）
- **验收**：Library > Sources tab 中可添加源、触发扫描；Settings 中链接指向 Library > Sources

### M2-C：Browse 页面内部分类导航移除
- **范围**：
  - 从 `BrowseV2Feature.tsx` 中移除 taxonomy panel（领域按钮 + 分类树）
  - 保留并提升 filter bar（存储状态、卡片类型、排序）
  - 添加面包屑或页面标题指示当前分类
  - 确保右侧详情面板布局不变
- **不改**：不修改 `list_cards()` API 调用逻辑；不修改 `DOMAIN_TYPE_MAP` 和 `CATEGORY_TREE`
- **风险**：中（触及核心 Feature 组件布局）
- **验收**：侧边栏分类导航驱动 Browse 页面内容；URL 参数正确传递；面包屑正确显示

### M2-D：旧页面路由兼容和权重降低
- **范围**：
  - Books/Media/Games/Software 旧路由改为重定向到 Browse 预设参数
  - `/books` → `/browse-v2?domain=documents`
  - `/library/media` → `/browse-v2?domain=media`
  - `/library/games` → `/browse-v2?domain=apps&category=game`
  - `/software` → `/browse-v2?domain=apps&category=software`
  - 保留直接 URL 访问旧路由的能力（`Navigate` 组件）
- **不改**：不删除旧 Feature 组件（保留代码，只是路由入口变更）
- **风险**：中（路由重定向可能产生循环）
- **验收**：侧边栏不再显示旧入口；直接访问 `/books` 等旧 URL 正确重定向

### M2-E：前端烟雾测试和 Beta 文档更新
- **范围**：
  - 更新 `BETA_TESTING_CHECKLIST.md` 反映新导航
  - 更新 `MANUAL_ACCEPTANCE_GUIDE.md`
  - 更新 `README.md` 的导航描述
  - 运行 `npm run build` 确认通过
  - 全量后端测试确认无回归
- **不改**：不修改后端
- **风险**：低
- **验收**：文档与 UI 一致；build 和测试通过

---

## 12. Acceptance Criteria

### M2-A 验收标准
- [ ] 侧边栏按新分组显示：Home / Search / 文件库（浏览分类 + 管理 + 再找回） / 系统
- [ ] Library Overview 显示"从这里开始"引导卡片（至少 4 张）
- [ ] 所有引导卡片链接指向正确的页面/标签页
- [ ] `npm run build` 通过
- [ ] 所有现有路由仍可访问

### M2-B 验收标准
- [ ] Library > Sources tab 显示 SourceManagementFeature
- [ ] 可添加、查看、扫描源
- [ ] Settings 中保留 Source Management 入口链接
- [ ] 后端测试全部通过

### M2-C 验收标准
- [ ] Browse 页面内部分类导航面板已移除
- [ ] 侧边栏分类导航正确驱动 Browse 页面内容
- [ ] 面包屑显示当前分类路径
- [ ] 存储状态/卡片类型筛选器仍可用
- [ ] 右侧详情面板正常显示

### M2-D 验收标准
- [ ] `/books` 重定向到 `/browse-v2?domain=documents`
- [ ] `/library/media` 重定向到 `/browse-v2?domain=media`
- [ ] `/software` 重定向到 `/browse-v2?domain=apps&category=software`
- [ ] `/library/games` 重定向到 `/browse-v2?domain=apps&category=game`
- [ ] 无重定向循环

### M2-E 验收标准
- [ ] 所有文档更新反映新导航
- [ ] `npm run build` 通过
- [ ] 全部后端测试通过（当前 794/795）

---

## 13. Risks

| 风险 | 可能性 | 影响 | 规避方式 |
|------|--------|------|----------|
| 侧边栏分类树过长影响可用性 | 中 | 中 | 默认折叠子分类；手风琴展开；小屏折叠为图标 |
| 旧路由重定向产生循环 | 低 | 高 | 每个重定向单独测试；添加重定向深度限制 |
| LibraryFeature tab 逻辑变更引入 bug | 中 | 中 | 仅增加一个 tab，不修改现有 tab 逻辑 |
| 用户习惯旧导航，反馈负面 | 中 | 中 | 保留所有旧路由可访问；Beta 期间收集反馈 |
| Source Management 移到 Library 后 Settings 变空壳 | 低 | 低 | Settings 保留兼容链接和系统状态功能 |
| "文件库"命名让用户误解为 Explorer | 低 | 中 | UI 强调分类浏览，不强调目录树 |

---

## 14. Non-goals

以下为 M2 **明确不做**的事项：

1. ❌ 不合并 Source 和 Managed Root 数据模型
2. ❌ 不让 Managed Root 自动扫描
3. ❌ 不删除旧路由（`/books`、`/library/media` 等）
4. ❌ 不删除旧 Feature 组件
5. ❌ 不做 delete / source cleanup
6. ❌ 不做 AI 自动分类
7. ❌ 不做 Explorer 替代品
8. ❌ 不重写 Browse v2 业务逻辑（`list_cards()`、`get_object_detail()` 等）
9. ❌ 不改 Phase 8 compose / amendment / plan 语义
10. ❌ 不把 plan create UI 误导成 execute
11. ❌ 不在 Beta 前做任何 M2 代码变更
12. ❌ 不新增后端 API 端点（M2 全阶段前端 only）
13. ❌ 不新增数据库迁移
14. ❌ 不让用户自定义分类
15. ❌ 不做文件夹树导航
16. ❌ 不做游戏启动器或软件安装管理器

---

## 15. Final Recommendation

### 建议执行 M2，分 5 阶段

**核心理由**：
1. 当前信息架构割裂是 Beta 测试者最可能反馈的困惑点
2. Browse v2 分类导航设计优秀但被埋没——值得提升为全局导航
3. 所有 M2 阶段均为纯前端改动，后端零影响
4. "信息架构合并，数据模型不合并"的策略保证了安全边界

**推荐执行顺序**：
- **现在**：完成 M2-Plan（本报告）
- **Beta 期间**：收集用户对当前导航的反馈
- **Beta 后**：按 M2-A → M2-B → M2-C → M2-D → M2-E 执行

**最高优先级**：M2-A（侧边栏信息架构 + Overview 引导卡片）——纯 i18n 和组件重组，零风险，最高收益。

---

## Questions Needing User Confirmation

1. **侧边栏分类导航的默认展开行为**：媒体子分类（9 项）默认折叠——是否接受？还是希望默认展开全部？

2. **Search 的位置**：本报告建议 Search 与 Home 并列顶层。是否接受？还是保持在"再找回"子区？

3. **旧路由重定向时机**：M2-D 阶段将 `/books` 等重定向到 Browse 预设——是在 beta 后立即做，还是等收集反馈后再决定？

4. **Source Management 移入 Library 的时机**：M2-B 阶段——是否接受在 Library 中新增 `sources` tab？

5. **Browse 页面内部分类导航移除时机**：M2-C 阶段——是否接受在侧边栏已有完整分类导航后移除 Browse 内部的 taxonomy panel？
