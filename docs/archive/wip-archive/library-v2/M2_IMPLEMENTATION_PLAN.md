# M2-A Revised — File Library Sidebar Replacement and Browse Preset Routing

> 状态：实现计划（等待用户确认后执行）  
> 基于：2026-05-22 Agents Team 评审 + 用户 5 点决策确认

---

## 核心变更概览

| # | 变更 | 文件 | 类型 |
|---|------|------|------|
| 1 | 左侧导航重构为文件库中心导航 | `AppSidebar.tsx` | 组件重构 |
| 2 | 提取 Browse 分类常量到共享模块 | `shared/browse-taxonomy.ts`（新） | 代码提取 |
| 3 | BrowseV2Feature 读取 URL 参数 | `BrowseV2Feature.tsx` | 状态管理变更 |
| 4 | 旧路由重定向到 Browse preset | `AppRouter.tsx` | 路由变更 |
| 5 | Library 增加 Sources tab | `LibraryFeature.tsx` | 组件变更 |
| 6 | Browse 页面移除内部分类面板 | `BrowseV2Feature.tsx` | 组件变更 |
| 7 | Library Overview 引导卡片 | `LibraryOverviewPanel.tsx` | 组件变更 |
| 8 | i18n 全面更新 | 8 个 locale 文件 | 文案变更 |

---

## 变更 1：提取 Browse 分类常量

### 问题
`CATEGORY_TREE`、`DOMAINS`、`DomainValue` 等类型当前定义在 `BrowseV2Feature.tsx` 内部。AppSidebar 需要引用同一份分类数据来构建导航。

### 方案
创建 `apps/frontend/src/shared/browse-taxonomy.ts`，从 BrowseV2Feature.tsx 提取：

```ts
// 提取的内容（从 BrowseV2Feature.tsx 第 18-69 行移出）：
export const DOMAINS = [...] as const;
export type DomainValue = (typeof DOMAINS)[number]["value"];
export type CategoryItem = { value: string; labelKey: string };
export type CategoryGroup = { groupKey?: string; items: CategoryItem[] };
export const CATEGORY_TREE: Record<DomainValue, CategoryGroup[]> = {...};
```

BrowseV2Feature.tsx 改为从共享模块导入这些常量。

### 不改
- DOMAINS 和 CATEGORY_TREE 的值完全不变
- 不添加、不删除任何 domain 或 category
- 不影响 API 调用逻辑

### 文件
- **新建**：`apps/frontend/src/shared/browse-taxonomy.ts`
- **修改**：`apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`（移除本地定义，添加 import）

---

## 变更 2：BrowseV2Feature 读取 URL 参数

### 问题
当前 `domain` 和 `category` 是 `useState`（第 172-173 行），不受 URL 参数控制。侧边栏分类链接（`/browse-v2?domain=media&category=movie`）无法驱动页面内容。

### 方案
将 `domain` 和 `category` 从 `useState` 改为从 URL search params 读取。

```tsx
// Before (lines 172-173):
const [domain, setDomain] = useState<DomainValue>("media");
const [category, setCategory] = useState("");

// After:
import { useSearchParams } from "react-router-dom";

const [searchParams, setSearchParams] = useSearchParams();
const domain = (searchParams.get("domain") as DomainValue) || "media";
const category = searchParams.get("category") || "";
```

`setScope` 函数改为通过 `setSearchParams` 更新 URL：

```tsx
// Before (lines 284-288):
function setScope(nextDomain: DomainValue, nextCategory = "") {
  setDomain(nextDomain);
  setCategory(nextCategory);
  setPage(1);
}

// After:
function setScope(nextDomain: DomainValue, nextCategory = "") {
  setSearchParams(prev => {
    const next = new URLSearchParams(prev);
    next.set("domain", nextDomain);
    if (nextCategory) {
      next.set("category", nextCategory);
    } else {
      next.delete("category");
    }
    return next;
  }, { replace: true });
  setPage(1);
}
```

`storageState` 和 `cardKind` 也改为可选 URL 参数（保持一致）：

```tsx
const storageState = searchParams.get("storage") || "all";
const cardKind = searchParams.get("kind") || "all";
```

### 影响
- 页面 URL 变为用户可分享的永久链接（如 `/browse-v2?domain=media&category=movie`）
- 浏览器前进/后退按钮正常工作
- 侧边栏 NavLink 可以直接链接到带参数的 URL

### 不改
- `listBrowseCards()` API 调用不变
- 分页、排序等参数保持 `useState`（不放入 URL）
- 不修改 API 签名

