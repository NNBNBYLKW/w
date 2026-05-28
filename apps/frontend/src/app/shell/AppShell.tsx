import { useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { hasDesktopWindowControlsBridge } from "../../services/desktop/windowControls";
import { t, useLocale } from "../../shared/text";
import { useUIStore } from "../providers/uiStore";
import { AppSidebar } from "./AppSidebar";
import { DesktopTitleBar } from "./DesktopTitleBar";
import { PageContentHeader } from "./PageContentHeader";
import { RightPanelContainer } from "./RightPanelContainer";
import { ToastContainer } from "./ToastContainer";
import { useKeyboardShortcuts } from "../../shared/hooks/useKeyboardShortcuts";


export function AppShell() {
  useKeyboardShortcuts();
  const location = useLocation();
  const { locale } = useLocale();
  const isDetailsPanelOpen = useUIStore((state) => state.isDetailsPanelOpen);
  const isSidebarCollapsed = useUIStore((state) => state.isSidebarCollapsed);
  const isQuickPanelOpen = useUIStore((state) => state.isQuickPanelOpen);
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
  }, [location.pathname, isDetailsPanelOpen, locale]);

  const shell = (
    <div className={`app-shell app-shell--design-pen${isSidebarCollapsed ? " app-shell--sidebar-collapsed" : ""}${isQuickPanelOpen ? " app-shell--quick-panel-open" : ""}`}>
      <a className="skip-link" href="#workbench-main-content">
        {t("shell.skipToContent")}
      </a>
      <AppSidebar />
      {isQuickPanelOpen && (
        <div className="quick-access-panel">
          <h4>Recent Files</h4>
          <ul className="quick-access-panel__list">
            <li className="quick-access-panel__item">—</li>
          </ul>
          <h4 style={{ marginTop: 16 }}>Favorites</h4>
          <ul className="quick-access-panel__list">
            <li className="quick-access-panel__item">—</li>
          </ul>
        </div>
      )}
      <div className="app-shell__main">
        <div
          className={`app-shell__content${
            isDetailsPanelOpen ? " app-shell__content--details-open" : " app-shell__content--details-hidden"
          }`}
        >
          <main
            id="workbench-main-content"
            className="page-content-shell"
            data-show-top-fade={showTopFade ? "true" : "false"}
            data-show-bottom-fade={showBottomFade ? "true" : "false"}
            tabIndex={-1}
          >
            <PageContentHeader />
            <div className="page-content" ref={pageContentRef}>
              <Outlet />
            </div>
            <div className="page-content-fade page-content-fade--top" aria-hidden="true" />
            <div className="page-content-fade page-content-fade--bottom" aria-hidden="true" />
          </main>
          <RightPanelContainer />
        </div>
      </div>
      <ToastContainer />
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
