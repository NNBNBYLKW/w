import { BooksFeature } from "../../features/books/BooksFeature";
import { t } from "../../shared/text";


export function BooksPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.books.eyebrow")}</span>
        <h3>{t("pages.books.title")}</h3>
        <p>{t("pages.books.description")}</p>
      </header>
      <BooksFeature />
    </section>
  );
}
