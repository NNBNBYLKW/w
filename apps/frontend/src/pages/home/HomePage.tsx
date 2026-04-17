import { HomeOverviewFeature } from "../../features/home-overview/HomeOverviewFeature";


export function HomePage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Workbench entry</span>
        <h3>Home</h3>
        <p>Use this lightweight entry page to review system status, recent indexing activity, and source coverage before jumping into a focused workbench flow.</p>
      </header>
      <HomeOverviewFeature />
    </section>
  );
}
