# Page Spec — Library Pending

## 1. Page Role
整理候选项评审与 plan generation。用户在此查看 scanned candidates，选择 template，生成 suggestions，创建 organize plan。

## 2. Route / Entry
Route: `/library?tab=pending`
File: `apps/frontend/src/features/library/LibraryFeature.tsx`
Component: `LibraryPendingPanel` + `CandidateDetail`

## 3. Existing Components / Files
- `LibraryPendingPanel` — toolbar, candidate list, root selector, add form
- `CandidateDetail` — selected candidate detail + suggestions
- `CandidateList` — side list

## 4. Data Sources / API
- `listOrganizeCandidates(params)` — candidate list
- `scanOrganizeCandidates()` — scan trigger
- `generateOrganizePlan(candidateIds, targetRootId, templateKey)` — generate plan
- `listLibraryRoots()` — target root lookup
- `listOrganizeTemplates()` — template dropdown
- `generateOrganizeSuggestions(candidateId)` — generate suggestions
- `listOrganizeSuggestions(candidateId)` — list suggestions
- `acceptOrganizeSuggestion(id)` / `rejectOrganizeSuggestion(id)` — lifecycle

## 5. Must Preserve
- Candidate scanning and listing
- Multi-select + generate plan
- Target root resolution
- Template selection
- Suggestions with rule_based provider
- All safety notices

## 6. Design Target
From `design.pen`: Candidate list (left) + detail (right). Suggestions panel with Accept/Reject. Template dropdown. Root selector modal.

## 7. UI Structure
```
Tab: Pending
├── Toolbar
│   ├── Template dropdown (Auto / movie_default / anime_default / ...)
│   ├── [Scan Candidates]
│   └── [Generate Plan]
├── Target root info line
├── Candidate Layout (horizontal)
│   ├── Candidate List (left column)
│   │   ├── CandidateRow (selected)
│   │   ├── CandidateRow
│   │   └── ...
│   └── Candidate Detail (right column)
│       ├── display_name, type, confidence, source_path
│       ├── Suggestions Section
│       │   ├── [Generate Suggestions]
│       │   ├── SuggestionCard (template_key, pending, Accept/Reject)
│       │   ├── SuggestionCard (title, accepted)
│       │   └── SuggestionCard (tags, rejected)
│       └── Safety note ("rule_based · local only")
└── Root Selector Modal (conditional)
```

## 8. States
- Loading candidates
- No candidates
- Candidate selected
- Suggestions loading
- Suggestions generated (pending)
- Suggestions accepted/rejected
- 0 roots → source root fallback
- 1 root → auto-selected
- Multiple roots + default → default selected
- Multiple roots + no default → must select

## 9. Risk Points
- Root selector modal on multi-root setups
- Suggestions duplicate prevention
- Template key validation on generate

## 10. Acceptance Checklist
- [ ] Candidate list loads
- [ ] Candidate detail renders on select
- [ ] Template dropdown works
- [ ] Scan / Generate buttons work
- [ ] Root selector modal works
- [ ] Suggestions generate/list/accept/reject works
- [ ] No real LLM/cloud AI claims in UI
