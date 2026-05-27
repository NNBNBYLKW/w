import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { SystemStatusFeature } from "../../features/system-status/SystemStatusFeature";
import { useTheme, type ThemeMode } from "../../shared/theme";
import { t, useLocale, type LocaleCode } from "../../shared/text";
import { ConfirmDialog, KeyValueRow, SectionCard, WorkbenchMasthead, WorkbenchPage } from "../../shared/ui/components";
import { getRuntimeDiagnostics, getSystemStatus, clearThumbnailCache } from "../../services/api/systemApi";


export function SettingsPage() {
  const { locale, setLocale } = useLocale();
  const { theme, setTheme } = useTheme();
  const [clearCacheConfirm, setClearCacheConfirm] = useState(false);
  const [cacheClearResult, setCacheClearResult] = useState<string | null>(null);
  const themeOptions: Array<{ label: string; value: ThemeMode }> = [
    { label: t("settings.appearance.options.light"), value: "light" },
    { label: t("settings.appearance.options.dark"), value: "dark" },
  ];
  const localeOptions: Array<{ label: string; value: LocaleCode }> = [
    { label: t("settings.locale.options.en"), value: "en" },
    { label: t("settings.locale.options.zhCN"), value: "zh-CN" },
  ];

  const systemQuery = useQuery({
    queryKey: ["system-status"],
    queryFn: getSystemStatus,
    staleTime: 60_000,
  });

  const runtimeQuery = useQuery({
    queryKey: ["runtime-diagnostics"],
    queryFn: getRuntimeDiagnostics,
    staleTime: 60_000,
  });

  const clearCacheMutation = useMutation({
    mutationFn: clearThumbnailCache,
    onSuccess: () => {
      setCacheClearResult(t("settings.cacheManagement.clearThumbnailsSuccess"));
      setClearCacheConfirm(false);
    },
    onError: () => {
      setCacheClearResult(t("settings.cacheManagement.clearThumbnailsFailed"));
      setClearCacheConfirm(false);
    },
  });

  return (
    <WorkbenchPage className="settings-workbench utility-surface utility-surface--settings" variant="settings">
      <WorkbenchMasthead
        eyebrow={t("pages.settings.title")}
        title={t("settings.appearance.title")}
        description={t("pages.settings.description")}
      />
      <div className="settings-operations-grid">
        <div className="settings-operations-grid__preferences">
          <section className="feature-shell settings-section-card">
        <div className="feature-header utility-surface__header">
          <span className="page-header__eyebrow">{t("settings.appearance.eyebrow")}</span>
          <h3>{t("settings.appearance.title")}</h3>
          <p>{t("settings.appearance.description")}</p>
        </div>
        <div className="settings-segmented-control" role="group" aria-label={t("settings.appearance.ariaLabel")}>
          {themeOptions.map((option) => (
            <button
              key={option.value}
              className={`secondary-button settings-segmented-button${
                theme === option.value ? " settings-segmented-button--selected" : ""
              }`}
              type="button"
              onClick={() => setTheme(option.value)}
              aria-pressed={theme === option.value}
            >
              {option.label}
            </button>
          ))}
        </div>
          </section>
          <section className="feature-shell settings-section-card">
        <div className="feature-header utility-surface__header">
          <span className="page-header__eyebrow">{t("settings.locale.eyebrow")}</span>
          <h3>{t("settings.locale.title")}</h3>
          <p>{t("settings.locale.description")}</p>
        </div>
        <div className="settings-segmented-control settings-locale-switch" role="group" aria-label={t("settings.locale.ariaLabel")}>
          {localeOptions.map((option) => (
            <button
              key={option.value}
              className={`secondary-button settings-segmented-button settings-locale-button${
                locale === option.value ? " settings-segmented-button--selected settings-locale-button--selected" : ""
              }`}
              type="button"
              onClick={() => setLocale(option.value)}
              aria-pressed={locale === option.value}
            >
              {option.label}
            </button>
          ))}
        </div>
          </section>

          {/* About Section */}
          <SectionCard title={t("settings.about.title")}>
            <div className="feature-header utility-surface__header">
              <span className="page-header__eyebrow">{t("settings.about.eyebrow")}</span>
              <p>{t("settings.about.description")}</p>
            </div>
            {systemQuery.isLoading || runtimeQuery.isLoading ? (
              <p className="settings-loading">{t("settings.about.loading")}</p>
            ) : (
              <div className="kv-list">
                <KeyValueRow label={t("settings.about.appName")} value="Workbench Beta" />
                <KeyValueRow label={t("settings.about.version")} value="v0.2.0" />
                <KeyValueRow
                  label={t("settings.about.databasePath")}
                  value={runtimeQuery.data?.database_path ?? "—"}
                  mono
                />
                <KeyValueRow
                  label={t("settings.about.dataDirectory")}
                  value={runtimeQuery.data?.data_dir ?? "—"}
                  mono
                />
              </div>
            )}
          </SectionCard>

          {/* Cache Management Section */}
          <SectionCard title={t("settings.cacheManagement.title")}>
            <div className="feature-header utility-surface__header">
              <span className="page-header__eyebrow">{t("settings.cacheManagement.eyebrow")}</span>
              <p>{t("settings.cacheManagement.description")}</p>
            </div>
            {cacheClearResult ? (
              <p className="settings-success-message">{cacheClearResult}</p>
            ) : null}
            <button
              className="secondary-button"
              type="button"
              onClick={() => setClearCacheConfirm(true)}
              disabled={clearCacheMutation.isPending}
            >
              {clearCacheMutation.isPending
                ? "Clearing..."
                : t("settings.cacheManagement.clearThumbnails")}
            </button>
          </SectionCard>
        </div>
        <div className="settings-operations-grid__system">
          <SystemStatusFeature
            eyebrow={t("settings.systemStatus.eyebrow")}
            title={t("settings.systemStatus.title")}
            description={t("settings.systemStatus.description")}
          />
          <section className="feature-shell settings-section-card">
            <div className="feature-header utility-surface__header">
              <span className="page-header__eyebrow">{t("settings.sourcesRedirect.eyebrow")}</span>
              <h3>{t("settings.sourcesRedirect.title")}</h3>
              <p>{t("settings.sourcesRedirect.description")}</p>
            </div>
            <Link to="/library?tab=sources" className="action-button action-button--primary">
              {t("settings.sourcesRedirect.action")}
            </Link>
          </section>
        </div>
      </div>

      <ConfirmDialog
        open={clearCacheConfirm}
        title={t("settings.cacheManagement.clearThumbnailsConfirmTitle")}
        message={t("settings.cacheManagement.clearThumbnailsConfirmMessage")}
        confirmLabel={t("settings.cacheManagement.clearThumbnails")}
        onConfirm={() => clearCacheMutation.mutate()}
        onCancel={() => setClearCacheConfirm(false)}
      />
    </WorkbenchPage>
  );
}

export default SettingsPage;
