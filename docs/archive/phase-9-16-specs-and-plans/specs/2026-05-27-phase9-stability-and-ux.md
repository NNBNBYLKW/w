# Phase 9 — 稳定性和体验升级：设计规范

> 2026-05-27 | 状态：待实施
> 涵盖：Bug 修复、共享组件基础设施、UX 统一、清理、技术债务、功能收尾

---

## 目标

修复数据完整性问题，统一前端 UX 模式，清理死代码，完成 Library v2 最后子阶段，为正式版奠定基础。

## 原则

- 每批次产出可独立测试和交付的工作软件
- 所有共享组件均编写测试
- 破坏性操作必须经过确认对话框
- 不引入新的深层能力或改变产品边界

---

## 批次 A：基础 Bug 修复（无依赖，先交付）

### B1：修复修订计划完成状态变异（P0）

**文件：** `apps/backend/app/services/library/organize.py`

**问题：** `_finalize_amendment_plan` 在 `completed_with_errors` 状态下变更对象成员关系。规范要求：仅 `completed` 状态可变更成员关系。

**修复：** 在 `_finalize_amendment_plan` 中查找成员关系变更逻辑（添加/移除成员数据库写入）。在变更代码块前增加守卫：若 `plan.status != "completed"`，仅记录日志后返回，跳过所有成员关系变更。

**测试：**
```python
def test_amendment_completed_with_errors_does_not_mutate_membership(self):
    # 执行一个会产生 completed_with_errors 的修订计划
    # 断言对象成员计数与执行前相同
```

**文件修改范围：** `organize.py`（守卫语句，约 5 行）、`tests/test_library_organize.py` 或等效文件（新增测试用例）。

---

### B2：修复移除成员目标目录缺失（P1）

**文件：** `apps/backend/app/services/library/organize.py`

**问题：** 移除成员计划以 `90_Loose/Removed_{object_root}` 为目标路径，但计划中未生成对应的 `mkdir` 操作，新移除成员流程预检查失败。

**修复：** 在移除成员计划生成逻辑中，当计算出的目标目录尚不存在于文件系统时，在实际 `move` 操作前插入一个 `action_type = "mkdir"` 的创建目录操作。

**测试：**
```python
def test_remove_member_plan_includes_mkdir_for_missing_target(self):
    # 创建移除成员计划
    # 断言操作列表中有一个 mkdir 操作，目标为 90_Loose/Removed_xxx
    # 预检查通过
```

**文件修改范围：** `organize.py`（计划生成逻辑，约 10 行）、相应测试文件。

---

### B3：修复 GET 端点变更数据库状态（P1）

**文件：** `apps/backend/app/api/routes/library_organize.py`

**问题：** `get_plan_detail`（GET `/plans/{id}`）内部调用 `_refresh_plan_conflicts` + `session.commit()`，违反 HTTP GET 只读语义。

**修复：** 从 `get_plan_detail` 中移除 `_refresh_plan_conflicts` 的提交调用。将冲突刷新移至 `mark_ready`（POST）和新增的 `POST /plans/{id}/refresh-conflicts` 端点。若 `get_plan_detail` 返回的数据中需要冲突状态，可在 GET 中计算但不提交；亦可仅返回已存储的冲突数据。

**测试：**
```python
def test_get_plan_detail_does_not_write_to_database(self):
    # 对 GET /plans/{id} 发出请求
    # 使用 sqlalchemy 检查会话的 dirty/new 集合是否为空
    # 或不启动任何提交
```

**文件修改范围：** `library_organize.py`（移除提交，约 5 行）、`organize.py`（如需拆分刷新方法）、相应测试文件。

---

## 批次 B：共享组件基础设施（依赖批次 A 完成）

### S1：Modal 组件

**创建：** `apps/frontend/src/shared/ui/components/Modal.tsx`

**API：**
```tsx
interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  width?: number; // 默认 520
}
```

**行为：** Portal 渲染（`createPortal` → `document.body`）。焦点陷井（Tab 在 Modal 内循环）。按 Escape 关闭。点击遮罩层关闭。`aria-modal="true"`、`role="dialog"`、`aria-labelledby`。

**测试：**
- 关闭状态下不渲染任何内容
- 打开状态下渲染标题和子内容
- 按 Escape 触发 onClose
- 点击遮罩层触发 onClose
- 焦点停留在 Modal 内

**重构影响：** 后续批次中，`ComposeObjectModal` 和收件箱 Modal 迁移为使用此组件。

---

### S2：Pagination 组件

**创建：** `apps/frontend/src/shared/ui/components/Pagination.tsx`

**API：**
```tsx
interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  showPageInput?: boolean; // 默认 false
}
```

**渲染：** "第 {page} 页，共 {totalPages} 页" + 上一页按钮（第 1 页时禁用）+ 下一 页按钮（最后一页时禁用）。若 `showPageInput` 为 true，则额外显示跳转至第 N 页的输入框。

**测试：**
- 处于第 1 页时上一页按钮禁用
- 处于最后一页时下一页按钮禁用
- 点击上一页/下一页后触发 onPageChange，传入正确值
- 当 totalPages = 0 时渲染 "无结果"

