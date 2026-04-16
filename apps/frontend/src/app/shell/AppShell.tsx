import { Outlet } from "react-router-dom";

import { AppSidebar } from "./AppSidebar";
import { AppTopBar } from "./AppTopBar";
import { RightPanelContainer } from "./RightPanelContainer";


export function AppShell() {
  return (
    <div className="app-shell">
      <AppSidebar />
      <div className="app-shell__main">
        <AppTopBar />
        <div className="app-shell__content">
          <main className="page-content">
            <Outlet />
          </main>
          <RightPanelContainer />
        </div>
      </div>
    </div>
  );
}
