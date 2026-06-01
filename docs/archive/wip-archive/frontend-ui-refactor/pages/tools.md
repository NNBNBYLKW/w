# Page Spec — Tools

## 1. Page Role
受控本地工具入口。当前唯一工具是 Video Merge。

## 2. Route / Entry
Route: `/tools`
Files:
- `apps/frontend/src/pages/tools/ToolsPage.tsx` → `ToolsPage`
- `apps/frontend/src/features/tools/ToolsFeature.tsx` → `ToolsFeature`

## 3. Existing Components / Files
`ToolsFeature` — tool list, create run form, run status display.

## 4. Data Sources / API
- `listTools()` — available tools
- `listToolRuns({page, page_size})` — run history
- `getToolRun(runId)` — single run detail
- `createVideoMergeRun({input_paths, output_path})` — create merge
- `listIndexedFiles({...})` — select input files

## 5. Must Preserve
- Tool listing
- Video merge tool (create, monitor, view output)
- Safety constraints (no arbitrary commands)

## 6. Design Target
From `design.pen`: Tool cards with description. Run list with status. Create form with file selection.

## 7. UI Structure
```
Tools Page
├── PageHeader ("Tools" + description)
├── Tool Card (Video Merge)
│   ├── Tool description
│   ├── Create run form (input files, output path)
│   └── Run history list (status, timestamps, log)
└── EmptyState (no tools available)
```

## 8. States
- Loading tools
- Tools available
- No tools
- Run creating
- Run pending/running/completed/failed
- Error

## 9. Risk Points
- Video merge is subprocess — don't do UI refactor that could break execution monitoring
- Keep safety guard: no arbitrary user scripts

## 10. Acceptance Checklist
- [ ] Tools page loads
- [ ] Video Merge tool visible
- [ ] Create run form works
- [ ] Run history loads
- [ ] Run status updates
