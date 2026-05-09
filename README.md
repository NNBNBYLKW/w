# Workbench

Windows local-first asset management workbench built around indexed files, shared details, and lightweight organization flows.

当前仓库已经进入**测试版阶段**。README 的目标不是替代正式文档，而是让第一次进入仓库的人先快速搞清楚 4 件事：

- 这个项目是什么
- 它已经做到哪一步
- 当前能做什么、不能做什么
- 应该怎么启动、接下来先看哪些文档

当前最核心的产品主链仍然是：

`find -> inspect -> tag -> refind -> browse`

## 项目简介

Workbench 是一个建立在 **Windows 本地文件系统** 之上的 local-first 资产工作台。

它不是试图替代真实文件系统，而是在真实文件之上补一层**索引、详情、组织和再找回**能力，让本地资产更容易被浏览、轻量整理和重新找到。当前产品的核心形态是：

- `Search` / `Files` 作为通用 indexed-files surface
- `Media` / `Documents` / `Games` / `Software` 作为受控 subset surfaces
- `Recent` / `Tags` / `Collections` 作为组织与再找回 surfaces
- `DetailsPanelFeature` 作为统一详情中心

它主要解决的是这样一类问题：本地文件很多，但仅靠文件夹结构和文件名，不足以支撑“找到 -> 看清楚 -> 标记 -> 以后再找回来”的日常工作流。

## 当前阶段

项目当前处于**测试版阶段**，并且已经完成了当前测试版主线的能力收口：

- `Media` 媒体库
- `Games` 游戏库
- `Documents` 文档库
- `Software` 软件库
- 组织层与库体验补齐
- 测试版范围冻结
- 测试版体验统一
- API 文档收口
- 文档体系整理

这意味着当前重点已经不是继续横向扩功能，而是：

- 做测试版验证
- 观察真实使用问题
- 做问题分级与收敛
- 继续做稳定性、性能和正式发布前的收口

最近几轮前端工作的重点也属于这个阶段目标的一部分：主要是在统一三栏工作台、导航与 details 的控制样式、状态提示与滚动体验，而不是继续新增产品能力线。

当前前端工程层面还已经补上两项服务于测试版验证准备的基础能力：

- 高可见 UI 文案已抽离为独立文本资源
- 当前已经具备轻量中英文切换与 `Light / Dark` 主题切换能力，并在 `Settings` 中提供入口

这些工作属于体验统一、协作维护和外部验证准备的一部分，不代表项目进入了新的功能扩张阶段。

## 项目不是什么

为了避免误解，当前项目**不是**：

- 通用文件管理器或 Windows Explorer 替代品
- 游戏平台、游戏启动器或平台账号聚合器
- 电子书阅读器或阅读平台
- 软件安装管理器、卸载中心或包管理器
- AI 中台、自动标签平台、推荐系统或自动规则系统
- 复杂统一对象中台驱动的多产品平台

## 当前已完成能力

### 垂类库

- `Media`
  - 面向图片 / 视频的浏览与最小筛选
  - 图片与视频缩略图使用统一 thumbnail 语义；一体化桌面包随包携带 `ffmpeg`，开发模式仍可回退到系统 `PATH`
  - 视频在 shared details 中支持 6 帧静态循环预览；该预览只在 details 中出现，不扩展到列表动态预览
  - 与 shared details、tags、collections、recent 的回流闭环
- `Documents`
  - 用户侧 `Books / 图书` 已调整为 `Documents / 文档`
  - 内部 route / placement 仍保留 `/library/books` 与 `books` 兼容命名，避免旧数据和调用链断裂
  - PDF / EPUB / MOBI / AZW3 仍进入 Documents
  - DOC / DOCX / PPT / PPTX / XLS / XLSX / CSV / TXT / MD / RTF / ODT / ODS / ODP 等常见文档格式也会进入 Documents
  - PDF 文件可通过统一 thumbnail endpoint 按需生成第一页 PNG 缩略图，用于 Documents / Search / Files / DetailsPanel 的轻量 inspect
  - PDF 缩略图使用 `pypdfium2` / PDFium；这不是阅读器、OCR 或多页预览能力
