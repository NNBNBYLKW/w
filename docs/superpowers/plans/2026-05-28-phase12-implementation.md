# Phase 12 — Deep-Water Capabilities: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all 12 deferred deep-water capabilities — duplicate detection, code signing, auto-update, smart video thumbnails, video player, document preview, ebook reader, theme editor, AI classification suggestions, game launcher, game session tracking, and multi-panel layout.

**Architecture:** Batch A (infrastructure — 4 items, all independent) → Batch B (media + document depth — 4 items, B1 depends on A4) → Batch C (intelligence + platform — 4 items, C3 depends on C2). Each batch produces independently shippable software.

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy + SQLite (backend), React 18 + TypeScript + CSS (frontend), Electron + TypeScript (desktop)

---

## Batch A: Infrastructure + Low Complexity

### Task A1: Duplicate file detection

**Files:**
- Create: `apps/backend/app/workers/checksum/__init__.py`
- Create: `apps/backend/app/workers/checksum/worker.py`
- Modify: `apps/backend/app/db/session/engine.py` (add index on checksum_hint)
- Modify: `apps/backend/app/api/routes/files.py` (add GET /files/duplicates)
- Modify: `apps/frontend/src/features/details-panel/DetailsPanelBody.tsx` (show duplicate hint)

- [ ] **Step 1: Create ChecksumWorker**

Create `apps/backend/app/workers/checksum/worker.py`:

```python
import hashlib
from pathlib import Path

class ChecksumWorker:
    @staticmethod
    def compute_sha256(file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
```

- [ ] **Step 2: Add duplicate detection endpoint**

In `apps/backend/app/api/routes/files.py`:

```python
@router.get("/files/duplicates")
def list_duplicates(min_size: int = 0, db=Depends(get_db)):
    from sqlalchemy import func
    dups = db.execute(
        select(File.checksum_hint, func.count(File.id).label("cnt"), func.group_concat(File.id).label("ids"))
        .where(File.checksum_hint.isnot(None), File.file_kind != "other", File.size_bytes >= min_size)
        .group_by(File.checksum_hint)
        .having(func.count(File.id) > 1)
    ).fetchall()
    groups = []
    for ch, cnt, ids in dups:
        file_ids = [int(x) for x in ids.split(",")]
        files = db.execute(select(File).where(File.id.in_(file_ids))).scalars().all()
        groups.append({"checksum": ch, "count": cnt, "files": [{"id": f.id, "name": f.name, "path": f.path, "size_bytes": f.size_bytes} for f in files]})
    return {"items": groups}
```

- [ ] **Step 3: Frontend — show duplicate hint in details panel**

In `DetailsPanelBody.tsx`, add a section: if the file has a checksum and other files share it, show "⚠ Possible duplicate of: {other_file.name}".

- [ ] **Step 4: Run backend tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/checksum/ apps/backend/app/api/routes/files.py apps/backend/app/db/session/engine.py apps/frontend/src/features/details-panel/DetailsPanelBody.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add duplicate file detection with SHA-256 checksum worker"
```

---

### Task A2: App icon + code signing

**Files:**
- Modify: `apps/desktop/package.json`
- Modify: `apps/desktop/electron/main.ts` (set custom icon path)

- [ ] **Step 1: Update electron-builder config**

In `apps/desktop/package.json`, add icon configuration:

```json
"build": {
  "win": {
    "target": "nsis",
    "icon": "build-resources/icon.ico"
  },
  "nsis": {
    "installerIcon": "build-resources/icon.ico"
  }
}
```

- [ ] **Step 2: Add code signing configuration**

```json
"build": {
  "win": {
    "certificateFile": "${env.CSC_LINK}",
    "certificatePassword": "${env.CSC_KEY_PASSWORD}"
  }
}
```

- [ ] **Step 3: Set app icon in BrowserWindow**

In `main.ts`, add `icon: path.join(__dirname, "../build-resources/icon.ico")` to BrowserWindow options.

- [ ] **Step 4: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/desktop/package.json apps/desktop/electron/main.ts
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(desktop): add app icon and code signing configuration"
```

---

