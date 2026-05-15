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

- `Search` / `Library` / `Files` 作为通用 indexed-files surface
- `Media` / `Documents` / `Games` / `Software` 作为受控 subset surfaces
- `Recent` / `Tags` / `Collections` 作为组织与再找回 surfaces
- `Tools` 作为受控文件处理工具入口（当前仅 `video_merge`）
- `DetailsPanelFeature` 作为统一详情中心

它主要解决的是这样一类问题：本地文件很多，但仅靠文件夹结构和文件名，不足以支撑"找到 -> 看清楚 -> 标记 -> 以后再找回来"的日常工作流。

## 当前阶段

项目当前处于**测试版阶段**，并且已经完成了当前测试版主线的能力收口：

- `Media` 媒体库
- `Games` 游戏库
- `Documents` 文档库
- `Software` 软件库
- 组织层与库体验补齐
- `Library` 文件库（Phase 1-4 已完成）
  - Phase 1: Library shell + Path Browser
  - Phase 2: Object scanner（只读扫描 `[TYPE]` 对象根）
  - Phase 3: Organize plan drafts（候选人扫描、计划生成、Mark Ready）
  - Phase 4: Organize plan execution（Preflight → 用户确认 → Execute → Logs）
- **Library v2 — Managed Import Workflow (Phase 7A–7G complete)**
  - 完整受管文件库工作流：Import → Inbox → Object Detection → Review → Draft Plan → Execute → Managed Library → Browse/Search/Details → Recovery
  - Hybrid mode：与原有 source-scan beta 主线共存，不替换旧逻辑
  - 安全原则：import copy-only、source preserved、execute 仅移动 Inbox copy、no source cleanup、no auto delete
  - 详见 [docs/library-v2/](docs/library-v2/)
- `Tools` 第一版（Video Merge 视频合并工具）
- 测试版范围冻结
- 测试版体验统一
- API 文档收口
- 文档体系整理
