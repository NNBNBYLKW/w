# Workbench Library v2

> Status: **Phase 7A–7F Complete, Phase 8 Complete, v0.3.0 source updates documented** | 2026-05-28

## Source vs Managed Root

Understanding the difference between Sources and Managed Roots is essential:

- **Source**: A folder you scan to **index** files. Sources are read-only — Workbench never modifies, moves, or deletes files within them. Files discovered via source scanning are marked as `external` and remain at their original location.
- **Managed Root**: A folder where organized files **land**. Files are moved or copied from sources (or the inbox) into managed roots via organize plans. Once placed, files are marked as `managed` and are tracked within the library structure.

## What is Library v2

Library v2 extends Workbench from a source-scan indexing tool into a managed library workflow. Users can import files and folders into a managed library, review and classify them, generate organize plans, execute moves, and browse by storage scope.

Library v2 operates in **hybrid mode** alongside the existing source-scan beta mainline. Source scanning continues to work unchanged.

## Main Chain

```
Import → Inbox → Object Detection → Review → Organize Candidate
→ Draft Plan → Execute → Managed Library → Browse/Search/Details → Recovery
```

## Storage States

| State | Meaning |
|---|---|
| `external` | File found by source scan (original beta path) |
| `inbox` | File copied into 00_Inbox, not yet organized |
| `managed` | File moved to managed library target after execute |

Default browse/search shows **All** — external files are never hidden.

## Phase Summary

| Phase | Capability | Status |
|---|---|---|
| 7A | Data foundation: storage_state, import tables, operation_journal, path_history | ✓ |
| 7B | Copy-only import: batches, inbox items, file copy to 00_Inbox | ✓ |
| 7B+ | Folder-as-object: object boundary detection, member roles | ✓ |
| 7C | Inbox review: confirm, reject, create OrganizeCandidate, draft plan | ✓ |
| 7D | Execute + path sync: move to managed, sync files.path, storage_state=managed | ✓ |
| 7E | Storage scope: search/browse/details filters, storage summary | ✓ |
| 7F | Recovery: orphan/missing detection, failed import retry, diagnostics | ✓ |
| 8+ | Browse v2 object management: compose, amendment add/remove, soft member status | ✓ |
| 13+ | Source-backed updates: soft trash API, persisted recovery findings, safe repair subset, checksum duplicate report, mixed amendment draft creation | Partial / documented |

## Safety Invariants

- Copy-only default (no move on import)
- No overwrite (auto-suffix on conflict)
- No delete of source files
- Preflight required before execute
- operation_journal for all file operations
- file_path_history for all path changes
- recovery_findings are persisted
- backend-only trash/restore is soft index state, not filesystem deletion
- duplicate detection is report-only; no auto cleanup
- AI never executes actions or writes final facts

## Document Index

- [Phase 7 Completion Report](PHASE7_COMPLETION_REPORT.md)
- [Architecture](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
- [Manual Acceptance Guide](MANUAL_ACCEPTANCE_GUIDE.md)
- [Known Limitations](KNOWN_LIMITATIONS.md)
- [Beta Testing Checklist](BETA_TESTING_CHECKLIST.md)
