# Workbench 深度架构审查

> 2026-05-27 | 审查范围：全栈（Backend / Frontend / Desktop）
> 审查维度：代码质量 · 代码利用率 · 安全风险

---

## 总体概览

| 系统 | 文件数 | 总行数（估） | 测试覆盖 | 严重问题 |
|---|---|---|---|---|
| Backend (Python/FastAPI) | ~176 | ~25,000 | 85 测试文件，集成测试为主 | 2 |
| Frontend (React/TypeScript) | ~186 | ~22,500 | 5 测试文件，30 用例 | 4 |
| Desktop (Electron) | 5 源文件 | ~500 | 0 | 1 |

---

# 第一部分：Backend (Python/FastAPI)

## 1.1 架构概览

```
main.py (FastAPI app factory)
  ├── api/routes/ (13 路由模块)
  │     └── 依赖注入: Session = Depends(get_db)
  ├── services/ (业务逻辑层, ~20 服务)
  │     ├── 模块级单例实例化
  │     └── 自行创建 Repository 实例
  ├── repositories/ (数据访问层, ~12 repository)
  │     └── SQLAlchemy ORM 查询封装
  ├── db/models/ (24 张表的 ORM 模型)
  ├── workers/ (无状态 worker: scanner, metadata, thumbnails)
  └── core/ (配置, 分类, 异常处理)
```

依赖方向: Routes → Services → Repositories → Models ✅ 单向，无循环依赖

## 1.2 模块审查

### core/ — 核心配置与分类

| 文件 | 行数 | 质量 | 利用率 | 安全 |
|---|---|---|---|---|
| `config/settings.py` | 53 | 🟢 良好 — Pydantic Settings, `__file__` 相对路径 | 完全使用 | 无问题 |
| `classification.py` | 191 | 🟢 良好 — 文件分类的唯一真相源，扩展集以 dataclass 组织 | 完全使用 | 无问题 |
| `time.py` | 8 | 🟢 `utcnow()` 提供但被各模块重复定义 | **🟡 利用率低** —10+ 个服务模块重复定义了 `_utcnow()` | 无问题 |
| `errors/exceptions.py` | 22 | 🟢 AppError 层次清晰 | 完全使用 | 无问题 |
| `errors/handlers.py` | 26 | 🟢 统一异常处理 | 完全使用 | 无问题 |

### db/ — 数据库层

| 文件 | 行数 | 质量 | 利用率 | 安全 |
|---|---|---|---|---|
| `session/engine.py` | 490 | 🟡 所有 ALTER TABLE 迁移堆在一个文件 | 完全使用 | **🔴 F-string SQL** — `_table_columns()` 使用 `f"PRAGMA table_info({table_name})"` |
| `session/session.py` | 17 | 🟢 标准 get_db 生成器 | 完全使用 | 无问题 |
| `models/` (14 文件) | ~500 | 🟢 24 张表映射清晰 | 完全使用 | 无问题 |
| `migrations/0001_initial_core.sql` | 329 | 🟢 | — | 无问题 |
| `migrations/0002_library_v2.sql` | 109 | 🟢 | — | 无问题 |

**🔴 严重 — F-string SQL 注入风险 (`engine.py:385`)**
```python
def _table_columns(connection, table_name: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(
        f"PRAGMA table_info({table_name})"  # table_name 直接拼入 SQL
    ).fetchall()}
```
当前所有调用方传入硬编码表名，未实际可被利用。但函数签名本身是注入向量，未来误用风险高。

**🟡 警告 — Repository 方法重复 (`file/repository.py:722`)**
`list_media_files`、`list_book_files`、`list_software_files`、`list_game_files` 四个方法逻辑几乎相同，仅 placement 过滤值不同。应合并为一个参数化方法。

### api/routes/ — API 路由层