### 文件
- **修改**：`apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`

---

## 变更 3：左侧导航重构

### 问题
`AppSidebar.tsx` 当前是 4 组平坦导航项，不支持展开/折叠子分类。

### 方案
重构 `AppSidebar.tsx`，支持：

1. **可展开分类导航**：`NavItem` 扩展为支持 `children?: NavSubItem[]`
2. **媒体 9 子分类默认折叠**：当前激活时才展开
3. **Search 放入"再找回"分组**
4. **新增"文件库"管理分组**

#### 新 navGroups 结构

```tsx
type NavSubItem = {
  to: string;
  labelKey: Parameters<typeof t>[0];
};

type NavItem = {
  to?: string;
  labelKey: Parameters<typeof t>[0];
  icon: NavigationIconName;
  children?: NavSubItem[];
  defaultExpanded?: boolean;
};

const navGroups: Array<{
  labelKey: Parameters<typeof t>[0];
  items: NavItem[];
}> = [
  // ── 顶层：Home ──
  {
    labelKey: "shell.sidebar.groups.main",
    items: [
      { to: "/home", labelKey: "navigation.items.home", icon: "home" },
    ],
  },
  // ── 文件库 — 浏览分类 ──
  {
    labelKey: "shell.sidebar.groups.fileLibrary",  // "文件库"
    items: [
      { to: "/library?tab=overview", labelKey: "navigation.items.fileLibOverview", icon: "dashboard" },
      { to: "/browse-v2", labelKey: "navigation.items.browseAll", icon: "media" },
      // 分类导航
      {
        labelKey: "navigation.items.browseMedia",     // "媒体"
        icon: "media",
        defaultExpanded: false,
        children: [
          { to: "/browse-v2?domain=media", labelKey: "features.browseV2.categories.all" },
          { to: "/browse-v2?domain=media&category=movie", labelKey: "features.browseV2.categories.movie" },
          { to: "/browse-v2?domain=media&category=series_anime", labelKey: "features.browseV2.categories.series_anime" },
          { to: "/browse-v2?domain=media&category=course", labelKey: "features.browseV2.categories.course" },
          { to: "/browse-v2?domain=media&category=video_collection", labelKey: "features.browseV2.categories.video_collection" },
          { to: "/browse-v2?domain=media&category=video_clip", labelKey: "features.browseV2.categories.video_clip" },
          { to: "/browse-v2?domain=media&category=image_album", labelKey: "features.browseV2.categories.image_album" },
          { to: "/browse-v2?domain=media&category=comic", labelKey: "features.browseV2.categories.comic" },
          { to: "/browse-v2?domain=media&category=audio", labelKey: "features.browseV2.categories.audio" },
        ],
      },
      { to: "/browse-v2?domain=documents", labelKey: "navigation.items.browseDocuments", icon: "books" },
      { to: "/browse-v2?domain=apps", labelKey: "navigation.items.browseApps", icon: "software" },
      { to: "/browse-v2?domain=assets", labelKey: "navigation.items.browseAssets", icon: "collections" },
    ],
  },
  // ── 文件库 — 管理 ──
  {
    labelKey: "shell.sidebar.groups.manage",
    items: [
      { to: "/library?tab=sources", labelKey: "navigation.items.scanFolders", icon: "search" },
      { to: "/library?tab=roots", labelKey: "navigation.items.managedRoots", icon: "settings" },
      { to: "/library?tab=inbox", labelKey: "navigation.items.inbox", icon: "recent" },
      { to: "/library?tab=plans", labelKey: "navigation.items.plans", icon: "collections" },
    ],
  },
  // ── 再找回 ──
  {
    labelKey: "shell.sidebar.groups.refind",
    items: [
      { to: "/search", labelKey: "navigation.items.search", icon: "search" },
      { to: "/recent", labelKey: "navigation.items.recent", icon: "recent" },
      { to: "/tags", labelKey: "navigation.items.tags", icon: "tags" },
      { to: "/collections", labelKey: "navigation.items.collections", icon: "collections" },
    ],
  },
  // ── 系统 ──
  {
    labelKey: "shell.sidebar.groups.system",
    items: [
      { to: "/tools", labelKey: "navigation.items.tools", icon: "tools" },
      { to: "/settings", labelKey: "navigation.items.settings", icon: "settings" },
    ],
  },
];
```

#### 展开/折叠行为

