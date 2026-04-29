import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import { listRecentImports } from "../../services/api/recentApi";
import { getSources } from "../../services/api/sourcesApi";
import { queryKeys } from "../../services/query/queryKeys";
import { SystemStatusFeature } from "../system-status/SystemStatusFeature";


function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString();
}


function formatScanStatusLabel(value: string | null): string {
  if (value === "running") {
    return t("settings.sourceManagement.scanStatus.running");
  }
  if (value === "failed") {
    return t("settings.sourceManagement.scanStatus.failed");
  }
  if (value === "succeeded") {
    return t("settings.sourceManagement.scanStatus.succeeded");
  }
  return t("settings.sourceManagement.scanStatus.none");
}


export function HomeOverviewFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const quickLinks = [
    { to: "/search", label: t("features.homeOverview.quickLinks.items.search") },
    { to: "/files", label: t("features.homeOverview.quickLinks.items.files") },
    { to: "/library/media", label: t("features.homeOverview.quickLinks.items.media") },
    { to: "/recent", label: t("features.homeOverview.quickLinks.items.recent") },
    { to: "/tags", label: t("features.homeOverview.quickLinks.items.tags") },
    { to: "/collections", label: t("features.homeOverview.quickLinks.items.collections") },
    { to: "/settings", label: t("features.homeOverview.quickLinks.items.settings") },
  ];

  const recentQueryParams = {
    range: "7d" as const,
    page: 1,
    page_size: 10,
    sort_order: "desc" as const,
  };

  const recentQuery = useQuery({
    queryKey: queryKeys.recent(recentQueryParams),
    queryFn: () => listRecentImports(recentQueryParams),
  });

  const sourcesQuery = useQuery({
    queryKey: queryKeys.sources,
    queryFn: getSources,
  });

  return (
    <section className="home-overview">
      <SystemStatusFeature
        eyebrow={t("features.homeOverview.systemOverviewEyebrow")}
        title={t("settings.systemStatus.title")}
        description={t("features.homeOverview.systemOverviewDescription")}
      />

      <div className="home-overview-grid">
        <section className="feature-shell">
          <div className="feature-header">
            <span className="page-header__eyebrow">{t("features.homeOverview.recentPreview.eyebrow")}</span>
            <h3>{t("features.homeOverview.recentPreview.title")}</h3>
            <p>{t("features.homeOverview.recentPreview.description")}</p>
          </div>

          {recentQuery.isLoading ? <p>{t("features.homeOverview.recentPreview.loading")}</p> : null}

          {recentQuery.error instanceof Error ? (
            <div className="status-block page-card">
              <strong>{t("features.homeOverview.recentPreview.unavailableTitle")}</strong>
              <p>{recentQuery.error.message}</p>
            </div>
          ) : null}

          {recentQuery.data && recentQuery.data.items.length === 0 ? (
            <div className="future-frame">{t("features.homeOverview.recentPreview.empty")}</div>
          ) : null}

          {recentQuery.data && recentQuery.data.items.length > 0 ? (
            <div className="recent-list">
              {recentQuery.data.items.map((item) => (
                <button
                  key={item.id}
                  className={`recent-row${selectedItemId === String(item.id) ? " recent-row--selected" : ""}`}
                  type="button"
                  onClick={() => selectItem(String(item.id))}
                >
                  <div className="recent-row__meta">
                    <strong>{item.name}</strong>
                    <p>{item.path}</p>
                  </div>
                  <div className="recent-row__badges">
                    <span className="status-pill">{item.file_type}</span>
                    <span className="status-pill">{formatTimestamp(item.discovered_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          ) : null}
        </section>

        <section className="feature-shell">
          <div className="feature-header">
            <span className="page-header__eyebrow">{t("features.homeOverview.sourcesOverview.eyebrow")}</span>
            <h3>{t("features.homeOverview.sourcesOverview.title")}</h3>
            <p>{t("features.homeOverview.sourcesOverview.description")}</p>
          </div>

          {sourcesQuery.isLoading ? <p>{t("features.homeOverview.sourcesOverview.loading")}</p> : null}

          {sourcesQuery.error instanceof Error ? (
            <div className="status-block page-card">
              <strong>{t("features.homeOverview.sourcesOverview.unavailableTitle")}</strong>
              <p>{sourcesQuery.error.message}</p>
            </div>
          ) : null}

          {sourcesQuery.data && sourcesQuery.data.length === 0 ? (
            <div className="future-frame">{t("features.homeOverview.sourcesOverview.empty")}</div>
          ) : null}

          {sourcesQuery.data && sourcesQuery.data.length > 0 ? (
            <div className="source-list">
              {sourcesQuery.data.slice(0, 5).map((source) => (
                <article className="source-row" key={source.id}>
                  <div className="source-row__meta">
                    <strong>{source.display_name ?? source.path}</strong>
                    <p className="source-row__path">{source.path}</p>
                    {source.last_scan_status === "failed" && source.last_scan_error_message ? (
                      <p className="source-row__path">
                        {t("features.homeOverview.sourcesOverview.scanFailed", {
                          message: source.last_scan_error_message,
                        })}
                      </p>
                    ) : null}
                  </div>
                  <div className="source-row__actions">
                    <span className="status-pill">{formatScanStatusLabel(source.last_scan_status)}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </section>

        <section className="feature-shell">
          <div className="feature-header">
            <span className="page-header__eyebrow">{t("features.homeOverview.quickLinks.eyebrow")}</span>
            <h3>{t("features.homeOverview.quickLinks.title")}</h3>
            <p>{t("features.homeOverview.quickLinks.description")}</p>
          </div>

          <div className="quick-links-grid">
            {quickLinks.map((link) => (
              <Link key={link.to} className="quick-link-card" to={link.to}>
                {link.label}
              </Link>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
