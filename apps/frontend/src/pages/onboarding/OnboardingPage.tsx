import { SourceManagementFeature } from "../../features/source-management/SourceManagementFeature";


export function OnboardingPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Phase 0</span>
        <h3>Source onboarding</h3>
        <p>Add sources, review persisted source rows, and trigger placeholder scan tasks.</p>
      </header>
      <SourceManagementFeature />
    </section>
  );
}
