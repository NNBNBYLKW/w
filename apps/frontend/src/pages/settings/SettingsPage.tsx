import { SourceManagementFeature } from "../../features/source-management/SourceManagementFeature";
import { SystemStatusFeature } from "../../features/system-status/SystemStatusFeature";


export function SettingsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Current MVP settings</span>
        <h3>Settings</h3>
        <p>Manage the current source and system capabilities here without expanding into a broader preferences surface.</p>
      </header>
      <SystemStatusFeature
        eyebrow="Current runtime"
        title="System status"
        description="Review the current runtime and indexed-content totals before adding or rescanning sources."
      />
      <SourceManagementFeature />
    </section>
  );
}
