# Windows 本地资产管理工作台 前端脚手架初始化建议 v1

## 1. 文档目的

本文件用于把《前端工程目录与状态管理草案》继续下沉到**可立即开工的脚手架层**。

当前目标不是写业务实现，而是先明确：
- 前端项目初始化时应先创建哪些目录
- 应先落哪些页面壳、Feature 壳、共享组件壳
- 哪些 provider、query key、store、types 要先建好
- 哪些文件适合先放占位实现，保证主链能尽快串起来
- 第一批代码骨架应该按什么顺序搭建

本文件的核心目标是：

> **把文档结构翻译成第一批真实文件与目录。**

这样你后面无论自己写、交给开发者、还是交给代码模型执行，都能直接从一个清晰骨架起步，而不是从空仓库反复讨论。

---

## 2. 初始化总原则

### 2.1 总体原则
1. **先搭壳层，再搭页面，再接 Feature，再接数据**
2. **先建目录与占位文件，再逐步填实现**
3. **共享能力优先于单页细节**
4. **详情侧栏、搜索、筛选、标签这些核心能力要尽早有壳**
5. **第一批文件要服务主链，而不是追求目录完美完整**

### 2.2 当前不建议的初始化方式
不建议：
- 一上来创建几十个空目录但没有真正入口
- 一上来把所有 P1/P2 页面都建齐
- 一上来为未来做复杂设计系统和故事书体系
- 一上来先写很重的状态系统

初始化的目标不是“看起来像大项目”，而是：

> **保证第一阶段最小主链能快速落地。**

---

## 3. 第一批应创建的目录

