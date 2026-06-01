# 04 — Acceptance Checklist

---

## 1. Build

- [ ] `cd apps/frontend && npm run build` exits 0
- [ ] No new TypeScript errors
- [ ] No new ESLint warnings (if lint configured)
- [ ] CSS output < 100 KB (within reason)

---

## 2. Per-Page Manual Checklist

### App Shell
- [ ] Sidebar renders all 12 nav items
- [ ] Sidebar collapse/expand works (236px ↔ 74px)
- [ ] Active nav item highlighted (accent bg + left border)
- [ ] PageContentHeader shows correct title per route
- [ ] Backend connection status indicator visible
- [ ] Details panel toggle works

### DetailsPanel
- [ ] Empty state ("No file selected") renders
- [ ] Loading state renders
- [ ] Error state renders
- [ ] File detail: metadata header correct
- [ ] File detail: path, type, size, timestamps visible
- [ ] Placement section renders (auto/effective)
- [ ] Tags section: add/remove tags works
- [ ] Color tag section: select/clear works
- [ ] Favorite/Rating section works
- [ ] Game status section works (conditional)
- [ ] Preview section works (image/video)
- [ ] Open File / Open Folder buttons work

### Search
- [ ] Search input works
- [ ] Results list renders
- [ ] Filter by type/kind/source/extension works
- [ ] Pagination works
- [ ] Empty/no-results state correct
- [ ] Clicking result opens DetailsPanel

### Library > Overview
- [ ] Stat cards render with correct counts
- [ ] Type grid renders
- [ ] Scan Library Objects button works
- [ ] Safety notice visible

### Library > Managed Roots
- [ ] Root cards render with correct data
- [ ] path, managed/default/disabled badges separated
- [ ] Enable/Disable button works
- [ ] Set Default button shows/hides correctly
- [ ] Add form: folder picker works (Electron)
- [ ] Add form: manual input fallback (browser)
- [ ] Cancel button shows "Cancel" / "取消" (not i18n key)
- [ ] Error states: duplicate/overlap/invalid path

### Library > Path Browser
- [ ] FileBrowser loads
- [ ] Navigate directories works
- [ ] View toggle (details/icons)

### Library > Pending
- [ ] Candidate list renders
- [ ] Candidate detail renders on select
- [ ] Scan Candidates / Generate Plan buttons work
- [ ] Template dropdown shows built-in templates
- [ ] Root selector modal works (multi-root scenario)
- [ ] Suggestions section: Generate/lists/Accept/Reject works
- [ ] Suggestions provider shows "rule_based"

### Library > Objects
- [ ] Object list renders with type/status
- [ ] Filter by type/review status works
- [ ] Pagination works

### Library > Organize Plans
- [ ] Plan list renders with status pills
- [ ] Plan detail renders (actions, path preview, logs)
- [ ] Mark Ready / Preflight / Execute flow works
- [ ] Phase 5A Reconcile block renders
- [ ] Phase 5B Copy Failed Actions block renders
- [ ] Phase 5C Rollback block renders
- [ ] Phase 5D-1 Merge block renders
- [ ] Phase 5D-2 Template display renders
- [ ] Phase 5D-3 Suggestions display renders

### Documents / Media / Games / Software
- [ ] Each page loads
- [ ] Filter/sort controls work
- [ ] File list/grid renders
- [ ] Pagination works
- [ ] Empty/no-results states correct
- [ ] Clicking row opens DetailsPanel

### Tools
- [ ] Tool list renders (Video Merge)
- [ ] Create run / view runs works

### Recent
- [ ] Recent imports / tagged / color-tagged tabs work
- [ ] File list renders

### Tags
- [ ] Tag list/cloud renders
- [ ] Clicking tag shows tagged files
- [ ] Empty state correct

### Collections
- [ ] Collection list renders
- [ ] Create/update/delete collection works
- [ ] Collection files view works

### Settings
- [ ] Source management renders
- [ ] Add/scan source works
- [ ] System status displays
- [ ] Folder picker works (Electron)

### Home/Onboarding
- [ ] Home page renders
- [ ] Onboarding flow works

---

## 3. No Lost Feature Checklist

- [ ] Phase 5A reconcile — still accessible
- [ ] Phase 5B copy-failed-actions — still accessible
- [ ] Phase 5C rollback — still accessible
- [ ] Phase 5D-1 merge — still accessible
- [ ] Phase 5D-2 templates — still accessible
- [ ] Phase 5D-3 suggestions — still accessible
- [ ] Managed roots enable/disable — works both ways
- [ ] Folder picker — works in Electron / falls back in browser
- [ ] DetailsPanel — shows same sections as before
- [ ] All 12 nav items — present and working

---

## 4. No Backend/API Change Checklist

- [ ] `git diff -- apps/backend/` is empty
- [ ] No API route modified
- [ ] No new API call added
- [ ] No existing API call removed
- [ ] No schema/model/DB change

---

## 5. No Overclaim Checklist

- [ ] No "real LLM" mentioned as implemented
- [ ] No "cloud AI" / "OpenAI" / "Ollama" in UI
- [ ] No "template CRUD" in UI
- [ ] No "auto execute" / "auto generate plan" in UI
- [ ] No "organize_templates" management UI
- [ ] No provider/model routing UI
- [ ] No prompt platform UI
- [ ] No automatic metadata fetching claim
- [ ] Suggestions labeled "rule_based" (not AI/LLM)

---

## 6. No Generated Artifacts Checklist

- [ ] `git status --short` shows only source/docs/config changes
- [ ] No `runtime/`, `cache/`, `build/`, `dist/`, `release/` in git
- [ ] No `*.db`, `*.sqlite`, `*.exe`
- [ ] No test-generated `asset.yaml` / `asset.yaml.bak`

---

## 7. i18n Checklist

- [ ] No bare i18n keys visible (e.g., `common.actions.cancel`)
- [ ] "Cancel" / "取消" renders correctly in both locales
- [ ] All new UI text has en + zh-CN keys
