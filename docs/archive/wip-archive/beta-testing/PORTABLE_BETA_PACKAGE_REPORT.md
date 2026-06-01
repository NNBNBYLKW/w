# Portable Beta Package Report

> Date: 2026-05-15 | Build: #1

---

## Build Source

- **Git commit**: `035b303`
- **Dirty working tree**: yes (50+ modified files from organize improvements: candidate lifecycle fix, partial failure handling, script classification, ready-action-edit, preflight UX)
- **Branch**: main

## Commands Run

| Step | Command | Result |
|------|---------|--------|
| Frontend build | `cd apps/frontend && npm run build` | ✓ built in 1.41s |
| Backend bundle | `powershell ./scripts/build-backend.ps1` | ✓ PyInstaller success |
| FFmpeg prepare | `node ./scripts/prepare-ffmpeg-resource.mjs` | ✓ ffmpeg.exe prepared |
| Electron build | `npm run build` (tsc) | ✓ |
| Packager | `npx electron-builder --win --x64 --dir` | ✓ win-unpacked created |
| Portable assembly | Copy win-unpacked + docs + sample data | ✓ |
| Zip | `Compress-Archive` | ✓ |

## Artifacts Created

| Artifact | Path | Size |
|----------|------|------|
| Portable folder | `release/portable-beta/Workbench-Beta-Portable/` | ~285 MB |
| Zip file | `release/portable-beta/Workbench-Beta-Portable-20260515-035b303-dirty.zip` | **199 MB** |

## Included Files

```
Workbench-Beta-Portable/
├── Workbench Beta.exe          (201 MB, valid PE32+ x64)
├── resources/
│   ├── app.asar
│   ├── backend/
│   │   ├── workbench-backend.exe    (12.7 MB)
│   │   └── _internal/
│   ├── ffmpeg/
│   │   └── ffmpeg.exe              (79 MB)
│   └── frontend/
│       └── dist/
├── README_FIRST.txt            (使用说明，中文)
├── VERSION.txt
├── USER_MANUAL_BEGINNER.md     (小白使用说明书)
├── BETA_TESTER_CHECKLIST.md    (测试清单)
├── KNOWN_LIMITATIONS.md        (已知限制)
├── RECOVERY_GUIDE.md           (恢复说明)
├── FILE_CLASSIFICATION_RULES.md (文件分类规则)
└── sample-test-data/
    ├── source/
    │   ├── documents/          (readme.txt, notes.md)
    │   ├── media/              (placeholder)
    │   ├── software/           (sample-script.bat)
    │   └── organize/           ([MOVIE] + [SOFTWARE] 样例)
    └── managed/                (README only)
```

## Excluded Files (Verified)

- [x] No `.git/`
- [x] No `node_modules/`
- [x] No `.venv/` or `__pycache__/`
- [x] No `.pytest_cache/`
- [x] No `docs/_wip/`
- [x] No `*.db` / `*.sqlite` / `*.sqlite3`
- [x] No `logs/` / `cache/` / `thumbnails/`
- [x] No nested release artifacts
- [x] No real user file libraries (G:\WorkbenchLibraryTest, etc.)
- [x] No `skills-lock.json` or `.agents/`

## Smoke Test

| Check | Result |
|-------|--------|
| EXE valid PE32+ | ✓ 201 MB, x86-64, GUI |
| Backend exe present | ✓ workbench-backend.exe |
| Frontend dist present | ✓ |
| FFmpeg present | ✓ ffmpeg.exe |
| Launch attempt (non-interactive) | Process started and terminated cleanly (8s) |
| **Interactive UI smoke** | **NOT VERIFIED** |

The interactive UI smoke test requires a Windows desktop with display — cannot be run in this headless environment. A manual click-through test is needed before distributing to testers.

## Known Limitations

- This is a **beta testing package**, not a production release
- Working tree is dirty (uncommitted organize improvements)
- Interactive UI smoke not verified (requires desktop environment)
- Clean-machine test not run (requires a Windows machine without Python/Node/dev tools)
- No code signing — Windows SmartScreen may show a warning
- Default Electron icon used (no custom app icon)
- No NSIS installer included (this is portable/unpacked only)

## Recommendation

**Can hand to ONE trusted non-technical tester** after verifying the following on a Windows desktop:
1. Double-click `Workbench Beta.exe` starts successfully
2. Settings page shows system status OK
3. Backend auto-starts without errors
4. Add sample-test-data/source as a source directory
5. Scan and search work
6. DetailsPanel, tags, ratings work
7. Library Organize: generate plan + preflight only (do not execute on real data)

**Do NOT distribute broadly** until:
- Interactive smoke is verified
- Clean-machine test passes
- Current uncommitted changes are committed or explicitly documented