- `Games`
  - `effective_placement=games` 的 smart view
  - 游戏入口文件识别与库式浏览
  - 轻量状态表达
  - 复用统一 thumbnail pipeline：`.exe` 显示现有 exe icon，image / video / PDF 尽量显示缩略图
  - archive / rom / iso / shortcut 等无真实缩略图的文件显示稳定 fallback
  - 与 shared details、组织层、open actions 的回流闭环
- `Software`
  - 软件相关文件识别与信息表达
  - 与 shared details、tags、collections、recent 的回流闭环

### 横向组织层

- `tags` / `color tags`
  - 单文件写入与批量写入
- `collections`
  - 当前是 saved retrieval surface，不是规则引擎
- `recent family`
  - `imports`
  - `tagged`
  - `color-tagged`
- `favorite` / `rating`
  - 作为全局轻量 user meta 使用
- `shared details`
  - 当前唯一统一详情中心
  - 支持单文件设置 library placement：Auto / Documents / Media / Games / Software / Files only
- `refind` / `open actions`
  - 让用户可以从 details、tags、collections、recent 回到对应 subset surface，或直接打开文件 / 所在目录

### 分类与手动归类

当前分类层已经持久化并通过验收：

- `file_kind` 表示文件物理类型
- `auto_placement` 表示系统自动推荐库位置
- `manual_placement` 表示用户手动指定库位置
- `effective_placement = manual_placement ?? auto_placement`，不单独落库
- `manual_placement` 永远优先；scan / backfill / auto classification 不覆盖用户手动设置

普通 `.zip` / `.rar` / `.7z` 等 archive 默认 `file_kind=archive`、`auto_placement=none`，不会自动进入 Games 或 Software。用户可以通过 DetailsPanel 或 Batch organize 手动设置为 Games / Software / Documents / Media，也可以设置为 Files only。项目不新增 Archives 独立页面；压缩包通过 Files 页面 Archives quick filter 查找。

### 近期体验收口

近期已完成并通过验收的体验修复包括：

- 视频 DetailsPanel 预览保持 6 帧，但采样点基于 ffprobe duration 均匀分布在视频内部，cache version 已更新为 `v2`
- ffprobe / ffmpeg subprocess 输出在 Windows 下使用安全 UTF-8 decode，避免 GBK locale 导致 `UnicodeDecodeError`
- Settings 切换语言后，Sidebar、Shell、当前页面与 DetailsPanel 文案即时刷新
- Home / Search / Files / Recent 的深色模式颜色残留已修复，列表、卡片、hover 与 selected 状态走 theme tokens

### 共通交互与体验边界

- single click = select + show details
- double click = open file
- filters apply immediately
- empty / loading / no-results 有明确状态
- browser mode 支持主要浏览与组织流程，但桌面打开动作会降级

### 当前界面形态

当前前端已经更明确地收口成一套统一工作台壳层：

- 左侧是可展开 / 收起的导航区
- 中间是当前页面对应的浏览与检索区
- 右侧是 shared details 区
- details 当前支持显示 / 隐藏，隐藏后中间区会补位
- 顶部区域保持轻量，只承担当前页面标题、克制的 backend 状态提示和 details 显隐控制

这些变化描述的是当前 UI 形态和体验一致性，不是新的产品能力。

当前高可见文案和页面级 UI copy 也已经不再主要散落在组件里，而是通过前端轻量文本层组织，并可跟随当前 locale 切换。这属于当前前端工程和 beta 验证准备的一部分，不是单独的新产品能力。

## 当前不做什么

测试版阶段当前明确**不做**这些方向：

- 不做新的平台化扩张，不新增新的垂类库线
- 不做 AI 自动标签、OCR、语义检索、推荐系统或自动规则
- 不把 `Games` 做成游戏平台、启动器体系或联网封面抓取系统
- 不把 `Documents` 做成阅读器、Office 编辑器或文档管理平台
- 不把 `Software` 做成安装管理平台
- 不新增 Archives 独立页面
- 不引入 AI 主分类；如果未来引入 AI，也只能做 suggestion，不直接写最终分类
- 不做完整 archive 解压入库；后续如做 archive 内容探测，也应保持轻量
- 不把 `Collections` 做成 smart rules platform
- 不做复杂统一对象中台或新一轮大架构重写

如果某项需求会把项目重新带回“继续扩功能”的节奏，它就不是当前 README 应该表达成既定事实的内容。

