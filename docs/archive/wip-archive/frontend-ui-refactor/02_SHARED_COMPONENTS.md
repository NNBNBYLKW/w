# 02 — Shared Components

---

## 1. Existing (Already Created)

All in `apps/frontend/src/shared/ui/components/`:

### StatusBadge
```tsx
<StatusBadge variant="accent | secondary | success | warning | danger | muted">
  text
</StatusBadge>
```
10px uppercase pill with variant-colored background.

### PlanStatusPill
```tsx
<PlanStatusPill status="draft | ready | executing | completed | completed_with_errors | failed | cancelled" />
```
Uses `StatusBadge` internally with status→variant mapping.

### EmptyState
```tsx
<EmptyState icon={<Icon />} title="No results" description="Try adjusting filters." />
```
Centered flex column for empty/loading/error/no-results states.

### SectionCard
```tsx
<SectionCard title="Section Title">
  {children}
</SectionCard>
```
Card wrapper with `--bg-surface`, border, 12px radius, 20px padding.

---

## 2. Existing (Icons)

### SidebarIcon
```tsx
import { SidebarIcon } from "../../shared/ui/icons";
<SidebarIcon name="home" />
```
22 named SVG icons, all `currentColor`. Located in `apps/frontend/src/shared/ui/icons/SidebarIcon.tsx`.

---

## 3. Existing (Other Shared)

| Component | File | Purpose |
|-----------|------|---------|
| `useRetryingThumbnail` | `shared/ui/thumbnail.tsx` | Image loading with retry |
| `useThumbnailWarmup` | `shared/ui/thumbnail.tsx` | Preload thumbnails |
| `ViewModeToggle` | `shared/ui/view-mode.tsx` | Details/Icons toggle |
| `t()` | `shared/text/runtime.ts` | i18n function |
| `useLocale()` | `shared/text/context.tsx` | Locale hook |
| `useUIStore` | Zustand store | Sidebar collapse, details toggle, theme |

---

## 4. Recommended for Migration

Components that should be extracted from feature-local to shared during migration:

### FileRow
- **From**: `DetailsPanelFeature` / search / books / media / games / software
- **Goal**: Consistent file row with thumbnail, name, metadata, actions
- **Props**: `file`, `selected`, `onClick`, `showThumbnail`, `thumbnailSize`

### PageHeader
- **From**: Every feature's header section
- **Goal**: Consistent `title + description + actions` pattern
- **Props**: `title`, `description`, `eyebrow?`, `actions?`

### FilterBar
- **From**: Search, books, media, games, software, recent, tags feature files
- **Goal**: Consistent filter/sort/type selector bar
- **Props**: `filters[]`, `sortBy`, `sortOrder`, `onChange`

### ActionButton
- **From**: Various feature files
- **Goal**: Consistent button with icon + label + variant
- **Props**: `label`, `icon?`, `variant`, `onClick`, `disabled`

### KeyValueRow
- **From**: DetailsPanel, Settings
- **Goal**: Consistent `label: value` row
- **Props**: `label`, `value`, `mono?`, `longValue?`

---

## 5. What NOT to Extract

- Business-logic-heavy mutations (keep in feature files)
- Feature-specific form layouts
- API call wrappers
- State management hooks