建议先创建如下目录骨架：

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
```

### 3.1 为什么先不建太多目录
当前阶段不必一开始就建：
- `selection-mode/`（若暂不做多选）
- `collections/`（P1）
- `games/ books/ apps/` Feature（P1）
- 复杂 cache 目录

这些可以在 Phase 3/4 之后再加，不要抢第一批骨架的注意力。

---

## 4. 第一批必须创建的文件清单

以下清单优先按“能让应用跑起来并挂上主链页面”的思路排列。

---

## 4.1 App 壳层文件

### app/

#### `src/app/App.tsx`
职责：
- 应用根入口
- 挂载 providers
- 渲染 router

#### `src/app/shell/AppShell.tsx`
职责：
- 左侧导航
- 顶部栏
- 页面内容容器
- 右侧详情侧栏容器

#### `src/app/shell/AppSidebar.tsx`
职责：
- 渲染主导航

#### `src/app/shell/AppTopBar.tsx`
职责：
- 页面标题区
- 全局搜索入口
- 预留全局动作位

#### `src/app/shell/RightPanelContainer.tsx`
职责：
- 详情侧栏容器
- 根据全局 selectedItemId 显示或隐藏 DetailsPanelFeature

#### `src/app/router/index.tsx`
职责：
- 路由定义与页面映射

#### `src/app/providers/AppProviders.tsx`
职责：
- 汇总 QueryProvider / ThemeProvider / UIStoreProvider 等

#### `src/app/styles/global.css`
职责：
- 全局基础样式

---

## 4.2 页面文件

### 必须先建的页面

#### `src/pages/onboarding/OnboardingPage.tsx`
- 第一批最重要页面之一
- 优先服务扫描源添加与首次扫描

#### `src/pages/search/SearchPage.tsx`
- 第一批最重要页面之一
- 优先服务搜索结果页主链

#### `src/pages/media-library/MediaLibraryPage.tsx`
- 第一批最重要页面之一
- 优先服务素材库主链

#### `src/pages/recent/RecentImportsPage.tsx`
- 第一批较重要页面
- 优先服务整理入口

#### `src/pages/files/FilesPage.tsx`
- 服务路径导向浏览

### 第二批再补的页面

#### `src/pages/home/HomePage.tsx`
- 可以在 Search / Onboarding / Media 起壳后再补

#### `src/pages/tags/TagsPage.tsx`
- 在标签主链成立后补

#### `src/pages/settings/SettingsPage.tsx`
- 可在扫描源与系统状态主链初步成立后补

---

## 4.3 第一批 Feature 壳文件

### 最优先 Feature

#### `src/features/source-management/SourceManagementFeature.tsx`
职责：
- 扫描源列表
- 添加扫描源按钮
- 启动扫描按钮

#### `src/features/search/SearchFeature.tsx`
职责：
- 搜索页主内容区
- 搜索结果容器
- 筛选栏与结果联动

#### `src/features/media-library/MediaLibraryFeature.tsx`
职责：
- 素材库主内容区
- 图片/视频切换
- 网格展示

#### `src/features/details-panel/DetailsPanelFeature.tsx`
职责：
- 详情侧栏主体
- 标签、颜色标签、打开动作

#### `src/features/filters/FiltersFeature.tsx`
职责：
- FilterBar + FilterChipRow 统一封装

#### `src/features/recent-imports/RecentImportsFeature.tsx`
职责：
- 最近导入列表
- 时间范围切换

### 第二批 Feature

#### `src/features/file-browser/FileBrowserFeature.tsx`
- 全部文件页

#### `src/features/tagging/TaggingFeature.tsx`
- 标签页与标签结果

---

## 4.4 第一批共享组件文件

### shared/components/

#### `GlobalSearchInput.tsx`
- 顶部搜索入口与搜索页输入统一

#### `EmptyState.tsx`
- 页面空状态

#### `NoResultsBlock.tsx`
- 搜索/筛选无结果

#### `LoadingSkeleton.tsx`
- 列表 / 网格 / 详情骨架

#### `ConfirmDialog.tsx`
- 删除扫描源、重建索引等高风险动作

#### `ToastViewport.tsx`
- 全局轻反馈

### shared/ui/

#### `Button.tsx`
#### `Input.tsx`
#### `Badge.tsx`
#### `Tabs.tsx`
#### `Dropdown.tsx`
#### `Skeleton.tsx`

这些组件一开始可以很薄，重点是统一基础外观与用法。

---

## 4.5 第一批核心业务组件文件

### 应先落的组件

#### `src/features/filters/components/FilterBar.tsx`
#### `src/features/filters/components/FilterChipRow.tsx`
#### `src/features/tagging/components/TagPicker.tsx`
#### `src/features/tagging/components/ColorTagPicker.tsx`
#### `src/features/details-panel/components/FilePreviewBlock.tsx`
#### `src/features/details-panel/components/MetadataBlock.tsx`
#### `src/features/details-panel/components/ActionsBlock.tsx`
#### `src/features/media-library/components/MediaGrid.tsx`
#### `src/features/media-library/components/MediaCard.tsx`
#### `src/features/file-browser/components/FileList.tsx`
#### `src/features/file-browser/components/FileListRow.tsx`

### 说明
这些组件不需要第一天就写满逻辑，但壳和 props 方向应尽早确定。

---

## 5. 第一批实体与类型文件

### 建议先创建

#### `src/entities/file/types.ts`
定义：
- `FileItem`
- `FileListItemVM`
- `FileDetailVM`
- `FileType`

#### `src/entities/source/types.ts`
定义：
- `SourceVM`
- `SourceStatus`

#### `src/entities/tag/types.ts`
定义：
- `Tag`
- `TagSummary`
- `ColorTag`

#### `src/entities/library-item/types.ts`
定义：
- `LibraryItem`
- `MediaCardVM`
- `LibraryType`

#### `src/entities/task/types.ts`
定义：
- `Task`
- `TaskStatus`
- `TaskType`

### 原则
第一批类型不追求完美覆盖所有未来字段，只覆盖当前 P0 主链所需。

---

## 6. 第一批常量与工具文件

### shared/constants/
建议先建：

#### `routes.ts`
定义路由常量：
- HOME
- ONBOARDING
- SEARCH
- FILES
- MEDIA_LIBRARY
- TAGS
- RECENT
- SETTINGS

#### `fileTypes.ts`
定义文件类型枚举和显示文案

#### `colorTags.ts`
定义颜色标签常量：
- red
- yellow
- green
- blue
- purple
- none

#### `sortOptions.ts`
定义通用排序选项

### shared/utils/
建议先建：

#### `formatFileSize.ts`
#### `formatDateTime.ts`
#### `truncatePath.ts`
#### `buildQueryString.ts`

---

## 7. 第一批 API 文件与 query key 文件

## 7.1 services/api/
建议先建：

#### `sourcesApi.ts`
包含：
- getSources
- createSource
- updateSource
- deleteSource
- triggerSourceScan

#### `searchApi.ts`
包含：
- searchFiles

#### `filesApi.ts`
包含：
- getFiles
- getFileDetail
- setFileColorTag
- addFileTag
- removeFileTag

#### `mediaApi.ts`
包含：
- getMediaLibraryItems

#### `tagsApi.ts`
包含：
- getTags
- createTag
- getFilesByTag

#### `systemApi.ts`
包含：
- getSystemStatus

#### `recentApi.ts`
包含：
- getRecentFiles

---

## 7.2 services/query/
建议先建：

#### `queryKeys.ts`
定义：
```text
sources
system-status
search(...)
files(...)
file-detail(...)
media-library(...)
recent(...)
tags
tag-files(...)
```

#### `sourcesQueries.ts`
#### `searchQueries.ts`
#### `filesQueries.ts`
#### `mediaQueries.ts`
#### `tagsQueries.ts`
#### `recentQueries.ts`

### 原则
- 第一批先把 query key 统一
- query hook 与 API 调用不要写死在页面里

---

## 8. 第一批全局 store / 状态文件

### 8.1 当前建议只建一个轻量 UI store
建议文件：

#### `src/app/providers/uiStore.ts` 或 `src/shared/hooks/useUIStore.ts`

### 初始状态建议只包含：
- `selectedItemId`
- `isDetailsPanelOpen`
- `theme`
- `toasts`

### 行为建议只包含：
- `selectItem(id)`
- `clearSelection()`
- `openDetailsPanel()`
- `closeDetailsPanel()`
- `pushToast(toast)`
- `removeToast(id)`

### 当前不建议放进去的状态
- SearchPage 的 query
- 各页面 filters
- 各页面 pagination
- 各页面 selectionMode

这些都应留在页面 / Feature 层。

---

## 9. 第一批 hooks 文件建议

### shared/hooks/
优先创建：

#### `useDebounce.ts`
给搜索输入使用

#### `useToggle.ts`
给弹层、收起展开状态使用

#### `usePageTitle.ts`
简化页面标题设置

### features 内部 hooks

#### `features/search/hooks/useSearchPageState.ts`
管理：
- query
- filters
- sort
- viewMode
- page

#### `features/media-library/hooks/useMediaLibraryState.ts`
管理：
- scope
- filters
- density
- sort
- page

#### `features/recent-imports/hooks/useRecentImportsState.ts`
管理：
- range
- sort
- viewMode

#### `features/details-panel/hooks/useDetailsPanel.ts`
管理：
- 详情读取
- 标签 / 颜色标签写操作后的局部刷新

---

## 10. 第一批文件内容建议：哪些先放占位

### 10.1 先写“壳”比先写“满”更重要
以下文件第一批可以先写占位结构：
- HomePage
- TagsPage
- SettingsPage
- FileBrowserFeature
- TaggingFeature
- ConfirmDialog
- ToastViewport

### 10.2 第一批不应只是空 return null
即使是占位，也应至少具备：
- 组件结构
- 基础 props
- 基础 className / layout
- TODO 注释说明未来职责

这样后续接业务时不容易返工。

---

## 11. 推荐初始化顺序（文件级）

## Step 1：先让应用能打开
1. `App.tsx`
2. `AppProviders.tsx`
3. `router/index.tsx`
4. `AppShell.tsx`
5. `AppSidebar.tsx`
6. `AppTopBar.tsx`
7. `global.css`

### 结果
- 应用可启动
- 左右布局骨架可见
- 路由可切换

---

## Step 2：先让页面能挂上
1. OnboardingPage
2. SearchPage
3. MediaLibraryPage
4. RecentImportsPage
5. FilesPage
6. HomePage
7. TagsPage
8. SettingsPage

### 结果
- 所有 P0 页面都有占位入口

---

## Step 3：先搭最关键共享能力
1. GlobalSearchInput
2. EmptyState
3. NoResultsBlock
4. LoadingSkeleton
5. Button / Input / Tabs / Dropdown
6. UI store

### 结果
- 页面开始有统一基础语言

---

## Step 4：先搭四个核心 Feature 壳
1. SourceManagementFeature
2. SearchFeature
3. DetailsPanelFeature
4. MediaLibraryFeature

### 结果
- 第一批主链页面开始有真正业务承载点

---

## Step 5：接 API 层与 query key
1. services/api/*
2. services/query/queryKeys.ts
3. queries hooks

### 结果
- 页面和后端协议真正开始连接

---

## Step 6：补细部组件
1. FilterBar / FilterChipRow
2. TagPicker / ColorTagPicker
3. MediaCard
4. FileList / FileListRow
5. ActionsBlock / MetadataBlock / FilePreviewBlock

### 结果
- 页面开始接近真实 MVP

---

## 12. 推荐最小提交里程碑

### Commit A：应用壳与路由骨架
应包含：
- app/
- router/
- 基础页面占位

### Commit B：共享基础组件与全局 UI 状态
应包含：
- Button/Input/Skeleton
- GlobalSearchInput
- UI store

### Commit C：Onboarding + Search 主链骨架
应包含：
- SourceManagementFeature
- SearchFeature
- DetailsPanelFeature 壳

### Commit D：MediaLibrary 主链骨架
应包含：
- MediaLibraryFeature
- MediaCard 壳
- 筛选组件壳

### Commit E：API/query 层接入
应包含：
- api files
- query keys
- 基础 query hooks

这样做的好处是：
- 每次提交都能看到明确进展
- 回滚和定位问题更容易

---

## 13. 第一批应该先跑通的页面主链

当前最推荐先打通这一组：

### 主链 1
`OnboardingPage` → 添加扫描源 → 触发扫描

### 主链 2
`SearchPage` → 搜索结果 → 单击看详情 → 双击打开

### 主链 3
`MediaLibraryPage` → 浏览素材 → 单击看详情 → 标签 / 颜色标签

只要这三条主链骨架先成立，后面的 Home / Tags / Recent / Settings 都更容易接入。

---

## 14. 当前最应避免的脚手架问题

### 14.1 问题：一开始就创建过多无用文件
后果：
- 工程看起来大，但没有主链
- 维护者很难判断哪些是真正关键文件

### 14.2 问题：所有页面先空壳齐全，但 Feature 没骨架
后果：
- 页面间无法共享能力
- 后面会回到“每页各写一套”

### 14.3 问题：先把所有通用组件抽满
后果：
- 容易进入“设计系统工程”，偏离主线

### 14.4 问题：API 层先写得过度复杂
后果：
- 前后端协议还没稳定，服务层先复杂化

### 14.5 当前建议
始终围绕：
> **扫描源 → 搜索 → 详情 → 标签 → 素材库**
来决定第一批要建哪些文件。

---

## 15. 当前结论

这份前端脚手架初始化建议的核心不是“把目录搭得很漂亮”，而是：

> **先把最关键的页面壳、Feature 壳、共享组件壳、API 壳、状态壳搭起来，让整个前端工程从第一天开始就朝统一工作台而不是零散页面集合发展。**

只要这一点做到，后续无论是你自己写、交给开发者，还是交给代码模型继续展开，整体都会稳得多。

---

## 16. 下一步建议

在这份文档之后，最适合继续推进的方向有两个：
1. **后端脚手架初始化建议 v1**
2. **真正开始生成前端骨架代码**

如果你想继续保持“文档先行、结构先稳”的节奏，我更推荐下一步做：

> **后端脚手架初始化建议 v1**

这样前后端都会有对应的脚手架文档，之后再进入代码实现会更顺。

