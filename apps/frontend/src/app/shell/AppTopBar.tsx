import { useQuery } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";

import { SidebarIcon } from "../../shared/ui/icons";
import { useUIStore } from "../providers/uiStore";
import { getSystemStatus } from "../../services/api/systemApi";
import { queryKeys } from "../../services/query/queryKeys";


const pageTitles: Record<string, string> = {
  "/": "Home",
  "/onboarding": "Onboarding",
  "/search": "Search",
  "/files": "Files",
  "/books": "Books",
  "/software": "Software",
  "/library/media": "Media Library",
  "/library/games": "Games",
  "/recent": "Recent Imports",
  "/tags": "Tags",
  "/collections": "Collections",
  "/settings": "Settings",
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
  const detailsToggleLabel = isDetailsPanelOpen ? "Hide details" : "Show details";
  const detailsToggleIcon = isDetailsPanelOpen ? "sidebar1" : "sidebar2";
  const connectionLabel = isBackendConnected ? "Connected" : "Disconnected";

  return (
    <header className="app-topbar">
      <div>
        <span className="app-topbar__eyebrow">Windows Local Asset Workbench</span>
        <h2>{pageTitles[location.pathname] ?? "Workbench"}</h2>
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
