# 01 — Design System

---

## 1. Color Tokens (Dark Theme)

From `apps/frontend/src/app/styles/tokens.css` `:root[data-theme="dark"]` (as of commit `88bcd03`, `global.css` is now an import aggregator):

| Token | Hex | Role |
|-------|-----|------|
| `--bg-app` | `#0a1628` | App background |
| `--bg-page` / `--bg-sidebar` | `#0d1b2a` | Page / sidebar bg |
| `--bg-surface` | `#111d32` | Card/section surface |
| `--bg-card` | `#162236` | Embedded card |
| `--border-soft` / `--border-default` | `#1e2d44` | Soft border |
| `--text-strong` / `--text-primary` | `#e2e8f0` | Primary text |
| `--text-secondary` | `#94a3b8` | Secondary text |
| `--text-muted` | `#64748b` | Muted / metadata |
| `--accent-primary` | `#4dabf7` | Primary action / selected |
| `--accent-secondary` | `#20c997` | Draft / info |
| `--accent-success` | `#51cf66` | Success / enabled |
| `--accent-warning` | `#f59f00` | Warning / pending |
| `--accent-danger` | `#ff6b6b` | Danger / error / disabled |
| `--accent-on` | `#0a1628` | Text on accent bg |

---

## 2. Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Tight badge padding |
| `--space-sm` | 8px | Small gaps |
| `--space-md` | 12px | Card padding, row gaps |
| `--space-lg` | 16px | Section gaps |
| `--space-xl` | 24px | Page padding |

---

## 3. Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Buttons, inputs |
| `--radius-md` | 12px | Cards |
| `--radius-lg` | 18px | Modals |
| 999px | — | Pills, badges |

---

## 4. Typography

| Token | Font | Usage |
|-------|------|-------|
| `--font-display` | Inter | Headings |
| `--font-ui` | Inter | Body, labels |
| `--font-mono` | JetBrains Mono | Paths, codes, IDs |

Size scale: 9/10/11/12/13/14/15/16/18/20/24px.

---

## 5. Component Tokens

### Cards
- `section-card`: `bg: --bg-surface`, `border: 1px solid --border-soft`, `radius: 12px`, `padding: 20px`, `gap: 12px`

### Badges / Pills
- `status-badge`: `font-size: 10px`, `border-radius: 4px`, `padding: 1px 8px`
- `status-badge--accent/secondary/success/warning/danger/muted` → background colors
- `placeholder-pill`: `font-size: 11px`, `uppercase`, `color: --text-soft`

### Buttons
- Primary: `bg: --accent-primary`, `color: #fff`, `radius: 6px`
- Secondary: `bg: --bg-card/--control-bg`, `color: --text-secondary`
- Ghost: transparent bg, `color: --text-soft`
- Danger: `bg: --accent-danger`, `color: #fff`
- Disabled: opacity 0.5 or muted colors

### Empty States
- `empty-state`: centered flex column, `min-height: 120px`, `gap: 6px`

---

## 6. Layout Tokens

| Zone | Width | Notes |
|------|-------|-------|
| Sidebar (expanded) | 236px | Collapses to 74px |
| Details Panel | 344px | Togglable |
| Titlebar | 40px | Desktop-only |
| Content | `1fr` | Fills remainder |

---

## 7. Icon System

- Source: `apps/frontend/src/assets/icons/navigation/` (SVG files)
- Import: `vite-plugin-svgr` via `?react` suffix
- Color: `fill="currentColor"` on all SVGs
- Component: `SidebarIcon` in `apps/frontend/src/shared/ui/icons/SidebarIcon.tsx`
- Icon names: `NavigationIconName` union type (22 literals)

---

## 8. Theme Switching

- Light: `:root` (default)
- Dark: `:root[data-theme="dark"]`
- Toggle: via `useUIStore` state, applied to `<html data-theme="...">`
