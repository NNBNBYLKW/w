# Changelog

## v0.3.0 (2026-05-28)

### Core
- **File Library**: Complete Library v2 with BrowseV2 as unified entry point
- **Organize**: Full plan lifecycle — draft → ready → preflight → execute with conflict detection
- **Import**: Copy-only inbox import with inbox item management and folder import
- **Objects**: Library object scanning, managed compose, object amendment (add/remove members)
- **Mixed Amendment**: Single plan can now add and remove members simultaneously
- **Recovery**: Diagnostic-only scan with auto-repair for safe scenarios (path_mismatch, retryable import)

### Browse & Search
- **BrowseV2**: Domain-based navigation (Media/Documents/Apps/Assets), object + loose file cards
- **Search**: Source/parent_path filters, favorite/rating filters, search history
- **Recent**: Unified timeline with All activity tab

### Organization
- **Tags**: Full CRUD, rename/delete/merge, color coding with dot display
- **Collections**: CRUD, statistics (file count, size, date range), reorder/rename/group
- **Batch Operations**: Batch tags, color tags, placement, favorite, rating
- **Favorites & Ratings**: Cross-site filtering, batch operations

### Details Panel
- Embedded video player with hover preview on cards
- Paginated PDF preview with page navigation
- EPUB ebook reader with chapter navigation
- Image lightbox with click-to-zoom
- Notes field with auto-save
- Copy path button, sibling files section
- Show in folder (desktop mode)

### Performance
- Bulk INSERT for scan speed, metadata skip for archive/executable files
- Virtualized card grid via custom useVirtualList hook
- Composite indexes for search, recent, file listing queries
- WAL mode for SQLite, periodic VACUUM
- Lazy-loaded thumbnails with IntersectionObserver
- Route-level code splitting (React.lazy for all pages)
- Details panel switching optimization (React.memo + staleTime)

### Security
- Electron sandbox enabled (sandbox: true, contextIsolation: true, nodeIntegration: false)
- F-string SQL injection eliminated
- GET endpoints verified read-only (no DB mutations)
- Error boundaries in place

### UI/UX
- Shared component library: Modal, Pagination, ProgressBar, CardSkeleton, Lightbox, Toast, ConfirmDialog
- Customizable accent color (8 presets)
- Global keyboard shortcuts (Ctrl+K search, Ctrl+B sidebar, Ctrl+D details, Escape close)
- Empty state guidance with action buttons
- User-friendly error messages via useErrorMessage hook
- Quick-access panel with recent files and favorites (Ctrl+Q)

### Developer Experience
- CI/CD: GitHub Actions workflow (backend pytest + frontend vitest + tsc)
- CSS split into component-level files
- God components split to <=400 lines (BrowseV2Feature, DetailsPanelFeature, CollectionsFeature)
- organize.py partially split (file ops + candidate management extracted)
- Unified API client (getApiBaseUrl + parseResponse)
- Version number standardized to 0.3.0 across all packages
- PlanKind converted to StrEnum
- Database migration version gating (CURRENT_SCHEMA_VERSION=9)

### Testing
- Backend: 825 tests passing
- Frontend: 78 tests passing (10 test files)
- E2E: Playwright configuration and smoke tests created
- New test files for Phase 12/13 features (checksum, trash, game sessions, move import, suggester)