| 文件 | 行数 | 质量 | 利用率 | 安全 |
|---|---|---|---|---|
| `system.py` | 27 | 🟢 简单委托 | 完全使用 | `/debug/runtime` 泄露内部路径 — localhost 可接受 |
| `sources.py` | 49 | 🟢 CRUD 模板 | 完全使用 | 🟡 路径验证仅做 `resolve()`，无范围检查 |
| `files.py` | 217 | 🟢 功能完整 | 完全使用 | 无问题 |
| `search.py` | 47 | 🟢 | 完全使用 | 无问题 |
| `tags.py` | 46 | 🟢 | 完全使用 | 无问题 |
| `collections.py` | 64 | 🟢 | 完全使用 | 无问题 |
| `importing.py` | 621 | 🟡 偏大，路由内嵌业务逻辑 | 完全使用 | 🟡 F-string WHERE 子句动态拼接 |
| `library.py` | 173 | 🟢 | 完全使用 | 无问题 |
| `library_objects.py` | 112 | 🟢 | 完全使用 | 无问题 |
| `library_organize.py` | 288 | 🟢 | 完全使用 | 无问题 |
| `library_roots.py` | 146 | 🟢 | 完全使用 | 🟡 `_resolve_path` 无范围限制 |
| `recent.py` | 63 | 🟢 | 完全使用 | 无问题 |
| `tools.py` | 47 | 🟢 | 完全使用 | 无问题 |

**🟡 警告 — 路由层模块级服务单例**
```python
files_service = FilesService()  # 模块导入时即实例化
```
这使测试困难（单例跨请求保持状态），且无法做请求级别的 scoping。

### services/ — 业务逻辑层

| 文件 | 行数 | 质量 | 利用率 | 安全 |
|---|---|---|---|---|
| `library/organize.py` | **3,342** | **🔴 God Module** — 12+ 种操作混在一个类 | 高 | 🟡 直接操作文件系统，`shutil.move/copy2` 无抽象层 |
| `importing/service.py` | **1,790** | 🔴 第二大的 God Module | 高 | 🟡 接受客户端传入的文件路径列表，无范围校验 |
| `thumbnails/service.py` | **951** | 🟡 复杂的线程池+队列状态机 | 高 | 🟡 ffmpeg/ffprobe 子进程调用，路径来自 DB |
| `tools/service.py` | 244 | 🟡 | 高 | 🟡 `video_merge.py` 使用 `shell=True` 风险低但需关注 |
| `collections/service.py` | 206 | 🟢 | 高 | 无问题 |
| `tags/service.py` | 174 | 🟢 | 高 | 无问题 |
| `source_management/service.py` | 155 | 🟢 | 高 | 🟡 `_canonicalize_source_path` 无范围限制 |
| `importing/recovery.py` | 458 | 🟡 偏大 | 中 | 无问题 |
| `importing/object_boundary.py` | 345 | 🟢 复杂规则引擎，合理 | 中 | 无问题 |

**🔴 严重 — `organize.py` God Module (3,342 行)**
包含：候选人扫描、计划生成、冲突检测、预检查、执行、文件操作 (move/copy/replace)、回滚、对账、YAML 合并、模板渲染、建议生成、受管控 compose、修正计划。应拆分为 5-6 个模块。

**🔴 严重 — `importing/service.py` God Module (1,790 行)**
混合了数据类定义、编排逻辑、文件系统操作 (`shutil.copy2`)、repository 访问。高度耦合。

### workers/ — 后台工作器

| 文件 | 行数 | 质量 | 利用率 | 安全 |
|---|---|---|---|---|
| `scanning/scanner.py` | 123 | 🟢 `os.scandir()` 遍历，拒绝符号链接 | 高 | 🟢 安全 |
| `metadata/extractor.py` | 152 | 🟡 broad except 静默吞异常 | 高 | 🟡 ffprobe 子进程调用 |
| `thumbnails/generator.py` | 42 | 🟢 | 中 | 无问题 |
| `thumbnails/video_generator.py` | 154 | 🟢 | 中 | 🟡 ffmpeg 子进程调用 |
| `thumbnails/pdf_generator.py` | 97 | 🟢 | 中 | 无问题 |
| `thumbnails/exe_icon_generator.py` | 292 | 🟢 ctypes Win32 API，实现干净 | 低 (仅 Windows) | 🟢 ctypes 调用受控 |

## 1.3 后端汇总

| 严重度 | 数量 | 关键项 |
|---|---|---|
| 🔴 严重 | 2 | `organize.py` (3,342行 God Module)、F-string SQL 注入向量 |
| 🟡 警告 | 8 | `importing/service.py` God Module、Repository 方法重复、`_utcnow()` 10x 重复、broad except 吞异常、路径验证不完整、模块级单例、CORS `null` origin、`__import__()` 动态导入 |
| 🟢 建议 | 5 | 颜色标签验证重复、硬编码目录名、无认证（本地应用可接受）、无 HTTPS（localhost 可接受）、子进程路径无消毒 |

---

# 第二部分：Frontend (React/TypeScript)

