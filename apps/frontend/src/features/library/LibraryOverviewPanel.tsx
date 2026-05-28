import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { t } from "../../shared/text";
import { LoadingState } from "../../shared/ui/components/LoadingState";
import { queryKeys } from "../../services/query/queryKeys";
import { invalidateLibraryObjectSurfaces } from "../../services/query/invalidation";
import { getLibraryOverview, getOrganizeStats, scanLibraryObjects } from "../../services/api/libraryObjectsApi";
import { formatTimestamp } from "./shared/helpers";

async function getStorageSummary() {
  const base = (
    window as typeof window & { assetWorkbench?: { getBackendBaseUrl?: () => string } }
  ).assetWorkbench?.getBackendBaseUrl?.() ?? import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
  const res = await fetch(`${base}/library/storage-summary`);
  if (!res.ok) throw new Error("Failed to load storage summary");
  return res.json() as Promise<{ total_count: number; external_count: number; inbox_count: number; managed_count: number }>;
}

function StartHereCard({
  icon,
  title,
  description,
  action,
  to,
}: {
  icon: string;
  title: string;
  description: string;
  action: string;
  to: string;
}) {
  const navigate = useNavigate();
  return (
    <button
      className="library-start-card"
      type="button"
      onClick={() => navigate(to)}
    >
      <span className="library-start-card__icon" aria-hidden="true">{icon}</span>
      <div className="library-start-card__body">
        <strong className="library-start-card__title">{title}</strong>
        <p className="library-start-card__desc">{description}</p>
      </div>
      <span className="library-start-card__action">{action}</span>
    </button>
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
      await invalidateLibraryObjectSurfaces(queryClient);
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

function StorageSummarySection() {
  const q = useQuery({
    queryKey: ["storage-summary"],
    queryFn: getStorageSummary,
    refetchOnWindowFocus: false,
  });
  const d = q.data;
  return (
    <div className="library-overview-card">
      <span className="page-header__eyebrow">{t("features.library.storageSummary.eyebrow")}</span>
      {q.isLoading ? <LoadingState /> : null}
      {q.isError ? <p className="muted-text">{t("features.library.storageSummary.unavailable")}</p> : null}
      {d ? (
        <div className="library-stat-grid">
          <div className="library-stat-card">
            <span>{t("features.library.storageSummary.totalFiles")}</span>
            <strong>{d.total_count.toLocaleString()}</strong>
          </div>
          <div className="library-stat-card">
            <span>{t("features.library.storageSummary.external")}</span>
            <strong>{d.external_count.toLocaleString()}</strong>
          </div>
          <div className="library-stat-card">
            <span>{t("features.library.storageSummary.inbox")}</span>
            <strong>{d.inbox_count.toLocaleString()}</strong>
          </div>
          <div className="library-stat-card">
            <span>{t("features.library.storageSummary.managed")}</span>
            <strong>{d.managed_count.toLocaleString()}</strong>
          </div>
        </div>
      ) : null}
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
      <div className="library-start-here">
        <span className="page-header__eyebrow">{t("features.library.overview.startHereEyebrow")}</span>
        <h3>{t("features.library.overview.startHereTitle")}</h3>
        <div className="library-start-cards">
          <StartHereCard
            icon="📂"
            title={t("features.library.overview.scanCardTitle")}
            description={t("features.library.overview.scanCardDesc")}
            action={t("features.library.overview.scanCardAction")}
            to="/library?tab=sources"
          />
          <StartHereCard
            icon="📁"
            title={t("features.library.overview.rootsCardTitle")}
            description={t("features.library.overview.rootsCardDesc")}
            action={t("features.library.overview.rootsCardAction")}
            to="/library?tab=roots"
          />
          <StartHereCard
            icon="📥"
            title={t("features.library.overview.importCardTitle")}
            description={t("features.library.overview.importCardDesc")}
            action={t("features.library.overview.importCardAction")}
            to="/library?tab=inbox"
          />
          <StartHereCard
            icon="🔍"
            title={t("features.library.overview.browseCardTitle")}
            description={t("features.library.overview.browseCardDesc")}
            action={t("features.library.overview.browseCardAction")}
            to="/browse-v2"
          />
          <StartHereCard
            icon="📋"
            title={t("features.library.overview.plansCardTitle")}
            description={t("features.library.overview.plansCardDesc")}
            action={t("features.library.overview.plansCardAction")}
            to="/library?tab=plans"
          />
        </div>
      </div>

      <div className="library-overview-card">
        <span className="page-header__eyebrow">{t("features.library.overview.statsEyebrow")}</span>
        {overviewQuery.isLoading ? <LoadingState /> : null}
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

        <StorageSummarySection />
      </div>
      <ScanObjectsButton />
    </section>
  );
}