- `NavItem` with `children` 渲染一个可点击的父行 + 子项列表
- `defaultExpanded: false` 表示默认折叠
- **自动展开**：如果当前 URL 匹配任一子项的 `to`，父行自动展开
- 手动点击父行切换展开/折叠
- 侧边栏折叠为图标模式时，子项不显示

#### 渲染逻辑（伪代码）

```tsx
function NavGroupWithChildren({ item }: { item: NavItem }) {
  const [expanded, setExpanded] = useState(
    item.defaultExpanded ?? false
  );
  const location = useLocation();

  // Auto-expand when a child is active
  const isChildActive = item.children?.some(
    child => location.pathname + location.search === child.to
  );
  const isOpen = expanded || isChildActive;

  return (
    <>
      <button onClick={() => setExpanded(!isOpen)}>
        <SidebarIcon name={item.icon} />
        <span>{t(item.labelKey)}</span>
        <ChevronIcon direction={isOpen ? "down" : "right"} />
      </button>
      {isOpen && item.children?.map(child => (
        <NavLink to={child.to} key={child.to}>
          {t(child.labelKey)}
        </NavLink>
      ))}
    </>
  );
}
```

### 不改
- 侧边栏折叠机制不变（`useUIStore.isSidebarCollapsed`）
- 品牌区域不变
- 页脚不变
- 不引入第三方手风琴组件

### 文件
- **修改**：`apps/frontend/src/app/shell/AppShell.tsx`（仅改组件）
- **修改**：`apps/frontend/src/app/shell/AppSidebar.tsx`（主要改动）

---

## 变更 4：旧路由重定向

### 旧 → 新映射

| 旧路由 | 新路由 | BrowseV2 参数 |
|--------|--------|-------------|
| `/library/media` | `/browse-v2` | `?domain=media` |
| `/books` | `/browse-v2` | `?domain=documents` |
| `/library/games` | `/browse-v2` | `?domain=apps&category=game` |
| `/software` | `/browse-v2` | `?domain=apps&category=software` |

### 实现

在 `AppRouter.tsx` 中将旧路由的 `element` 从 Page 组件改为 `Navigate`：

```tsx
// Before:
<Route path="/books" element={<BooksPage />} />
<Route path="/library/media" element={<MediaLibraryPage />} />

// After:
<Route path="/books" element={<Navigate to="/browse-v2?domain=documents" replace />} />
<Route path="/library/media" element={<Navigate to="/browse-v2?domain=media" replace />} />
<Route path="/library/games" element={<Navigate to="/browse-v2?domain=apps&category=game" replace />} />
<Route path="/software" element={<Navigate to="/browse-v2?domain=apps&category=software" replace />} />
```

### 保留
- `BooksPage`、`MediaLibraryPage`、`GamesPage`、`SoftwarePage` 组件代码保留在源码中
- `BooksFeature`、`MediaLibraryFeature`、`GamesFeature`、`SoftwareFeature` 组件代码保留
- 如果未来需要恢复独立页面，只需还原 route element
- 侧边栏不再有指向这些旧路由的链接

### 文件
- **修改**：`apps/frontend/src/app/router/index.tsx`

---

## 变更 5：Library 增加 Sources tab

### 方案
在 `LibraryFeature.tsx` 的 `libraryTabs` 数组中新增 `sources` tab，渲染已有的 `SourceManagementFeature` 组件。

```tsx
// 新增 tab 值：
const libraryTabs = [
  { value: "overview", ... },
  { value: "sources", labelKey: "features.library.tabs.sources" },  // NEW
  { value: "roots", ... },
  { value: "inbox", ... },
  { value: "plans", ... },
  { value: "path", ... },
  { value: "pending", ... },
  { value: "objects", ... },
];

// 条件渲染（第 86-93 行区域）：
{activeTab === "sources" ? <SourceManagementFeature /> : null}
```

### 不动的 tab
- `roots`（受管库）、`inbox`（导入）、`plans`（计划）、`overview`（总览）完全不动
- `path`、`pending`、`objects` 保留但视觉权重降低

### Settings 中的 Source Management
- 保留 `SourceManagementFeature` 在 Settings 页面中
- 添加一行说明文字："扫描文件夹管理也可以在文件库 > 扫描文件夹中找到"
- 不删除 Settings 中的入口

### 文件
- **修改**：`apps/frontend/src/features/library/LibraryFeature.tsx`
- **修改**：`apps/frontend/src/pages/settings/SettingsPage.tsx`（可选 — 加说明文字）

---

