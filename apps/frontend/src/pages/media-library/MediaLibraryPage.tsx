import { MediaLibraryFeature } from "../../features/media-library/MediaLibraryFeature";


export function MediaLibraryPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Indexed media listing</span>
        <h3>Media Library</h3>
        <p>Browse active indexed image and video files with a minimal scope switch and stable pagination.</p>
      </header>
      <MediaLibraryFeature />
    </section>
  );
}
