# Windows 本地资产管理工作台 前端工程目录与状态管理草案

## 1. 文档目的

本文件用于将当前已经完成的产品、原型、架构、Schema、API 与开发阶段文档，继续下沉为**前端工程层面的结构草案**。

当前目标不是写具体业务代码，而是先明确：
- 前端工程目录怎么组织
- 页面、Feature、实体、共享组件如何分层
- 哪些状态应放在全局，哪些状态应放在页面局部
- 详情侧栏、搜索、标签、筛选这些跨页面能力如何安放
- 如何在不做过度设计的前提下，为第一阶段代码实现提供稳定骨架

本文件的核心目标是：

> **让前端从“页面集合”变成“结构清楚、状态边界明确的桌面工作台工程”。**

---

## 2. 前端工程目标

### 2.1 第一阶段前端真正要解决的问题
第一阶段前端不是要做一个“炫酷 UI 演示项目”，而是要稳定承载以下主链：

> **扫描源配置 → 搜索 → 详情查看 → 标签 / 颜色标签 → 素材库浏览 → 最近导入整理 → 打开文件 / 打开目录**

### 2.2 当前前端成功标准
当前前端结构成立的标志不是“目录很多”，而是：
1. 页面层清晰
2. Feature 复用清晰
3. 共享组件边界清晰
4. 全局状态不过度膨胀
5. 详情侧栏能跨页面复用
6. 搜索、标签、筛选交互在多个页面中保持一致

---

## 3. 前端设计原则

### 3.1 分层原则
前端至少分为以下几层：
1. **App Shell 层**
2. **Pages 层**
3. **Features 层**
4. **Entities 层**
5. **Shared 层**
6. **Services / API 层**

### 3.2 状态原则
1. 全局状态只放真正跨页面共享的状态
2. 页面自己的筛选、排序、视图模式优先页面内管理
3. 组件内部状态不轻易上提
4. 不为了“以后也许用得到”就先做一个巨大 store

### 3.3 复用原则
必须尽早统一的能力：
- 全局搜索
- 标签选择
- 颜色标签选择
- 筛选器与筛选胶囊
- 详情侧栏
- 空状态 / 无结果 / 骨架屏 / Toast

### 3.4 当前阶段反过度设计原则
1. 不做复杂 DDD 过度包装
2. 不做微前端式拆分
3. 不做多个 store 并列互相嵌套的状态迷宫
4. 不为未来游戏库 / 书库 / 软件库先抽象一整套重型插件协议

---

## 4. 目录结构总览（建议）

以下是一套偏稳妥、适合第一阶段的目录结构建议：

```text
src/
  app/
    shell/
    router/
    providers/
    styles/
  pages/
    home/
    onboarding/
    search/
    files/
    media-library/
    tags/
    recent/
    settings/
  features/
    search/
    source-management/
    file-browser/
    media-library/
    tagging/
    details-panel/
    filters/
    recent-imports/
    selection-mode/
  entities/
    file/
    source/
    tag/
    library-item/
    task/
  shared/
    ui/
    components/
    hooks/
    utils/
    constants/
    types/
  services/
    api/
    mappers/
    query/
    cache/
```

---

## 5. 各层职责说明

## 5.1 app/

### 作用
承载应用级骨架，不放具体业务页面逻辑。

### 建议子目录

#### app/shell/
存放：
- AppShell
- SidebarLayout
- TopBar
- RightPanelContainer
- 全局弹层容器
- 全局通知容器

#### app/router/
存放：
- 路由定义
- 路由常量
- 页面懒加载配置（如需要）

#### app/providers/
存放：
- QueryProvider / API Provider
- ThemeProvider
- GlobalStoreProvider（若使用）
- RouterProvider

#### app/styles/
存放：
- 全局样式
- 主题变量
- reset / base 样式

### 不应放在 app/ 的内容
- 搜索页业务查询逻辑
- 标签写入逻辑
- 素材库卡片展示逻辑
- 具体实体映射逻辑

---

## 5.2 pages/

### 作用
作为页面路由入口，负责：
- 组合页面所需 Feature
- 决定页面布局
- 与 AppShell 对接
- 放置页面级容器逻辑

