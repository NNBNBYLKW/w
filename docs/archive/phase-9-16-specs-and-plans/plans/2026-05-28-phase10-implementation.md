# Phase 10 — Performance, Tech Debt, and Feature Enhancement: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 2 remaining bugs, scale performance to 50K+ files, split all remaining God modules/CSS, add CI/CD, and implement 11 feature enhancements and organization-layer extensions — 30 active tasks across 4 batches.

**Architecture:** Batch A (bug fixes + DB hardening) → Batch B (performance scaling) → Batch C (tech debt cleanup) → Batch D (feature enhancements). Batches are independent — any batch can start once its dependencies are met.

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy + SQLite (backend), React 18 + TypeScript + Vitest + CSS (frontend), GitHub Actions (CI/CD)

---

## Batch A: Bug Fixes + Database Hardening (5 tasks)

### Task A1: Fix BrowseV2 object_count / loose_file_count TypeScript errors

**Files:**
- Modify: `apps/backend/app/schemas/browse_v2.py` — add fields to response schema
- Modify: `apps/frontend/src/services/api/browseV2Api.ts` — add fields to TS type
- Verify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx:294-295` — uses these fields

- [ ] **Step 1: Add fields to backend response schema**

In `apps/backend/app/schemas/browse_v2.py`, find the `BrowseV2Response` class and add:

```python
class BrowseV2Response(BaseModel):
    items: list[BrowseV2Card]
    page: int
    page_size: int
    total_pages: int
    total_items: int
    summary: BrowseV2Summary | None = None
    object_count: int = 0
    loose_file_count: int = 0
```

- [ ] **Step 2: Populate the fields in the browse_v2 service**

In `apps/backend/app/services/library/browse_v2.py`, in the `list_cards` method that builds the response dict, add:

```python
result["object_count"] = len([c for c in combined if c.get("card_kind") == "object"])
result["loose_file_count"] = len([c for c in combined if c.get("card_kind") == "file"])
```

- [ ] **Step 3: Add fields to frontend type**

In `apps/frontend/src/services/api/browseV2Api.ts`, update `BrowseV2Response`:

```typescript
export interface BrowseV2Response {
  items: BrowseV2Card[];
  page: number;
  page_size: number;
  total_pages: number;
  total_items: number;
  summary: BrowseV2Summary | null;
  object_count: number;
  loose_file_count: number;
}
```

- [ ] **Step 4: Verify TS errors are resolved**

Run: `Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx tsc --noEmit 2>&1 | Select-String "object_count|loose_file_count"`

Expected: No errors referencing these fields.

- [ ] **Step 5: Run backend tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/schemas/browse_v2.py apps/backend/app/services/library/browse_v2.py apps/frontend/src/services/api/browseV2Api.ts
git -C "T:\Windows\Documents\GitHub\w" commit -m "fix: add object_count and loose_file_count to BrowseV2 response"
```

---

### Task A2: Fix useExecutePlan unmount race condition

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/hooks/useExecutePlan.ts`

- [ ] **Step 1: Add cancellation ref**

Replace the hook implementation with the fixed version:

```typescript
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
    executed: false, executionStatus: null, summary: null, progress: null,
  });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
      if (pollRef.current !== null) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

  const start = async (planId: number) => {
    cancelledRef.current = false;
    setS({ loading: true, planId, preflight: null, error: null, executed: false, executionStatus: null, summary: null, progress: null });
    try {
      const pf = await preparePlan(planId);
      if (cancelledRef.current) return;
      setS(prev => ({ ...prev, loading: false, preflight: pf }));
    } catch (e) {
      if (cancelledRef.current) return;
      setS(prev => ({ ...prev, loading: false, error: String(e) }));
    }
  };

  const execute = async () => {
    if (!s.preflight?.can_execute || s.planId === null) return;
    if (pollRef.current !== null) return;
    setS(prev => ({ ...prev, loading: true }));
    try {
      const planId = s.planId;
      await executePlan(planId);
      if (cancelledRef.current) return;
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
    } catch (e) {
      if (cancelledRef.current) return;
      setS(prev => ({ ...prev, loading: false, error: String(e) }));
    }
  };

  const reset = () => {
    cancelledRef.current = true;
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

Key additions: `cancelledRef` checked after every `await`, `reset()` sets `cancelledRef.current = true`.

- [ ] **Step 2: Type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/browse-v2/hooks/useExecutePlan.ts
git -C "T:\Windows\Documents\GitHub\w" commit -m "fix(frontend): add cancellation ref to useExecutePlan to prevent unmount race"
```

---

### Task A3: Database migration version gating

**Files:**
- Modify: `apps/backend/app/db/session/engine.py:437-455`

- [ ] **Step 1: Wrap each _ensure_* call in version gating**

In `initialize_database()`, restructure to check `CURRENT_SCHEMA_VERSION` before running each migration block:

```python
CURRENT_SCHEMA_VERSION = 4  # bumped from 3

def initialize_database() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    sql = settings.baseline_sql_path.read_text(encoding="utf-8")
    connection = sqlite3.connect(settings.database_path)
    try:
        connection.executescript(sql)
        current = _get_schema_version(connection)
        if current < 1:
            _ensure_classification_columns(connection)
            _backfill_file_classification(connection)
        if current < 2:
            _ensure_tool_runs_table(connection)
            _ensure_library_object_tables(connection)
            _ensure_library_organize_tables(connection)
            _ensure_library_roots_table(connection)
        if current < 3:
            _ensure_library_v2_tables(connection)
            _ensure_library_v2_source(connection)
        if current < 4:
            _ensure_source_discovered_count(connection)
            _ensure_recovery_findings_table(connection)
        _ensure_schema_version(connection)
        connection.commit()
    finally:
        connection.close()

def _get_schema_version(connection: sqlite3.Connection) -> int:
    connection.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL, applied_at TEXT NOT NULL DEFAULT (datetime('now')))")
    row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return row[0] if row and row[0] is not None else 0
