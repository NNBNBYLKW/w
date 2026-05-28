import { SourceManagementFeature } from "../../features/source-management/SourceManagementFeature";
import { SystemStatusFeature } from "../../features/system-status/SystemStatusFeature";
import { t, useLocale, type LocaleCode } from "../../shared/text";


export function SettingsPage() {
  const { locale, setLocale } = useLocale();
  const localeOptions: Array<{ label: string; value: LocaleCode }> = [
    { label: t("settings.locale.options.en"), value: "en" },
    { label: t("settings.locale.options.zhCN"), value: "zh-CN" },
  ];

  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.settings.eyebrow")}</span>
        <h3>{t("pages.settings.title")}</h3>
        <p>{t("pages.settings.description")}</p>
      </header>
      <section className="feature-shell">
        <div className="feature-header">
          <span className="page-header__eyebrow">{t("settings.locale.eyebrow")}</span>
          <h3>{t("settings.locale.title")}</h3>
          <p>{t("settings.locale.description")}</p>
        </div>
        <div className="settings-locale-switch" role="group" aria-label={t("settings.locale.ariaLabel")}>
          {localeOptions.map((option) => (
            <button
              key={option.value}
              className={`secondary-button settings-locale-button${locale === option.value ? " settings-locale-button--selected" : ""}`}
              type="button"
              onClick={() => setLocale(option.value)}
              aria-pressed={locale === option.value}
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>
      <SystemStatusFeature
        eyebrow={t("settings.systemStatus.eyebrow")}
        title={t("settings.systemStatus.title")}
        description={t("settings.systemStatus.description")}
      />
      <SourceManagementFeature />
    </section>
  );
}
