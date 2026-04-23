import { CollectionsFeature } from "../../features/collections/CollectionsFeature";


export function CollectionsPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Saved retrieval surface</span>
        <h3>Collections</h3>
        <p>
          Use saved retrieval conditions as reusable entry points for active indexed files. Selection continues into
          shared details and the existing open actions.
        </p>
      </header>
      <CollectionsFeature />
    </section>
  );
}