```

- [ ] **Step 2: Run backend tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/db/session/engine.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(backend): add version-gated database migration system"
```

---

### Task A4: Enable WAL mode + periodic VACUUM

**Files:**
- Modify: `apps/backend/app/db/session/engine.py`
- Modify: `apps/backend/app/main.py`

- [ ] **Step 1: Enable WAL mode in database initialization**

In `initialize_database()`, after the connection is created, add:

```python
connection.execute("PRAGMA journal_mode=WAL")
```

In `create_engine`, add `poolclass=StaticPool` and ensure WAL is set on each new connection via an event listener:

```python
from sqlalchemy.pool import StaticPool
from sqlalchemy import event

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(engine, "connect")
def _set_wal(dbapi_connection, connection_record):
    dbapi_connection.execute("PRAGMA journal_mode=WAL")
```

- [ ] **Step 2: Add periodic VACUUM to backup routine**

In `_backup_database()` in `main.py`, add:

```python
# VACUUM every 5th startup or when DB has doubled in size
backup_count_file = settings.data_dir / "backups" / "startup_count.txt"
try:
    count = int(backup_count_file.read_text().strip())
except Exception:
    count = 0
count += 1
backup_count_file.write_text(str(count))
if count >= 5:
    with sqlite3.connect(str(settings.database_path)) as conn:
        conn.execute("VACUUM")
    backup_count_file.write_text("0")
    logger.info("Database VACUUM completed")
```

- [ ] **Step 3: Run backend tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/db/session/engine.py apps/backend/app/main.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(backend): enable WAL mode and periodic VACUUM"
```

---

### Task A5: Convert plan_kind to StrEnum

**Files:**
- Modify: `apps/backend/app/db/models/organize.py`
- Modify: `apps/backend/app/services/library/organize.py`

- [ ] **Step 1: Convert PlanKind to StrEnum**

In `organize.py`, replace the PlanKind string constant class with:

```python
from enum import StrEnum

class PlanKind(StrEnum):
    ORGANIZE_INBOX = "organize_inbox"
    FIX_OBJECT_REVIEW = "fix_object_review"
    OBJECT_CREATION_MANAGED_COMPOSE = "object_creation_managed_compose"
    OBJECT_AMENDMENT = "object_amendment"
```

- [ ] **Step 2: Add SQLAlchemy enum to model**

In `apps/backend/app/db/models/organize.py`:

```python
from sqlalchemy import Enum as SAEnum
from app.services.library.organize import PlanKind

plan_kind: Mapped[str] = mapped_column(
    SAEnum(PlanKind, name="plan_kind_enum", create_constraint=False),
    nullable=False,
)
```

- [ ] **Step 3: Verify all PlanKind references use the enum values — run backend tests**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/db/models/organize.py apps/backend/app/services/library/organize.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "refactor(backend): convert PlanKind to StrEnum with SQLAlchemy enum type"
```

---

## Batch B: Performance Scaling (6 tasks)

### Task B1: Scan speed — bulk INSERT + metadata skip

**Files:**
- Modify: `apps/backend/app/workers/scanning/scanner.py`
- Modify: `apps/backend/app/services/scanning/service.py`

- [ ] **Step 1: Define skip-extensions set**

In `scanner.py`, define extensions that should skip metadata extraction:

```python
SKIP_METADATA_EXTENSIONS = {
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",  # archives
    ".exe", ".dll", ".msi", ".apk", ".app",               # executables
    ".iso", ".bin", ".cue", ".img",                        # disk images
    ".lnk", ".url",                                        # shortcuts
}
```

- [ ] **Step 2: Add skip-metadata flag to DiscoveredFileRecord**

In the `DiscoveredFileRecord` dataclass, add:

```python
skip_metadata: bool = False
```

Set it during scan: `skip_metadata = ext.lower() in SKIP_METADATA_EXTENSIONS`