## 2.1 架构概览

```
pages/ (15 页面组件, 4 个 lazy-loaded)
  └── features/ (19 功能模块)
        ├── services/api/ (20+ API 客户端)
        ├── services/query/ (React Query key + invalidation)
        └── services/desktop/ (Electron bridge)
              └── shared/ui/  shared/text/  shared/theme/  shared/hooks/
                    └── entities/ (12 实体类型定义)
                          └── locales/ (en + zh-CN, 8 模块)
```

状态管理: 单一 Zustand store (UI 状态) + React Query (服务端状态)

## 2.2 模块审查

### features/ — 核心功能模块

| 文件 | 行数 | 质量 | 利用率 | 安全 |
|---|---|---|---|---|
| `collections/CollectionsFeature.tsx` | **889** | **🔴 超大** — 表单状态 + 突变 + 分页 + 列表 + 兼容计算 | 高 | 🟢 |
| `games/GamesFeature.tsx` | **865** | **🔴 超大** — 被 browse-v2 重定向替代 | **🟡 遗留代码** | 🟢 |
| `media-library/MediaLibraryFeature.tsx` | **801** | 🔴 超大 — 被 browse-v2 替代 | **🟡 遗留代码** | 🟢 |
| `library/LibraryInboxPanel.tsx` | **770** | 🔴 超大 | 高 | 🟢 |
| `software/SoftwareFeature.tsx` | **720** | 🔴 超大 — 被 browse-v2 替代 | **🟡 遗留代码** | 🟢 |
| `books/BooksFeature.tsx` | **667** | 🔴 超大 — 被 browse-v2 替代 | **🟡 遗留代码** | 🟢 |
| `details-panel/DetailsPanelFeature.tsx` | **660** | 🔴 超大 — 5 种上下文的 JSX 三元嵌套 200+ 行 | 高 | 🟢 |
| `browse-v2/BrowseV2Feature.tsx` | **633** | 🔴 超大 — 管理 4 个 modal + 筛选 + 分页 + 选择 | 高 | 🟡 `any` 类型转换 |
| `tools/ToolsFeature.tsx` | **568** | 🔴 超大 | 中 | 🟢 |
| `search/SearchFeature.tsx` | 430 | 🟡 偏大 | 高 | 🟢 |
| `recent-imports/RecentImportsFeature.tsx` | 404 | 🟡 偏大 | 高 | 🟢 |

**🔴 严重 — 13 个组件超过 400 行，6 个超过 600 行。最大的 `CollectionsFeature.tsx` (889 行) 应拆分为 3-4 个子组件。**

**🟡 警告 — 遗留代码：`books`、`games`、`software`、`media-library` 四个 feature 已被 browse-v2 重定向替代，但仍保留完整代码 (~3,000+ 行)。这些应归档或删除。**

### services/api/ — API 客户端层

| 问题 | 严重度 | 详情 |
|---|---|---|
| `getApiBaseUrl()` 重复 20+ 次 | 🟡 | 每个 API 文件都定义了自己的 `getApiBaseUrl()` |
| `parseResponse()` 有 3+ 个变体 | 🟡 | `error.message` vs `detail` 检查不一致 |
| `useExecutePlan` 不清理 interval | **🔴** | 组件卸载后 `setInterval` 继续执行，内存泄漏 + 状态更新到已卸载组件 |

### shared/ — 共享层

| 文件 | 行数 | 质量 | 利用率 | 安全 |
|---|---|---|---|---|
| `ui/thumbnail.tsx` | 417 | 🟡 偏大 | 高 | 🟢 |
| `text/runtime.ts` | — | 🟢 `t(key, params?)` 模式干净 | 高 | 🟢 |
| `theme/index.tsx` | — | 🟢 Light/Dark 主题 | 高 | 🟢 |

### 重复代码热力图

| 模式 | 重复次数 | 影响 |
|---|---|---|
| `getApiBaseUrl()` | ~20 文件 | 抽取为 `services/api/client.ts` 即可消除 |
| `formatBytes()` | 6 文件 | 移到 `shared/utils.ts` |
| 排序/分页下拉框 | 6 个 feature | 创建 `useSortablePage` hook |
| 空/加载/错误三态渲染 | 每个 feature | 统一 `LoadingState` + `EmptyState` 组件（已有部分） |
| "跳转到 browse" 导航模式 | 3 个 feature | 抽取为 `useBrowseNavigation` hook |

