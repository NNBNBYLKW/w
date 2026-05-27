# P0 Critical Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 critical issues identified in the architecture review: Electron sandbox bypass, SQL injection vector, missing error boundary, and interval memory leak.

**Architecture:** Four independent fixes spanning three tiers. No cross-task dependencies — each task can be implemented and verified independently.

**Tech Stack:** Electron (TypeScript), Python 3.12 (FastAPI + SQLite), React 18 (TypeScript + Vitest)

---

### Task 1: Close Electron sandbox — move `openContainingFolder` fs ops to main process via IPC

**Files:**
- Modify: `apps/desktop/electron/main.ts:325` (enable sandbox, add IPC handler)
- Modify: `apps/desktop/electron/preload.ts:73-112` (replace fs calls with IPC invoke)

The preload script currently runs with `sandbox: false` because `openContainingFolder` uses `node:fs` (`fs.existsSync`, `fs.statSync`) to validate paths before opening them via `shell.openPath`. Move the fs validation + shell.openPath to a new IPC handler in main process, then the preload can run sandboxed.

- [ ] **Step 1: Add IPC handler in main process for `open-containing-folder`**

In `apps/desktop/electron/main.ts`, add a new channel constant near the existing channel constants (after line 17):

```typescript
const openContainingFolderChannel = "asset-workbench:open-containing-folder";
```

Then add the IPC handler inside `app.whenReady().then(...)` (after line 421, before `createMainWindow()`):

```typescript
  ipcMain.handle(openContainingFolderChannel, async (_event, filePath: string) => {
    const normalized = filePath.trim().replace(/\//g, "\\");
    if (!normalized) {
      return { ok: false as const, reason: "A usable file path is required." };
    }

    const parentDir = path.win32.dirname(normalized);
    if (!parentDir || parentDir === "." || parentDir === normalized) {
      return { ok: false as const, reason: "A containing folder could not be derived from this file path." };
    }

    if (!fs.existsSync(parentDir)) {
      return { ok: false as const, reason: "The containing folder does not exist." };
    }

    try {
      if (!fs.statSync(parentDir).isDirectory()) {
        return { ok: false as const, reason: "The containing folder does not exist." };
      }
    } catch {
      return { ok: false as const, reason: "The containing folder could not be verified." };
    }

    const errorMessage = await shell.openPath(parentDir);
    if (errorMessage) {
      return { ok: false as const, reason: errorMessage };
    }

    return { ok: true as const };
  });
```

- [ ] **Step 2: Replace preload `openContainingFolder` with IPC invoke**

In `apps/desktop/electron/preload.ts`, remove the `node:fs` and `node:path` imports (lines 1-2). Remove `deriveContainingFolderPath` (lines 37-49). Replace `openContainingFolder` (lines 73-112) with:

```typescript
const openContainingFolderChannel = "asset-workbench:open-containing-folder";

async function openContainingFolder(filePath: string): Promise<OpenActionResult> {
  return ipcRenderer.invoke(openContainingFolderChannel, filePath);
}
```

Also remove the unused `normalizeInputPath` function (lines 31-34) if it's no longer used — check: it's still used by `openFile` (line 53), so keep it.

- [ ] **Step 3: Enable sandbox in BrowserWindow**

In `apps/desktop/electron/main.ts`, change `sandbox: false` to `sandbox: true` at line 325, and remove the comment on lines 323-324:

```typescript
      sandbox: true,
```

- [ ] **Step 4: Build and verify TypeScript compiles**

Run:
```powershell
Set-Location "T:\Windows\Documents\GitHub\w\apps\desktop"; npx tsc --noEmit
```

Expected: Zero TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add apps/desktop/electron/main.ts apps/desktop/electron/preload.ts
git commit -m "fix(desktop): move openContainingFolder fs ops to main process, enable sandbox"
```

---

### Task 2: Fix F-string SQL injection vector in `_table_columns()`

**Files:**
- Modify: `apps/backend/app/db/session/engine.py:384-385`

The function `_table_columns()` interpolates `table_name` directly into a PRAGMA query via f-string. All current callers pass hardcoded table names, making it unexploitable today, but the function signature is a latent injection vector. The fix uses a parameterized approach by validating `table_name` against SQLite's own `sqlite_master` table.

- [ ] **Step 1: Replace the f-string with a safe query**

In `apps/backend/app/db/session/engine.py`, replace lines 384-385:

```python
def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = ? AND name = ?",
        ("table", table_name),
    ).fetchone()
    if row is None:
        return set()
    return {str(col[1]) for col in connection.execute(
        "PRAGMA table_info(?)", (table_name,)
    ).fetchall()}
