import { FileBrowserFeature } from "../../features/file-browser/FileBrowserFeature";
import { t } from "../../shared/text";


export function FilesPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.files.eyebrow")}</span>
        <h3>{t("pages.files.title")}</h3>
        <p>{t("pages.files.description")}</p>
      </header>
      <FileBrowserFeature />
    </section>
  );
}