**重构影响：** 后续批次中接入 Search、Tags、Collections、BrowseV2、Recent、FileBrowser 的 Pagination（约 6 处）。

---

### S3：ProgressBar 组件

**创建：** `apps/frontend/src/shared/ui/components/ProgressBar.tsx`

**API：**
```tsx
interface ProgressBarProps {
  done: number;
  total: number;
  showLabel?: boolean; // 默认 false — 显示 "45 / 100"
}
```

**渲染：** 彩色填充条（`width: (done/total)%`），CSS transition 动画。若 `total` 为 0 则渲染不确定进度条（脉冲动画）。

**测试：**
- 渲染正确的填充宽度
- `showLabel` 展示 "45 / 100"
- done = 0 / total = 0 渲染不确定参数变体

---

### U2：ConfirmDialog 组件

**创建：** `apps/frontend/src/shared/ui/components/ConfirmDialog.tsx`

**API：**
```tsx
interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string; // 默认 "确认"
  onConfirm: () => void;
  onCancel: () => void;
}
```

**实现：** 基于 Modal。底部操作栏：取消按钮 + 确认按钮（危险操作可用红色样式）。

**测试：**
- 点击确认后触发 onConfirm
- 点击取消后触发 onCancel
- 未交互时仅显示标题和消息

---

### U1：Toast 组件

**创建：** `apps/frontend/src/app/shell/ToastContainer.tsx`

**说明：** `uiStore` 已有 `toasts: ToastItem[]` 数组和 `pushToast` / `dismissToast` 方法。ToastContainer 在 `AppShell` 中渲染，订阅 `useUIStore` 中的 toasts。

**渲染：** 固定定位，右下角。每条 toast 4 秒后自动消失。类型：`success`（绿色）、`error`（红色）、`info`（蓝色）。退出时带淡出动画。

**测试：**
- 调用 pushToast 后 toast 渲染
- 4 秒后 toast 消失
- 可手动关闭某条 toast
- 多条 toast 正确堆叠显示

---

## 批次 C：UX 统一与清理（依赖批次 B 完成）

### U3：统一空/加载/错误状态

**文件：** 约 8 个 feature 文件

**方案：**
- 将 `LoadingState` 已有组件接入 `SourceManagementFeature` 和 `FileBrowserFeature`（替换 `<p>Loading...</p>`）
- 将 `EmptyState` 已有组件接入 `TagBrowserFeature`、`BooksFeature`、`GamesFeature`、`SoftwareFeature`、`MediaLibraryFeature`、`FileBrowserFeature`（替换 `div.future-frame`）
- 新建 `ErrorState` 组件：

```tsx
interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}
```

在各 feature 中替换 `status-block` div，接入该组件。

**测试：** 确认每个仍有效的 feature 在加载中、空结果、错误这三种场景下均有正确渲染。

---

### U4：全局键盘快捷键

**创建：** `apps/frontend/src/shared/hooks/useKeyboardShortcuts.ts`

**方案：**
```tsx
// 注册于 AppShell
useKeyboardShortcuts({
  "Control+k": () => navigate("/search"),
  "/": () => { if (!isInputFocused()) navigate("/search"); },
  "Escape": () => { closeDetailsPanel(); },
});
```

检查 `event.target` 是否为 `input` / `textarea` / `[contenteditable]`，若是则跳过 `/` 的绑定。`useEffect` 在组件挂载时添加监听，卸载时移除。

**测试：** 验证按键触发预期操作，且在输入框中跳过文本类快捷键。

---

### C1：移除废弃的 Books/Games/Software Feature

**文件：** 删除以下文件，并清理相关引用。

**删除（feature + 页面）：**
- `apps/frontend/src/features/books/BooksFeature.tsx`
- `apps/frontend/src/pages/books/BooksPage.tsx`
- `apps/frontend/src/features/games/GamesFeature.tsx`
- `apps/frontend/src/pages/games/GamesPage.tsx`
- `apps/frontend/src/features/software/SoftwareFeature.tsx`
- `apps/frontend/src/pages/software/SoftwarePage.tsx`
- `apps/frontend/src/features/media-library/MediaLibraryFeature.tsx`
- `apps/frontend/src/pages/media-library/MediaLibraryPage.tsx`

**检查后删除（实体类型）：**
- 检查 `entities/book/types.ts`、`entities/game/types.ts`、`entities/software/types.ts` 是否仍被未弃用的代码引用
- 若仅被上述已弃用的 feature 引用，则一并删除；否则保留

**修改：**
- `router/index.tsx` — 移除这些页面的导入和重定向规则
- 导航栏中移除这些入口（如存在）

---

### C2：统一 API 客户端

**创建：** `apps/frontend/src/services/api/client.ts`

```tsx
export function getApiBaseUrl(): string {
  // 此为全局唯一的实现，从现有代码中提取
  // 检查 desktop bridge → env var → 回退到 localhost
}

export async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? body.message ?? `HTTP ${response.status}`);
  }
  return response.json();
}
```

**修改：** 约 20 个 API 文件，将各自的 `getApiBaseUrl()` 和 `parseResponse()` 改为从 `client.ts` 导入。

