import { useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { hasDesktopWindowControlsBridge } from "../../services/desktop/windowControls";
import { useUIStore } from "../providers/uiStore";
import { AppSidebar } from "./AppSidebar";
import { DesktopTitleBar } from "./DesktopTitleBar";
import { AppTopBar } from "./AppTopBar";
import { RightPanelContainer } from "./RightPanelContainer";


export function AppShell() {
  const location = useLocation();
  const isDetailsPanelOpen = useUIStore((state) => state.isDetailsPanelOpen);
  const isSidebarCollapsed = useUIStore((state) => state.isSidebarCollapsed);
  const isDesktopShell = hasDesktopWindowControlsBridge();
  const pageContentRef = useRef<HTMLDivElement | null>(null);
  const [showTopFade, setShowTopFade] = useState(false);
  const [showBottomFade, setShowBottomFade] = useState(false);

  useEffect(() => {
    const element = pageContentRef.current;
    if (!element) {
      setShowTopFade(false);
      setShowBottomFade(false);
      return;
    }

    const updateFadeState = () => {
      const { clientHeight, scrollHeight, scrollTop } = element;
      const isScrollable = scrollHeight > clientHeight + 1;

      if (!isScrollable) {
        setShowTopFade(false);
        setShowBottomFade(false);
        return;
      }

      setShowTopFade(scrollTop > 1);
      setShowBottomFade(scrollHeight - clientHeight - scrollTop > 1);
    };

    updateFadeState();

    element.addEventListener("scroll", updateFadeState, { passive: true });

    const resizeObserver = new ResizeObserver(() => {
      updateFadeState();
    });
    resizeObserver.observe(element);

    const contentElement = element.firstElementChild;
    if (contentElement instanceof HTMLElement) {
      resizeObserver.observe(contentElement);
    }

    return () => {
      element.removeEventListener("scroll", updateFadeState);
      resizeObserver.disconnect();
    };
  }, [location.pathname, isDetailsPanelOpen]);

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
          <main
            className="page-content-shell"
            data-show-top-fade={showTopFade ? "true" : "false"}
            data-show-bottom-fade={showBottomFade ? "true" : "false"}
          >
            <div className="page-content" ref={pageContentRef}>
              <Outlet />
            </div>
            <div className="page-content-fade page-content-fade--top" aria-hidden="true" />
            <div className="page-content-fade page-content-fade--bottom" aria-hidden="true" />
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
