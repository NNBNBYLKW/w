import { TagBrowserFeature } from "../../features/tag-browser/TagBrowserFeature";
import { t } from "../../shared/text";


export function TagsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.tags.eyebrow")}</span>
        <h3>{t("pages.tags.title")}</h3>
        <p>{t("pages.tags.description")}</p>
      </header>
      <TagBrowserFeature />
    </section>
  );
}
