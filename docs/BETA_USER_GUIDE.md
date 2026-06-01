# Workbench Beta User Guide (v0.3.0)

## 1. What Workbench Is

Workbench is a **Windows local-first asset workbench**. It helps you organize your personal media files — movies, anime, games, courses, image sets, document sets, and more — into a structured library.

The core workflow is:

**find → inspect → tag → refind → browse**

- **Find**: Scan folders on your computer to discover files.
- **Inspect**: View file details, thumbnails, previews, and metadata.
- **Tag**: Add tags, color tags, favorites, and ratings to files.
- **Refind**: Use Recent, Tags, Collections, and browse surfaces to find files again.
- **Browse**: View files organized by type (Media, Documents, Games, Software).

Everything runs on your local machine. Nothing is uploaded to the cloud.

### Current Capabilities

- **BrowseV2** with domain/category taxonomy sidebar for structured browsing
- **Source scan** with bulk INSERT for fast file indexing
- **Managed Roots** for organizing files into structured libraries
- **Import to Inbox** (copy-only with same-volume move support)
- **Organize Plans** with draft -> ready -> preflight -> execute lifecycle
- **Object management** with amendment (add/remove members)
- **Recovery diagnostics** with safe auto-repair
- **Trash/Restore** (30-day soft delete with restore)
- **Game launcher** with session tracking
- **AI classification suggestions** (rule-based)
- **AI recognition** for images, audio, documents, and executables
- **Dark/light theme** with custom accent colors
- **Internationalization** (English + Simplified Chinese)
- **Keyboard shortcuts** for common actions

## 2. What Workbench Is Not

Workbench is **not**:

- **A file explorer replacement.** It does not replace Windows Explorer. It is a library organizer, not a file manager.
- **A full game platform.** Workbench can launch games and track play sessions, but does not replace dedicated game platforms like Steam or GOG.
- **A media player.** It shows thumbnails and previews but is not a video or audio player.
- **A document reader or editor.** It detects document formats but does not open or edit them.
- **A software installer.** It catalogs software-related files but does not install or run them.
- **An AI auto-classification platform.** Suggestions are rule-based and run entirely locally. No cloud AI, no LLM, no external API calls, no training data uploaded.

## 3. Core Concepts

### Source
A folder on your computer that you want Workbench to scan. Sources are where files come from. Workbench **reads** from sources — it never modifies, moves, or deletes files within them. Files discovered via source scanning remain at their original location and are marked as `external`. You can have multiple sources (e.g., `G:\Downloads`, `D:\Media\Inbox`).

### Managed Library Root
A folder where organized files **land**. When you run an organize plan, files are moved or copied from sources (or the inbox) into a managed root. Only use folders you control. Files in managed roots are tracked as `managed` storage state.

### DetailsPanel
The right-side panel that shows full information about a selected file: path, size, type, metadata, preview, tags, color tags, favorites, ratings, placement, and open actions.

### Tags / Color Tags
- **Tags**: Normal text labels you can attach to files (e.g., "watched", "favorite", "archive").
- **Color Tags**: Five colors (red, yellow, green, blue, purple) for visual categorization.

### Collections
Smart lists of files based on criteria like file type, tag, color tag, or source. Collections auto-update when files match their criteria.

### Library Objects
Higher-level entries in your library (e.g., a movie, an anime series, a game). Objects can contain multiple files and have an `asset.yaml` metadata file.

### Candidates
Files or objects that Workbench detected as "pending organization" — they need a target location and possibly metadata.

### Organize Plans
A plan describes what Workbench will do: which files to move, where to put them, and what metadata to write. **Plans do not execute automatically.** You must explicitly mark them ready, preflight, and confirm execution.

### Preflight
A safety check that runs before execution. It verifies that every action in the plan is safe: paths are within boundaries, files are not overwritten, and targets are reachable. If preflight finds issues, execution is blocked.

### Execute
The actual file operations: creating directories, moving files, writing `asset.yaml`. **This is the only step that modifies your disk.**

### Reconcile
After execution, reconcile checks what actually happened on disk vs. what the plan expected. Useful for verifying that everything went correctly.

### Rollback Draft
A draft plan that reverses the file moves from a completed or failed plan. **Rollback is always a draft.** You must still mark it ready, preflight, and execute — just like any other plan.

### asset.yaml
A small metadata file that Workbench writes into your managed library. It contains title, year, type, tags, and other fields. Workbench follows a **create-only / safe merge** policy: it never overwrites an existing `asset.yaml` without creating a backup first.

## 4. First Run

1. **Launch Workbench.** You should see the home page with the sidebar and an empty details panel.
2. **Open Settings.** Check that "System Status" shows `database: ok`. This means the local backend is running.
3. **Add a source.** Go to Settings → Sources, click "Add Source", and select a folder with some files (e.g., `Downloads` or a test folder).
4. **Scan the source.** Click "Scan" next to the source. Wait for it to complete. The scan discovers all files in the folder.
5. **Search files.** Go to Search. You should see files from your source. Try searching by name.
6. **Inspect a file.** Click a file in the search results. The DetailsPanel on the right shows its details.

