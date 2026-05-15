import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import { WorkbenchMasthead, WorkbenchPage } from "../../shared/ui/components";
import { LibraryOverviewPanel } from "./LibraryOverviewPanel";
import { LibraryRootsPanel } from "./LibraryRootsPanel";
import { LibraryPathBrowserPanel } from "./LibraryPathBrowserPanel";
import { LibraryObjectsPanel } from "./LibraryObjectsPanel";
import { LibraryPendingPanel } from "./LibraryPendingPanel";
import { LibraryPlansPanel } from "./LibraryPlansPanel";
import { formatSuggestionPayloadSummary, formatBytes, normalizeObjectTypeLabel } from "./shared/helpers";


type LibraryTab = "overview" | "roots" | "path" | "pending" | "objects" | "plans";

const libraryTabs: Array<{ value: LibraryTab; labelKey: Parameters<typeof t>[0] }> = [
  { value: "overview", labelKey: "features.library.tabs.overview" },
  { value: "roots", labelKey: "features.library.tabs.roots" },
  { value: "path", labelKey: "features.library.tabs.path" },
  { value: "pending", labelKey: "features.library.tabs.pending" },
  { value: "objects", labelKey: "features.library.tabs.objects" },
  { value: "plans", labelKey: "features.library.tabs.plans" },
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
          {activeTab === "roots" ? <LibraryRootsPanel /> : null}
          {activeTab === "path" ? <LibraryPathBrowserPanel /> : null}
          {activeTab === "pending" ? <LibraryPendingPanel /> : null}
          {activeTab === "objects" ? <LibraryObjectsPanel /> : null}
          {activeTab === "plans" ? <LibraryPlansPanel /> : null}
        </div>
      </div>
    </WorkbenchPage>
  );
}

export { formatSuggestionPayloadSummary, formatBytes, normalizeObjectTypeLabel, objectTypes, organizeDetectedTypes, type LibraryTab, isLibraryTab };