### 页面建议
- `pages/home/`
- `pages/onboarding/`
- `pages/search/`
- `pages/files/`
- `pages/media-library/`
- `pages/tags/`
- `pages/recent/`
- `pages/settings/`

### 每个页面目录建议包含
```text
pages/search/
  SearchPage.tsx
  SearchPage.module.css (或同类样式文件)
  SearchPage.types.ts (如需要)
```

### Pages 层应保持克制
Pages 不应充满：
- API 细节
- 复杂状态转换
- 标签写入实现
- 缩略图策略判断

Pages 应主要负责：
- 页面标题
- Feature 排布
- 页面级空状态衔接
- 页面级局部状态组合

---

## 5.3 features/

### 作用
封装与某一业务能力强相关的 UI、状态、交互和局部数据流。

这层是第一阶段前端结构最关键的一层。

### 为什么必须要有这层
如果没有 features 层，很容易变成：
- 页面里塞满业务代码
- 共享组件变成知道太多业务的“半页面组件”
- 相同能力在 Search / Media / Recent / Tags 页面各写一套

### 当前建议 Feature 列表

#### features/search/
职责：
- 搜索输入与 query 消费
- 搜索结果请求
- 搜索页列表/网格切换
- 搜索页筛选器联动

#### features/source-management/
职责：
- 扫描源列表
- 添加 / 删除 / 启用 / 禁用扫描源
- 触发扫描任务

#### features/file-browser/
职责：
- 目录树
- 全部文件页列表
- 路径浏览交互

#### features/media-library/
职责：
- 图片 / 视频范围切换
- 素材网格展示
- 密度切换
- 素材筛选联动

#### features/tagging/
职责：
- 标签列表
- 标签结果展示
- 标签增删行为
- 详情侧栏内标签变更复用

#### features/details-panel/
职责：
- 详情读取
- 详情侧栏 UI 结构
- 标签 / 颜色标签 / 打开动作
- 跨页面复用

#### features/filters/
职责：
- FilterBar
- FilterChipRow
- 排序与筛选行为协调

#### features/recent-imports/
职责：
- 最近导入时间范围切换
- 最近导入结果展示
- 与详情联动

#### features/selection-mode/
职责：
- 多选状态
- 批量操作条
- 批量标签 / 颜色标签

### Feature 目录建议结构
例如：
```text
features/media-library/
  components/
  hooks/
  model/
  api/
  MediaLibrarySection.tsx
```

其中：
- `components/`：此 feature 私有组件
- `hooks/`：feature 私有 hooks
- `model/`：局部状态 / 类型 / selector
- `api/`：该 feature 对 services/api 的薄封装（可选）

---

## 5.4 entities/

### 作用
承载较稳定的业务对象定义与对象级辅助逻辑。

### 当前建议实体
- `entities/file/`
- `entities/source/`
- `entities/tag/`
- `entities/library-item/`
- `entities/task/`

### 每个实体目录可包含
- `types.ts`
- `mappers.ts`
- `helpers.ts`
- `constants.ts`

### 举例
#### entities/file/
可包含：
- `FileItem`
- `FileListItemVM`
- `FileDetailVM`
- 文件类型枚举
- 路径显示辅助函数

### 说明
Entities 层不是后端 ORM 映射复制，而是前端相对稳定的对象定义层。

---

## 5.5 shared/

### 作用
承载全项目通用的 UI 和无业务偏向的基础能力。

### 建议子目录

#### shared/ui/
放最基础、弱业务的视觉组件：
- Button
- Input
- Dialog
- Badge
- Tabs
- Dropdown
- Skeleton
- Tooltip

#### shared/components/
放跨多个 Feature 复用，但已有一定产品语义的组件：
- GlobalSearchInput
- EmptyState
- NoResultsBlock
- LoadingSkeleton
- ConfirmDialog
- ToastViewport

#### shared/hooks/
放通用 hooks：
- useDebounce
- useToggle
- usePrevious
- useLocalPreference

#### shared/utils/
放工具函数：
- 时间格式化
- 路径格式化
- 文件大小格式化
- 条件构造工具

#### shared/constants/
放常量：
- 路由常量
- 排序选项
- 颜色标签定义
- 文件类型定义