```

The initial `sqlite_master` lookup validates that `table_name` is a real table before passing it to PRAGMA. If `table_name` is not a valid table identifier, an empty set is returned — no SQL injection possible.

- [ ] **Step 2: Run backend tests to verify schema init still works**

Run:
```powershell
Set-Location "T:\Windows\Documents\GitHub\w\apps\backend"
& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest tests/test_phase0_smoke.py tests/test_library_v2_recovery.py -v --tb=short
```

Expected: All schema-related tests pass (no PRAGMA errors).

- [ ] **Step 3: Commit**

```bash
git add apps/backend/app/db/session/engine.py
git commit -m "fix(backend): replace f-string SQL in _table_columns with parameterized PRAGMA"
```

---

### Task 3: Add React ErrorBoundary to AppProviders

**Files:**
- Create: `apps/frontend/src/shared/ui/ErrorBoundary.tsx`
- Modify: `apps/frontend/src/app/providers/AppProviders.tsx:22-29` (wrap children in ErrorBoundary)

- [ ] **Step 1: Create ErrorBoundary component**

Create `apps/frontend/src/shared/ui/ErrorBoundary.tsx`:

```tsx
import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[ErrorBoundary]", error.message, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "100vh",
            padding: 32,
            fontFamily: '"Segoe UI", sans-serif',
            color: "#5a1f1f",
            background: "#fff8f8",
          }}
        >
          <div style={{ maxWidth: 480, textAlign: "center" }}>
            <h2 style={{ margin: "0 0 12px", fontSize: 22 }}>Something went wrong</h2>
            <p style={{ color: "#876a6a", lineHeight: 1.6, margin: "0 0 20px" }}>
              An unexpected error occurred. Try refreshing the page.
            </p>
            <details style={{ textAlign: "left", fontSize: 13, color: "#6b4f4f" }}>
              <summary style={{ cursor: "pointer", marginBottom: 8 }}>Error details</summary>
              <pre style={{
                padding: 12,
                borderRadius: 8,
                background: "#fff",
                border: "1px solid #f1c7c7",
                overflow: "auto",
                maxHeight: 200,
              }}>
                {this.state.error?.message ?? "Unknown error"}
              </pre>
            </details>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

- [ ] **Step 2: Wrap children in ErrorBoundary inside AppProviders**

In `apps/frontend/src/app/providers/AppProviders.tsx`, add the import (after line 5):

```tsx
import { ErrorBoundary } from "../../shared/ui/ErrorBoundary";
```

Then wrap the `{children}` in the return statement (line 26):

```tsx
          <Router><ErrorBoundary>{children}</ErrorBoundary></Router>
```

- [ ] **Step 3: Write a test for ErrorBoundary**

Add to `apps/frontend/tests/components.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "../../src/shared/ui/ErrorBoundary";

function BrokenComponent(): JSX.Element {
  throw new Error("test crash");
}

describe("ErrorBoundary", () => {
  it("renders fallback UI when child throws", () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <BrokenComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("test crash")).toBeInTheDocument();
    (console.error as jest.Mock).mockRestore();
  });

  it("renders children normally when no error", () => {
    render(
      <ErrorBoundary>
        <p>all good</p>
      </ErrorBoundary>
    );
    expect(screen.getByText("all good")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run frontend tests**

Run:
```powershell
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npm test -- --run
```

Expected: All tests pass, including the 2 new ErrorBoundary tests.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/shared/ui/ErrorBoundary.tsx apps/frontend/src/app/providers/AppProviders.tsx apps/frontend/tests/components.test.tsx
git commit -m "feat(frontend): add ErrorBoundary component with test coverage"
```

---

