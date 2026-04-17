import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { listRecentImports } from "../../services/api/recentApi";
import { getSources } from "../../services/api/sourcesApi";
import { queryKeys } from "../../services/query/queryKeys";
import { SystemStatusFeature } from "../system-status/SystemStatusFeature";


const QUICK_LINKS = [
  { to: "/search", label: "Open Search" },
  { to: "/files", label: "Browse Files" },
  { to: "/library/media", label: "Open Media Library" },
  { to: "/recent", label: "Review Recent Imports" },
  { to: "/tags", label: "Find By Tag" },
  { to: "/settings", label: "Open Settings" },
];


function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString();
}


export function HomeOverviewFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);

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
        eyebrow="Workbench entry"
        title="System status"
        description="Use this page as a lightweight entry point for current runtime health and indexed-content coverage."
      />

      <div className="home-overview-grid">
        <section className="feature-shell">
          <div className="feature-header">
            <span className="page-header__eyebrow">Recent imports preview</span>
            <h3>Recently indexed files</h3>
            <p>Preview the latest indexed files from the last 7 days before jumping into the full recent-imports page.</p>
          </div>

          {recentQuery.isLoading ? <p>Loading recent imports preview...</p> : null}

          {recentQuery.error instanceof Error ? (
            <div className="status-block page-card">
              <strong>Recent imports preview unavailable</strong>
              <p>{recentQuery.error.message}</p>
            </div>
          ) : null}

          {recentQuery.data && recentQuery.data.items.length === 0 ? (
            <div className="future-frame">No active indexed files were discovered in the last 7 days yet.</div>
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
            <span className="page-header__eyebrow">Sources overview</span>
            <h3>Indexed source coverage</h3>
            <p>Review persisted source rows and jump into settings when you need to add or rescan a source.</p>
          </div>

          {sourcesQuery.isLoading ? <p>Loading sources overview...</p> : null}

          {sourcesQuery.error instanceof Error ? (
            <div className="status-block page-card">
              <strong>Sources overview unavailable</strong>
              <p>{sourcesQuery.error.message}</p>
            </div>
          ) : null}

          {sourcesQuery.data && sourcesQuery.data.length === 0 ? (
            <div className="future-frame">No persisted sources yet. Open Settings to add your first indexed source.</div>
          ) : null}

          {sourcesQuery.data && sourcesQuery.data.length > 0 ? (
            <div className="source-list">
              {sourcesQuery.data.slice(0, 5).map((source) => (
                <article className="source-row" key={source.id}>
                  <div className="source-row__meta">
                    <strong>{source.display_name ?? source.path}</strong>
                    <p className="source-row__path">{source.path}</p>
                    {source.last_scan_status === "failed" && source.last_scan_error_message ? (
                      <p className="source-row__path">Last scan failed: {source.last_scan_error_message}</p>
                    ) : null}
                  </div>
                  <div className="source-row__actions">
                    <span className="status-pill">{source.last_scan_status ?? "No scan yet"}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </section>

        <section className="feature-shell">
          <div className="feature-header">
            <span className="page-header__eyebrow">Quick links</span>
            <h3>Jump into a workbench flow</h3>
            <p>Open the existing search, browse, media, recent, tags, or settings flows without changing the shared shell.</p>
          </div>

          <div className="quick-links-grid">
            {QUICK_LINKS.map((link) => (
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
