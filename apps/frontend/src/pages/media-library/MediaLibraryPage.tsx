import { MediaLibraryFeature } from "../../features/media-library/MediaLibraryFeature";


export function MediaLibraryPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Indexed media library</span>
        <h3>Media</h3>
        <p>
          Browse active indexed images and videos as a visual media subset surface. Selection continues into the shared
          details panel and existing open actions.
        </p>
      </header>
      <MediaLibraryFeature />
    </section>
  );
}
