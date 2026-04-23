import { BooksFeature } from "../../features/books/BooksFeature";


export function BooksPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Library subset surface</span>
        <h3>Books</h3>
        <p>
          Browse recognized ebook files in a focused subset surface. Selection continues into shared details and the
          existing open actions.
        </p>
      </header>
      <BooksFeature />
    </section>
  );
}
