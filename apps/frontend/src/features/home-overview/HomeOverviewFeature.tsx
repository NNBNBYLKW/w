import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import type { ComponentType, SVGProps } from "react";

import { useUIStore } from "../../app/providers/uiStore";
import SevenZipIcon from "../../assets/icons/navigation/7Z.svg?react";
import ExcelIcon from "../../assets/icons/navigation/Excel.svg?react";
import MarkdownIcon from "../../assets/icons/navigation/MD.svg?react";
import Mp3Icon from "../../assets/icons/navigation/mp3.svg?react";
import M4aIcon from "../../assets/icons/navigation/m4a.svg?react";
import PowerPointIcon from "../../assets/icons/navigation/PowerPoint.svg?react";
import RarIcon from "../../assets/icons/navigation/RAR.svg?react";
import TextIcon from "../../assets/icons/navigation/TXT.svg?react";
import WavIcon from "../../assets/icons/navigation/wav.svg?react";
import WordIcon from "../../assets/icons/navigation/Word.svg?react";
import ZipIcon from "../../assets/icons/navigation/zip.svg?react";
import { t } from "../../shared/text";
import { LoadingState, MetricStrip, WorkbenchMasthead, WorkbenchPage, WorkbenchResultFrame } from "../../shared/ui/components";
import { SidebarIcon, type NavigationIconName } from "../../shared/ui/icons";
import type { BookListItemVM } from "../../entities/book/types";
import type { GameListItemVM } from "../../entities/game/types";
import type { MediaListItemVM } from "../../entities/media/types";
import type { RecentListItemVM } from "../../entities/recent/types";
import type { SoftwareListItemVM } from "../../entities/software/types";
import { listBooks } from "../../services/api/booksApi";
import { listGames } from "../../services/api/gamesApi";
import { listMediaLibrary } from "../../services/api/mediaLibraryApi";
import { listRecentImports } from "../../services/api/recentApi";
import { listSoftware } from "../../services/api/softwareApi";
import { queryKeys } from "../../services/query/queryKeys";
import { SystemStatusFeature } from "../system-status/SystemStatusFeature";

function RecentActivitySection() {
  const params = { range: "7d", page: 1, page_size: 5, sort_order: "desc" } as const;
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.recent(params),
    queryFn: () => listRecentImports(params),
    refetchOnWindowFocus: false,
  });
  if (isLoading || !data || data.items.length === 0) return null;
  return (
    <div className="home-recent-activity">
      <span className="page-header__eyebrow">Recent Activity</span>
      <div className="home-recent-activity__list">
        {data.items.slice(0, 5).map((item: RecentListItemVM) => (
          <div className="home-recent-activity__row" key={item.id} title={item.path}>
            <span>{item.name}</span>
            <time>{item.discovered_at?.replace("T", " ").slice(0, 19)}</time>
          </div>
        ))}
      </div>
    </div>
  );
}


const HOME_MODULE_PAGE_SIZE = 8;

type HomeRowIcon = ComponentType<SVGProps<SVGSVGElement>>;

type HomeDashboardItem = {
  id: number;
  title: string;
  path: string;
  modifiedAt: string;
  sizeBytes: number | null;
  format: string;
  icon?: HomeRowIcon;
  mark: string;
  tone: "documents" | "software" | "media" | "games";
};

type HomeDashboardModuleProps = {
  emptyLabel: string;
  error: Error | null;
  icon: NavigationIconName;
  isLoading: boolean;
  items: HomeDashboardItem[];
  title: string;
  viewAllTo: string;
};

function formatTimestamp(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? t("common.states.unavailable") : date.toLocaleString();
}

function formatBytes(value: number | null): string {
  if (value === null) {
    return t("common.states.sizeUnavailable");
  }

  const units = ["bytes", "KB", "MB", "GB", "TB"];
  let size = value;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  if (unitIndex === 0) {
    return `${value.toLocaleString()} bytes`;
  }

  const rounded = size >= 10 ? Math.round(size) : Math.round(size * 10) / 10;
  return `${rounded.toLocaleString()} ${units[unitIndex]}`;
}

function formatHomeMetadata(item: HomeDashboardItem): string {
  return [item.format, formatTimestamp(item.modifiedAt), formatBytes(item.sizeBytes)].filter(Boolean).join(" · ");
}