#### shared/types/
放少量真正通用的类型，不要让这里变成“全项目类型垃圾堆”。

---

## 5.6 services/

### 作用
封装 API 通信与数据映射，是前端与本地应用服务的边界层。

### 建议子目录

#### services/api/
存放 API 调用函数：
- `sourcesApi.ts`
- `filesApi.ts`
- `searchApi.ts`
- `tagsApi.ts`
- `mediaApi.ts`
- `tasksApi.ts`

#### services/mappers/
用于把服务端返回转换为前端 view model。

#### services/query/
如果使用查询库（如 TanStack Query），这里可放 query key、query options、组合查询 hooks。

#### services/cache/
放极少量本地缓存辅助逻辑（如需要）。

### 原则
- Page 不直接写 fetch 细节
- Feature 可以通过 services/query 获取数据
- 服务端字段格式转换尽量在 mappers 层完成

---

## 6. 推荐路由结构

### 6.1 P0 路由
```text
/
/onboarding
/search
/files
/library/media
/tags
/recent
/settings
```

### 6.2 P1 预留路由
```text
/library/games
/library/books
/library/apps
/collections
```

### 6.3 路由设计原则
1. 路由主要描述页面，而不是组件细节
2. 详情侧栏优先不独立成重路由页面
3. 第一阶段不必为 every item 都建立独立详情 URL
4. 未来若需要深链接，可补 `/item/:id` 或各库详情路由

---

## 7. 全局状态与页面局部状态草案

## 7.1 为什么要先定状态边界
这个产品很容易失控的地方之一就是：
- 搜索词想全局化
- 筛选器想全局化
- 详情项想全局化
- 多选状态也想全局化

最后会变成一个非常庞大且相互污染的状态树。

所以第一阶段必须明确：

> **只有真正跨页面共享的状态才进全局。**

---

## 7.2 建议放在全局的状态

### A. 详情侧栏状态
建议字段：
- `selectedItemId`
- `isDetailsPanelOpen`
- `selectedItemContext`（可选，如 current page）

### B. 应用主题与 UI 偏好
建议字段：
- `theme`
- `sidebarCollapsed`（如需要）

### C. 全局通知状态
建议字段：
- `toasts[]`

### D. 扫描源摘要 / 系统状态摘要（可选）
仅在多个页面都需要展示时进入全局缓存层，而不一定进入全局 UI store。

---

## 7.3 建议放在页面局部的状态

### SearchPage
- `query`
- `filters`
- `sort`
- `viewMode`
- `page`
- `selectionMode`
- `selectedIds`

### MediaLibraryPage
- `viewScope`（image/video/all）
- `filters`
- `sort`
- `density`
- `page`
- `selectionMode`
- `selectedIds`

### RecentImportsPage
- `range`
- `sort`
- `viewMode`
- `selectionMode`
- `selectedIds`

### FilesPage
- `currentSourceId`
- `currentParentPath`
- `sort`
- `viewMode`

### TagsPage
- `currentTagId`
- `sort`
- `viewMode`
- `filters`

### Onboarding / Settings
- 表单临时状态
- 当前操作中的 loading 状态

---

## 7.4 建议放在 Feature 层的局部状态

某些状态既不适合全局，也不应完全留在页面层，适合放在 Feature 内部 hook / model：

### examples
- TagPicker 的输入值
- ColorTagPicker 的弹层开关（如果有）
- FilterBar 的局部展开 / 收起
- SelectionModeFeature 的选中集合与批量模式状态
- SourceManagement 的当前操作 loading

---

## 8. 推荐状态管理方式（策略层）

### 8.1 第一阶段建议
使用组合式策略，而不是一个“大一统状态系统”：

1. **服务端数据** → 查询库管理（如 TanStack Query）
2. **全局 UI 状态** → 轻量 store（如 Zustand / Context + reducer）
3. **页面局部状态** → 页面内部 state / feature hook
4. **组件临时状态** → 组件内部 state

### 8.2 为什么这样更合适
因为本产品同时包含：
- 服务端查询数据
- 桌面 UI 状态
- 高频局部筛选状态
- 详情侧栏联动

