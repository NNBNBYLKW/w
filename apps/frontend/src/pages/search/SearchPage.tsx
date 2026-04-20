import { SearchFeature } from "../../features/search/SearchFeature";


export function SearchPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Search results</span>
        <h3>Search</h3>
        <p>Review active indexed search results by name or path with the current filters, sorting, and pagination.</p>
      </header>
      <SearchFeature />
    </section>
  );
}