function normalizeFormatMark(value: string | null | undefined, fallback: string): string {
  const normalized = (value ?? "").trim().replace(/^\./, "").toUpperCase();
  return (normalized || fallback).slice(0, 5);
}

function getExtensionFromPath(path: string): string {
  const fileName = path.split(/[\\/]/).pop() ?? path;
  const lastDot = fileName.lastIndexOf(".");
  return lastDot >= 0 ? fileName.slice(lastDot + 1).toLowerCase() : "";
}

function getHomeRowIcon(format: string): HomeRowIcon | undefined {
  switch (format.toLowerCase()) {
    case "doc":
    case "docx":
    case "rtf":
    case "odt":
      return WordIcon;
    case "xls":
    case "xlsx":
    case "csv":
    case "ods":
      return ExcelIcon;
    case "ppt":
    case "pptx":
    case "odp":
      return PowerPointIcon;
    case "md":
      return MarkdownIcon;
    case "txt":
      return TextIcon;
    case "zip":
      return ZipIcon;
    case "7z":
      return SevenZipIcon;
    case "rar":
      return RarIcon;
    case "mp3":
      return Mp3Icon;
    case "m4a":
      return M4aIcon;
    case "wav":
      return WavIcon;
    default:
      return undefined;
  }
}

function normalizeFormat(value: string | null | undefined, path: string, fallback: string): string {
  const normalized = (value ?? "").trim().replace(/^\./, "").toLowerCase();
  return normalized || getExtensionFromPath(path) || fallback.toLowerCase();
}

function getMediaMark(fileType: string): string {
  if (fileType === "image") {
    return t("features.media.types.imageShort");
  }
  if (fileType === "video") {
    return t("features.media.types.videoShort");
  }
  if (fileType === "audio") {
    return "AUD";
  }
  return normalizeFormatMark(fileType, "MED");
}

function mapBookItem(item: BookListItemVM): HomeDashboardItem {
  const format = normalizeFormat(item.book_format, item.path, "doc");
  return {
    id: item.id,
    title: item.display_title,
    path: item.path,
    modifiedAt: item.modified_at,
    sizeBytes: item.size_bytes,
    format: normalizeFormatMark(format, "DOC"),
    icon: getHomeRowIcon(format),
    mark: normalizeFormatMark(format, "DOC"),
    tone: "documents",
  };
}

function mapSoftwareItem(item: SoftwareListItemVM): HomeDashboardItem {
  const format = normalizeFormat(item.software_format, item.path, "app");
  return {
    id: item.id,
    title: item.display_title,
    path: item.path,
    modifiedAt: item.modified_at,
    sizeBytes: item.size_bytes,
    format: normalizeFormatMark(format, "APP"),
    icon: getHomeRowIcon(format),
    mark: normalizeFormatMark(format, "APP"),
    tone: "software",
  };
}

function mapMediaItem(item: MediaListItemVM): HomeDashboardItem {
  const format = normalizeFormat(null, item.path, item.file_type);
  return {
    id: item.id,
    title: item.name,
    path: item.path,
    modifiedAt: item.modified_at,
    sizeBytes: item.size_bytes,
    format: normalizeFormatMark(format, "MED"),
    icon: getHomeRowIcon(format),
    mark: getMediaMark(item.file_type),
    tone: "media",
  };
}

function mapGameItem(item: GameListItemVM): HomeDashboardItem {
  const format = normalizeFormat(item.game_format, item.path, "game");
  return {
    id: item.id,
    title: item.display_title,
    path: item.path,
    modifiedAt: item.modified_at,
    sizeBytes: item.size_bytes,
    format: normalizeFormatMark(format, "GAME"),
    icon: getHomeRowIcon(format),
    mark: normalizeFormatMark(format, "GAME"),
    tone: "games",
  };
}

