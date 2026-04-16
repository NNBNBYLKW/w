import { SearchFeature } from "../../features/search/SearchFeature";


export function SearchPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Phase 2A</span>
        <h3>Indexed search</h3>
        <p>Search now queries active indexed file records by name or path, with minimal file-type filtering, sorting, and pagination.</p>
      </header>
      <SearchFeature />
    </section>
  );
}
