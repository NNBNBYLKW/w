import { RecentImportsFeature } from "../../features/recent-imports/RecentImportsFeature";


export function RecentImportsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Recently indexed files</span>
        <h3>Recent Imports</h3>
        <p>Review active indexed files by when they were first discovered by the index, with a small recent-import window switch.</p>
      </header>
      <RecentImportsFeature />
    </section>
  );
}