function HomeDashboardModule({
  emptyLabel,
  error,
  icon,
  isLoading,
  items,
  title,
  viewAllTo,
}: HomeDashboardModuleProps) {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);

  return (
    <section className="home-dashboard-card">
      <div className="home-dashboard-card__header">
        <div className="home-dashboard-card__title">
          <span className="home-dashboard-card__icon" aria-hidden="true">
            <SidebarIcon name={icon} />
          </span>
          <h3>{title}</h3>
        </div>
        <Link className="secondary-button home-dashboard-card__link" to={viewAllTo}>
          {t("features.homeOverview.dashboard.viewAll")}
        </Link>
      </div>

      {isLoading ? <LoadingState /> : null}

      {error ? (
        <div className="home-dashboard-card__state home-dashboard-card__state--error">
          <strong>{t("features.homeOverview.dashboard.unableToLoad")}</strong>
          <p>{error.message}</p>
        </div>
      ) : null}

      {!isLoading && !error && items.length === 0 ? (
        <div className="home-dashboard-card__state">{emptyLabel}</div>
      ) : null}

      {!isLoading && !error && items.length > 0 ? (
        <div className="home-dashboard-list">
          {items.slice(0, HOME_MODULE_PAGE_SIZE).map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.id}
                className={`home-dashboard-row${
                  selectedItemId === String(item.id) ? " home-dashboard-row--selected" : ""
                }`}
                type="button"
                onClick={() => selectItem(String(item.id))}
              >
                <span className={`home-dashboard-row__mark home-dashboard-row__mark--${item.tone}`} aria-hidden="true">
                  {Icon ? <Icon className="home-dashboard-row__icon" /> : item.mark}
                </span>
                <span className="home-dashboard-row__copy">
                  <strong title={item.title}>{item.title}</strong>
                  <span title={formatHomeMetadata(item)}>{formatHomeMetadata(item)}</span>
                </span>
              </button>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

export function HomeOverviewFeature() {
  const booksQueryParams = {
    page: 1,
    page_size: HOME_MODULE_PAGE_SIZE,
    sort_by: "modified_at" as const,
    sort_order: "desc" as const,
  };
  const softwareQueryParams = {
    page: 1,
    page_size: HOME_MODULE_PAGE_SIZE,
    sort_by: "modified_at" as const,
    sort_order: "desc" as const,
  };
  const mediaQueryParams = {
    view_scope: "all" as const,
    page: 1,
    page_size: HOME_MODULE_PAGE_SIZE,
    sort_by: "modified_at" as const,
    sort_order: "desc" as const,
  };
  const gamesQueryParams = {
    page: 1,
    page_size: HOME_MODULE_PAGE_SIZE,
    sort_by: "modified_at" as const,
    sort_order: "desc" as const,
  };

  const booksQuery = useQuery({
    queryKey: queryKeys.booksList(booksQueryParams),
    queryFn: () => listBooks(booksQueryParams),
  });
  const softwareQuery = useQuery({
    queryKey: queryKeys.softwareList(softwareQueryParams),
    queryFn: () => listSoftware(softwareQueryParams),
  });
  const mediaQuery = useQuery({
    queryKey: queryKeys.mediaLibrary(mediaQueryParams),
    queryFn: () => listMediaLibrary(mediaQueryParams),
  });
  const gamesQuery = useQuery({
    queryKey: queryKeys.gamesList(gamesQueryParams),
    queryFn: () => listGames(gamesQueryParams),
  });
  const moduleStats = [
    {
      label: t("features.homeOverview.dashboard.modules.documents.title"),
      value: booksQuery.data?.total ?? 0,
      tone: "info" as const,
    },
    {
      label: t("features.homeOverview.dashboard.modules.media.title"),
      value: mediaQuery.data?.total ?? 0,
      tone: "primary" as const,
    },
    {
      label: t("features.homeOverview.dashboard.modules.software.title"),
      value: softwareQuery.data?.total ?? 0,
      tone: "success" as const,
    },
    {
      label: t("features.homeOverview.dashboard.modules.games.title"),
      value: gamesQuery.data?.total ?? 0,
      tone: "warning" as const,
    },
  ];

  return (
    <WorkbenchPage className="home-overview" variant="home">
      <WorkbenchMasthead
        eyebrow={t("features.homeOverview.launch.eyebrow")}
        title={t("features.homeOverview.launch.title")}
        description={t("features.homeOverview.launch.description")}
        actions={
          <>
            <Link className="primary-button" to="/search">
              {t("features.homeOverview.launch.primaryAction")}
            </Link>
            <Link className="secondary-button" to="/library">
              {t("features.homeOverview.launch.secondaryAction")}
            </Link>
          </>
        }
      >
        <MetricStrip className="home-launch-metrics" items={moduleStats} />
      </WorkbenchMasthead>

      <div className="home-launch-grid">
        <section className="home-workflow-panel" aria-label={t("features.homeOverview.workflow.ariaLabel")}>
          <div className="home-workflow-panel__header">
            <span className="workbench-eyebrow">{t("features.homeOverview.workflow.eyebrow")}</span>
            <h4>{t("features.homeOverview.workflow.title")}</h4>
          </div>
          <div className="home-workflow-lane">
            {[
              {
                to: "/search",
                icon: "search" as const,
                titleKey: "features.homeOverview.workflow.steps.find.title" as const,
                descriptionKey: "features.homeOverview.workflow.steps.find.description" as const,
              },
              {
                to: "/library",
                icon: "files" as const,
                titleKey: "features.homeOverview.workflow.steps.inspect.title" as const,
                descriptionKey: "features.homeOverview.workflow.steps.inspect.description" as const,
              },
              {
                to: "/tags",
                icon: "tags" as const,
                titleKey: "features.homeOverview.workflow.steps.tag.title" as const,
                descriptionKey: "features.homeOverview.workflow.steps.tag.description" as const,
              },
              {
                to: "/browse-v2?domain=media",
                icon: "media" as const,
                titleKey: "features.homeOverview.workflow.steps.browse.title" as const,
                descriptionKey: "features.homeOverview.workflow.steps.browse.description" as const,
              },
            ].map((step, index) => (
              <Link className="home-workflow-step" key={step.to} to={step.to}>
                <span className="home-workflow-step__index">{String(index + 1).padStart(2, "0")}</span>
                <span className="home-workflow-step__icon" aria-hidden="true">
                  <SidebarIcon name={step.icon} />
                </span>
                <span className="home-workflow-step__copy">
                  <strong>{t(step.titleKey)}</strong>
                  <span>{t(step.descriptionKey)}</span>
                </span>
              </Link>
            ))}
          </div>
        </section>

        <div className="home-launch-grid__status">
          <SystemStatusFeature
            eyebrow={t("features.homeOverview.systemOverviewEyebrow")}
            title={t("settings.systemStatus.title")}
            description={t("features.homeOverview.systemOverviewDescription")}
            variant="compact"
          />
        </div>
      </div>

      <RecentActivitySection />

      <WorkbenchResultFrame
        className="home-module-frame"
        title={t("features.homeOverview.dashboard.title")}
        meta={t("features.homeOverview.dashboard.description")}
      >
        <div className="home-dashboard-grid">
          <HomeDashboardModule
            emptyLabel={t("features.homeOverview.dashboard.modules.documents.empty")}
            error={booksQuery.error instanceof Error ? booksQuery.error : null}
            icon="books"
            isLoading={booksQuery.isLoading}
            items={(booksQuery.data?.items ?? []).map(mapBookItem)}
            title={t("features.homeOverview.dashboard.modules.documents.title")}
            viewAllTo="/browse-v2?domain=documents"
          />
          <HomeDashboardModule
            emptyLabel={t("features.homeOverview.dashboard.modules.software.empty")}
            error={softwareQuery.error instanceof Error ? softwareQuery.error : null}
            icon="software"
            isLoading={softwareQuery.isLoading}
            items={(softwareQuery.data?.items ?? []).map(mapSoftwareItem)}
            title={t("features.homeOverview.dashboard.modules.software.title")}
            viewAllTo="/browse-v2?domain=apps&category=software"
          />
          <HomeDashboardModule
            emptyLabel={t("features.homeOverview.dashboard.modules.media.empty")}
            error={mediaQuery.error instanceof Error ? mediaQuery.error : null}
            icon="media"
            isLoading={mediaQuery.isLoading}
            items={(mediaQuery.data?.items ?? []).map(mapMediaItem)}
            title={t("features.homeOverview.dashboard.modules.media.title")}
            viewAllTo="/browse-v2?domain=media"
          />
          <HomeDashboardModule
            emptyLabel={t("features.homeOverview.dashboard.modules.games.empty")}
            error={gamesQuery.error instanceof Error ? gamesQuery.error : null}
            icon="games"
            isLoading={gamesQuery.isLoading}
            items={(gamesQuery.data?.items ?? []).map(mapGameItem)}
            title={t("features.homeOverview.dashboard.modules.games.title")}
            viewAllTo="/browse-v2?domain=apps&category=game"
          />
        </div>
      </WorkbenchResultFrame>
    </WorkbenchPage>
  );
}
