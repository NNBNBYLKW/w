# Page Spec — Library Organize Plans

## 1. Page Role
整理计划控制台。创建、审查、执行 organize plans。包含完整 Phase 5 执行后闭环。

## 2. Route / Entry
Route: `/library?tab=plans`
File: `apps/frontend/src/features/library/LibraryFeature.tsx`
Components: `LibraryPlansPanel` + `PlanDetail`

## 3. Existing Components / Files
- `LibraryPlansPanel` — plan list with status filter
- `PlanDetail` — full plan view (summary, candidates, actions, path preview, asset.yaml, execution logs, Phase 5 blocks)

## 4. Data Sources / API
- `listOrganizePlans(params)` — plan list
- `getOrganizePlan(id)` — plan detail
- `markOrganizePlanReady(id)`, `preflightOrganizePlan(id)`, `executeOrganizePlan(id)` — lifecycle
- `cancelOrganizePlan(id)` — cancel
- `updateOrganizeAction(id, {...})` — edit action
- `reconcileOrganizePlan(id)` — 5A
- `copyFailedActions(id)` — 5B
- `generateRollbackPlan(id)` — 5C
- `generateAssetYamlMerge(actionId)` — 5D-1
- `getOrganizePlanLogs(id)` — execution logs

## 5. Must Preserve
- All plan lifecycle operations (draft→ready→preflight→execute)
- All Phase 5 operations
- Action list with conflict/stale/blocked/warning states
- Path preview (before/after)
- Asset.yaml preview
- Execution logs

## 6. Design Target
From `design.pen`: Plan cards with status pill + metadata. Plan detail with sections for summary, candidates, actions (type-badged), path preview, YAML preview, execution logs. Phase 5 follow-up blocks: Reconcile (5A), Copy Failed (5B), Rollback (5C), Merge (5D-1), Templates (5D-2), Suggestions (5D-3).

## 7. UI Structure
```
Tab: Plans
├── Plan List (left)
│   ├── PlanCard (status pill + title + metadata)
│   └── ...
└── Plan Detail (right, when selected)
    ├── Plan Header (title + PlanStatusPill)
    ├── Plan Summary
    ├── Candidates
    ├── Actions (type badges: mkdir, move, rename, write_asset_yaml...)
    ├── Path Preview (before / after)
    ├── Asset YAML Preview
    ├── Action Buttons (Mark Ready, Preflight, Execute, Cancel)
    ├── Phase 5 Follow-up (when completed/completed_with_errors/failed)
    │   ├── Reconcile (5A)
    │   ├── Copy Failed Actions (5B)
    │   ├── Generate Rollback (5C)
    │   ├── asset.yaml Merge (5D-1)
    │   └── Templates (5D-2) + Suggestions (5D-3) info
    └── Execution Logs
```

## 8. States
- Plan status: draft / ready / executing / completed / completed_with_errors / failed / cancelled
- Preflight: passed / blocked (with counts)
- Execution: running / finished
- Reconcile: pending / reconciled / failed
- Rollback: generated / no rollbackable actions
- Merge: generated / blocked

## 9. Risk Points
- Plan execution is async (polling)
- Many conditional sections based on status
- SQLite locking on concurrent operations

## 10. Acceptance Checklist
- [ ] Plan list loads with status filter
- [ ] Plan detail renders all sections
- [ ] Mark Ready / Preflight / Execute flow works
- [ ] Cancel work
- [ ] Phase 5A Reconcile block works
- [ ] Phase 5B Copy Failed Actions works
- [ ] Phase 5C Rollback works
- [ ] Phase 5D-1 Merge works
- [ ] Phase 5D-2 template display
- [ ] Phase 5D-3 suggestions display
