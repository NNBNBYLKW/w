import { SourceManagementFeature } from "../../features/source-management/SourceManagementFeature";
import { t } from "../../shared/text";


export function OnboardingPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.onboarding.eyebrow")}</span>
        <h3>{t("pages.onboarding.title")}</h3>
        <p>{t("pages.onboarding.description")}</p>
      </header>
      <SourceManagementFeature />
    </section>
  );
}
