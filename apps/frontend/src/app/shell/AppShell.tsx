import { Outlet } from "react-router-dom";

import { hasDesktopWindowControlsBridge } from "../../services/desktop/windowControls";
import { useUIStore } from "../providers/uiStore";
import { AppSidebar } from "./AppSidebar";
import { DesktopTitleBar } from "./DesktopTitleBar";
import { AppTopBar } from "./AppTopBar";
import { RightPanelContainer } from "./RightPanelContainer";


export function AppShell() {
  const isDetailsPanelOpen = useUIStore((state) => state.isDetailsPanelOpen);
  const isSidebarCollapsed = useUIStore((state) => state.isSidebarCollapsed);
  const isDesktopShell = hasDesktopWindowControlsBridge();

  const shell = (
    <div className={`app-shell${isSidebarCollapsed ? " app-shell--sidebar-collapsed" : ""}`}>
      <AppSidebar />
      <div className="app-shell__main">
        <AppTopBar />
        <div
          className={`app-shell__content${
            isDetailsPanelOpen ? " app-shell__content--details-open" : " app-shell__content--details-hidden"
          }`}
        >
          <main className="page-content">
            <Outlet />
          </main>
          <RightPanelContainer />
        </div>
      </div>
    </div>
  );

  if (!isDesktopShell) {
    return shell;
  }

  return (
    <div className="app-frame">
      <DesktopTitleBar />
      {shell}
    </div>
  );
}
