# Library v2 Beta Testing Checklist

## Before Testing

- [ ] Use disposable test directories only — not real important files
- [ ] Configure a managed library root in Library > Roots
- [ ] Prepare small test files and a test folder with software-like contents
- [ ] Run backend tests: `cd apps/backend && python -m pytest tests/test_library_v2_*.py -v`
- [ ] Run frontend build: `cd apps/frontend && npm run build`

## Import Flow

- [ ] Import single file → source preserved, inbox copy exists
- [ ] Import same file twice → auto-suffix (name (1).ext), no overwrite
- [ ] Import folder as object → object candidate created, members folded
- [ ] Import folder as loose files → individual inbox items created
- [ ] Import non-existent path → failed item visible, batch completed_with_errors

## Review Flow

- [ ] Select inbox item → set final_object_type → select target root → Confirm
- [ ] Reject inbox item → status changes to rejected
- [ ] Confirm object candidate → set final_type + launch candidate
- [ ] Create OrganizeCandidate from inbox item → candidate linked
- [ ] Create OrganizeCandidate from object candidate → one candidate only (members not split)

## Plan and Execute

- [ ] Generate Draft Plan → plan status = draft, no files moved
- [ ] Mark Ready → Preflight → Execute → plan completes
- [ ] After execute: source file still exists
- [ ] After execute: file moved to managed target (search finds it)
- [ ] After execute: DetailsPanel shows storage_state = Managed
- [ ] After execute: inbox item status = organized

## Storage Scope

- [ ] Search default All → external files visible
- [ ] Search External filter → only source-scanned files
- [ ] Search Inbox filter → only imported files
- [ ] Search Managed filter → only organized files
- [ ] Media/Books/Games/Software pages → storage scope dropdown present
- [ ] Library Overview → storage summary counts shown
- [ ] DetailsPanel → storage section shows state + path info

## Recovery

- [ ] Recovery summary returns counts (clean state = 0 high)
- [ ] Orphan inbox file detected (manually add file to 00_Inbox)
- [ ] Missing inbox copy detected (manually delete inbox copy)
- [ ] Missing managed file detected (manually move managed file)
- [ ] Orphan file not deleted by scan
- [ ] Failed import retry works (source restored → retry → imported)
- [ ] Retry preserves source, does not overwrite

## Bug Report Format

If a test fails, report:
1. Phase and step number
2. Expected behavior
3. Actual behavior
4. Error message or screenshot
5. Test directory contents used