## 5. Basic Workflow

Here is the full workflow from start to finish. **Use a test folder with disposable files for your first time.**

### Find
1. Go to Settings → Sources → Add a test source folder.
2. Click "Scan" to index files.
3. Go to Search to confirm files are discovered.

### Inspect
4. Click a file in search results.
5. The DetailsPanel shows: name, path, size, type, timestamps, metadata, preview.
6. Click different files to compare details.

### Tag
7. In the DetailsPanel, add a tag (e.g., "test").
8. Add a color tag (e.g., red).
9. Mark as favorite, set a rating.
10. All changes save immediately.

### Refind
11. Go to Recent to see recently discovered or tagged files.
12. Go to Tags to browse files by tag.
13. Go to Collections to see any smart collections matching your files.

### Organize (test folder only)
14. Go to Library → Managed Roots → Add a managed root (a test output folder).
15. Go to Library → Pending → Scan Candidates.
16. Select candidates and click "Generate Plan".
17. Review the plan: check source paths, target paths, action types.
18. Click "Mark Ready" to lock the plan.
19. Click "Preflight" to run safety checks.
20. If preflight passes (`can_execute: true`), click "Execute" and confirm.
21. After execution, click "Reconcile" to verify the results.
22. Files should now be in your managed root.

### Rollback (only if needed)
23. Go to Library → Plans → select the completed plan.
24. Click "Generate Rollback".
25. A new draft plan appears that reverses the moves.
26. You must still mark ready, preflight, and execute the rollback.

## 6. Safe Organizing Rules

Workbench follows these safety rules:

- **Create-only asset.yaml.** If an `asset.yaml` already exists at the target, execution is blocked.
- **No overwrite.** If a file already exists at the target path, execution is blocked.
- **No delete/rmdir.** Only mkdir, move, rename, and asset.yaml write are supported.
- **No script execution.** Workbench never runs or opens files.
- **Rollback is draft only.** Generate-rollback creates a draft plan. It does not move files back automatically. You must explicitly execute it.
- **Preflight is required.** You cannot execute a plan that has not passed preflight.
- **Test first.** Use a disposable test folder before organizing your real library.

## 7. Recovery / Troubleshooting

### Backend unavailable
If the status indicator shows "disconnected" or the app shows a blank page:
- The backend process may have stopped. Close and restart Workbench.
- In the desktop app, the backend starts automatically.
- In dev mode, make sure `uvicorn` is running on port 8000.

### Source folder missing
If a source folder was deleted or moved:
- Go to Settings → Sources → disable or remove the source.
- The existing indexed files remain in the database.

### Thumbnail unavailable
If a file shows "Preview unavailable" instead of an image:
- This is normal for corrupted video files or unsupported formats.
- The app shows a placeholder, not an error.
- Thumbnails are generated on demand and cached.

### Plan preflight failed
Preflight rejected the plan:
- Read the blocked action messages in the plan detail.
- Common causes: target path outside source/managed root, target already exists, source no longer exists, managed root disabled.
- Edit the affected actions or fix the underlying issue.

### Plan execution failed
If execution stops partway:
- Check the execution log in the plan detail.
- Some actions may have succeeded, some failed. The plan status shows `failed` or `completed_with_errors`.
- Use "Copy Failed Actions" to create a new draft plan with just the failed actions.

### App closed during execution
If Workbench closes or crashes during plan execution:
- When you restart, the plan is automatically marked as "failed" with a note: "Interrupted on application startup."
- You can regenerate and re-execute the plan, or use rollback to move files back.

### Rollback draft generated
- The rollback is a draft plan that reverses the file moves.
- It does not undo `mkdir` or `asset.yaml` writes.
- You must mark ready, preflight, and execute it — just like any plan.
- If rollback preconditions fail (files moved, paths changed), some actions may be blocked.

### Managed root rejected
If Workbench rejects a folder as a managed library root:
- The folder may be a system directory (Windows, Program Files), a drive root, or the Workbench data directory.
- Choose a different folder — one you created for your library.

## 8. Known Limitations

See `docs/KNOWN_LIMITATIONS.md` for the current list. Key ones:

- **Large scans can be slow.** A 10K-file test scan took ~4.5 minutes. Larger libraries will take longer.
- **Media thumbnails load slowly** on the Media page for large libraries (loading many images at once).
- **Clean-machine installer smoke test** has not been completed yet — the packaging pipeline has been verified but the installer has not been tested on a fresh Windows machine.
- **Frontend automated tests are partial.** Vitest and Playwright smoke infrastructure exist, but manual QA is still required for beta release confidence.
- **No cross-volume move atomicity guarantee.** Moving files between different drives is not guaranteed to be atomic.
- **Operation logs are not automatic rollback.** `operation_journal` and `file_path_history` exist, but recovery still relies on explicit retry, copy-failed-actions, rollback drafts, or manual review.
- **AI classification is rule-based.** Suggestions are generated by local rules and models. No LLM or cloud services are used.
