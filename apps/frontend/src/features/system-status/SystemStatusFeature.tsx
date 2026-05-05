import { useQuery } from "@tanstack/react-query";

import { t } from "../../shared/text";
import { getSystemStatus } from "../../services/api/systemApi";
import { queryKeys } from "../../services/query/queryKeys";


type SystemStatusFeatureProps = {
  eyebrow?: string;
  title?: string;
  description?: string;
};


export function SystemStatusFeature({
  eyebrow = t("settings.systemStatus.defaultEyebrow"),
  title = t("settings.systemStatus.defaultTitle"),
  description = t("settings.systemStatus.defaultDescription"),
}: SystemStatusFeatureProps) {
  const systemStatusQuery = useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: getSystemStatus,
  });

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">{eyebrow}</span>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>

      {systemStatusQuery.isLoading ? <p>{t("settings.systemStatus.loading")}</p> : null}

      {systemStatusQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("settings.systemStatus.unavailableTitle")}</strong>
          <p>{systemStatusQuery.error.message}</p>
        </div>
      ) : null}

      {systemStatusQuery.data ? (
        <dl className="system-status-grid">
          <div className="system-status-card">
            <dt>{t("settings.systemStatus.cards.app")}</dt>
            <dd>{systemStatusQuery.data.app}</dd>
          </div>
          <div className="system-status-card">
            <dt>{t("settings.systemStatus.cards.database")}</dt>
            <dd>{systemStatusQuery.data.database}</dd>
          </div>
          <div className="system-status-card">
            <dt>{t("settings.systemStatus.cards.sources")}</dt>
            <dd>{systemStatusQuery.data.sources_count}</dd>
          </div>
          <div className="system-status-card">
            <dt>{t("settings.systemStatus.cards.indexedFiles")}</dt>
            <dd>{systemStatusQuery.data.files_count}</dd>
          </div>
          <div className="system-status-card">
            <dt>{t("settings.systemStatus.cards.tasks")}</dt>
            <dd>{systemStatusQuery.data.tasks_count}</dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}
