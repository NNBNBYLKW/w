import { useQuery } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";

import { useUIStore } from "../providers/uiStore";
import { getSystemStatus } from "../../services/api/systemApi";
import { queryKeys } from "../../services/query/queryKeys";


const pageTitles: Record<string, string> = {
  "/": "Home",
  "/onboarding": "Onboarding",
  "/search": "Search",
  "/files": "Files",
  "/library/media": "Media Library",
  "/recent": "Recent Imports",
  "/tags": "Tags",
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

  return (
    <header className="app-topbar">
      <div>
        <span className="app-topbar__eyebrow">Windows Local Asset Workbench</span>
        <h2>{pageTitles[location.pathname] ?? "Workbench"}</h2>
      </div>
      <div className="app-topbar__actions">
        <div className="status-pill">
          Backend: {data?.app === "ok" && data?.database === "ok" ? "Connected" : "Checking"}
        </div>
        <button
          className="ghost-button"
          type="button"
          onClick={() => setDetailsPanelOpen(!isDetailsPanelOpen)}
        >
          {isDetailsPanelOpen ? "Hide details" : "Show details"}
        </button>
      </div>
    </header>
  );
}
