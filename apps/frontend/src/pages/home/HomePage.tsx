import { HomeOverviewFeature } from "../../features/home-overview/HomeOverviewFeature";


export function HomePage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Lightweight overview</span>
        <h3>Home</h3>
        <p>Use this lightweight overview page as the main entry to system status, source coverage, and the current indexed-file flows.</p>
      </header>
      <HomeOverviewFeature />
    </section>
  );
}