- [ ] **Step 3: Implement batch UPSERT in scanning service**

In `scanning/service.py`, modify `run_source_scan_inline` to batch files:

```python
BATCH_SIZE = 500
scanned = scanner.scan_path(source.path)
batches = [scanned[i:i+BATCH_SIZE] for i in range(0, len(scanned), BATCH_SIZE)]
for batch in batches:
    file_repository.bulk_upsert_files(session, batch)
```

In FileRepository, add `bulk_upsert_files` using `session.execute(insert(File).values(...).on_conflict_do_update(...))`.

- [ ] **Step 4: Skip metadata extraction for skip-flagged files**

In `metadata/service.py:enrich_scanned_files`, check `record.skip_metadata` and skip the extraction for those files.

- [ ] **Step 5: Measure performance with 10K test files, run full test suite, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/scanning/scanner.py apps/backend/app/services/scanning/service.py apps/backend/app/repositories/file/repository.py apps/backend/app/services/metadata/service.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "perf(backend): implement bulk INSERT and metadata skip for scan speed"
```

---

### Task B2: Media grid virtualization

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`
- Create: `apps/frontend/src/shared/hooks/useVirtualList.ts`

- [ ] **Step 1: Create useVirtualList hook**

Create `apps/frontend/src/shared/hooks/useVirtualList.ts`:

```typescript
import { useState, useRef, useCallback, useEffect } from "react";

interface VirtualListOptions {
  itemHeight: number;
  overscan?: number;
  totalItems: number;
}

export function useVirtualList(
  containerRef: React.RefObject<HTMLElement>,
  { itemHeight, overscan = 3, totalItems }: VirtualListOptions,
) {
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      setContainerHeight(entries[0].contentRect.height);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [containerRef]);

  const onScroll = useCallback((e: React.UIEvent<HTMLElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(totalItems, startIndex + visibleCount + overscan * 2);
  const offsetY = startIndex * itemHeight;

  return {
    startIndex, endIndex, offsetY, totalHeight: totalItems * itemHeight, onScroll,
  };
}
```

- [ ] **Step 2: Apply to BrowseV2Feature card list**

In BrowseV2Feature, wrap the card grid container and use the hook:

```tsx
const containerRef = useRef<HTMLDivElement>(null);
const { startIndex, endIndex, offsetY, totalHeight, onScroll } = useVirtualList(
  containerRef,
  { itemHeight: 180, totalItems: allCards.length },
);
const visibleCards = allCards.slice(startIndex, endIndex);
```

Render `visibleCards` inside a container with `height: totalHeight` and `paddingTop: offsetY`.

- [ ] **Step 3: Run tests, type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/shared/hooks/useVirtualList.ts apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "perf(frontend): add virtualized window rendering for BrowseV2 card grid"
```

---

### Task B3: Fix BrowseV2 mixed pagination

**Files:**
- Modify: `apps/backend/app/services/library/browse_v2.py`

- [ ] **Step 1: Merge objects and loose files before pagination**

Replace the current logic (lines 268-282) with:

```python
    # Merge and sort all cards before pagination
    all_cards = object_cards + loose_file_cards
    
    # Sort: objects first, then loose files; alphabetically within each group
    all_cards.sort(key=lambda c: (
        0 if c.get("card_kind") == "object" else 1,
        str(c.get("title", "")).lower(),
    ))
    
    total_items = len(all_cards)
    total_pages = max(1, math.ceil(total_items / page_size))
    
    # Apply pagination to the merged list
    start = (page - 1) * page_size
    items = all_cards[start:start + page_size]
```

- [ ] **Step 2: Run backend tests, verify no skipped/duplicated cards**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/services/library/browse_v2.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "fix(backend): merge objects and loose files before pagination to prevent skipped cards"
```

---

### Task B4: Search/Recent query optimization

**Files:**
- Modify: `apps/backend/app/db/migrations/` (new index SQL)
- Modify: `apps/backend/app/db/session/engine.py` (add index creation)

- [ ] **Step 1: Add composite indexes**

In `engine.py`, add a new `_ensure_performance_indexes` function:

```python
def _ensure_performance_indexes(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_is_deleted_discovered_at "
        "ON files(is_deleted, discovered_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_is_deleted_name "
        "ON files(is_deleted, name)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_is_deleted_modified_at "
        "ON files(is_deleted, modified_at_fs)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_is_deleted_source_id "
        "ON files(is_deleted, source_id)"
    )
```

Call this in `initialize_database()` under the latest version gate.

- [ ] **Step 2: Run tests, verify query times improve, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/db/session/engine.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "perf(backend): add composite indexes for search, recent, and file listing queries"
```

---

### Task B5: Thumbnail progressive loading

**Files:**
- Modify: `apps/frontend/src/shared/ui/thumbnail.tsx`

- [ ] **Step 1: Implement intersection observer + lazy loading**

```tsx
import { useEffect, useRef, useState } from "react";

