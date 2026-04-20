import { SourceManagementFeature } from "../../features/source-management/SourceManagementFeature";
import { SystemStatusFeature } from "../../features/system-status/SystemStatusFeature";


export function SettingsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Source and system entry</span>
        <h3>Settings</h3>
        <p>Use this lightweight page as the source and system entry for the local-first workbench.</p>
      </header>
      <SystemStatusFeature
        eyebrow="System overview"
        title="System status"
        description="Review current runtime and indexed-content totals before adding or rescanning sources."
      />
      <SourceManagementFeature />
    </section>
  );
}
