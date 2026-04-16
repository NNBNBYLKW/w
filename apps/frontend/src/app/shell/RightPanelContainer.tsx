import { useUIStore } from "../providers/uiStore";
import { DetailsPanelFeature } from "../../features/details-panel/DetailsPanelFeature";


export function RightPanelContainer() {
  const isDetailsPanelOpen = useUIStore((state) => state.isDetailsPanelOpen);

  if (!isDetailsPanelOpen) {
    return null;
  }

  return (
    <aside className="right-panel-container">
      <DetailsPanelFeature />
    </aside>
  );
}
