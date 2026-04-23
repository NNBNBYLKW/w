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
- `Media` / `Games` / `Books` / `Software` 作为受控 subset surfaces
- `Recent` / `Tags` / `Collections` 作为组织与再找回 surfaces
- `DetailsPanelFeature` 作为统一详情中心

它主要解决的是这样一类问题：本地文件很多，但仅靠文件夹结构和文件名，不足以支撑“找到 -> 看清楚 -> 标记 -> 以后再找回来”的日常工作流。

## 当前阶段

项目当前处于**测试版阶段**，并且已经完成了当前测试版主线的能力收口：

- `Media` 媒体库
- `Games` 游戏库
- `Books` 电子书库
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
  - 与 shared details、tags、collections、recent 的回流闭环
- `Games`
  - 游戏入口文件识别与库式浏览
  - 轻量状态表达
  - 与 shared details、组织层、open actions 的回流闭环
- `Books`
  - 电子书入口与信息表达增强
  - 与 shared details、tags、collections、recent 的回流闭环
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
- `refind` / `open actions`
  - 让用户可以从 details、tags、collections、recent 回到对应 subset surface，或直接打开文件 / 所在目录

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

## 当前不做什么

测试版阶段当前明确**不做**这些方向：

- 不做新的平台化扩张，不新增新的垂类库线
- 不做 AI 自动标签、OCR、语义检索、推荐系统或自动规则
- 不把 `Games` 做成游戏平台或启动器体系
- 不把 `Books` 做成阅读器
- 不把 `Software` 做成安装管理平台
- 不把 `Collections` 做成 smart rules platform
- 不做复杂统一对象中台或新一轮大架构重写

如果某项需求会把项目重新带回“继续扩功能”的节奏，它就不是当前 README 应该表达成既定事实的内容。

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
- 再在其上暴露 `Media / Games / Books / Software` 这些 subset surfaces
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

## 启动方式

### 最快开始

仓库根目录提供了 Windows 便捷脚本：

- `start-dev.ps1`
  - 默认启动 backend + frontend
  - 传入 `-StartDesktop` 时也会启动 desktop
- `start-dev.bat`
  - 作为 PowerShell 启动脚本的 Windows 包装入口

这些脚本适合本地开发时快速拉起窗口，但 README 以下面的分组件命令作为更稳定的说明入口。

### Backend

```powershell
cd apps/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

当前后端会在启动时从 `apps/backend/app/db/migrations/0001_initial_core.sql` 初始化 SQLite 数据库到 `apps/backend/data/`。

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

API 文档入口在：

- [docs/api/README.md](docs/api/README.md)
  - 当前真实已落地 API 合同的总入口
  - `core-workbench.md`
  - `library-subsets.md`
  - `organization-and-retrieval.md`

当前后端没有开放 Swagger / OpenAPI 页面，因此 `docs/api/README.md` 这组 Markdown 文档就是当前 API 合同入口。

## 推荐阅读顺序

如果你是第一次进入仓库，建议按这个顺序看：

1. [README.md](README.md)
2. [docs/测试版当前状态总览.md](<docs/测试版当前状态总览.md>)
3. [docs/测试版范围与边界.md](<docs/测试版范围与边界.md>)
4. [docs/测试版验证准备.md](<docs/测试版验证准备.md>)
5. [docs/api/README.md](docs/api/README.md)
6. `docs/api/` 下的其他 API 文档

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