### Task A3: Auto-update system

**Files:**
- Modify: `apps/desktop/package.json` (add electron-updater dependency + publish config)
- Modify: `apps/desktop/electron/main.ts` (add autoUpdater)
- Modify: `apps/frontend/src/pages/settings/SettingsPage.tsx` (add Check for Updates button)

- [ ] **Step 1: Add dependency and publish config**

```json
// package.json
"dependencies": { "electron-updater": "^6.0.0" },
"build": { "publish": { "provider": "github", "owner": "NNBNBYLKW", "repo": "w" } }
```

- [ ] **Step 2: Wire autoUpdater in main process**

In `main.ts`, after app.whenReady:

```typescript
import { autoUpdater } from "electron-updater";

app.whenReady().then(() => {
  if (app.isPackaged) {
    autoUpdater.checkForUpdatesAndNotify();
  }
});
```

- [ ] **Step 3: Add frontend update button**

In SettingsPage.tsx, add "Check for Updates" button that calls `ipcRenderer.invoke("asset-workbench:check-for-updates")`.

- [ ] **Step 4: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/desktop/package.json apps/desktop/electron/main.ts apps/frontend/src/pages/settings/SettingsPage.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(desktop): add auto-update system via electron-updater"
```

---

### Task A4: Smart video frame selection

**Files:**
- Modify: `apps/backend/app/workers/thumbnails/video_generator.py`

- [ ] **Step 1: Implement smart frame selection**

In `video_generator.py`, replace the fixed 10% seek with a non-black-frame detection:

```python
import subprocess, json

