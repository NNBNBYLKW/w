import { FileBrowserFeature } from "../../features/file-browser/FileBrowserFeature";


export function FilesPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Indexed listing</span>
        <h3>Indexed Files</h3>
        <p>Browse active indexed file records by source and exact directory, without switching into tree navigation.</p>
      </header>
      <FileBrowserFeature />
    </section>
  );
}
