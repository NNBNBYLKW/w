import { TagBrowserFeature } from "../../features/tag-browser/TagBrowserFeature";


export function TagsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Tag retrieval surface</span>
        <h3>Tags</h3>
        <p>Use normal tags as a retrieval surface for active indexed files. Selection continues into shared details and the existing open actions.</p>
      </header>
      <TagBrowserFeature />
    </section>
  );
}
