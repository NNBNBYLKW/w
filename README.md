# Workbench

Windows local-first asset management workbench built around indexed files, shared details, and lightweight organization flows.

当前仓库已经进入**测试版阶段**。README 的目标不是替代正式文档，而是让第一次进入仓库的人先快速搞清楚 4 件事：

- 这个项目是什么
- 它已经做到哪一步
- 当前能做什么、不能做什么
- 应该怎么启动、接下来先看哪些文档

当前最核心的产品主链：

`browse → inspect → organize → refind`

## 项目简介

Workbench 是一个建立在 **Windows 本地文件系统** 之上的 local-first 资产工作台。版本 **0.2.0**。

它不是试图替代真实文件系统，而是在真实文件之上补一层**索引、详情、组织和再找回**能力，让本地资产更容易被浏览、轻量整理和重新找到。当前产品的核心形态是：

- **File Library（文件库）** 作为管理中心：扫描文件夹、受管库、导入、整理计划
- **Browse（浏览）** 作为内容消费面：按媒体/文档/应用/素材领域浏览对象和松散文件
- `Search` / `Tags` / `Collections` / `Recent` 作为再找回 surfaces
- `Tools` 作为受控文件处理工具入口（当前仅 `video_merge`）
- `DetailsPanelFeature` 作为统一详情中心
- `Settings` 作为应用偏好入口

它主要解决的是这样一类问题：本地文件很多，但仅靠文件夹结构和文件名，不足以支撑"浏览 -> 检视 -> 组织 -> 再找回"的日常工作流。

## 当前阶段

项目当前处于**测试版阶段（v0.2.0）**，已完成 M2 导航重构和 M3 质量优化：

- **Phase 8 — Browse v2 / Object Management**（完成）
  - Browse v2 领域分类浏览（媒体/文档/应用/素材）
  - 对象详情与成员管理（添加/移除成员）
  - 对象合成（Compose）与修正（Amendment）
  - 受管文件库完整工作流：Import → Inbox → Review → Plan → Execute → Browse
  - 安全原则：import copy-only、source preserved、preflight required、no source cleanup、no auto delete
  - 详见 [docs/library-v2/](docs/library-v2/)
- **M2 — 文件库中心导航重构**（完成，commit `e9bc012`）
  - 左侧导航重构为文件库中心结构，Browse 分类树提升到全局侧边栏
  - 旧 Media/Books/Games/Software 路由重定向到 Browse 领域预设
- **M3 — 功能补全与技术债清理**（完成，commits `1d904cb`~`49018f6`）
  - P0 数据正确性修复（type_prefix、compose guard）
  - P1 体验优化（错误处理、角色标签、过时文案、操作反馈）
  - P2 技术债清理（utcnow 替换、代码分割、plan_kind 常量化、schema 版本管理、日志轮转、DB 备份、recovery 增强、操作历史、CI/CD）
  - 前端测试基础设施（Vitest + 27 tests）
- `Library` 文件库 Phase 1-4（已完成）
- `Tools` 第一版（Video Merge 视频合并工具）
- 测试版范围冻结
