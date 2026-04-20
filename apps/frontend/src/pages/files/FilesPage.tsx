import { FileBrowserFeature } from "../../features/file-browser/FileBrowserFeature";


export function FilesPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Indexed-files browse</span>
        <h3>Files</h3>
        <p>Browse active indexed file records by source and exact directory.</p>
      </header>
      <FileBrowserFeature />
    </section>
  );
}
