import { SourceManagementFeature } from "../../features/source-management/SourceManagementFeature";


export function OnboardingPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Getting started</span>
        <h3>Source setup</h3>
        <p>Start source setup for the local-first workbench, review saved source rows, and run an initial scan.</p>
      </header>
      <SourceManagementFeature />
    </section>
  );
}
