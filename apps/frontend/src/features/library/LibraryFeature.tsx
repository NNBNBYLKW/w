import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import { WorkbenchMasthead, WorkbenchPage } from "../../shared/ui/components";
import { LibraryInboxPanel } from "./LibraryInboxPanel";
import { LibraryOverviewPanel } from "./LibraryOverviewPanel";
import { LibraryRootsPanel } from "./LibraryRootsPanel";
import { LibraryPathBrowserPanel } from "./LibraryPathBrowserPanel";
import { LibraryObjectsPanel } from "./LibraryObjectsPanel";
import { LibraryPendingPanel } from "./LibraryPendingPanel";
import { LibraryPlansPanel } from "./LibraryPlansPanel";
import { SourceManagementFeature } from "../source-management/SourceManagementFeature";
import { formatSuggestionPayloadSummary, formatBytes, normalizeObjectTypeLabel } from "./shared/helpers";


type LibraryTab = "overview" | "sources" | "roots" | "path" | "pending" | "objects" | "plans" | "inbox";

const libraryTabs: Array<{ value: LibraryTab; labelKey: Parameters<typeof t>[0] }> = [
  { value: "overview", labelKey: "features.library.tabs.overview" },
  { value: "sources", labelKey: "features.library.tabs.sources" },
  { value: "roots", labelKey: "features.library.tabs.roots" },
  { value: "inbox", labelKey: "features.library.tabs.inbox" },
  { value: "plans", labelKey: "features.library.tabs.plans" },
  { value: "path", labelKey: "features.library.tabs.path" },
  { value: "pending", labelKey: "features.library.tabs.pending" },
  { value: "objects", labelKey: "features.library.tabs.objects" },
];

const objectTypes = ["movie", "anime", "collection", "game", "course", "imgset", "docset", "project", "clip", "unknown_object"];
const organizeDetectedTypes = ["movie", "anime", "game", "course", "imgset", "docset", "clip", "unknown"];

function isLibraryTab(value: string | null): value is LibraryTab {
  return libraryTabs.some((tab) => tab.value === value);
}

export function LibraryFeature() {
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get("tab");
  const activeTab: LibraryTab = isLibraryTab(rawTab) ? rawTab : "overview";
  const setDetailsPanelOpen = useUIStore((state) => state.setDetailsPanelOpen);

  useEffect(() => {
    setDetailsPanelOpen(false);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (rawTab !== activeTab) {
      setSearchParams({ tab: activeTab }, { replace: true });
    }
  }, [activeTab, rawTab, setSearchParams]);

  const setActiveTab = (tab: LibraryTab) => {
    setSearchParams({ tab });
  };

  return (
    <WorkbenchPage className="library-feature" variant="library">
      <WorkbenchMasthead
        eyebrow={t("features.library.eyebrow")}
        title={t("features.library.title")}
        description={t("features.library.description")}
      />

      <div className="library-breadcrumb" style={{padding: "0 0 8px", fontSize: 13, color: "var(--color-text-muted)"}}>
        {t("navigation.items.fileLibOverview")} &rsaquo; {t(libraryTabs.find(tab => tab.value === activeTab)?.labelKey ?? "features.library.tabs.overview")}
      </div>

      <div className="library-workspace">
        <aside className="library-tab-rail" aria-label={t("features.library.tabsAriaLabel")}>
          <div className="library-tab-rail__header">
            <span className="workbench-eyebrow">{t("features.library.tabsAriaLabel")}</span>
          </div>
          <div className="settings-segmented-control library-tabs" role="tablist" aria-label={t("features.library.tabsAriaLabel")}>
            {libraryTabs.map((tab) => (
              <button
                key={tab.value}
                className={`secondary-button settings-segmented-button${activeTab === tab.value ? " settings-segmented-button--selected" : ""}`}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.value}
                onClick={() => setActiveTab(tab.value)}
              >
                {t(tab.labelKey)}
              </button>
            ))}
          </div>
        </aside>

        <div className="library-tab-panel" role="tabpanel">
          {activeTab === "overview" ? <LibraryOverviewPanel /> : null}
          {activeTab === "sources" ? <SourceManagementFeature /> : null}
          {activeTab === "roots" ? <LibraryRootsPanel /> : null}
          {activeTab === "path" ? <LibraryPathBrowserPanel /> : null}
          {activeTab === "pending" ? <LibraryPendingPanel /> : null}
          {activeTab === "objects" ? <LibraryObjectsPanel /> : null}
          {activeTab === "plans" ? <LibraryPlansPanel /> : null}
          {activeTab === "inbox" ? <LibraryInboxPanel /> : null}
        </div>
      </div>
    </WorkbenchPage>
  );
}

export { formatSuggestionPayloadSummary, formatBytes, normalizeObjectTypeLabel, objectTypes, organizeDetectedTypes, type LibraryTab, isLibraryTab };