## 变更 6：Browse 页面移除内部分类面板

### 移除范围
删除 `BrowseV2Feature.tsx` 第 397-440 行的 `<nav className="browse-v2-taxonomy">` 元素。

即删除：
```tsx
<nav className="browse-v2-taxonomy" aria-label={...}>
  {DOMAINS.map(...)}  // 整个 domain 按钮 + category tree
</nav>
```

### 保留
- filter bar（存储状态、卡片类型、排序）
- 内容区（卡片网格 + 详情面板）
- 面包屑：添加当前分类路径显示

### 面包屑实现

```tsx
// 在 filter bar 上方添加：
<div className="browse-v2-breadcrumb">
  <span>{t("navigation.items.fileLibrary")}</span>
  <span> › </span>
  <span>{t(DOMAINS.find(d => d.value === domain)?.labelKey)}</span>
  {category ? (
    <>
      <span> › </span>
      <span>{getCategoryLabel(domain, category)}</span>
    </>
  ) : null}
</div>
```

### 文件
- **修改**：`apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`

---

## 变更 7：Library Overview 引导卡片

### 方案
重写 `LibraryOverviewPanel.tsx` 的 placeholder 区域为"从这里开始"引导卡片。

```tsx
function StartHereCards() {
  return (
    <div className="library-start-here">
      <div className="library-start-card" onClick={() => navigate("/library?tab=sources")}>
        <span className="library-start-card__icon">📂</span>
        <strong>{t("features.library.overview.scanCardTitle")}</strong>
        <p>{t("features.library.overview.scanCardDesc")}</p>
        <span className="library-start-card__action">{t("features.library.overview.scanCardAction")}</span>
      </div>
      <div className="library-start-card" onClick={() => navigate("/library?tab=roots")}>
        <span className="library-start-card__icon">📁</span>
        <strong>{t("features.library.overview.rootsCardTitle")}</strong>
        <p>{t("features.library.overview.rootsCardDesc")}</p>
        <span className="library-start-card__action">{t("features.library.overview.rootsCardAction")}</span>
      </div>
      <div className="library-start-card" onClick={() => navigate("/library?tab=inbox")}>
        <span className="library-start-card__icon">📥</span>
        <strong>{t("features.library.overview.importCardTitle")}</strong>
        <p>{t("features.library.overview.importCardDesc")}</p>
        <span className="library-start-card__action">{t("features.library.overview.importCardAction")}</span>
      </div>
      <div className="library-start-card" onClick={() => navigate("/browse-v2")}>
        <span className="library-start-card__icon">🔍</span>
        <strong>{t("features.library.overview.browseCardTitle")}</strong>
        <p>{t("features.library.overview.browseCardDesc")}</p>
        <span className="library-start-card__action">{t("features.library.overview.browseCardAction")}</span>
      </div>
      <div className="library-start-card" onClick={() => navigate("/library?tab=plans")}>
        <span className="library-start-card__icon">📋</span>
        <strong>{t("features.library.overview.plansCardTitle")}</strong>
        <p>{t("features.library.overview.plansCardDesc")}</p>
        <span className="library-start-card__action">{t("features.library.overview.plansCardAction")}</span>
      </div>
    </div>
  );
}
```

### 保留
- 对象扫描统计（`ScanObjectsButton`）
- 存储摘要（`StorageSummarySection`）
- organizer stats（来自 `getOrganizeStats`）

### 文件
- **修改**：`apps/frontend/src/features/library/LibraryOverviewPanel.tsx`

---

## 变更 8：i18n 全面更新

### 需新增/修改的 i18n keys

#### `locales/en/navigation.ts` — 新增
```ts
fileLibOverview: "Overview",
browseAll: "Browse All",
browseMedia: "Media",
browseDocuments: "Documents",
browseApps: "Applications",
browseAssets: "Asset Packs",
scanFolders: "Scan Folders",
managedRoots: "Managed Roots",
inbox: "Inbox",
plans: "Plans",
fileLibrary: "File Library",
```

#### `locales/zh-CN/navigation.ts` — 新增
```ts
fileLibOverview: "总览",
browseAll: "浏览全部",
browseMedia: "媒体",
browseDocuments: "文档",
browseApps: "应用",
browseAssets: "素材",
scanFolders: "扫描文件夹",
managedRoots: "受管库",
inbox: "导入暂存",
plans: "待执行计划",
fileLibrary: "文件库",
```

