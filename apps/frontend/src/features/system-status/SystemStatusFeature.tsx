import { useQuery } from "@tanstack/react-query";

import { getSystemStatus } from "../../services/api/systemApi";
import { queryKeys } from "../../services/query/queryKeys";


type SystemStatusFeatureProps = {
  eyebrow?: string;
  title?: string;
  description?: string;
};


export function SystemStatusFeature({
  eyebrow = "System status",
  title = "Runtime and index status",
  description = "Review the current app, database, source, task, and file totals.",
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

      {systemStatusQuery.isLoading ? <p>Loading system status...</p> : null}

      {systemStatusQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>System status unavailable</strong>
          <p>{systemStatusQuery.error.message}</p>
        </div>
      ) : null}

      {systemStatusQuery.data ? (
        <dl className="system-status-grid">
          <div className="system-status-card">
            <dt>App</dt>
            <dd>{systemStatusQuery.data.app}</dd>
          </div>
          <div className="system-status-card">
            <dt>Database</dt>
            <dd>{systemStatusQuery.data.database}</dd>
          </div>
          <div className="system-status-card">
            <dt>Sources</dt>
            <dd>{systemStatusQuery.data.sources_count}</dd>
          </div>
          <div className="system-status-card">
            <dt>Indexed files</dt>
            <dd>{systemStatusQuery.data.files_count}</dd>
          </div>
          <div className="system-status-card">
            <dt>Tasks</dt>
            <dd>{systemStatusQuery.data.tasks_count}</dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}