如果全部塞到一个 store 里，会很快变得难以维护。

### 8.3 当前不建议
- 不建议全量 Redux 化所有状态
- 不建议把查询结果复制进全局 store 再消费
- 不建议 Page/Feature/Component 同时维护同一份筛选状态

---

## 9. 推荐 query / 缓存分层

## 9.1 服务端数据分类

### A. 相对稳定、可缓存的数据
- 标签列表
- 扫描源列表
- 系统状态摘要

### B. 高频变化、页面驱动的数据
- 搜索结果
- 素材库结果
- 最近导入结果
- 某标签下的文件结果

### C. 单项详情数据
- `GET /files/{id}`

### D. 写操作结果
- 添加标签
- 移除标签
- 设置颜色标签
- 添加扫描源
- 触发扫描

## 9.2 建议 query key 结构
例如：
```text
['sources']
['system-status']
['tags']
['search', query, filters, sort, page]
['files', sourceId, parentPath, sort, page]
['media-library', viewScope, filters, sort, page]
['recent', range, sort, page]
['file-detail', fileId]
['tag-files', tagId, filters, sort, page]
```

### 9.3 写操作后的刷新策略
- 标签更新后：
  - 更新 `file-detail`
  - 视情况局部失效当前页面结果列表
- 颜色标签更新后：
  - 同上
- 添加扫描源 / 触发扫描后：
  - 更新 `sources`
  - 更新 `system-status`

### 9.4 当前建议
优先采用“局部失效 + 局部刷新”，不要每次写操作后整页重拉所有数据。

---

## 10. 详情侧栏状态与数据流建议

### 10.1 为什么单独强调
RightDetailsPanel / DetailsPanelFeature 是整个产品跨页面中枢，必须单独确定数据流。

### 10.2 当前建议的数据流
```text
用户单击页面中的文件项
→ 更新全局 selectedItemId
→ 打开右侧详情侧栏
→ DetailsPanelFeature 读取 ['file-detail', fileId]
→ 渲染详情
→ 用户执行标签 / 颜色标签 / 打开动作
→ 局部刷新详情与当前列表项回显
```

### 10.3 侧栏不应做的事
- 不应自己维护独立的列表状态
- 不应知道太多页面筛选逻辑
- 不应强依赖某一个页面的私有实现

### 10.4 侧栏与页面的边界
- 页面负责“谁被选中”
- 侧栏负责“选中项的详情展示和操作”
- 写操作完成后，由局部失效或回调刷新当前页显示

---

## 11. 页面目录进一步建议

## 11.1 pages/search/
建议：
```text
pages/search/
  SearchPage.tsx
  SearchPage.layout.tsx（可选）
  SearchPage.hooks.ts（可选）
```

SearchPage 负责：
- 页面标题
- 引入 SearchFeature + RightDetailsPanel
- 挂载页面局部状态容器

## 11.2 pages/media-library/
建议：
```text
pages/media-library/
  MediaLibraryPage.tsx
  MediaLibraryPage.hooks.ts
```

## 11.3 pages/recent/
建议：
```text
pages/recent/
  RecentImportsPage.tsx
```

## 11.4 pages/files/
建议：
```text
pages/files/
  FilesPage.tsx
```

## 11.5 pages/tags/
建议：
```text
pages/tags/
  TagsPage.tsx
```

---

## 12. Feature 目录进一步建议

## 12.1 features/search/
建议：
```text
features/search/
  components/
    SearchResultsHeader.tsx
    SearchResultsContainer.tsx
  hooks/
    useSearchPageState.ts
  model/
    search.types.ts
    search.filters.ts
  SearchFeature.tsx
```

## 12.2 features/media-library/
建议：
```text
features/media-library/
  components/
    MediaScopeTabs.tsx
    MediaGridSection.tsx
    DensityToggle.tsx
  hooks/
    useMediaLibraryState.ts
  model/
    media-library.types.ts
  MediaLibraryFeature.tsx
```

## 12.3 features/details-panel/
建议：
```text
features/details-panel/
  components/
    FilePreviewBlock.tsx
    MetadataBlock.tsx
    ActionsBlock.tsx
  hooks/
    useDetailsPanel.ts
  DetailsPanelFeature.tsx
```