同样，当前前端文本层、语言切换与主题切换也**不是**：

- 完整国际化平台
- 多语言中台
- 后端多语言系统
- 远程语言包系统
- 浏览器语言自动识别系统
- 复杂主题编辑器、主题市场或自定义 accent 系统

## 系统结构与仓库结构

### 系统结构

当前系统是一个本地优先的三层组合：

- `apps/backend`
  - FastAPI 后端
  - 提供索引文件、搜索、shared details、tags / color tags、collections、recent family、subset libraries 等 HTTP API
  - 当前使用 SQLite，本地启动时会从 baseline SQL 初始化数据库
- `apps/frontend`
  - React + Vite 工作台前端
  - 提供统一 app shell、主页面和 shared details 交互
- `apps/desktop`
  - Electron 桌面壳
  - 提供选目录、打开文件、打开所在文件夹等 desktop bridge 能力

当前实现的核心思路不是“每条垂类库各自独立长成一个产品”，而是：

- 先有统一的 indexed files 主语义
- 再在其上暴露 `Media / Documents / Games / Software` 这些 subset surfaces
- 再通过 `shared details`、`tags`、`color tags`、`collections`、`recent family` 完成轻量组织和再找回

浏览器模式可以运行当前大部分浏览、检索和组织流程；Electron 桌面壳则补上与本地桌面环境强相关的动作。

### 仓库结构

```text
apps/
  backend/   FastAPI backend + SQLite bootstrap + tests
  frontend/  React + Vite workbench UI
  desktop/   Electron shell
docs/        当前正式文档入口
  api/       当前 API 合同文档
  archive/   历史归档文档
  _wip/      临时开发文档与未冻结材料
```

文档边界建议按下面理解：

- `docs/` 顶层：当前正式文档
- `docs/api/`：当前真实已落地 API 合同入口
- `docs/archive/`：历史文档归档，可参考，但不是当前事实入口
- `docs/_wip/`：临时开发文档，不应默认当作正式口径

### 当前导航图标资源策略

当前导航相关图标继续使用 SVG 文件 + 组件封装方案，而不是回退到页面内联 SVG。当前工程位置是：

- `apps/frontend/src/assets/icons/navigation/`
  - 导航与导航相关控制图标的原始 SVG 资源
- `apps/frontend/src/shared/ui/icons/`
  - 当前统一图标封装入口，例如 `SidebarIcon`

当前资源规范是：

- 导航图标应保持单色、可自动变色
- 不应在 SVG 资源里写死黑色、白色、蓝色等状态色
- outline 图标优先使用 `stroke="currentColor"`
- filled 图标优先使用 `fill="currentColor"`
- 不应为 default / hover / active / current-page 准备多份不同颜色版本
- 不应带白色背景底板或仅用于导出工具的背景/裁剪噪音

当前导航图标颜色由组件状态和 CSS 控制，而不是由 SVG 文件本身写死。这样侧边栏中的默认、hover、active 和 current-page 高亮都可以继续走同一套状态样式。

这里的 `navigation` 图标属于前端 UI 资源，不等于 Electron 应用图标、安装包图标或其他桌面壳资源。

### 当前前端文本层与 locale 结构

当前前端文案资源和 locale 运行时主要位于：

- `apps/frontend/src/locales/`
  - 当前包含 `en/` 和 `zh-CN/` 两套 locale 资源
- `apps/frontend/src/shared/text/`
  - 当前轻量文本入口、locale 运行时和 `LocaleProvider`

当前前端通过 `t(key, params?)` 读取高可见 UI 文案，并在 `Settings` 中提供轻量语言切换入口。

`Settings` 也提供 `Light / Dark` 主题切换。语言与主题偏好都只使用前端本地存储持久化，不涉及后端 contract 变更。

## 启动方式

### 最快开始

仓库根目录提供了 Windows 便捷脚本：

- `start-dev.ps1`
  - 默认启动 backend + frontend
  - 传入 `-StartDesktop` 时也会启动 desktop
- `start-dev.bat`
  - 作为 PowerShell 启动脚本的 Windows 包装入口

推荐开发启动方式：

```powershell
.\start-dev.ps1 -StartDesktop
```

也可以直接双击：

```text
start-dev.bat
```