#### `locales/en/shell.ts` — 修改分组标签
```ts
sidebar: {
  groups: {
    main: "Workbench",
    fileLibrary: "File Library",
    manage: "Manage",
    refind: "Refind",
    system: "System",
  }
}
```

#### `locales/zh-CN/shell.ts` — 修改分组标签
```ts
sidebar: {
  groups: {
    main: "资产工作台",
    fileLibrary: "文件库",
    manage: "管理",
    refind: "再找回",
    system: "系统",
  }
}
```

#### `locales/en/features.ts` — 修改 library.overview
新增 start-here 卡片文案（scanCardTitle, rootsCardTitle, importCardTitle, browseCardTitle, plansCardTitle 及对应 description 和 action）。

#### `locales/zh-CN/features.ts` — 对应中文

#### `locales/en/pages.ts` — 更新 Library / Browse 描述

#### `locales/zh-CN/pages.ts` — 对应中文

### 文件
- **修改**：`locales/en/navigation.ts`、`locales/zh-CN/navigation.ts`
- **修改**：`locales/en/shell.ts`、`locales/zh-CN/shell.ts`
- **修改**：`locales/en/features.ts`、`locales/zh-CN/features.ts`
- **修改**：`locales/en/pages.ts`、`locales/zh-CN/pages.ts`

---

## 执行顺序

| 步骤 | 变更 | 依赖 | 风险 |
|------|------|------|------|
| **Step 1** | 提取 `shared/browse-taxonomy.ts` | 无 | 低 |
| **Step 2** | BrowseV2Feature URL 参数化 | Step 1 | 中 |
| **Step 3** | AppSidebar 重构（新 navGroups + 展开子导航） | Step 1, 2 | 中 |
| **Step 4** | 旧路由重定向 | 无 | 低 |
| **Step 5** | Library Sources tab | 无 | 低 |
| **Step 6** | Browse 内部分类面板移除 + 面包屑 | Step 2, 3 | 中 |
| **Step 7** | Library Overview 引导卡片 | 无 | 低 |
| **Step 8** | i18n 全面更新 | Step 3, 5, 6, 7 | 低 |
| **Step 9** | `npm run build` 验证 | 全部 | — |

### 可并行的步骤组
- Step 1 + Step 4 + Step 5 + Step 7 可并行（互不依赖）
- Step 2 必须在 Step 1 之后
- Step 3 必须在 Step 1-2 之后（需要 taxonomy 常量和 URL 参数路由）
- Step 6 必须在 Step 2-3 之后
- Step 8 可在 Step 3/5/6/7 各自完成后增量添加

---

## 不变项清单

- ❌ 不修改后端 API
- ❌ 不修改数据库 schema
- ❌ 不修改 `listBrowseCards()` / `getBrowseObjectDetail()` 逻辑
- ❌ 不修改 `Source` 和 `ManagedRoot` 数据模型
- ❌ 不给 Managed Root 添加扫描
- ❌ 不删除任何旧路由（仅重定向）
- ❌ 不删除旧 Feature/Page 组件
- ❌ 不修改 OrganizePlan / Amendment / Compose 语义
- ❌ 不实现 delete / source cleanup
- ❌ 不实现 AI 功能

---

## 风险矩阵

| 风险 | 级别 | 规避 |
|------|------|------|
| URL 参数化破坏 BrowseV2Feature 内部状态流 | 中 | Step 2 优先做，充分测试 domain/category/storageState/cardKind 联动 |
| 侧边栏展开/折叠逻辑 bug | 中 | 保持简单：仅一层嵌套，不递归 |
| 媒体 9 子分类使侧边栏过长 | 低 | 默认折叠；仅在激活媒体域时展开 |
| 旧路由重定向产生循环 | 低 | 单向重定向（旧 → 新），不反向 |
| i18n key 遗漏 | 低 | npm run build 会暴露未定义 key（TypeScript 类型安全） |

---

## 验证方式

1. `npm run build` — 零错误
2. 手动点击侧边栏每个链接 — 跳转到正确页面/参数
3. 媒体子分类默认折叠 — 点击媒体展开，URL 变为 `/browse-v2?domain=media`
4. 点击"电影/长视频" — URL 变为 `/browse-v2?domain=media&category=movie`，页面显示正确内容
5. 直接访问 `/books` — 重定向到 `/browse-v2?domain=documents`
6. Library > Sources tab — 显示 SourceManagementFeature，可添加/扫描源
7. 侧边栏折叠模式 — 图标模式正常显示
8. Browse 页面 — 内部分类面板已移除，面包屑正确显示