### Task 4: Fix `useExecutePlan` interval memory leak

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/hooks/useExecutePlan.ts:27-46`

The `execute` function creates a `setInterval` on line 33 that is never cleaned up. If the component unmounts while polling, the interval continues firing and calls `setS` on an unmounted component. Fix by tracking the interval ID with `useRef` and clearing it on unmount.

- [ ] **Step 1: Add interval cleanup**

Replace the entire file `apps/frontend/src/features/browse-v2/hooks/useExecutePlan.ts`:

```tsx
import { useEffect, useRef, useState } from "react";
import { preparePlan, executePlan, getOrganizePlan, type PreparePlanResponse } from "../../../services/api/libraryOrganizeApi";

export interface ExecutePlanState {
  loading: boolean; planId: number | null;
  preflight: PreparePlanResponse | null; error: string | null;
  executed: boolean; executionStatus: string | null;
  summary: Record<string, unknown> | null;
  progress: { total: number; done: number } | null;
}

export function useExecutePlan() {
  const [s, setS] = useState<ExecutePlanState>({
    loading: false, planId: null, preflight: null, error: null,
    executed: false, executionStatus: null, summary: null,
    progress: null,
  });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current !== null) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

  const start = async (planId: number) => {
    setS({ loading: true, planId, preflight: null, error: null, executed: false, executionStatus: null, summary: null, progress: null });
    try {
      const pf = await preparePlan(planId);
      setS(prev => ({ ...prev, loading: false, preflight: pf }));
    } catch (e) { setS(prev => ({ ...prev, loading: false, error: String(e) })); }
  };

  const execute = async () => {
    if (!s.preflight?.can_execute || s.planId === null) return;
    setS(prev => ({ ...prev, loading: true }));
    try {
      const planId = s.planId;
      await executePlan(planId);
      const poll = setInterval(async () => {
        try {
          const detail = await getOrganizePlan(planId);
          const actions = detail.actions as Array<{status: string}>;
          const done = actions.filter(a => a.status === "succeeded" || a.status === "failed").length;
          setS(prev => ({ ...prev, progress: { total: actions.length, done } }));
          if (["completed", "completed_with_errors", "failed"].includes(detail.plan.status)) {
            clearInterval(poll);
            pollRef.current = null;
            let summary: Record<string, unknown> | null = null;
            try { if (detail.plan.summary_json) summary = JSON.parse(detail.plan.summary_json); } catch {}
            setS(prev => ({ ...prev, loading: false, executed: true, executionStatus: detail.plan.status, summary, progress: null }));
          }
        } catch { /* keep polling */ }
      }, 2000);
      pollRef.current = poll;
    } catch (e) { setS(prev => ({ ...prev, loading: false, error: String(e) })); }
  };

  const reset = () => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setS({
      loading: false, planId: null, preflight: null, error: null,
      executed: false, executionStatus: null, summary: null, progress: null,
    });
  };

  return { ...s, start, execute, reset };
}
```

Key changes:
- Added `useRef<ReturnType<typeof setInterval> | null>(null)` to track the interval ID
- Added `useEffect` cleanup that clears the interval on unmount
- Captured `planId` in a local variable before the interval closure to avoid stale state
- `reset()` also clears any active interval
- On poll completion, sets `pollRef.current = null` to mark cleanup as handled

- [ ] **Step 2: Verify TypeScript compiles**

Run:
```powershell
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx tsc --noEmit 2>&1 | Select-String "useExecutePlan"
```

Expected: No errors referencing `useExecutePlan`.

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/features/browse-v2/hooks/useExecutePlan.ts
git commit -m "fix(frontend): clean up useExecutePlan polling interval on unmount"
```

---

## Final Verification

After all 4 tasks are complete, run the full test suites:

```powershell
# Backend tests
Set-Location "T:\Windows\Documents\GitHub\w\apps\backend"
& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest tests/ --tb=short -q 2>&1 | Select-Object -Last 5

# Frontend tests
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"
npm test -- --run 2>&1 | Select-Object -Last 10

# Desktop TypeScript check
Set-Location "T:\Windows\Documents\GitHub\w\apps\desktop"
npx tsc --noEmit
```

Expected:
- Backend: 808 passed, 1 pre-existing failure (unchanged)
- Frontend: All tests pass (at least 32: existing 30 + 2 new ErrorBoundary tests)
- Desktop: Zero TypeScript errors