当前脚本会在启动前清理 `8000` / `5173` 上的旧开发进程，然后启动：

- backend：`http://127.0.0.1:8000`
- frontend：`http://127.0.0.1:5173`
- desktop：`npm run dev`（使用 `-StartDesktop` 或默认 bat 入口时）

脚本启动后会检查 backend 指纹，正常输出应包含：

- `OK: backend uses .venv Python`
- `OK: process_id = ...`
- `OK: process_start_time = ...`
- `OK: PDF thumbnail render mode is subprocess-v1`

如果这些检查缺失，优先排查是否命中了旧 backend 进程。

### Backend

开发模式推荐使用仓库根目录的 `.venv`，不要临时切到系统 Python。

```powershell
cd apps/backend
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

当前后端会在启动时从 `apps/backend/app/db/migrations/0001_initial_core.sql` 初始化 SQLite 数据库到 `apps/backend/data/`。

### 正确停止开发服务

停止 backend 时，请在 `Backend Dev` 窗口中按 `Ctrl+C`。如果 PowerShell 提示：

```text
Terminate batch job (Y/N)?
```

请输入：

```text
Y
```

不建议只关闭 PowerShell 窗口。`uvicorn --reload` 会同时存在 reloader 父进程和 server 子进程；如果只关窗口，旧进程可能残留并继续占用 `8000`，后续访问 `http://127.0.0.1:8000` 时就会命中旧 backend。

### 启动前端口检查

如果怀疑命中了旧 backend 或 frontend dev server，先检查端口：

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress, LocalPort, State, OwningProcess

Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress, LocalPort, State, OwningProcess
```

必要时清理旧进程：

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
  }

Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue |
  ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
  }
```

### 启动后后端指纹检查

启动后确认当前访问到的是新 backend：

```powershell
$base = "http://127.0.0.1:8000"

Invoke-RestMethod "$base/debug/runtime" -TimeoutSec 5 | ConvertTo-Json -Depth 8
Invoke-RestMethod "$base/debug/thumbnails/warmup" -TimeoutSec 5 | ConvertTo-Json -Depth 8
```

通过标准：

- `sys_executable` 指向仓库根目录的 `.venv\Scripts\python.exe`
- `process_id` 存在
- `process_start_time` 存在
- `/debug/thumbnails/warmup` 中能看到 `pdf_render_mode=subprocess-v1`
- `service_module_path`、`service_module_mtime`、`pdf_render_command_kind` 等实现指纹存在

异常表现：

- `sys_executable` 是 `C:\Python314\python.exe`：说明没有使用 `.venv`，或访问到了旧进程
- `process_id` / `process_start_time` 缺失：说明当前 backend 可能是旧代码
- `pdf_render_mode=subprocess-v1` 缺失：说明 thumbnail warmup 当前不是最新实现

### Python 版本注意事项

backend 推荐使用项目根目录 `.venv` 中的 Python 3.12。Python 3.14 可能在 app 导入 ORM model 阶段触发 SQLAlchemy 类型解析错误，例如：

```text
TypeError: descriptor '__getitem__' requires a 'typing.Union' object but received a 'tuple'
```

这个错误不是 PDF thumbnail 本身的问题。不要手改 `pyvenv.cfg`，也不要复制 `python.exe` 到 venv 中；如需切换 Python 版本，应按项目当前约定重新准备 `.venv`。

### Frontend

```powershell
cd apps/frontend
npm install
npm run dev
```

生产构建：

```powershell
cd apps/frontend
npm run build
```

### Desktop

```powershell
cd apps/desktop
npm install
npm run build
npm run dev
```

当前 `desktop` 是 Electron 壳，不是独立后端或独立产品入口。默认情况下，它依赖：

- frontend dev server：`http://127.0.0.1:5173`
- backend API：`http://127.0.0.1:8000`

如果只在浏览器里跑 frontend，主要浏览与组织流程仍然可用，但 `open file` / `open containing folder` 这类桌面动作会降级。

### Beta 桌面包

当前 beta 已升级为一体化 Windows 桌面包：

