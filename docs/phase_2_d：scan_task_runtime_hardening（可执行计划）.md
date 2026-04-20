# Phase 2D：Scan / Task Runtime Hardening（已实现）

> **历史文档说明**
>
> 本文档保留为较早阶段的实现记录，不再作为当前仓库的 canonical current-state source。
>
> 当前应优先阅读：
>
> - `README.md`
> - `docs/current-project-status-dossier.md`
> - release-facing current-state docs

## Summary

当前 repo 已按窄范围落地 Phase 2D，目标只包括：

- 同一 source 的 active scan 冲突保护
- `GET /sources` 的最小派生失败反馈
- 现有 source 相关前端表面的更清晰 running / failed 表达

本阶段没有扩成新的 runtime 产品面：

- 没有新增 task routes
- 没有新增 runtime page
- 没有新增 scan history / retry system
- 没有改动 inline scan 模型

## Current backend behavior

- `POST /sources/{id}/scan`
  - 若同一 source 已存在 `pending` 或 `running` 的 `scan_source` task：
    - 返回 `409 SCAN_ALREADY_RUNNING`
  - 否则继续当前 inline scan 主链
  - 成功响应 shape 保持：
    - `task_id`
    - `status`
- `GET /sources`
  - 当前新增最小派生字段：
    - `last_scan_error_message`
  - 语义：
    - 读取该 source 最新一条 `scan_source` task
    - 若最新 task 为 `failed`，返回其 `error_message`
    - 若最新 task 为 `succeeded` / `running` / `pending`，返回 `null`

## Current frontend behavior

- `SourceManagementFeature`
  - source row 现在能更清楚表达：
    - current `last_scan_status`
    - running 提示
    - failed + `last_scan_error_message`
    - local same-source conflict feedback
- `HomeOverviewFeature`
  - 保持轻量 overview
  - 只在 source 最近一次 scan 为 failed 时显示一行轻量失败提示

## Scope boundaries

本阶段明确不做：

- background queue / worker platform
- tasks page / tasks API expansion
- Home dashboard redesign
- Search / Files / Media / Recent / Collections feature expansion
- desktop runtime changes
