# Phase 12 — 垂直深水区能力：设计规范

> 2026-05-28 | 状态：待实施
> 范围：12 项深层能力，分 3 个批次——基础设施、媒体与文档、智能化与平台

---

## 目标

实现所有 beta 范围外延迟的深层能力：重复检测、代码签名、自动更新、视频播放器、文档阅读器、AI 分类、游戏启动器、主题编辑器、多面板布局。

## 原则

- 每个批次产出可独立交付的工作软件
- AI 功能仅做建议层——不直接写入最终分类或执行文件操作
- 视频和文档阅读器内嵌在详情面板中，不替代外部应用
- 游戏启动器仅启动已索引的游戏入口文件，不做平台集成

---

## 批次 A：基础设施与低复杂度（4 项）

### A1：重复文件检测

**文件：** `apps/backend/app/workers/ `（新 worker）、`apps/backend/app/repositories/file/repository.py`、`apps/frontend/src/features/search/`

**方案：**
- 后端：创建 `ChecksumWorker`，扫描时计算文件 SHA-256。写入已有的 `files.checksum_hint` 列。在已有 `POST /files/batch/` 相关功能上增加 `GET /files/duplicates?min_size=N`（仅报告重复项，不自动删除）。
- 前端：在搜索结果中添加"发现重复项"标记。详情面板中若存在重复文件则显示"可能存在重复"提示。

**边界：** 不自动删除重复项。用户始终手动选择如何处理。

---

### A2：应用图标 + 代码签名

**文件：** `apps/desktop/package.json`、`apps/desktop/build-resources/`（新图标文件）、`apps/desktop/electron-builder.yml`（签名配置）

**方案：**
- 图标：为应用创建自定义 `.ico` 文件（256x256 + 较小尺寸）。替换默认 Electron 图标。
- 代码签名：在 `electron-builder` 配置中添加 `certificateFile`、`certificatePassword` 环境变量。需要用户提供签名证书（或使用自签名证书进行本地构建）。

**边界：** 代码签名需要从证书颁发机构获取证书——本项仅实现配置基础设施。自签名作为开发模式的回退方案。

---

### A3：自动更新系统

**文件：** `apps/desktop/electron/main.ts`、`apps/desktop/package.json`

**方案：**
- 使用 `electron-updater` 包。添加 `autoUpdater.checkForUpdatesAndNotify()`。
- 在 `electron-builder` 配置中添加 `publish` 配置，指向 GitHub Releases。
- 前端：在设置页面中添加"检查更新"按钮及当前版本显示。

**边界：** Windows-only（`.exe` + NSIS）。自动更新仅在已签名的正式构建中启用。

---

### A4：智能选帧 / 全库预生成缩略图

**文件：** `apps/backend/app/workers/thumbnails/video_generator.py`、`apps/backend/app/services/thumbnails/service.py`

**方案：**
- **智能选帧：** 不再对视频缩略图始终使用 10% 位置，改为在第 5% 到 50% 之间采样位置中挑选最亮的一帧（避免黑帧）。使用 ffprobe 检测黑帧计数，先跳到第一个非黑帧。
- **全库预生成：** 在 `POST /files/thumbnails/warmup` 中添加 `scope=all` 选项。后台线程池依次预热所有文件。最多 6 个并发工作线程。在设置页面中追踪进度。

---

## 批次 B：媒体与文档深度（4 项）

### B1：视频悬停预览 / 内嵌播放器

**文件：** `apps/frontend/src/features/details-panel/sections/DetailsPreviewSection.tsx`、`apps/frontend/src/shared/ui/video/`（新目录）

**方案：**
- **悬停预览（卡片）：** 在 BrowseV2 中对视频卡片使用 `<video>` 元素，当鼠标悬停时静音自动播放前 3 秒。使用视频海报帧作为 `poster` 属性，`preload="none"` 避免大量加载。
- **内嵌播放器（详情面板）：** 在 `DetailsPreviewSection` 中嵌入 `<video controls>` 元素。支持播放/暂停、进度条拖动、音量控制。默认不自动播放。基于已有的静态 6 帧预览构建——现在替换为真正的视频元素。

---

### B2：PDF/文档内嵌预览

**文件：** `apps/backend/app/workers/thumbnails/pdf_generator.py`、`apps/frontend/src/features/details-panel/sections/DetailsPreviewSection.tsx`

**方案：**
- 后端：扩展 `PdfThumbnailGeneratorWorker` 以渲染前 N 页（默认为 5 页）作为独立缩略图。通过 `GET /files/{id}/pdf-pages` 返回页面图片 URL。
- 前端：在详情面板中为 PDF 文件渲染分页预览区域。使用已有的翻页按钮（左右箭头）来翻页。页面图片通过已有的缩略图管道进行懒加载。

---

### B3：内嵌电子书阅读器

**文件：** `apps/backend/app/workers/`（新 epub 解析器）、`apps/frontend/src/features/details-panel/`（阅读器组件）

**方案：**
- 后端：创建 `EpubParserWorker`，使用 Python 标准库 `zipfile` + `xml.etree` 解析 EPUB 文件（EPUB 是一个包含 XHTML 章节的 ZIP 文件）。提取：元数据（标题、作者）、目录、按顺序排列的章节文本。通过 `GET /files/{id}/epub-content` API 返回。
- 前端：为 EPUB 文件创建最小阅读器组件。渲染：标题、作者、目录（可点击）、章节内容（纯文本，无 HTML 排版）。保留阅读进度于 localStorage 中。

