import { MediaLibraryFeature } from "../../features/media-library/MediaLibraryFeature";
import { t } from "../../shared/text";


export function MediaLibraryPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.media.eyebrow")}</span>
        <h3>{t("pages.media.title")}</h3>
        <p>{t("pages.media.description")}</p>
      </header>
      <MediaLibraryFeature />
    </section>
  );
}
