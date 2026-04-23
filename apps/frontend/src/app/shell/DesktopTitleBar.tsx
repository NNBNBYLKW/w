import { useEffect, useState } from "react";

import { SidebarIcon } from "../../shared/ui/icons";
import {
  closeDesktopWindow,
  getDesktopWindowState,
  hasDesktopWindowControlsBridge,
  minimizeDesktopWindow,
  subscribeToDesktopWindowState,
  toggleDesktopWindowMaximize,
} from "../../services/desktop/windowControls";


export function DesktopTitleBar() {
  const [isMaximized, setIsMaximized] = useState(false);
  const isDesktopShell = hasDesktopWindowControlsBridge();

  useEffect(() => {
    if (!isDesktopShell) {
      return;
    }

    let isActive = true;

    void getDesktopWindowState().then((state) => {
      if (isActive) {
        setIsMaximized(state.isMaximized);
      }
    });

    const unsubscribe = subscribeToDesktopWindowState((state) => {
      setIsMaximized(state.isMaximized);
    });

    return () => {
      isActive = false;
      unsubscribe();
    };
  }, [isDesktopShell]);

  if (!isDesktopShell) {
    return null;
  }

  const maximizeIconName = isMaximized ? "maxmize2" : "maxmize1";
  const maximizeLabel = isMaximized ? "Restore window" : "Maximize window";

  return (
    <header className="desktop-titlebar">
      <div className="desktop-titlebar__brand" aria-label="Asset Workbench window title">
        <span className="desktop-titlebar__brand-icon" aria-hidden="true">
          <SidebarIcon name="software" />
        </span>
        <span className="desktop-titlebar__brand-title">Asset Workbench</span>
      </div>
      <div className="desktop-titlebar__controls">
        <button
          className="desktop-titlebar__button"
          type="button"
          aria-label="Minimize window"
          title="Minimize window"
          onClick={() => {
            void minimizeDesktopWindow();
          }}
        >
          <span className="desktop-titlebar__button-icon" aria-hidden="true">
            <SidebarIcon name="minimize" />
          </span>
        </button>
        <button
          className="desktop-titlebar__button"
          type="button"
          aria-label={maximizeLabel}
          title={maximizeLabel}
          onClick={() => {
            void toggleDesktopWindowMaximize().then((state) => {
              setIsMaximized(state.isMaximized);
            });
          }}
        >
          <span className="desktop-titlebar__button-icon" aria-hidden="true">
            <SidebarIcon name={maximizeIconName} />
          </span>
        </button>
        <button
          className="desktop-titlebar__button desktop-titlebar__button--close"
          type="button"
          aria-label="Close window"
          title="Close window"
          onClick={() => {
            void closeDesktopWindow();
          }}
        >
          <span className="desktop-titlebar__button-icon" aria-hidden="true">
            <SidebarIcon name="close" />
          </span>
        </button>
      </div>
    </header>
  );
}