**边界：** 不支持 EPUB3 富媒体、嵌入字体或复杂 CSS。仅限纯文本章节——足够完成快速查阅。

---

### B4：主题编辑器 / 自定义强调色

**文件：** `apps/frontend/src/shared/theme/`、`apps/frontend/src/pages/settings/SettingsPage.tsx`

**方案：**
- 在设置页面中添加"外观"区域。当前主题切换器（Light/Dark）仍保留。
- 自定义强调色：颜色选择器从 8 种预设强调色中选择（蓝、绿、紫、红、橙、青、粉、灰）。选择后写入 localStorage 并通过 CSS 变量（`--color-accent`、`--color-accent-hover` 等）应用。
- 可选："跟随系统主题"开关，使用 `prefers-color-scheme: dark` 媒体查询自动切换。

---

## 批次 C：智能化与平台（4 项）

### C1：AI 自动分类建议

**文件：** `apps/backend/app/services/classification/suggester.py`（新文件）、`apps/frontend/src/features/library/`

**方案：**
- **后端：** 创建基于规则的建议引擎（`RuleBasedSuggester`）。阶段 1 使用已有的 `classification.py` 规则 + 文件名模式匹配 + 目录名启发式规则。返回建议：`{ file_id, suggested_type, suggested_placement, confidence, reason }`。通过 `POST /library/classify-suggestions` API 暴露。
- **前端：** 在 Library 待处理面板中为扫描结果添加"查看建议"按钮，显示建议列表及接受/拒绝操作。
- **未来：** 如果之后添加 AI，可以插入一个 `AISuggester` 替代规则引擎，API 接口保持不变。

**铁律：** AI 建议绝不写入最终分类或执行文件操作。用户必须手动接受每条建议。

---

### C2：游戏启动器

**文件：** `apps/desktop/electron/main.ts`、`apps/desktop/electron/preload.ts`、`apps/frontend/src/features/games/`（新建，基于 BrowseV2，专注于游戏）

**方案：**
- **桌面端：** 通过 `child_process.spawn` 添加 `launch-file` IPC 通道。通过 `shell.openPath` 启动游戏可执行文件。支持通过已有路径引用 `.lnk` 快捷方式。
- **前端：** 在 BrowseV2 中为游戏分类创建专属游戏浏览视图。游戏卡片显示：标题、检测到的 exe 计数、游戏状态（未启动/进行中/已完成/已搁置）。详情面板中添加"启动"操作——调用 IPC `launch-file` 通道的同时，也通过已有的 `openIndexedFile` 桌面桥接作为回退。

**边界：** 不跟踪进程生命周期（启动后无"关闭"功能）。不注入叠加层和钩子，不管理游戏存档。

---

### C3：平台账号 / 游戏时长追踪

**文件：** `apps/backend/app/db/models/game.py`（新模型）、`apps/frontend/src/features/games/`

**方案：**
- 后端：添加 `game_sessions` 表（`file_id`、`started_at`、`ended_at`、`duration_seconds`）。`POST /games/{file_id}/sessions` 开始会话，`PATCH /games/{file_id}/sessions/{id}` 结束会话。
- 前端：在游戏详情中显示总游戏时长。游戏卡片上显示"最近游玩"状态。"启动"按钮变为按钮组——点击"开始会话"。关闭游戏后显示"结束会话"——带已过时间的确认信息。
- 平台账号：最小实现——通过 `game_accounts` 表（`file_id`、`platform`、`display_name`）关联的平台账号名称。游戏详情中展示为一个信息徽章。

**边界：** 不进行实时 API 集成（Steam/Epic/Xbox）。平台账号为纯文本标签。会话为手动开始/停止。

---

### C4：多面板 / 拖拽布局

**文件：** `apps/frontend/src/app/shell/AppShell.tsx`、`apps/frontend/src/app/styles/shell-layout.css`

**方案：**
- 拖拽调整尺寸：详情面板和浏览区域之间的分隔条已经存在——增强它以支持在主区域左侧添加第二个可选面板。
- 保存的面板布局：在 localStorage 中保存面板配置（可见性 + 宽度比例）。键名：`WORKBENCH_PANEL_LAYOUT`。
- 第二个面板（可选）：可在左侧导航栏和内容区域之间放置一个紧凑的"快速访问"侧面板。通过 `Ctrl+Q` 切换。显示：最近文件（10 个）、已收藏文件、已保存的搜索。可折叠。

**边界：** 不完整的拖拽仪表盘。最大限度为 3 个面板（导航 + 可选快速面板 + 主内容 + 详情面板）。不跨页面持久化。

---

## 依赖关系图

```
批次 A（基础设施）——无依赖，全部 4 项均可并行
  └── 批次 B（媒体与文档深度）——B1 需要 A4（智能选帧）
  └── 批次 C（智能化与平台）——C3 需要 C2
```

## 验证

每批次：
- 后端：所有测试通过
- 前端：所有测试通过，无新的 TS 错误
- 手动冒烟：重复检测、视频预览、文档翻页、游戏启动、主题切换
