import { HomeOverviewFeature } from "../../features/home-overview/HomeOverviewFeature";
import { t } from "../../shared/text";


export function HomePage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.home.eyebrow")}</span>
        <h3>{t("pages.home.title")}</h3>
        <p>{t("pages.home.description")}</p>
      </header>
      <HomeOverviewFeature />
    </section>
  );
}
