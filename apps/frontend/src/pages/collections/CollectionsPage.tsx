import { CollectionsFeature } from "../../features/collections/CollectionsFeature";


export function CollectionsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Saved collections</span>
        <h3>Collections</h3>
        <p>Use saved collections as a reusable retrieval entry for active indexed files.</p>
      </header>
      <CollectionsFeature />
    </section>
  );
}
