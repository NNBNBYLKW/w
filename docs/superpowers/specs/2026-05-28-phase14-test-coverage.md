# Phase 14 — 测试填补：设计规范

> 2026-05-28 | 状态：待实施
> 范围：15 项测试填补——后端新功能测试、前端 hook/feature 测试、E2E 配置

---

## 目标

填补评估中发现的测试空白：为 Phase 12/13 新增后端功能添加测试，为前端 hooks 和核心 features 添加测试，搭建 E2E 测试框架。

## 原则

- 测试行为，不测试实现细节
- 后端测试遵循已有的 TestCase + TestClient 模式
- 前端测试使用 @testing-library/react + vitest
- E2E 使用已有的 Playwright 依赖，不新增包

---

## 批次 A：后端新功能测试（5 项）

### A1：Checksum worker 测试
**文件：** `apps/backend/tests/test_checksum_worker.py`
- test_compute_sha256_known_content（对已知内容验证正确的 SHA-256）
- test_compute_sha256_empty_file（空文件 → 已知 hash）
- test_compute_sha256_nonexistent_file（FileNotFoundError）

### A2：Trash/Restore 测试
**文件：** `apps/backend/tests/test_trash.py`
- test_trash_file（标记 is_deleted=True，创建 TrashEntry）
- test_restore_file（恢复 is_deleted=False，删除 TrashEntry）
- test_list_trash（返回已删除文件列表）
- test_trash_already_deleted（对已删除文件调用 trash 返回 400）
- test_restore_not_trashed（对未删除文件调用 restore 返回 404）

### A3：Game sessions 测试
**文件：** `apps/backend/tests/test_game_sessions.py`
- test_start_session（创建 session，返回 id）
- test_end_session（设置 ended_at + duration_seconds）
- test_end_nonexistent_session（返回 404）

### A4：Move import 测试
**文件：** `apps/backend/tests/test_move_import.py`
- test_move_same_volume（使用临时目录验证 shutil.move 行为）
- test_copy_cross_volume（模拟跨卷回退）
- test_import_preserves_file_content（移动后内容不变）

### A5：分类 suggester + EPUB parser 测试
**文件：** `apps/backend/tests/test_classification_suggester.py`
- test_suggests_game_from_path（游戏目录 → 游戏建议）
- test_suggests_document_from_keyword（文件名含 document/movie 关键词）
- test_empty_suggestions_for_unknown（未知文件 → 返回空列表）

**文件：** `apps/backend/tests/test_epub_parser.py`
- test_parse_valid_epub（解析有效 EPUB，返回标题 + 章节）
- test_parse_corrupted_epub（损坏文件优雅处理）

---

## 批次 B：前端核心测试（5 项）

### B1：Hooks 测试 — useErrorMessage、useKeyboardShortcuts
**文件：** `apps/frontend/tests/hooks.test.tsx`

```tsx
// useErrorMessage
test("returns user-friendly message for known code")
test("returns raw message for unknown error")
test("returns fallback for non-Error values")

// useKeyboardShortcuts（使用 test harness 组件）
test("Ctrl+K navigates to /search")
test("Escape closes details panel")
test("slash in input field does not navigate")
```

### B2：Hooks 测试 — useVirtualList
**文件：** `apps/frontend/tests/virtual-list.test.tsx`

```tsx
test("computes startIndex and endIndex from scrollTop")
test("returns 0 items when totalItems is 0")
test("offsetY equals startIndex * itemHeight")
test("totalHeight equals totalItems * itemHeight")
```

### B3：Shared component 测试 — CardSkeleton、Lightbox、ErrorState、EmptyState
**文件：** `apps/frontend/tests/more-components.test.tsx`

```tsx
// CardSkeleton
test("renders N skeleton cards")
test("renders row variant with different height")
test("default count is 6")

// Lightbox
test("renders image when open")
test("click toggles zoom scale")
test("renders nothing when closed")

// ErrorState
test("renders message text")
test("renders retry button when onRetry provided")
test("calls onRetry on button click")

// EmptyState
test("renders title and description")
test("renders action button when provided")
```

### B4：BrowseV2Feature 核心路径测试
**文件：** `apps/frontend/tests/browse-v2.test.tsx`

```tsx
test("renders domain selector with correct options")
test("renders cards from API data")
test("shows loading skeleton while fetching")
test("shows empty state when no cards")
test("clicking card selects it and opens detail panel")
```

### B5：SearchFeature + TagBrowserFeature 核心路径测试
add to browse-v2 test file or separate:

```tsx
// Search
test("renders search input and submits query")
test("shows search history dropdown on focus")
test("renders filter controls (source, parent_path, favorites, rating)")

// TagBrowser
test("renders tag list with colored dots")
test("shows rename/delete/merge menu on tag click")
test("shows tag file results when tag selected")
```

---

## 批次 C：E2E + CI 增强（3 项）

### C1：Playwright E2E 配置
**文件：** `apps/frontend/playwright.config.ts`（新建）

```typescript
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://127.0.0.1:5173" },
  webServer: { command: "npm run dev", url: "http://127.0.0.1:5173", reuseExistingServer: true },
});
```

### C2：核心 E2E 冒烟测试
**文件：** `apps/frontend/e2e/smoke.spec.ts`（新建）

```typescript
test("homepage loads and shows navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".app-sidebar")).toBeVisible();
});

test("can navigate to settings", async ({ page }) => {
  await page.goto("/");
  await page.click("text=Settings");
  await expect(page.locator("text=Theme")).toBeVisible();
});

test("search page loads with input", async ({ page }) => {
  await page.goto("/search");
  await expect(page.locator("input[placeholder*='Search']")).toBeVisible();
});
```

### C3：CI 添加前端 linting
**文件：** `.github/workflows/ci.yml`

在 frontend job 中添加：
```yaml
- run: npx tsc --noEmit  # already exists
- run: npx eslint src/ --ext .ts,.tsx --max-warnings 0  # new
```

在 backend job 中添加：
```yaml
- run: pip install ruff && ruff check apps/backend/  # new
```

---

## 依赖关系

批次 A（后端测试）→ 无依赖，5 项均可并行
批次 B（前端测试）→ 无依赖，5 项均可并行
批次 C（E2E + CI）→ 无依赖，3 项均可并行

所有 3 个批次可完全并行。总共 13 项。

## 验证

- 后端：新增测试全部通过，已有 809 项测试无回归
- 前端：新增测试全部通过，已有 62 项测试无回归
- E2E：Playwright 冒烟测试在开发服务器上通过
- CI：linting 步骤无 new violations
