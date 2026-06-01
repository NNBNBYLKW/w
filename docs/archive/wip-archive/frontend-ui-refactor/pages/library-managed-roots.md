# Page Spec — Library Managed Roots

## 1. Page Role
组织输出目标库管理。管理 managed library roots 的 CRU（无 D）。

## 2. Route / Entry
Route: `/library?tab=roots`
File: `apps/frontend/src/features/library/LibraryFeature.tsx`
Component: `LibraryRootsPanel`

## 3. Existing Components / Files
Within `LibraryFeature.tsx` — root card list, add form (folder picker + manual input).

## 4. Data Sources / API
- `listLibraryRoots()` — roots list
- `createLibraryRoot({root_path, display_name})` — add
- `updateLibraryRoot(id, {is_enabled, display_name, scan_policy})` — enable/disable/rename
- `setDefaultLibraryRoot(id)` — set default
- `selectFolder` electron bridge (optional)
- `queryKeys.libraryRoots` — query key

## 5. Must Preserve
- Enabled/disabled root distinction
- Default badge
- Enable/Disable button toggle
- Set Default (only for enabled roots)
- Folder picker (Electron) + browser fallback
- Overlap/duplicate validation
- Root path display (not concatenated with badges)

## 6. Design Target
From `design.pen`: Root cards with title row (display_name + badges), path row (monospace), action row. Disabled root shows Enable button. Add form with browser fallback warning.

## 7. UI Structure
```
Tab: Managed Roots
├── Section: Title + description
├── Root Card (enabled, default)
│   ├── Row1: display_name + [managed] [default] badges
│   ├── Row2: root_path (monospace)
│   └── Row3: [Disable]
├── Root Card (enabled, not default)
│   ├── Row1: display_name + [managed] badge
│   ├── Row2: root_path
│   └── Row3: [Set Default] [Disable]
├── Root Card (disabled)
│   ├── Row1: display_name + [managed] [disabled] badges
│   ├── Row2: root_path (muted)
│   └── Row3: [Enable]
├── [+ Add Managed Root]
└── Add Form (expandable)
    ├── Browser fallback notice
    ├── Path input + [Choose Folder]
    ├── Display name input
    ├── Error message
    └── [Add Root] [Cancel]
```

## 8. States
- Loading
- Empty (no roots)
- Error (create/update failed)
- Browser fallback mode
- Duplicate/overlap error
- Invalid path error

## 9. Risk Points
- Folder picker not available in browser
- Root path canonicalization
- Disabled default root auto-clear

## 10. Acceptance Checklist
- [ ] Root cards render with correct data
- [ ] Badges (managed/default/disabled) separated from path
- [ ] Enable/Disable toggle works
- [ ] Set Default works
- [ ] Add form: folder picker (Electron)
- [ ] Add form: manual fallback (browser)
- [ ] Cancel shows "Cancel" / "取消"
- [ ] Error states correct