### 测试覆盖

| 测试文件 | 用例数 | 覆盖范围 |
|---|---|---|
| `components.test.tsx` | 11 | ActionButton, AppSidebar, ThemeProvider |
| `i18n-coverage.test.ts` | 7 | en/zh-CN locale key parity |
| `lazy-pages.test.ts` | 4 | Lazy page default exports |
| `browse-taxonomy.test.ts` | 6 | Domain/category constants |
| **总计** | **30** | 仅基础组件和常量 |

**🔴 严重 — 零覆盖区域：** 所有 19 个 feature 模块、所有 API 客户端、所有自定义 hooks（`usePolling`、`useExecutePlan`、`useThumbnailWarmup` 等）、Zustand store、文本运行时。

### 安全审查

| 项目 | 状态 |
|---|---|
| `dangerouslySetInnerHTML` | 🟢 未发现使用 |
| XSS via 用户输入 | 🟢 所有数据渲染为 JSX 文本内容 |
| localStorage 敏感数据 | 🟢 仅存储 locale/theme/viewMode 偏好 |
| API keys 泄露 | 🟢 无硬编码密钥 |
| Open redirect | 🟢 导航始终使用硬编码路径 |
| Error boundaries | **🔴 零个 error boundary** — 任何未捕获错误导致整页崩溃 |
| `any` 类型使用 | 🟡 `BrowseV2Feature` 中 `card: any` 类型转换 |

## 2.3 前端汇总

| 严重度 | 数量 | 关键项 |
|---|---|---|
| 🔴 严重 | 4 | 13 个超大组件、零 error boundary、`useExecutePlan` interval 泄漏、零 feature/hook/API 测试覆盖 |
| 🟡 警告 | 7 | 遗留 feature 代码 ~3,000 行、`getApiBaseUrl()` 20x 重复、`parseResponse()` 3 变体、`formatBytes()` 6x 重复、排序/分页模式重复、`any` 类型转换、`useEffect` 副作用管理 |
| 🟢 建议 | 3 | 统一三态渲染、抽取浏览导航 hook、移除废弃路由 |

---

# 第三部分：Desktop (Electron)

## 3.1 架构概览

```
electron/main.ts (BrowserWindow + 后端进程管理)
  └── electron/preload.ts (contextBridge API)
        └── window.assetWorkbench (暴露给 renderer 的 API)
              ├── selectFolder / selectFiles (IPC → 原生对话框)
              ├── minimizeWindow / toggleMaximizeWindow / closeWindow
              ├── openFile / openContainingFolder (shell.openPath)
              ├── getBackendBaseUrl / getWindowState
              └── onWindowStateChanged (main → renderer 事件)
```

## 3.2 安全审查

| 设置 | 值 | 评估 |
|---|---|---|
| `nodeIntegration` | `false` | 🟢 正确 |
| `contextIsolation` | `true` | 🟢 正确 |
| `sandbox` | **`false`** | **🔴 预加载脚本拥有完整 Node.js 权限** |
| `webSecurity` | 默认 `true` | 🟢 正确 |
| Content-Security-Policy | **未配置** | 🟡 缺少纵深防御 |
| `shell.openPath` | 通过 preload 暴露 | 🟡 有路径验证，但依赖 preload/renderer 边界完整 |

**🔴 严重 — `sandbox: false`**
预加载脚本 (`preload.ts`) 拥有完整 Node.js 权限（`node:fs`、`node:path`）。代码注释说明需要 `fs` 来实现 `openContainingFolder`。如果 renderer 进程被攻破，攻击者可通过 contextBridge API 间接访问 Node.js API。攻击面受限于显式的 `contextBridge` 暴露方法，但仍是一个重大风险。建议：将 `openContainingFolder` 的 fs 操作移到 main process 通过 IPC 执行，然后开启 sandbox。

## 3.3 代码质量

| 文件 | 质量 | 详情 |
|---|---|---|
| `main.ts` | 🟢 良好 | 后端生命周期管理（启动/健康检查/优雅关闭/强制 kill）实现干净 |
| `preload.ts` | 🟢 良好 | 结构化错误返回 `{ ok, reason }`，路径验证分层 |
| `scripts/build-backend.ps1` | 🟢 | PyInstaller 构建脚本 |
| `scripts/prepare-ffmpeg-resource.mjs` | 🟢 | FFmpeg 二进制复制 |

