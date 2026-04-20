import { BooksFeature } from "../../features/books/BooksFeature";


export function BooksPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Ebook subset listing</span>
        <h3>Books</h3>
        <p>Use Books as the dedicated ebook-subset entry in the indexed library, with shared file details and actions continuing through the common workbench flow.</p>
      </header>
      <BooksFeature />
    </section>
  );
}
