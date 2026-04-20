import { SoftwareFeature } from "../../features/software/SoftwareFeature";


export function SoftwarePage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Software-related files listing</span>
        <h3>Software</h3>
        <p>Review recognized .exe, .msi, and .zip files from the indexed library with shared details, sorting, and pagination.</p>
      </header>
      <SoftwareFeature />
    </section>
  );
}