---

### E1：详情面板"复制路径"按钮

**文件：** `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`

**方案：** 在 `DetailsFactListSection` 中文件路径旁增加一个 `Copy` 按钮。点击后将路径写入剪贴板，短暂显示"已复制"。

```tsx
const [copied, setCopied] = useState(false);
const handleCopy = async () => {
  await navigator.clipboard.writeText(file.path);
  setCopied(true);
  setTimeout(() => setCopied(false), 2000);
};
```

---

### E2：设置页面扩充

**文件：** `apps/frontend/src/pages/settings/SettingsPage.tsx`、`apps/frontend/src/locales/en/settings.ts`、`apps/frontend/src/locales/zh-CN/settings.ts`

**方案：** 新增两个 SectionCard：

1. **关于**：应用名称（Workbench Beta）、版本号（v0.2.0）、数据库路径（仅展示）、数据目录路径（仅展示）— 从 `/system/status` 获取
2. **缓存管理**：展示缩略图缓存估算大小（通过 thumbnail warmup API 获取）、"清除缓存"按钮 + ConfirmDialog 确认

---

### F2：对象成员计数修复

**文件：** `apps/backend/app/services/library/browse_v2.py`

**问题：** `LibraryObject` 模型没有 `member_count` 列，BrowseV2 查询未计算该字段。对象卡牌显示 "0 members"。

**修复：** 在 BrowseV2 的 `_build_object_cards` 或等效方法中，为每个对象增加子查询：`SELECT COUNT(*) FROM library_object_members WHERE object_id = ? AND member_status = 'active'`，将结果填充为 `member_count`。

**前端：** 确认 BrowseV2 卡牌组件读取并使用 `member_count` 字段。

---

## 批次 D：技术债务与收尾（与批次 C 可并行）

### T1：`datetime.utcnow` → `datetime.now(UTC)`

**文件：** 所有 `apps/backend/app/` 和 `apps/backend/tests/` 中的 Python 文件

**方案：** 全局替换 `datetime.utcnow()` → `utcnow()`（`app/core/time.py` 中已有的辅助函数）。在约 15 个服务/路由中删除各自的 `_utcnow()` 重复定义。使用脚本辅助完成批量替换。替换后运行完整测试套件验证。

---

### T2：路由级代码分割

**文件：** `apps/frontend/src/app/router/index.tsx`

**方案：** 将以下页面改为 `React.lazy` 懒加载：
- `HomePage`、`OnboardingPage`、`ToolsPage`、`RecentImportsPage`、`TagsPage`、`CollectionsPage`

每个均使用已有的 `PageLoader` Suspense 包装。预期将首屏 JS 体积从 848 KB 降低至约 400-500 KB。

---

### T3：数据库自动备份 + 日志轮转

**文件：** `apps/backend/app/main.py`

**方案：**
- `_backup_database()` 已存在（保留 3 份轮转备份）。无需改动。
- `_setup_logging()`：将 `backupCount` 从 5 增大到 10。增加应用启动时间戳日志。
- 在 `/system/status` 响应中增加 `last_backup_at` 字段，从最新备份文件的修改时间读取。

---

### F1：领域特定对象卡牌（Phase 8E）

**文件：** `apps/frontend/src/features/browse-v2/ObjectCard.tsx`（或等效的卡牌组件）

**方案：** 基于 `object_type` 属性进行条件渲染：

| object_type | 卡牌样式 |
|---|---|
| `movie` / `video` | 海报比例卡牌（aspect-ratio: 2/3），展示标题 + 年份 |
| `game` | 展示检测到的可执行文件数量 + 标题 |
| `book` / `document` | 展示格式标签（PDF/EPUB/DOCX）+ 标题 |
| 其他 | 现有默认卡牌，展示类型前缀 + 标题 |

**数据源：** 使用已有字段 — `object_type`、`title`、`year`、`primary_file_path`、`type_prefix`。不新增 API 端点或数据库列。所有信息已存在于 BrowseV2 响应中。

**CSS：** `apps/frontend/src/app/styles/browse.css` — 新增 `.object-card--movie`、`.object-card--game`、`.object-card--document` 样式类。

---

## 依赖关系图

```
批次 A (Bug 修复，无依赖)
  └── 批次 B (共享组件，依赖 A 通过)
       └── 批次 C (UX 统一，依赖 B)
  └── 批次 D (技术债务，与 C 并行)
```

## 验证策略

每批次完成后：
- 后端：`pytest tests/ -q` — 所有测试通过，无回归
- 前端：`vitest run` — 所有测试通过，新增测试覆盖新增组件
- 前端 TS：`tsc --noEmit` — 零错误
- 手动冒烟：导航至关键页面，确认无白屏

---

## 范围外（明确不纳入 Phase 9）

- 性能优化（扫描速度、虚拟化、数据库索引）→ Phase 10
- `organize.py` 拆分 → Phase 10
- CSS 文件组件级拆分 → Phase 10
- CI/CD 搭建 → Phase 10
- 深层能力（视频播放器、游戏启动器、AI 等）→ Phase 11+
- macOS/Linux 支持
- 自动更新系统