- Electron 安装包包含桌面壳、frontend 静态资源、PyInstaller 打包的 backend exe
- packaged mode 会自动启动本地 backend，不需要用户手动运行 `python -m uvicorn`
- packaged mode 会使用随包携带的 `ffmpeg.exe`，不需要用户自行配置 `PATH`
- PDF 第一页缩略图使用随 backend 打包的 `pypdfium2` / PDFium 运行时
- SQLite、thumbnail cache、video preview cache 会写入 Electron `userData` 下的 `backend-data/`

生成 Windows beta 安装包：

```powershell
cd apps/desktop
npm run package:win
```

产物输出到 `apps/desktop/release/integrated/`。当前版本号沿用 `0.1.0`，安装包名为 `Workbench Beta Integrated Setup 0.1.0.exe`。

旧的技术 beta 包已归档到 `apps/desktop/release/archive/technical-beta-0.1.0-manual-backend-20260425/`。该旧包需要手动 backend，仅用于回退参考，不再作为推荐交付形态。

注意：一体化包仍是 beta，不包含自动更新、后台服务安装、复杂安装向导或正式发布级签名/图标收口。

### 常见本地验证

```powershell
cd apps/backend
python -m unittest
```

```powershell
cd apps/frontend
npm run build
```

```powershell
cd apps/desktop
npm run build
```

## 文档入口

当前正式文档建议从这里进入：

- [docs/README.md](docs/README.md)
  - `docs/` 顶层正式文档索引
  - 当前正式文档、归档文档、`_wip` 文档的边界说明
- [docs/测试版当前状态总览.md](<docs/测试版当前状态总览.md>)
  - 当前项目是什么、已完成能力和当前产品形态
- [docs/测试版范围与边界.md](<docs/测试版范围与边界.md>)
  - 当前测试版必须包含什么、明确不做什么
- [docs/测试版验证准备.md](<docs/测试版验证准备.md>)
  - 当前测试版验证目标、建议路径和反馈优先级
- [docs/测试版发布准备.md](<docs/测试版发布准备.md>)
  - beta 包能力边界、安装/启动前提、smoke test 和已知限制
- [docs/前端文本层与语言切换.md](<docs/前端文本层与语言切换.md>)
  - 当前前端文案组织方式
  - `en / zh-CN` locale 结构、`t(key, params?)`、`Settings` 语言切换入口和当前 Light / Dark 主题入口
  - 后续补文案、补语言和继续接入页面时的维护说明

API 文档入口在：

- [docs/api/README.md](docs/api/README.md)
  - 当前真实已落地 API 合同的总入口
  - `core-workbench.md`
  - `library-subsets.md`
  - `organization-and-retrieval.md`

当前后端没有开放 Swagger / OpenAPI 页面，因此 `docs/api/README.md` 这组 Markdown 文档就是当前 API 合同入口。

前端文本层与 locale 切换属于前端 UI 工程能力，不属于 API contract 变更，因此当前说明写在 README 和 `docs/` 顶层正式文档中，而不是写入 `docs/api/`。

## 推荐阅读顺序

如果你是第一次进入仓库，建议按这个顺序看：

1. [README.md](README.md)
2. [docs/测试版当前状态总览.md](<docs/测试版当前状态总览.md>)
3. [docs/测试版范围与边界.md](<docs/测试版范围与边界.md>)
4. [docs/测试版验证准备.md](<docs/测试版验证准备.md>)
5. [docs/测试版发布准备.md](<docs/测试版发布准备.md>)
6. [docs/api/README.md](docs/api/README.md)
7. `docs/api/` 下的其他 API 文档

如果你需要快速在文档目录中定位正式文档和归档文档，再补看 [docs/README.md](docs/README.md)。

## 当前下一步

当前下一步不是继续做新的大能力批次，而是围绕测试版继续收口：

1. 做真实测试版验证
2. 记录用户理解偏差、主路径卡点和边界误解
3. 按 `P0 / P1 / P2 / P3` 做问题分级
4. 继续做体验一致性、稳定性和性能收口
5. 为正式发布前的整理与验收做准备

最近几轮前端改动也应按这个节奏理解：它们主要是在收口三栏壳层、导航 / details 控制表达、状态提示与整体视觉一致性，而不是把项目往新的功能方向继续扩张。

历史阶段文档仍保留在 [docs/archive/](docs/archive/) 里，但它们不应替代当前 README 和 `docs/` 顶层正式文档作为事实入口。