function useInView(options?: IntersectionObserverInit) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setInView(true);
        observer.disconnect();
      }
    }, options);
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref, options]);
  return { ref, inView };
}

// In thumbnail component:
const { ref, inView } = useInView({ rootMargin: "200px" });

return (
  <div ref={ref} className="thumbnail-container">
    {inView ? (
      <img src={thumbnailUrl} loading="lazy" alt="" />
    ) : (
      <div className="thumbnail-placeholder" />
    )}
  </div>
);
```

- [ ] **Step 2: Run tests, type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/shared/ui/thumbnail.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "perf(frontend): add intersection observer lazy loading for thumbnails"
```

---

### Task B6: Details panel switching performance

**Files:**
- Modify: `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`

- [ ] **Step 1: Add React.memo to section components**

```tsx
const MemoizedIdentitySection = React.memo(DetailsIdentitySection);
const MemoizedFactListSection = React.memo(DetailsFactListSection);
// ... apply to all 15 sections
```

- [ ] **Step 2: Use React Query staleTime to prevent refetches**

```tsx
const detailQuery = useQuery({
  queryKey: queryKeys.fileDetail(selectedItemId),
  queryFn: () => getFileDetails(selectedItemId!),
  enabled: selectedItemId !== null,
  staleTime: 30000, // 30s — don't refetch on focus if data is fresh
});
```

- [ ] **Step 3: Add key management**

```tsx
// Use file.id as key for the panel so React reuses the DOM
<div key={item.id} className="details-panel">
```

- [ ] **Step 4: Type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "perf(frontend): add React.memo, staleTime, and key management to details panel"
```

---

## Batch C: Tech Debt Deep Cleanup (9 tasks)

### Task C1: Split organize.py remaining steps

**Files:**
- Create: `apps/backend/app/services/library/organize_file_ops.py`
- Create: `apps/backend/app/services/library/organize_candidates.py`
- Modify: `apps/backend/app/services/library/organize.py`

- [ ] **Step 1: Extract file operations to organize_file_ops.py**

Move these methods from `OrganizeService` to a new `OrganizeFileOps` class: `_execute_mkdir`, `_execute_move`, `_execute_rename`, `_execute_write_asset_yaml`, `_execute_backup_asset_yaml`, `_resolve_root_for_mkdir_or_asset`

Create `organize_file_ops.py`:

```python
class OrganizeFileOps:
    """File operations extracted from OrganizeService."""
    
    @staticmethod
    def execute_mkdir(target: Path) -> None:
        target.mkdir(parents=True, exist_ok=False)
    
    @staticmethod
    def execute_move(source: Path, target: Path) -> None:
        shutil.move(str(source), str(target))
    
    # ... other methods
```

Update `organize.py` to import and delegate to `OrganizeFileOps`.

- [ ] **Step 2: Extract candidate management to organize_candidates.py**

Move methods: `_scan_candidates`, `_parse_candidate_source`, `_resolve_candidate_display_name`, `_generate_suggestions`, `_update_candidate_status`

Create `organize_candidates.py`:

```python
class OrganizeCandidateManager:
    """Candidate management extracted from OrganizeService."""
    
    def scan_candidates(self, session: Session, source: Source) -> list[OrganizeCandidate]:
        ...
```

- [ ] **Step 3: Verify organize.py is now ≤1500 lines, run full backend test suite**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/services/library/
git -C "T:\Windows\Documents\GitHub\w" commit -m "refactor(backend): extract file ops and candidate management from organize.py"
```

---

### Task C2: CSS component-level split

**Files:**
- Create: `apps/frontend/src/shared/ui/components/Modal.css`
- Create: `apps/frontend/src/shared/ui/components/ProgressBar.css`
- Create: `apps/frontend/src/shared/ui/components/Pagination.css`
- Modify: `apps/frontend/src/app/styles/components.css` (remove extracted styles)
- Modify: `apps/frontend/src/app/styles/shell.css` → split into `shell-layout.css`, `shell-sidebar.css`, `shell-titlebar.css`

- [ ] **Step 1: Extract Modal CSS**

Move all `.modal`-related styles (overlay, dialog, header, body, footer) from `components.css` to `Modal.css`. Import `Modal.css` in `Modal.tsx`.

- [ ] **Step 2: Extract ProgressBar CSS**

Move progress bar styles + `@keyframes progress-indeterminate` to `ProgressBar.css`. Import in `ProgressBar.tsx`.

- [ ] **Step 3: Extract Pagination CSS**

Move `.pagination` styles to `Pagination.css`. Import in `Pagination.tsx`.

- [ ] **Step 4: Split shell.css**

Split into:
- `shell-layout.css` — `.app-shell`, `.app-shell__content`, responsive
- `shell-sidebar.css` — `.app-sidebar`, nav items, collapse states
- `shell-titlebar.css` — `.desktop-titlebar` (desktop Electron mode)

Import each from their respective shell components.

