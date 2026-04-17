# 下一阶段开发任务模板（给 Codex 用）

## 使用说明

本文档用于在进入下一阶段开发时，快速生成一份适合提交给 Codex 的任务说明。

使用方式：

1. 复制本模板
2. 将方括号内容替换为当前阶段的实际信息
3. 明确“做什么 / 不做什么”
4. 再交给 Codex 先 plan、后实现

建议每次只针对一个窄阶段使用一次，不要把多个方向混成一个超大任务。

---

# 任务标题

[填写当前阶段标题，例如：Phase 6B: Double-click to Open]

---

## 1. 背景与当前状态

当前仓库已经具备以下已完成能力：

- source onboarding
- 首扫 / 重扫 delete-sync
- indexed search
- minimal details panel
- normal tags
- color tags
- files listing
- source / exact-directory browse
- media listing
- recent imports listing
- shared details-panel open actions

当前阶段目标是：

> [用一句话说明本阶段真正要补上的能力]

本阶段不应重做已有主链，也不应引入新的平台级复杂度。

---

## 2. 本阶段目标

### Goal
[写清楚本阶段唯一核心目标]

### 用户价值
[说明为什么这个阶段值得先做]

### 阶段边界
本阶段只做：
- [能力 1]
- [能力 2]
- [能力 3]

本阶段明确不做：
- [范围外项 1]
- [范围外项 2]
- [范围外项 3]

---

## 3. 需要优先阅读的文件

### 计划 / 文档
- `AGENTS.md`
- [相关 phase 文档]
- [相关 schema/API 草案]
- [相关验收总结或候选项文档]

### 重点代码文件
- [文件 1]
- [文件 2]
- [文件 3]
- [文件 4]

---

## 4. 允许修改的文件

- [允许修改文件 1]
- [允许修改文件 2]
- [允许修改文件 3]
- [允许修改文件 4]

如果实现过程中发现必须额外改动未列出的文件：
- 不要先扩散修改
- 先说明原因，再决定是否纳入范围

---

## 5. 明确不要修改的文件/区域

- [禁止修改区域 1]
- [禁止修改区域 2]
- [禁止修改区域 3]
- [禁止修改区域 4]

例如：
- 不改 backend route 以外的业务域
- 不改 Search / Files / Media / Recent 无关页面
- 不做大范围 UI 重构
- 不引入新的平台/插件/队列/微服务结构

---

## 6. 具体行为/语义要求

### 核心语义
- [语义要求 1]
- [语义要求 2]
- [语义要求 3]

### 错误处理
- [错误码 / 错误行为 1]
- [错误码 / 错误行为 2]

### 状态处理
- [loading / empty / error 要求]
- [局部状态与全局状态边界]

### 数据语义
- [字段语义要求 1]
- [字段语义要求 2]

---

## 7. 约束条件

必须遵守：

- 保持 router / service / repository 边界清晰
- repository 不承担业务流程语义
- service 负责业务规则与事务边界
- 不扩大 phase scope
- 不顺手做下一阶段功能
- diff 尽量小
- 文档与实现保持一致

如果是桌面端相关：
- 优先最小 bridge/runtime 修复
- 不做深度 shell integration

如果是前端相关：
- loading / empty / error 尽量局部化
- 不让局部动作破坏整个页面或详情面板

---

## 8. 实现前要求输出

在开始编码前，先输出：

1. 你理解的根因 / 目标
2. 计划修改的精确文件列表
3. 明确不会修改的文件/区域
4. 预期调用链 / 数据流
5. 验证计划

如果你发现当前仓库真实状态与计划不一致：
- 先指出差异
- 不要直接按想象扩展实现

---

## 9. 实现后要求输出

完成后必须输出：

1. `What changed`
2. `Files changed`
3. `How to verify manually`
4. `What remains intentionally not implemented`
5. `Docs updated`
6. 如果有测试：给出运行命令和结果

---

## 10. 验收要求

### 自动化 / 构建
- backend unittest 通过
- frontend build 通过
- desktop build 通过（如涉及桌面端）

### 手工验证
至少覆盖：
- [主链操作 1]
- [主链操作 2]
- [主链操作 3]
- [负向场景 1]
- [负向场景 2]

### 通过标准
- 功能符合本阶段目标
- 没有明显越界到下一阶段
- 主要状态与错误处理合理
- 文档同步完成

---

## 11. 交付格式模板

你可以要求 Codex 用下面格式回复：

```text
What changed
- ...

Files changed
- ...

How to verify manually
- ...

Validation
- ...

What remains intentionally not implemented
- ...

Docs updated
- ...
```

---

## 12. 可直接替换使用的简版提示词

```text
Do not implement unrelated features.

Goal:
[填写本阶段唯一目标]

Scope:
- [范围 1]
- [范围 2]
- [范围 3]

Not allowed:
- [禁止项 1]
- [禁止项 2]
- [禁止项 3]

Primary files to inspect:
- [文件 1]
- [文件 2]
- [文件 3]

Before coding:
Output:
1. exact files to change
2. exact behavior/semantics
3. validation plan
4. what remains out of scope

After coding:
Output:
1. what changed
2. files changed
3. how to verify manually
4. what remains intentionally not implemented
5. docs updated
```

---

## 13. 备注

建议每个 phase 单独保留：
- plan
- implementation summary
- acceptance result

这样后续仓库演进时，最不容易丢失边界与上下文。

