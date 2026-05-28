import { SoftwareFeature } from "../../features/software/SoftwareFeature";
import { t } from "../../shared/text";


export function SoftwarePage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.software.eyebrow")}</span>
        <h3>{t("pages.software.title")}</h3>
        <p>{t("pages.software.description")}</p>
      </header>
      <SoftwareFeature />
    </section>
  );
}
