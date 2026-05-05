import { SearchFeature } from "../../features/search/SearchFeature";
import { t } from "../../shared/text";


export function SearchPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.search.eyebrow")}</span>
        <h3>{t("pages.search.title")}</h3>
        <p>{t("pages.search.description")}</p>
      </header>
      <SearchFeature />
    </section>
  );
}
