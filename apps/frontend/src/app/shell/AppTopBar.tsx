import { useQuery } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";

import { SidebarIcon } from "../../shared/ui/icons";
import { t } from "../../shared/text";
import { useUIStore } from "../providers/uiStore";
import { getSystemStatus } from "../../services/api/systemApi";
import { queryKeys } from "../../services/query/queryKeys";


const pageTitleKeys: Record<string, Parameters<typeof t>[0]> = {
  "/home": "shell.topbar.pages.home",
  "/onboarding": "shell.topbar.pages.onboarding",
  "/search": "shell.topbar.pages.search",
  "/files": "shell.topbar.pages.files",
  "/books": "shell.topbar.pages.books",
  "/software": "shell.topbar.pages.software",
  "/library/media": "shell.topbar.pages.media",
  "/library/games": "shell.topbar.pages.games",
  "/recent": "shell.topbar.pages.recent",
  "/tags": "shell.topbar.pages.tags",
  "/collections": "shell.topbar.pages.collections",
  "/settings": "shell.topbar.pages.settings",
};


export function AppTopBar() {
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

  return (
    <header className="app-topbar">
      <div>
        <span className="app-topbar__eyebrow">{t("shell.topbar.eyebrow")}</span>
        <h2>{pageTitleKeys[location.pathname] ? t(pageTitleKeys[location.pathname]) : t("shell.topbar.fallbackTitle")}</h2>
      </div>
      <div className="app-topbar__actions">
        <div
          className={`app-topbar__connection-status${
            isBackendConnected ? " app-topbar__connection-status--connected" : ""
          }`}
          aria-label={connectionLabel}
          title={connectionLabel}
        >
          <span className="app-topbar__connection-icon" aria-hidden="true">
            <SidebarIcon name="connection" />
          </span>
        </div>
        <button
          className="ghost-button app-shell-icon-button app-topbar__details-toggle"
          type="button"
          aria-label={detailsToggleLabel}
          title={detailsToggleLabel}
          onClick={() => setDetailsPanelOpen(!isDetailsPanelOpen)}
        >
          <span className="app-shell-icon-button__icon app-topbar__details-toggle-icon" aria-hidden="true">
            <SidebarIcon name={detailsToggleIcon} />
          </span>
        </button>
      </div>
    </header>
  );
}
