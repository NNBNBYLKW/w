# Page Spec — Settings

## 1. Page Role
本地偏好设置入口。包含 source management 和 system status。

## 2. Route / Entry
Route: `/settings`
Files:
- `apps/frontend/src/pages/settings/SettingsPage.tsx` → `SettingsPage`
- `apps/frontend/src/features/source-management/SourceManagementFeature.tsx` → `SourceManagementFeature`
- `apps/frontend/src/features/system-status/SystemStatusFeature.tsx` → `SystemStatusFeature`

## 3. Existing Components / Files
- `SourceManagementFeature` — source list, add source (folder picker + manual), scan trigger, enable/disable
- `SystemStatusFeature` — backend status, environment info

## 4. Data Sources / API
- `getSources()` / `createSource()` / `triggerSourceScan()` from `sourcesApi`
- `getSystemStatus()` from `systemApi`
- `selectFolder` electron bridge (same as managed roots)

## 5. Must Preserve
- Source list and management
- Folder picker for sources
- Source scan triggers
- System status display
- Segmented control for theme toggle (if present)

## 6. Design Target
From `design.pen`: Card sections for Source Management and System Status. Source list with status/scan actions. Add source form with folder picker.

## 7. UI Structure
```
Settings Page
├── PageHeader ("Settings" + description)
├── Theme Toggle (light/dark segmented control)
├── Section: Source Management
│   ├── Source List
│   │   ├── SourceCard (path, status, enabled/disabled badge)
│   │   │   ├── [Scan]
│   │   │   └── [Disable/Enable]
│   │   └── ...
│   ├── [+ Add Source]
│   └── Add Form
│       ├── Folder picker / manual input
│       ├── Display name
│       └── [Add] [Cancel]
└── Section: System Status
    ├── Backend connection status
    ├── Environment fingerprint
    └── Diagnostic info
```

## 8. States
- Loading sources
- No sources
- Sources with status
- Scan running / completed / failed
- System online / offline
- Add form: folder picker / browser fallback

## 9. Risk Points
- Source scan is async
- Folder picker not available in browser

## 10. Acceptance Checklist
- [ ] Settings page loads
- [ ] Theme toggle works (light/dark)
- [ ] Source list renders
- [ ] Add/scan source works
- [ ] Folder picker works (Electron)
- [ ] Browser fallback works
- [ ] System status displays
- [ ] Cancel button shows "Cancel" / "取消"
