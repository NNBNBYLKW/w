import { MediaLibraryFeature } from "../../features/media-library/MediaLibraryFeature";


export function MediaLibraryPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Visual subset surface</span>
        <h3>Media</h3>
        <p>
          Browse indexed images and videos in a visual subset surface. Selection continues into shared details and the
          existing open actions.
        </p>
      </header>
      <MediaLibraryFeature />
    </section>
  );
}
