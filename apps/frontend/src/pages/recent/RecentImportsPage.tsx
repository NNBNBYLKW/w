import { RecentImportsFeature } from "../../features/recent-imports/RecentImportsFeature";


export function RecentImportsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Recently indexed files</span>
        <h3>Recent</h3>
        <p>Review recently indexed files by when they were first discovered, with the current range switch, sorting, and pagination.</p>
      </header>
      <RecentImportsFeature />
    </section>
  );
}