def _find_first_non_black_frame(video_path: str, duration_s: float) -> float:
    """Seek through 5%-50% of the video, find first non-black frame."""
    candidates = [duration_s * pct for pct in [0.05, 0.10, 0.20, 0.35, 0.50]]
    for seek_time in candidates:
        # Use ffmpeg to extract a single frame and check if it's black
        cmd = ["ffmpeg", "-ss", str(seek_time), "-i", video_path, "-vframes", "1",
               "-f", "lavfi", "-i", "color=black:s=1x1", "-filter_complex",
               "psnr", "-f", "null", "-"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if "psnr" in result.stderr:
            try:
                psnr_line = [l for l in result.stderr.split("\n") if "psnr_avg" in l][0]
                psnr = float(psnr_line.split("psnr_avg:")[1].strip())
                if psnr < 30:  # Below 30dB means it's NOT black
                    return seek_time
            except (IndexError, ValueError):
                pass
    return duration_s * 0.10  # Fallback to 10%
```

- [ ] **Step 2: Update poster generation to use smart frame**

In the poster generation method, use `_find_first_non_black_frame` instead of `duration * 0.10`.

- [ ] **Step 3: Add scope=all to thumbnail warmup**

In `apps/backend/app/api/routes/files.py`, modify the warmup endpoint to accept `scope: str = "ids"`. When `scope=all`, query all video files that don't have poster thumbnails and enqueue them.

- [ ] **Step 4: Run backend tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/thumbnails/video_generator.py apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(backend): add smart video frame selection and full-library thumbnail pre-generation"
```

---

## Batch B: Media + Document Depth

### Task B1: Video hover preview + embedded player

**Files:**
- Modify: `apps/frontend/src/features/browse-v2/BrowseV2CardList.tsx` (hover preview)
- Modify: `apps/frontend/src/features/details-panel/sections/DetailsPreviewSection.tsx` (embedded player)

- [ ] **Step 1: Add hover preview to video cards**

In `BrowseV2CardList.tsx`, for video cards:

```tsx
const [hoveredId, setHoveredId] = useState<string | null>(null);

// In card:
<div className="video-card" onMouseEnter={() => setHoveredId(card.id)} onMouseLeave={() => setHoveredId(null)}>
  {hoveredId === card.id ? (
    <video src={videoUrl} muted autoPlay preload="none" poster={posterUrl} style={{width:"100%", height:120, objectFit:"cover"}} />
  ) : (
    <img src={posterUrl} alt={card.title} />
  )}
</div>
```

- [ ] **Step 2: Add embedded player to details panel**

In `DetailsPreviewSection.tsx`, for video files:

```tsx
<video controls style={{maxWidth:"100%", maxHeight:"60vh"}} poster={posterUrl}>
  <source src={videoUrl} />
</video>
```

- [ ] **Step 3: Type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/features/browse-v2/BrowseV2CardList.tsx apps/frontend/src/features/details-panel/sections/DetailsPreviewSection.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add video hover preview on cards and embedded player in details panel"
```

---

### Task B2: PDF/document paginated preview

**Files:**
- Modify: `apps/backend/app/workers/thumbnails/pdf_generator.py`
- Modify: `apps/backend/app/api/routes/files.py` (add GET /files/{id}/pdf-pages)
- Modify: `apps/frontend/src/features/details-panel/sections/DetailsPreviewSection.tsx`

- [ ] **Step 1: Generate multi-page PDF thumbnails**

```python
def generate_pages(self, file_path: str, max_pages: int = 5):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(file_path)
    pages = []
    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        bitmap = page.render(scale=1.5)
        img = Image.frombytes("RGBA", (bitmap.width, bitmap.height), bitmap.data)
        pages.append(img)
    return pages
```

- [ ] **Step 2: Add PDF pages API**

```python
@router.get("/files/{file_id}/pdf-pages")
def get_pdf_pages(file_id: int, max_pages: int = 5, db=Depends(get_db)):
    file = files_service.get_file(db, file_id)
    pages = pdf_generator.generate_pages(str(Path(settings.data_dir) / "thumbnails" / f"{file_id}_page_*.jpg"), file.path, max_pages)
    return {"items": [{"page_index": i, "url": f"/files/{file_id}/thumbnail?page={i}"} for i in range(len(pages))]}
```

- [ ] **Step 3: Frontend — paginated preview component**

```tsx
function PdfPreview({ fileId, pageCount }: { fileId: number; pageCount: number }) {
  const [page, setPage] = useState(0);
  return (
    <div className="pdf-preview">
      <div className="pdf-preview__toolbar">
        <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>Prev</button>
        <span>Page {page + 1} of {pageCount}</span>
        <button onClick={() => setPage(p => Math.min(pageCount - 1, p + 1))} disabled={page >= pageCount - 1}>Next</button>
      </div>
      <img src={`/files/${fileId}/thumbnail?page=${page}`} alt={`Page ${page + 1}`} />
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/thumbnails/pdf_generator.py apps/backend/app/api/routes/files.py apps/frontend/src/features/details-panel/sections/DetailsPreviewSection.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add paginated PDF preview with page navigation"
```

---

### Task B3: Embedded ebook reader

**Files:**
- Create: `apps/backend/app/workers/epub/parser.py`
- Modify: `apps/backend/app/api/routes/files.py` (add GET /files/{id}/epub-content)
- Create: `apps/frontend/src/features/details-panel/sections/EbookReader.tsx`

- [ ] **Step 1: Create EPUB parser**

```python
import zipfile
from xml.etree import ElementTree as ET

class EpubParser:
    def parse(self, file_path: str):
        with zipfile.ZipFile(file_path) as zf:
            # Find container.xml to get rootfile path
            container = ET.parse(zf.open("META-INF/container.xml"))
            rootfile = container.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
            opf_path = rootfile.get("full-path")
            
            # Parse .opf for metadata and spine
            opf = ET.parse(zf.open(opf_path))
            ns = {"dc": "http://purl.org/dc/elements/1.1/"}
            title = opf.find(".//dc:title", ns)
            author = opf.find(".//dc:creator", ns)
            
            # Extract chapter paths from spine
            spine = opf.findall(".//{http://www.idpf.org/2007/opf}itemref")
            chapters = []
            for itemref in spine:
                idref = itemref.get("idref")
                item = opf.find(f".//{{http://www.idpf.org/2007/opf}}item[@id='{idref}']")
                if item is not None:
                    href = item.get("href")
                    opf_dir = str(Path(opf_path).parent)
                    chapter_path = str(Path(opf_dir) / href) if opf_dir != "." else href
                    try:
                        content = zf.read(chapter_path).decode("utf-8")
                        # Strip HTML tags for plain text
                        from html.parser import HTMLParser
                        class TextExtractor(HTMLParser):
                            def __init__(self): super().__init__(); self.text = []
                            def handle_data(self, data): self.text.append(data)
                        extractor = TextExtractor()
                        extractor.feed(content)
                        chapters.append({"title": chapter_path, "text": " ".join(extractor.text)})
                    except Exception:
                        pass
            return {"title": title.text if title is not None else None,
                    "author": author.text if author is not None else None,
                    "chapters": chapters}
```

- [ ] **Step 2: Add API endpoint**

```python
@router.get("/files/{file_id}/epub-content")
def get_epub_content(file_id: int, db=Depends(get_db)):
    file = files_service.get_file(db, file_id)
    parsed = EpubParser().parse(file.path)
    return {"item": parsed}
```

- [ ] **Step 3: Create EbookReader component**

```tsx
function EbookReader({ fileId }: { fileId: number }) {
  const { data } = useQuery({ queryKey: ["epub", fileId], queryFn: () => getEpubContent(fileId) });
  const [chapterIdx, setChapterIdx] = useState(0);
  const chapter = data?.item?.chapters?.[chapterIdx];
  return (
    <div className="ebook-reader">
      <h3>{data?.item?.title}</h3>
      <p>{data?.item?.author}</p>
      <select value={chapterIdx} onChange={e => setChapterIdx(Number(e.target.value))}>
        {data?.item?.chapters?.map((ch: any, i: number) => <option key={i} value={i}>{ch.title}</option>)}
      </select>
      <div className="ebook-reader__content">{chapter?.text}</div>
      <div className="ebook-reader__nav">
        <button onClick={() => setChapterIdx(i => Math.max(0, i - 1))} disabled={chapterIdx === 0}>Prev</button>
        <button onClick={() => setChapterIdx(i => Math.min((data?.item?.chapters?.length ?? 1) - 1, i + 1))}>Next</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/epub/ apps/backend/app/api/routes/files.py apps/frontend/src/features/details-panel/sections/EbookReader.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add EPUB ebook reader with chapter navigation"
```

---

### Task B4: Theme editor / custom accent color

**Files:**
- Modify: `apps/frontend/src/shared/theme/index.tsx`
- Modify: `apps/frontend/src/pages/settings/SettingsPage.tsx`
- Modify: `apps/frontend/src/app/styles/tokens.css`

- [ ] **Step 1: Add accent color palette**

In `tokens.css`, add CSS variables for accent variants:

```css
:root {
  --accent-hue: 217;
  --accent-sat: 91%;
}
```

In `theme/index.tsx`, add `setAccentColor(hue: number, sat: number)` function.

- [ ] **Step 2: Add color picker to settings**

```tsx
const ACCENT_PRESETS = [
  { name: "Blue", hue: 217, sat: 91 },
  { name: "Green", hue: 142, sat: 71 },
  { name: "Purple", hue: 271, sat: 91 },
  { name: "Red", hue: 0, sat: 84 },
  { name: "Orange", hue: 24, sat: 94 },
  { name: "Cyan", hue: 187, sat: 85 },
  { name: "Pink", hue: 330, sat: 81 },
  { name: "Gray", hue: 220, sat: 14 },
];

// In SettingsPage:
<SectionCard title="Appearance">
  <p>Accent color</p>
  <div className="accent-presets">
    {ACCENT_PRESETS.map(p => (
      <button key={p.name} className="accent-preset" style={{ backgroundColor: `hsl(${p.hue}, ${p.sat}%, 48%)` }}
              onClick={() => setAccent(p.hue, p.sat)} title={p.name} />
    ))}
  </div>
</SectionCard>
```

- [ ] **Step 3: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/shared/theme/index.tsx apps/frontend/src/pages/settings/SettingsPage.tsx apps/frontend/src/app/styles/tokens.css
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add customizable accent color with 8 presets"
```

---

## Batch C: Intelligence + Platform

### Task C1: AI classification suggestions

**Files:**
- Create: `apps/backend/app/services/classification/suggester.py`
- Modify: `apps/backend/app/api/routes/library_organize.py` (add POST /library/classify-suggestions)
- Modify: `apps/frontend/src/features/library/LibraryPendingPanel.tsx`

- [ ] **Step 1: Create RuleBasedSuggester**

```python
class RuleBasedSuggester:
    def suggest(self, file: File) -> list[dict]:
        suggestions = []
        name = file.name.lower()
        path = file.path.lower()
        
        # Filename pattern matching
        if any(kw in name for kw in ["movie", "film", "episode"]):
            suggestions.append({"type": "movie", "placement": "media", "confidence": 0.6, "reason": "Filename contains movie-related keywords"})
        if any(kw in name for kw in ["setup", "install", "portable"]):
            suggestions.append({"type": "software", "placement": "software", "confidence": 0.7, "reason": "Filename suggests software installer"})
        
        # Directory name heuristics
        if any(kw in path for kw in ["games", "game", "steam"]):
            suggestions.append({"type": "game", "placement": "games", "confidence": 0.8, "reason": "File is in a game-related directory"})
        if any(kw in path for kw in ["books", "ebooks", "documents"]):
            suggestions.append({"type": "document", "placement": "books", "confidence": 0.7, "reason": "File is in a document-related directory"})
        
        return suggestions
```

- [ ] **Step 2: Add API endpoint**

```python
@router.post("/library/classify-suggestions")
def get_classify_suggestions(payload: ClassificationSuggestionsRequest, db=Depends(get_db)):
    suggester = RuleBasedSuggester()
    files = [files_service.get_file(db, fid) for fid in payload.file_ids]
    results = []
    for f in files:
        suggestions = suggester.suggest(f)
        results.append({"file_id": f.id, "name": f.name, "suggestions": suggestions})
    return {"items": results}
```

- [ ] **Step 3: Frontend — suggestion UI**

In `LibraryPendingPanel.tsx`, add a "Get Suggestions" button. When clicked, calls the suggestion API and renders suggestion cards with Accept/Reject buttons. Accepted suggestions update file placement via the existing placement API.

- [ ] **Step 4: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/services/classification/suggester.py apps/backend/app/api/routes/library_organize.py apps/frontend/src/features/library/LibraryPendingPanel.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add rule-based classification suggestions with accept/reject UI"
```

---

### Task C2: Game launcher

**Files:**
- Modify: `apps/desktop/electron/main.ts` (add launch-file IPC)
- Modify: `apps/desktop/electron/preload.ts` (expose launchFile)
- Modify: `apps/frontend/src/services/desktop/openActions.ts`
- Modify: `apps/frontend/src/features/details-panel/sections/DetailsActionsSection.tsx`

- [ ] **Step 1: Add launch-file IPC handler**

In `main.ts`:

```typescript
ipcMain.handle("asset-workbench:launch-file", async (_event, filePath: string) => {
  try {
    const { spawn } = require("child_process");
    const proc = spawn(filePath, [], { detached: true, stdio: "ignore", cwd: path.dirname(filePath) });
    proc.unref();
    return { ok: true };
  } catch (e) {
    return { ok: false, reason: String(e) };
  }
});
```

- [ ] **Step 2: Expose in preload**

```typescript
launchFile: (filePath: string) => ipcRenderer.invoke("asset-workbench:launch-file", filePath),
```

- [ ] **Step 3: Frontend — Launch button**

In `DetailsActionsSection.tsx`, add a "Launch" button for files with `effective_placement === "games"`. Use the existing `openIndexedFile` as fallback for browser mode.

```tsx
{canLaunch && (
  <button className="primary-button" onClick={handleLaunch}>Launch Game</button>
)}
```

- [ ] **Step 4: TypeScript compile, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/desktop/electron/main.ts apps/desktop/electron/preload.ts apps/frontend/src/services/desktop/openActions.ts apps/frontend/src/features/details-panel/sections/DetailsActionsSection.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add game launcher with IPC process spawn"
```

---

### Task C3: Game session tracking

**Files:**
- Create: `apps/backend/app/db/models/game_session.py`
- Modify: `apps/backend/app/db/session/engine.py` (add migration)
- Modify: `apps/backend/app/api/routes/files.py` (add session endpoints)
- Modify: `apps/frontend/src/features/details-panel/sections/DetailsActionsSection.tsx`

- [ ] **Step 1: Create model**

```python
class GameSession(Base):
    __tablename__ = "game_sessions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"))
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    duration_seconds: Mapped[int | None]
```

- [ ] **Step 2: Add API**

```python
@router.post("/files/{file_id}/sessions")
def start_game_session(file_id: int, db=Depends(get_db)):
    session = GameSession(file_id=file_id, started_at=utcnow())
    db.add(session); db.commit()
    return {"id": session.id}

@router.patch("/files/{file_id}/sessions/{session_id}")
def end_game_session(file_id: int, session_id: int, db=Depends(get_db)):
    session = db.get(GameSession, session_id)
    session.ended_at = utcnow()
    session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())
    db.commit()
    return {"item": {"id": session.id, "duration_seconds": session.duration_seconds}}
```

- [ ] **Step 3: Frontend — Start/End session buttons**

In the Launch button group, start a session before launch:

```tsx
const handleLaunch = async () => {
  const session = await startGameSession(fileId);
  await launchFile(filePath);
  // Show "End Session" button with elapsed timer
  setActiveSession(session);
};
```

- [ ] **Step 4: Commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/db/models/game_session.py apps/backend/app/db/session/engine.py apps/backend/app/api/routes/files.py apps/frontend/src/features/details-panel/sections/DetailsActionsSection.tsx
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add game session tracking with start/end controls"
```

---

### Task C4: Multi-panel / drag layout

**Files:**
- Modify: `apps/frontend/src/app/shell/AppShell.tsx`
- Modify: `apps/frontend/src/app/styles/shell-layout.css`

- [ ] **Step 1: Add quick-access panel toggle**

In `AppShell.tsx`:

```tsx
const [showQuickPanel, setShowQuickPanel] = useState(() => {
  try { return JSON.parse(localStorage.getItem("WORKBENCH_QUICK_PANEL") ?? "false"); } catch { return false; }
});

// Ctrl+Q handler in useKeyboardShortcuts
if ((e.ctrlKey || e.metaKey) && e.key === "q") { e.preventDefault(); toggleQuickPanel(); }
```

- [ ] **Step 2: Add quick-access panel component**

```tsx
function QuickAccessPanel() {
  return (
    <div className="quick-access-panel">
      <div className="quick-access-section">
        <h4>Recent Files</h4>
        <QuickFileList limit={10} />
      </div>
      <div className="quick-access-section">
        <h4>Favorites</h4>
        <QuickFileList filter="favorite" limit={10} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: CSS — support 3-panel layout**

```css
.app-shell__content--quick-panel {
  grid-template-columns: 220px minmax(0, 1fr) 344px;
}

.quick-access-panel {
  width: 200px;
  border-right: 1px solid var(--color-border);
  padding: 12px;
  overflow-y: auto;
}
```

- [ ] **Step 4: Save layout preferences to localStorage**

```typescript
useEffect(() => {
  localStorage.setItem("WORKBENCH_PANEL_LAYOUT", JSON.stringify({
    quickPanel: showQuickPanel,
    detailsPanel: isDetailsPanelOpen,
    detailsWidth: detailsPanelWidth,
  }));
}, [showQuickPanel, isDetailsPanelOpen, detailsPanelWidth]);
```

- [ ] **Step 5: Type check, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/frontend/src/app/shell/AppShell.tsx apps/frontend/src/app/styles/shell-layout.css apps/frontend/src/shared/hooks/useKeyboardShortcuts.ts
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat(frontend): add quick-access panel with multi-panel drag layout"
```

---

## Final Verification

```powershell
# Backend
& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests/" -q --tb=line

# Frontend
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx vitest run; npx tsc --noEmit

# Desktop
Set-Location "T:\Windows\Documents\GitHub\w\apps\desktop"; npx tsc --noEmit
```

Expected: All tests pass across all three tiers.
