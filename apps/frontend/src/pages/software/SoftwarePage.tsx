import { SoftwareFeature } from "../../features/software/SoftwareFeature";


export function SoftwarePage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Library subset surface</span>
        <h3>Software</h3>
        <p>
          Browse recognized software-related files in a focused subset surface. Selection continues into shared details
          and the existing open actions.
        </p>
      </header>
      <SoftwareFeature />
    </section>
  );
}
