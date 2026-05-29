# Phase 15 — BrowseV2 UX Polish: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 40 BrowseV2 UX gaps — 4 critical (broken layout, memory pagination, missing sort/search), 17 important (phase labels, missing skeleton, duplicate metrics, card memo, URL persistence), 19 nice-to-have (context menu, drag-drop, keyboard nav, view modes).

**Architecture:** Batch A (critical fixes — restore taxonomy sidebar, SQL pagination, sort + search UI) → Batch B (important gaps — 17 items) → Batch C (nice-to-have — 19 items). Batches A and B can be dispatched in parallel for frontend-only items; A2 (backend SQL pagination) must complete before B4 and B16.

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy, React 18 + TypeScript + CSS

---

## Batch A: Critical Fixes (4 tasks)

### Task A1: Render taxonomy sidebar DOM

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`

Read the current file. Add a `<nav className="browse-v2-taxonomy">` as the first child of the browse-v2-layout div (before `<main>`):

```tsx
<nav className="browse-v2-taxonomy" aria-label="Browse categories">
  <div className="browse-v2-taxonomy__section">
    <h3 className="browse-v2-taxonomy__heading">Domains</h3>
    {DOMAINS.map(domain => (
      <button
        key={domain.value}
        className={`browse-v2-taxonomy__domain-button${domain.value === currentDomain ? " browse-v2-taxonomy__domain-button--active" : ""}`}
        onClick={() => setFilter("domain", domain.value)}
      >
        {t(domain.labelKey)}
      </button>
    ))}
  </div>
  {currentDomain && (
    <div className="browse-v2-taxonomy__section">
      <h3 className="browse-v2-taxonomy__heading">Categories</h3>
      <div className="browse-v2-taxonomy__groups">
        {CATEGORY_GROUPS[currentDomain]?.map(group => (
          <div key={group.key} className="browse-v2-taxonomy__group">
            <h4 className="browse-v2-taxonomy__group-label">{group.label}</h4>
            {group.items?.map(cat => (
              <button
                key={cat.value}
                className={`browse-v2-taxonomy__item${cat.value === currentCategory ? " browse-v2-taxonomy__item--active" : ""}`}
                onClick={() => setFilter("category", cat.value)}
              >
                {t(cat.labelKey)}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  )}
</nav>
```

Import `DOMAINS` and `CATEGORY_GROUPS` from the browse taxonomy constants. Use `useBrowseV2Filters` for `currentDomain` and `currentCategory`.

Type check, run dev server to verify layout, commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): render taxonomy sidebar in BrowseV2 with domains and categories"
```

---

### Task A2: SQL-level pagination

**Files:**
- Modify: `apps/backend/app/services/library/browse_v2.py`

Read the current `list_cards` method. Replace the in-memory merge-and-slice with a SQL UNION approach:

```python
from sqlalchemy import union_all, select, literal_column

def list_cards(self, session, domain, category=None, page=1, page_size=50,
               sort_by="title", sort_order="asc", storage_state=None, card_kind=None):
    # Build UNION of object cards + loose file cards with unified sort keys
    obj_query = select(
        LibraryObject.id.label("source_id"),
        literal_column("'object'").label("card_kind"),
        LibraryObject.title.label("sort_title"),
        ...
    ).where(...)
    
    file_query = select(
        File.id.label("source_id"),
        literal_column("'file'").label("card_kind"),
        File.name.label("sort_title"),
        ...
    ).where(...)
    
    combined = union_all(obj_query, file_query).alias("combined")
    
    # Apply sort + offset/limit at SQL level
    count_query = select(func.count()).select_from(combined)
    total = session.execute(count_query).scalar()
    
    offset = (page - 1) * page_size
    sort_col = combined.c.sort_title if sort_by == "title" else combined.c.sort_modified
    if sort_order == "desc":
        sort_col = sort_col.desc()
    
    rows = session.execute(
        select(combined).order_by(sort_col).offset(offset).limit(page_size)
    ).fetchall()
    
    # Build card dicts from rows (no full-table in-memory merge)
    ...
```

Run backend browse tests, commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/services/library/browse_v2.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "perf(backend): implement SQL-level pagination for browse cards"
```

---

### Task A3: Add sort controls

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`
- Modify: `apps/frontend/src/features/browse-v2/hooks/useBrowseV2SearchParams.ts`

Add sort dropdown to the filter toolbar:

```tsx
<select value={sortBy} onChange={e => setFilter("sort", e.target.value)}>
  <option value="title">Name</option>
  <option value="modified_at">Modified</option>
  <option value="file_type">Type</option>
</select>
<button onClick={() => setFilter("order", sortOrder === "asc" ? "desc" : "asc")}>
  {sortOrder === "asc" ? "↑" : "↓"}
</button>
```

In `useBrowseV2SearchParams.ts`, add `sort` and `order` to URL params:

```typescript
const sort = searchParams.get("sort") ?? "title";
const order = searchParams.get("order") ?? "asc";
```

Pass both to `useBrowseV2Cards` query. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/browse-v2/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add sort dropdown and asc/desc toggle to BrowseV2"
```

---

### Task A4: Add browse search input

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`
- Modify: `apps/frontend/src/features/browse-v2/hooks/useBrowseV2SearchParams.ts`

Add search input that does client-side filtering (backend already returns all matching records in the page, so filter `sortedActions`):

```tsx
const [searchQuery, setSearchQuery] = useState("");
const filteredCards = sortedCards.filter(card => {
  const title = card.title ?? card.name ?? "";
  return title.toLowerCase().includes(searchQuery.toLowerCase());
});
```

Add input to filter toolbar:

```tsx
<input
  type="search"
  placeholder="Search in browse..."
  value={searchQuery}
  onChange={e => setSearchQuery(e.target.value)}
  className="browse-v2-search"
/>
```

As URL param: `?query=...`. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/browse-v2/
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add search input to BrowseV2 with client-side filtering"
```

---

## Batch B: Important Gaps (17 tasks)

### Task B1: Remove Phase labels + legacy comments

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2Feature.tsx`
- Modify: `apps/backend/app/services/library/browse_v2.py`
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2DetailPanel.tsx`

- Replace `// Phase 8C-2: Compose selection` → `// Compose mode selection bar`
- Replace `// Phase 8D-D: Amendment state` → `// Object amendment state`
- Backend `notes: ["Object detail is read-only in Phase 8B."]` → `["Object detail view"]`
- Detail panel `t("features.browseV2.overview.readOnlyNotice")` → generic text

Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/browse-v2/ apps/backend/app/services/library/browse_v2.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "chore: remove Phase labels and legacy comments from BrowseV2"
```

---

### Tasks B2-B17: Batch fix remaining important gaps

All are mechanical frontend changes in the same few files. Implement as a single batch:

**B2:** Replace `<p>Loading...</p>` with `<CardSkeleton count={3} variant="row" />` in BrowseV2DetailPanel.tsx:60

**B3:** Remove first MetricStrip (lines 209-218) — keep only the filter-specific one. Or unify to always show filter-aware metrics.

**B4:** Add pagination to Add Members modal by reading `apps/frontend/src/features/browse-v2/BrowseV2Modals.tsx` and adding `<Pagination page={page} totalPages={totalPages} onPageChange={setPage} />`

**B5:** Replace `(card: any)` with `(card: BrowseV2Card)` in BrowseV2Modals.tsx:132

**B6:** In useBrowseV2SearchParams.ts, add `page` to URL params instead of useState(1):
```typescript
const page = parseInt(searchParams.get("page") ?? "1", 10);
// setFilter handles page
```

**B7:** Add `selected` to URL params: `selected={id}` in useBrowseV2SearchParams. Sync with `selectedObject` state.

**B8:** Add CSS transition to selection bar in browse.css:
```css
.browse-v2-selection-bar {
  transition: height 0.3s ease, opacity 0.3s ease;
}
```

**B9:** Add hover styles to `.browse-v2-member-row`:
```css
.browse-v2-member-row:hover { background: var(--color-surface-hover); cursor: pointer; }
```

**B10:** Show confidence on video ObjectCard (add to the video variant render block)

**B11:** Show `primary_file_id`, `cover_file_id`, `launch_file_id` as metadata rows in BrowseV2DetailPanel. Show `warnings[]` as yellow banner if non-empty.

**B12:** Make object name editable in detail panel — inline input on double-click, auto-save on blur

**B13:** Add "Select All" checkbox in the card list header:
```tsx
<input type="checkbox" checked={selectedIds.size === totalCardCount} onChange={toggleSelectAll} />
```

**B14:** Add drag-to-compose zone — `onDragOver` + `onDrop` on a compose dock area. Fall back to checkbox flow.

**B15:** Wrap LooseFileCard and ObjectCard exports with `React.memo`

**B16:** In useVirtualList, use `ResizeObserver` per-item to measure real heights instead of fixed 80px. Or switch to `react-window` with `VariableSizeList`.

**B17:** Remove duplicate `sizeLabel` from LooseFileCard meta section (keep only the header one).

Commit all B2-B17 together:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/browse-v2/ apps/frontend/src/app/styles/browse.css apps/frontend/src/shared/hooks/useVirtualList.ts
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): fix 16 important UX gaps in BrowseV2 (skeletons, memo, URL persistence, pagination, hover, etc.)"
```

---

## Batch C: Nice-to-Have (19 tasks)

### Task C1: Right-click context menu

Create a `<ContextMenu>` component on `onContextMenu`:

```tsx
const [contextMenu, setContextMenu] = useState<{x:number, y:number, card:BrowseV2Card} | null>(null);

<div onContextMenu={e => { e.preventDefault(); setContextMenu({x:e.clientX, y:e.clientY, card}); }}>
  {contextMenu && <ContextMenu x={contextMenu.x} y={contextMenu.y} card={contextMenu.card} onClose={() => setContextMenu(null)} />}
</div>
```

Menu items: "View details", "Open file", "Show in folder", "Add to collection".

### Task C2: Drag to compose zone

```tsx
const [dragOverCompose, setDragOverCompose] = useState(false);

<div className={`compose-drop-zone${dragOverCompose ? " compose-drop-zone--active" : ""}`}
     onDragOver={e => { e.preventDefault(); setDragOverCompose(true); }}
     onDragLeave={() => setDragOverCompose(false)}
     onDrop={e => { setDragOverCompose(false); openComposeModal(); }}>
  Drop files here to compose
</div>
```

### Task C3: Shift+Click and Ctrl+Click multi-select

```typescript
const handleCardClick = (card: BrowseV2Card, e: React.MouseEvent) => {
  if (e.shiftKey && lastClickedIndex !== null) {
    const range = sortedCards.slice(Math.min(lastClickedIndex, index), Math.max(lastClickedIndex, index) + 1);
    setSelectedIds(new Set(range.map(c => c.id)));
  } else if (e.ctrlKey) {
    setSelectedIds(prev => { const next = new Set(prev); if (next.has(card.id)) next.delete(card.id); else next.add(card.id); return next; });
  } else {
    setSelectedIds(new Set([card.id]));
  }
};
```

### Tasks C4-C19: Remaining nice-to-haves

**C4:** Roving tabindex on card grid container — Left/Right/Up/Down arrows move focus

**C5:** Adaptive polling in useExecutePlan — 2s, 2s, 2s, 5s, 10s, 30s max

**C6:** File type filter dropdown: image/video/document/executable/archive/audio/other

**C7:** Needs review checkbox + min-confidence dropdown

**C8:** Date range selector (7d/30d/1y/all) + min file size input

**C9:** View mode buttons: grid/list/table — persist in localStorage

**C10:** Breadcrumb shows selected object name and current page

**C11:** Replace `<p>Select an object</p>` with `<EmptyState title="Select a card" description="Click any card to view details" />`

**C12:** Add retry buttons to error states in detail panel and modals

**C13:** Add CSS transition to `.browse-v2-detail--active`:
```css
transition: transform 0.3s ease, opacity 0.3s ease;
```

**C14:** Use `<VirtualList itemHeight={60}>` inside ComposeObjectModal

**C15:** Show toast "Filters applied — back to page 1" when filters reset page

**C16:** Store compose/amendment success messages in localStorage, show in Plans page

**C17:** Add "Batch tag" and "Batch move" buttons to selection bar

**C18:** Add "Clear all filters" button

**C19:** Sort dropdown shows ↑/↓ icon on active column

Commit all C1-C19:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/browse-v2/ apps/frontend/src/app/styles/browse.css
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add 19 nice-to-have BrowseV2 interactions (context menu, drag-drop, multi-select, keyboard nav, view modes, etc.)"
```

---

## Final Verification

```powershell
# Backend
& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests/" -q --tb=line

# Frontend
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx vitest run; npx tsc --noEmit
```

Expected: All tests pass, zero new TS errors.
