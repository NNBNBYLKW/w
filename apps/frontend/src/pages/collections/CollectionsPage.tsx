import { CollectionsFeature } from "../../features/collections/CollectionsFeature";


export function CollectionsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Saved collections</span>
        <h3>Collections</h3>
        <p>Save a minimal set of reusable file-retrieval conditions here without expanding into a rules engine or advanced query builder.</p>
      </header>
      <CollectionsFeature />
    </section>
  );
}