- [ ] **Step 5: Verify no visual regressions, type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/
git -C "T:\Windows\Documents\GitHub\w" commit -m "refactor(frontend): split CSS into component-level files"
```

---

### Task C3: CI/CD pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]

jobs:
  backend:
    runs-on: windows-latest
    defaults:
      run:
        working-directory: apps/backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pip install httpx
      - run: python -m pytest tests/ -q --tb=line

  frontend:
    runs-on: windows-latest
    defaults:
      run:
        working-directory: apps/frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npx tsc --noEmit
      - run: npx vitest run
```

- [ ] **Step 2: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add .github/workflows/ci.yml
git -C "T:\Windows\Documents\GitHub\w" commit -m "ci: add GitHub Actions CI workflow for backend and frontend"
```

---

### Task C4: Extract inline workflow logic from routes

**Files:**
- Modify: `apps/backend/app/api/routes/importing.py`
- Modify: `apps/backend/app/api/routes/library.py`
- Modify: `apps/backend/app/services/importing/service.py`

- [ ] **Step 1: Move inline SQL from importing route to service**

Search `importing.py` for raw SQL/sa_text calls. Extract to `ImportService` methods. Route should only call service methods and return responses.

- [ ] **Step 2: Move aggregation from library route to service**

Search `library.py` for inline aggregation/logic. Extract to the appropriate service.

- [ ] **Step 3: Run backend tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/api/routes/ apps/backend/app/services/
git -C "T:\Windows\Documents\GitHub\w" commit -m "refactor(backend): extract inline SQL and aggregation from route layer to services"
```

---

### Task C5: Version number consistency

**Files:**
- Modify: `apps/frontend/package.json`
- Modify: `apps/desktop/package.json`
- Modify: `apps/backend/app/main.py`

- [ ] **Step 1: Standardize all versions to 0.3.0**

```json
// apps/frontend/package.json
"version": "0.3.0"

// apps/desktop/package.json
"version": "0.3.0"

// apps/backend/app/main.py
app = create_app()  # version updated to "0.3.0" in create_app
```

- [ ] **Step 2: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/package.json apps/desktop/package.json apps/backend/app/main.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "chore: standardize version numbers to 0.3.0 across all packages"
```

---

### Task C6: Skeleton component deduplication

**Files:**
- Create: `apps/frontend/src/shared/ui/components/CardSkeleton.tsx`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`

- [ ] **Step 1: Create unified CardSkeleton**

```tsx
interface CardSkeletonProps {
  count?: number;
  variant?: "card" | "row";
}

export function CardSkeleton({ count = 6, variant = "card" }: CardSkeletonProps) {
  return (
    <div className={`skeleton-grid skeleton-grid--${variant}`}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-card" aria-busy="true">
          <div className="skeleton-pulse" style={{ height: variant === "card" ? 120 : 40, borderRadius: 8 }} />
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Replace inline skeletons in BrowseV2Feature with CardSkeleton**

- [ ] **Step 3: Type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/shared/ui/components/CardSkeleton.tsx apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "refactor(frontend): create unified CardSkeleton, deduplicate loading skeletons"
```

---

### Task C7: Split BrowseV2Feature

