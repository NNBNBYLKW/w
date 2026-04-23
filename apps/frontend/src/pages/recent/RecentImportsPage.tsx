import { RecentImportsFeature } from "../../features/recent-imports/RecentImportsFeature";


export function RecentImportsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Recent retrieval family</span>
        <h3>Recent</h3>
        <p>
          Use recent imports, tags, and color tags as lightweight retrieval surfaces. Selection continues into shared
          details and the existing open actions.
        </p>
      </header>
      <RecentImportsFeature />
    </section>
  );
}
