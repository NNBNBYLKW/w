import { TagBrowserFeature } from "../../features/tag-browser/TagBrowserFeature";


export function TagsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Tag-scoped retrieval</span>
        <h3>Tags</h3>
        <p>Use normal tags as a retrieval entry point for active indexed files, without expanding into tag-management tooling.</p>
      </header>
      <TagBrowserFeature />
    </section>
  );
}
