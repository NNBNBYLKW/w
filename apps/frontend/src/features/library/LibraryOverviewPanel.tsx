import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { t } from "../../shared/text";
import { queryKeys } from "../../services/query/queryKeys";
import { getLibraryOverview, getOrganizeStats, scanLibraryObjects } from "../../services/api/libraryObjectsApi";
import { formatTimestamp } from "./shared/helpers";


function LibraryPlaceholderPanel({
  eyebrow,
  title,
  body,
  note,
}: {
  eyebrow: string;
  title: string;
  body: string;
  note: string;
}) {
  return (
    <section className="library-placeholder-panel">
      <div className="feature-header">
        <span className="page-header__eyebrow">{eyebrow}</span>
        <h3>{title}</h3>
        <p>{body}</p>
      </div>
      <div className="library-safety-note">
        <strong>{t("features.library.readOnlyBadge")}</strong>
        <p>{note}</p>
      </div>
    </section>
  );
}

function ScanObjectsButton() {
  const queryClient = useQueryClient();
  const [scanResult, setScanResult] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => scanLibraryObjects({ dry_run: false }),
    onSuccess: async (result) => {
      setScanResult(
        t("features.library.scan.result", {
          found: String(result.objects_found),
          review: String(result.needs_review),
        }),
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.libraryOverview }),
        queryClient.invalidateQueries({ queryKey: ["library-objects"] }),
      ]);
    },
  });

  return (
    <div className="library-scan-card">
      <div>
        <strong>{t("features.library.scan.title")}</strong>
        <p>{t("features.library.scan.description")}</p>
      </div>
      <button className="primary-button" type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
        {mutation.isPending ? t("features.library.scan.running") : t("features.library.scan.action")}
      </button>
      {scanResult ? <small>{scanResult}</small> : null}
      {mutation.isError ? <small className="danger-text">{(mutation.error as Error).message}</small> : null}
    </div>
  );
}

export function LibraryOverviewPanel() {
  const overviewQuery = useQuery({
    queryKey: queryKeys.libraryOverview,
    queryFn: getLibraryOverview,
  });
  const organizeStatsQuery = useQuery({
    queryKey: queryKeys.organizeStats,
    queryFn: getOrganizeStats,
  });
  const stats = overviewQuery.data;
  const organizeStats = organizeStatsQuery.data;
  return (
    <section className="library-overview-grid library-design-panel library-design-panel--overview">
      <LibraryPlaceholderPanel
        eyebrow={t("features.library.overview.eyebrow")}
        title={t("features.library.overview.title")}
        body={t("features.library.overview.description")}
        note={t("features.library.overview.safety")}
      />
      <div className="library-overview-card">
        <span className="page-header__eyebrow">{t("features.library.overview.statsEyebrow")}</span>
        {overviewQuery.isLoading ? <p>{t("common.states.loading")}</p> : null}
        {overviewQuery.isError ? <p>{t("features.library.scan.unableToLoad")}</p> : null}
        {stats ? (
          <div className="library-stat-grid">
            <div className="library-stat-card">
              <span>{t("features.library.stats.totalObjects")}</span>
              <strong>{stats.total_objects.toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.stats.needsReview")}</span>
              <strong>{stats.needs_review_count.toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.stats.unknownObjects")}</span>
              <strong>{stats.unknown_object_count.toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.stats.invalidYaml")}</span>
              <strong>{stats.asset_yaml_invalid_count.toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.organize.stats.pendingCandidates")}</span>
              <strong>{(organizeStats?.pending_candidates ?? 0).toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.organize.stats.draftPlans")}</span>
              <strong>{(organizeStats?.draft_plans ?? 0).toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.organize.stats.readyPlans")}</span>
              <strong>{(organizeStats?.ready_plans ?? 0).toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.organize.stats.blockedActions")}</span>
              <strong>{(organizeStats?.blocked_actions ?? 0).toLocaleString()}</strong>
            </div>
          </div>
        ) : null}
        <p className="library-muted-line">
          {t("features.library.stats.lastScan")}: {formatTimestamp(stats?.last_object_scan_at)}
        </p>
      </div>
      <ScanObjectsButton />
    </section>
  );
}
