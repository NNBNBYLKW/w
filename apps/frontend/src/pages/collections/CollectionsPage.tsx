import { CollectionsFeature } from "../../features/collections/CollectionsFeature";
import { t } from "../../shared/text";


export function CollectionsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.collections.eyebrow")}</span>
        <h3>{t("pages.collections.title")}</h3>
        <p>{t("pages.collections.description")}</p>
      </header>
      <CollectionsFeature />
    </section>
  );
}
