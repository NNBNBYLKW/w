import { RecentImportsFeature } from "../../features/recent-imports/RecentImportsFeature";
import { t } from "../../shared/text";


export function RecentImportsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.recent.eyebrow")}</span>
        <h3>{t("pages.recent.title")}</h3>
        <p>{t("pages.recent.description")}</p>
      </header>
      <RecentImportsFeature />
    </section>
  );
}
