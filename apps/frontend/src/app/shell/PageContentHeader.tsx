import { useQuery } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";

import { getSystemStatus } from "../../services/api/systemApi";
import { queryKeys } from "../../services/query/queryKeys";
import { t } from "../../shared/text";
import { SidebarIcon } from "../../shared/ui/icons";
import { useUIStore } from "../providers/uiStore";


type PageHeaderCopy = {
  titleKey: Parameters<typeof t>[0];
  descriptionKey?: Parameters<typeof t>[0];
};

const pageHeaderCopy: Record<string, PageHeaderCopy> = {
  "/home": { titleKey: "pages.home.title", descriptionKey: "pages.home.description" },
  "/onboarding": { titleKey: "pages.onboarding.title", descriptionKey: "pages.onboarding.description" },
  "/search": { titleKey: "pages.search.title", descriptionKey: "pages.search.description" },
  "/files": { titleKey: "pages.files.title", descriptionKey: "pages.files.description" },
  "/books": { titleKey: "pages.books.title", descriptionKey: "pages.books.description" },
  "/software": { titleKey: "pages.software.title", descriptionKey: "pages.software.description" },
  "/library/media": { titleKey: "pages.media.title", descriptionKey: "pages.media.description" },
  "/library/games": { titleKey: "pages.games.title", descriptionKey: "pages.games.description" },
  "/recent": { titleKey: "pages.recent.title", descriptionKey: "pages.recent.description" },
  "/tags": { titleKey: "pages.tags.title", descriptionKey: "pages.tags.description" },
  "/collections": { titleKey: "pages.collections.title", descriptionKey: "pages.collections.description" },
  "/settings": { titleKey: "pages.settings.title", descriptionKey: "pages.settings.description" },
};


export function PageContentHeader() {
  const location = useLocation();
  const isDetailsPanelOpen = useUIStore((state) => state.isDetailsPanelOpen);
  const setDetailsPanelOpen = useUIStore((state) => state.setDetailsPanelOpen);
  const { data } = useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: getSystemStatus,
  });
  const isBackendConnected = data?.app === "ok" && data?.database === "ok";
  const detailsToggleLabel = isDetailsPanelOpen ? t("shell.topbar.details.hide") : t("shell.topbar.details.show");
  const detailsToggleIcon = isDetailsPanelOpen ? "sidebar1" : "sidebar2";
  const connectionLabel = isBackendConnected ? t("shell.topbar.backend.connected") : t("shell.topbar.backend.disconnected");
  const copy = pageHeaderCopy[location.pathname];
  const title = copy ? t(copy.titleKey) : t("shell.topbar.fallbackTitle");
  const description = copy?.descriptionKey ? t(copy.descriptionKey) : undefined;

  return (
    <header className="page-content-header">
      <div className="page-content-header__copy">
        <h2 className="page-content-header__title">{title}</h2>
        {description ? <p className="page-content-header__description">{description}</p> : null}
      </div>
      <div className="page-content-header__actions">
        <div
          className={`page-content-header__connection-status${
            isBackendConnected ? " page-content-header__connection-status--connected" : ""
          }`}
          aria-label={connectionLabel}
          title={connectionLabel}
        >
          <span className="page-content-header__connection-icon" aria-hidden="true">
            <SidebarIcon name="connection" />
          </span>
        </div>
        <button
          className="ghost-button app-shell-icon-button page-content-header__details-toggle"
          type="button"
          aria-label={detailsToggleLabel}
          title={detailsToggleLabel}
          onClick={() => setDetailsPanelOpen(!isDetailsPanelOpen)}
        >
          <span className="app-shell-icon-button__icon page-content-header__details-toggle-icon" aria-hidden="true">
            <SidebarIcon name={detailsToggleIcon} />
          </span>
        </button>
      </div>
    </header>
  );
}