**缺失项：**
- 🟡 无 `uncaughtException` / `unhandledRejection` 处理器
- 🟡 无 electron-builder 代码签名配置
- 🔴 零测试（桌面 shell 完全无测试覆盖）

## 3.4 桌面端汇总

| 严重度 | 数量 | 关键项 |
|---|---|---|
| 🔴 严重 | 1 | `sandbox: false` — 预加载脚本拥有完整 Node.js 权限 |
| 🟡 警告 | 3 | 无 CSP 头、无崩溃处理器、无代码签名配置 |
| 🟢 建议 | 2 | 无 macOS/Linux 支持（仅 Windows/NSIS）、零测试 |

---

# 第四部分：跨层问题

## 4.1 全局测试赤字

| 层 | 测试文件 | 测试用例 | 关键空白 |
|---|---|---|---|
| Backend | 85 | ~500+ | 60% 模块缺少单元测试（worker、repository、缩略图服务等） |
| Frontend | 5 | 30 | 所有 feature、hook、API 客户端零覆盖 |
| Desktop | 0 | 0 | 完全无测试 |

## 4.2 重复与死代码

| 类型 | 位置 | 行数估算 |
|---|---|---|
| 遗留 feature 代码 | Frontend: books/games/software/media-library | ~3,000 |
| `getApiBaseUrl()` 重复 | Frontend: 20+ API 文件 | ~100 |
| `_utcnow()` 重复 | Backend: 10+ 服务文件 | ~30 |
| `formatBytes()` 重复 | Frontend: 6 文件 | ~30 |
| Repository 方法重复 | Backend: FileRepository 4 个方法 | ~100 |
| 排序/分页 UI 重复 | Frontend: 6 个 feature | ~200 |

**估算可消除的冗余代码：~3,500 行**

## 4.3 安全风险矩阵

| 风险 | 层 | 严重度 | 可被利用 |
|---|---|---|---|
| F-string SQL 注入向量 | Backend | 🔴 | 否（当前调用方安全） |
| `sandbox: false` | Desktop | 🔴 | 是（需先攻破 renderer） |
| 无 error boundary | Frontend | 🔴 | 是（任何渲染异常可导致崩溃） |
| 路径遍历（来源/根路径验证） | Backend | 🟡 | 潜在（需已认证的 API 调用） |
| 子进程路径注入 | Backend | 🟡 | 潜在（需恶意文件名存在于磁盘） |
| 无 CSP 头 | Desktop | 🟡 | 理论（仅加载本地内容） |
| 无认证 | Backend | 🟢 | 否（绑定 127.0.0.1） |

---

# 第五部分：优先级修复路线

## 立即修复 (P0)

| # | 问题 | 层 | 工作估量 |
|---|---|---|---|
| 1 | `sandbox: false` — 将 fs 操作移至 main process IPC | Desktop | 2h |
| 2 | `_table_columns()` F-string SQL 改为参数化查询 | Backend | 15min |
| 3 | 添加 `<ErrorBoundary>` 到 AppProviders | Frontend | 30min |
| 4 | `useExecutePlan` interval 清理 | Frontend | 15min |

## 短期改进 (P1)

| # | 问题 | 层 | 工作估量 |
|---|---|---|---|
| 5 | 拆分 `organize.py` (3,342 行 → 5 模块) | Backend | 4h |
| 6 | 抽取 `getApiBaseUrl()` + `parseResponse()` 到共享客户端 | Frontend | 1h |
| 7 | 移除遗留 books/games/software/media-library feature | Frontend | 1h |
| 8 | 添加 CSP 头 | Desktop | 30min |
| 9 | 添加 `uncaughtException` 处理器 | Desktop | 30min |
| 10 | 创建 `formatBytes()` 共享工具函数 | Frontend | 15min |

## 中期优化 (P2)

| # | 问题 | 层 | 工作估量 |
|---|---|---|---|
| 11 | 拆分超大组件 (Collections/BrowseV2/DetailsPanel 等) | Frontend | 8h |
| 12 | 创建 `useSortablePage` 共享 hook | Frontend | 2h |
| 13 | 统一 `_utcnow()` 导入 | Backend | 30min |
| 14 | 参数化 `FileRepository` 重复方法 | Backend | 1h |
| 15 | 添加 electron-builder 代码签名 | Desktop | 2h |
| 16 | 编写 feature 层关键测试 | Frontend | 4h |
| 17 | 编写 worker/repository 单元测试 | Backend | 4h |