## 12.4 features/tagging/
建议：
```text
features/tagging/
  components/
    TagsSidebar.tsx
    TagResultsSection.tsx
  hooks/
    useTaggingActions.ts
  TaggingFeature.tsx
```

## 12.5 features/source-management/
建议：
```text
features/source-management/
  components/
    SourcesList.tsx
    AddSourceButton.tsx
    ScanActions.tsx
  hooks/
    useSourceManagement.ts
  SourceManagementFeature.tsx
```

---

## 13. 共享组件优先级建议

### 13.1 第一批必须先稳定的共享组件
1. GlobalSearchInput
2. FilterBar
3. FilterChipRow
4. TagPicker
5. ColorTagPicker
6. RightDetailsPanel
7. EmptyState
8. NoResultsBlock
9. LoadingSkeleton

### 13.2 第二批共享组件
1. FileList
2. FileListRow
3. FileGrid
4. FileCard
5. MediaCard
6. BatchActionBar
7. ConfirmDialog
8. ToastViewport

### 13.3 原因
第一批组件直接决定：
- 搜索是否顺
- 标签是否轻
- 详情是否统一
- 页面状态是否统一

---

## 14. 推荐前端启动顺序（按工程骨架）

### Step A：搭壳层
1. AppShell
2. Sidebar
3. TopBar
4. RightPanelContainer
5. Router

### Step B：搭基础共享组件
1. Button / Input / Dialog / Skeleton
2. GlobalSearchInput
3. EmptyState / NoResultsBlock
4. Toast / ConfirmDialog

### Step C：搭关键 Feature 骨架
1. DetailsPanelFeature
2. SearchFeature
3. SourceManagementFeature
4. FiltersFeature

### Step D：接页面
1. OnboardingPage
2. SearchPage
3. FilesPage
4. MediaLibraryPage
5. RecentImportsPage
6. TagsPage
7. HomePage
8. SettingsPage

### Step E：接状态与查询
1. 全局 UI store
2. query keys
3. API services
4. 局部页面 state

这个顺序的好处是：
- 壳层先成立
- 高复用能力先成立
- 页面只是往壳层里装 Feature

---

## 15. 当前阶段最应避免的前端问题

### 15.1 问题：页面直接 fetch 数据并处理全部逻辑
后果：
- 页面过厚
- 逻辑无法复用
- 后续维护困难

### 15.2 问题：所有状态都塞进一个大 store
后果：
- 筛选状态互相污染
- 调试困难
- 更新范围过大

### 15.3 问题：共享组件知道太多业务上下文
后果：
- 组件难复用
- 组件越来越像“半个页面”

### 15.4 问题：Feature 粒度过细
后果：
- 工程结构碎片化
- 文件过多但边界不清

### 15.5 问题：Feature 粒度过粗
后果：
- SearchFeature 变成半个应用
- DetailsPanelFeature 变成全能业务面板

### 15.6 当前建议
Feature 粒度要以“一个稳定业务能力单元”为准，不按单组件拆，也不按整页吞。

---

## 16. 当前前端结构结论

当前最推荐的第一阶段前端工程方向可以浓缩为：

> **App Shell 统一骨架，Pages 负责页面布局，Features 负责核心业务能力复用，Entities 负责稳定对象定义，Shared 负责通用 UI，Services 负责 API 与数据映射。**

并配合：
- 轻量全局 UI 状态
- 页面局部筛选 / 排序状态
- 查询库管理服务端数据
- DetailsPanelFeature 作为跨页面中枢

这是一条足够稳、可扩展但不过度设计的前端骨架。

---

## 17. 下一步建议

在这份前端工程目录与状态管理草案之后，最适合继续推进的方向有两个：
1. **技术实现任务清单（更细粒度）**
2. **前端脚手架初始化建议（文件级）**

如果你准备直接进入代码层，我更推荐下一步先做：

> **前端脚手架初始化建议 v1**

因为到这里，产品结构、页面、组件、状态边界都已经有了，下一步最自然的就是把这些目录真正翻成“该先创建哪些文件、哪些目录、哪些空组件、哪些 provider、哪些 query key”的启动清单。