**Files:**
- Create: `apps/frontend/src/features/browse-v2/hooks/useBrowseV2Filters.ts`
- Create: `apps/frontend/src/features/browse-v2/BrowseV2CardList.tsx`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`

- [ ] **Step 1: Extract useBrowseV2Filters hook**

Move all filter state (domain, category, storage, sort, page, searchParams) into `useBrowseV2Filters.ts`:

```typescript
export function useBrowseV2Filters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const domain = searchParams.get("domain") ?? "media";
  const category = searchParams.get("category") ?? undefined;
  const sort = searchParams.get("sort") ?? "title";
  const order = searchParams.get("order") ?? "asc";
  const page = parseInt(searchParams.get("page") ?? "1", 10);
  
  const setFilter = (key: string, value: string | null) => {
    const next = new URLSearchParams(searchParams);
    if (value === null) next.delete(key);
    else next.set(key, value);
    setSearchParams(next);
  };
  
  return { domain, category, sort, order, page, setFilter, setPage: (p: number) => setFilter("page", String(p)) };
}
```

- [ ] **Step 2: Extract BrowseV2CardList component**

Move card rendering into its own component:

```tsx
interface BrowseV2CardListProps {
  cards: BrowseV2Card[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDoubleClick: (card: BrowseV2Card) => void;
  viewMode: "details" | "icons";
}

export function BrowseV2CardList({ cards, selectedId, onSelect, onDoubleClick, viewMode }: BrowseV2CardListProps) {
  // virtualized list rendering
}
```

- [ ] **Step 3: Verify BrowseV2Feature ≤400 lines, type check, tests pass, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/browse-v2/
git -C "T:\Windows\Documents\GitHub\w" commit -m "refactor(frontend): split BrowseV2Feature into filter hook and card list component"
```

---

### Task C8: Split DetailsPanelFeature

**Files:**
- Create: `apps/frontend/src/features/details-panel/hooks/useDetailsMutations.ts`
- Create: `apps/frontend/src/features/details-panel/DetailsPanelBody.tsx`
- Modify: `apps/frontend/src/features/details-panel/DetailsPanelFeature.tsx`

- [ ] **Step 1: Extract useDetailsMutations hook**

Move all mutation logic (tag add/remove, color tag, status, user meta, placement, open action) into `useDetailsMutations.ts`. The hook takes `queryClient` and `selectedItemId`, returns mutation objects and their pending states.

- [ ] **Step 2: Extract DetailsPanelBody component**

Move the main content rendering (all 15 section components, error/loading/empty states) into `DetailsPanelBody.tsx`. Accepts `item`, all mutation handlers, and view state as props.

- [ ] **Step 3: Verify ≤400 lines, type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/details-panel/
git -C "T:\Windows\Documents\GitHub\w" commit -m "refactor(frontend): split DetailsPanelFeature into mutations hook and body component"
```

---

### Task C9: Split CollectionsFeature

**Files:**
- Create: `apps/frontend/src/features/collections/CollectionForm.tsx`
- Create: `apps/frontend/src/features/collections/CollectionList.tsx`
- Create: `apps/frontend/src/features/collections/CollectionResults.tsx`
- Modify: `apps/frontend/src/features/collections/CollectionsFeature.tsx`

- [ ] **Step 1: Extract CollectionForm**

Create/edit form component with name, file type filter, tag filter, color filter, save button. Accepts `onSave`, `initialValues`, `onCancel` as props.

- [ ] **Step 2: Extract CollectionList**

Left sidebar list of collections. Accepts `collections`, `selectedId`, `onSelect`, `onDelete`, `onReorder` as props.

- [ ] **Step 3: Extract CollectionResults**

Right panel showing files matching the selected collection. Accepts `collection`, `files`, `page`, `totalPages`, `onPageChange`, `onBrowseRedirect` as props.

- [ ] **Step 4: Verify ≤400 lines, type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/collections/
git -C "T:\Windows\Documents\GitHub\w" commit -m "refactor(frontend): split CollectionsFeature into form, list, and results components"
```

---

## Batch D: Feature Enhancements + Organization Layer (10 tasks)

### Task D1: Saved search / search history

**Files:**
- Modify: `apps/frontend/src/features/search/SearchFeature.tsx`

- [ ] **Step 1: Add search history to localStorage**

```typescript
const RECENT_SEARCHES_KEY = "workbench_recent_searches";
const MAX_RECENT = 10;

function useSearchHistory() {
  const [recent, setRecent] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem(RECENT_SEARCHES_KEY) ?? "[]"); } catch { return []; }
  });
  
  const addSearch = (query: string) => {
    const next = [query, ...recent.filter(s => s !== query)].slice(0, MAX_RECENT);
    setRecent(next);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next));
  };
  
  return { recent, addSearch };
}
```

- [ ] **Step 2: Add dropdown to search input**

Show recent searches as a dropdown list when the search input is focused and empty. Click to populate the search field.

- [ ] **Step 3: Type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/search/SearchFeature.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add search history dropdown with localStorage persistence"
```

---

### Task D2: Tag management UI

**Files:**
- Modify: `apps/backend/app/api/routes/tags.py` — add rename/delete/merge endpoints
- Modify: `apps/backend/app/services/tags/service.py` — add service methods
- Modify: `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx` — add context menu

- [ ] **Step 1: Add backend endpoints**

In `tags.py`:

```python
@router.patch("/tags/{tag_id}")
def rename_tag(tag_id: int, payload: TagRenameRequest, db: Session = Depends(get_db)):
    return tags_service.rename_tag(db, tag_id, payload.name)

@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tags_service.delete_tag(db, tag_id)

@router.post("/tags/merge")
def merge_tags(payload: TagMergeRequest, db: Session = Depends(get_db)):
    return tags_service.merge_tags(db, payload.source_id, payload.target_id)
```

- [ ] **Step 2: Add frontend context menu**

In TagBrowserFeature, add `onContextMenu` or a `...` button per tag item. Show "Rename", "Delete", "Merge" options. Use `ConfirmDialog` for delete.

- [ ] **Step 3: Run backend tests, frontend type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/api/routes/tags.py apps/backend/app/services/tags/service.py apps/backend/app/api/schemas/tag.py apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add tag rename, delete, and merge with UI context menu"
```

---

### Task D3: Collection statistics

**Files:**
- Modify: `apps/backend/app/api/routes/collections.py`
- Modify: `apps/backend/app/services/collections/service.py`
- Modify: `apps/frontend/src/features/collections/CollectionResults.tsx` (from C9)

- [ ] **Step 1: Add stats endpoint**

```python
@router.get("/collections/{id}/stats")
def get_collection_stats(id: int, db: Session = Depends(get_db)):
    stats = collections_service.get_stats(db, id)
    return {"item": stats}
```

Stats: `total_files`, `total_size_bytes`, `oldest_file_at`, `newest_file_at`, `matching_count`.

- [ ] **Step 2: Display stats in collection results header**

Show: "1,234 files · 4.2 GB · Jan 2024 to May 2026"

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/api/routes/collections.py apps/backend/app/services/collections/service.py apps/frontend/src/features/collections/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add collection statistics endpoint and display"
```

---

### Task D4: Image zoom / lightbox

**Files:**
- Create: `apps/frontend/src/shared/ui/components/Lightbox.tsx`
- Modify: `apps/frontend/src/features/details-panel/sections/DetailsPreviewSection.tsx`

- [ ] **Step 1: Create Lightbox component**

```tsx
interface LightboxProps {
  open: boolean;
  src: string;
  alt?: string;
  onClose: () => void;
}

export function Lightbox({ open, src, alt, onClose }: LightboxProps) {
  const [scale, setScale] = useState(1);
  return (
    <Modal open={open} onClose={onClose} title={alt ?? "Preview"}>
      <div style={{ display: "flex", justifyContent: "center", overflow: "hidden" }}>
        <img
          src={src}
          alt={alt}
          style={{ maxWidth: "100%", maxHeight: "70vh", transform: `scale(${scale})`, transition: "transform 0.2s", cursor: scale > 1 ? "grab" : "zoom-in" }}
          onClick={() => setScale(s => s > 1 ? 1 : 2)}
        />
      </div>
    </Modal>
  );
}
```

- [ ] **Step 2: Wire into DetailsPreviewSection**

Add `onClick` on the image preview that opens the Lightbox.

- [ ] **Step 3: Type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/shared/ui/components/Lightbox.tsx apps/frontend/src/features/details-panel/sections/DetailsPreviewSection.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add image lightbox with click-to-zoom"
```

---

### Task D5: Notes field in details panel

**Files:**
- Modify: `apps/backend/app/db/models/file_user_meta.py` — add `notes` column
- Modify: `apps/backend/app/api/schemas/file.py` — add `notes` to response
- Modify: `apps/frontend/src/features/details-panel/`

- [ ] **Step 1: Backend — add notes column**

In `engine.py`, add migration:

```python
user_meta_cols = _table_columns(connection, "file_user_meta")
if "notes" not in user_meta_cols:
    connection.execute("ALTER TABLE file_user_meta ADD COLUMN notes TEXT NULL")
```

Update `FileUserMeta` model, `FileUserMetaPatchRequest`, `FileUserMetaResponse` schemas.

- [ ] **Step 2: Frontend — add notes textarea**

In `DetailsPanelFeature`, add an `InspectorSection` labeled "Notes" with a `<textarea>` that auto-saves on blur:

```tsx
<InspectorSection title="Notes">
  <textarea
    value={notes ?? ""}
    onChange={(e) => setNotes(e.target.value)}
    onBlur={() => userMetaMutation.mutate({ notes })}
    maxLength={2000}
    rows={3}
    style={{ width: "100%", resize: "vertical" }}
  />
  <p className="library-muted-line">{notes.length}/2000</p>
</InspectorSection>
```

- [ ] **Step 3: Run tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/ apps/frontend/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add notes field to file user meta with auto-save textarea"
```

---

### Task D6: Sibling files section

**Files:**
- Modify: `apps/backend/app/api/routes/files.py` — add sibling endpoint
- Modify: `apps/frontend/src/features/details-panel/`

- [ ] **Step 1: Add backend endpoint**

```python
@router.get("/files/{file_id}/siblings")
def get_sibling_files(
    file_id: int, limit: int = 20,
    db: Session = Depends(get_db),
):
    file = files_service.get_file(db, file_id)
    siblings = files_service.get_siblings(db, file.path, file_id, limit)
    return {"items": siblings}
```

- [ ] **Step 2: Add frontend section**

Add a collapsible `InspectorSection` at the bottom of the details panel:

```tsx
<Suspense fallback={<LoadingState />}>
  <SiblingFilesSection fileId={item.id} onSelectFile={onSelectFile} />
</Suspense>
```

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/api/routes/files.py apps/backend/app/services/files/service.py apps/frontend/src/features/details-panel/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add sibling files section to details panel"
```

---

### Task D7: Cross-site favorite/rating filters

**Files:**
- Modify: `apps/backend/app/api/routes/search.py` — add query params
- Modify: `apps/backend/app/services/search/service.py` — add filter logic
- Modify: `apps/frontend/src/features/search/SearchFeature.tsx` — add UI

- [ ] **Step 1: Backend — add query params and filtering**

```python
@router.get("/search")
def search_files(
    ...
    is_favorite: bool | None = Query(None),
    min_rating: int | None = Query(None, ge=1, le=5),
    ...
):
```

In `SearchService`, join `file_user_meta` and filter: `WHERE file_user_meta.is_favorite = 1` if `is_favorite=True`, `WHERE file_user_meta.rating >= min_rating` if set.

- [ ] **Step 2: Frontend — add filter controls**

Add a "Favorites only" switch and "Min rating" dropdown to the search filter bar. These filters also apply to BrowseV2.

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/ apps/frontend/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add cross-site favorite and rating filters to search"
```

---

### Task D8: Batch favorite/rating operations

**Files:**
- Modify: `apps/backend/app/api/routes/files.py`
- Modify: `apps/frontend/src/features/batch-organize/`

- [ ] **Step 1: Backend — add batch meta endpoint**

```python
@router.post("/files/batch/meta")
def batch_update_meta(payload: BatchMetaUpdateRequest, db: Session = Depends(get_db)):
    return file_user_meta_service.batch_update_meta(db, payload.file_ids, payload.is_favorite, payload.rating)
```

- [ ] **Step 2: Frontend — add buttons to batch bar**

Add Star/Favorite toggle and Rating dropdown alongside existing batch buttons. Wire to `POST /files/batch/meta`.

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/api/routes/files.py apps/backend/app/services/file_user_meta/service.py apps/backend/app/api/schemas/file.py apps/frontend/src/features/batch-organize/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add batch favorite and rating operations"
```

---

### Task D9: Tag color coding

**Files:**
- Modify: `apps/backend/app/db/models/tag.py` — add `color` column
- Modify: `apps/frontend/src/features/tag-browser/TagBrowserFeature.tsx`

- [ ] **Step 1: Backend — add color to tag model**

```python
# migration
connection.execute("ALTER TABLE tags ADD COLUMN color TEXT NULL")

# model
color: Mapped[str | None] = mapped_column(String, nullable=True)
```

Update tag create/update schemas to accept optional color.

- [ ] **Step 2: Frontend — display colored tags**

In TagBrowserFeature, render each tag with a colored dot based on `tag.color`:

```tsx
<span className="tag-color-dot" style={{ backgroundColor: tag.color ?? "var(--color-border)" }} />
<span>{tag.name}</span>
```

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/ apps/frontend/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add color coding to tags with colored dot display"
```

---

### Task D10: Collection reorder/rename/group

**Files:**
- Modify: `apps/backend/app/api/routes/collections.py`
- Modify: `apps/frontend/src/features/collections/CollectionsFeature.tsx`

- [ ] **Step 1: Backend — add sort_order, group_name columns**

```python
connection.execute("ALTER TABLE collections ADD COLUMN sort_order INTEGER DEFAULT 0")
connection.execute("ALTER TABLE collections ADD COLUMN group_name TEXT NULL")
```

Add `PATCH /collections/{id}` endpoint accepting `name`, `group_name`, `sort_order`.

- [ ] **Step 2: Frontend — drag-handle reorder + inline rename**

In `CollectionList` (from C9), add drag handles and inline rename input. Group collections by `group_name` with group headers. Default group: "Ungrouped".

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/ apps/frontend/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add collection reorder, rename, and grouping"
```

---

### Task D11: Complete Recent family timeline

**Files:**
- Modify: `apps/backend/app/api/routes/recent.py` — add `family=all`
- Modify: `apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx`

- [ ] **Step 1: Backend — add unified timeline endpoint**

```python
@router.get("/recent")
def get_recent(family: str = "imports", page: int = 1, ..., db: Session = Depends(get_db)):
    if family == "all":
        items = recent_service.get_unified_timeline(db, page, page_size)
    else:
        items = recent_service.get_by_family(db, family, page, page_size)
    return {"items": items, "page": page, "total_pages": ...}
```

- [ ] **Step 2: Frontend — add "All activity" tab**

Add a 4th tab "All activity" in RecentImportsFeature. Render unified events with event icon, filename, event description, timestamp:

```tsx
function RecentEventRow({ event }: { event: RecentEvent }) {
  const icon = event.family === "imports" ? "📥" : event.family === "tagged" ? "🏷️" : "🎨";
  return (
    <div className="recent-event-row">
      <span>{icon}</span>
      <span className="recent-event-file">{event.file_name}</span>
      <span className="recent-event-desc">{event.description}</span>
      <span className="recent-event-time">{formatRelative(event.occurred_at)}</span>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/api/routes/recent.py apps/backend/app/services/recent/service.py apps/frontend/src/features/recent-imports/RecentImportsFeature.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add unified Recent family timeline with All activity tab"
```

---

## Final Verification

After all 4 batches complete:

```powershell
# Backend — all tests pass
& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests/" -q --tb=line

# Frontend — all tests pass, no new TS errors  
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx vitest run; npx tsc --noEmit 2>&1 | Select-Object -Last 10

# CI — verify workflow triggers on push
```

Expected: Backend all pass, frontend all pass, zero new TypeScript errors, CI workflow file valid.
