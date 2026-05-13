import { t } from "../../shared/text";
import { FileBrowserFeature } from "../file-browser/FileBrowserFeature";

export function LibraryPathBrowserPanel() {
  return (
    <section className="library-path-panel library-design-panel library-design-panel--path">
      <div className="library-path-panel__intro library-design-hero">
        <span className="page-header__eyebrow">{t("features.library.path.eyebrow")}</span>
        <p>{t("features.library.path.description")}</p>
      </div>
      <FileBrowserFeature />
    </section>
  );
}
