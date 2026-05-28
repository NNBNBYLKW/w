import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useUIStore } from "../../app/providers/uiStore";

export function useKeyboardShortcuts() {
  const navigate = useNavigate();
  const setDetailsPanelOpen = useUIStore((s) => s.setDetailsPanelOpen);
  const toggleSidebarCollapsed = useUIStore((s) => s.toggleSidebarCollapsed);
  const toggleQuickPanelOpen = useUIStore((s) => s.toggleQuickPanelOpen);
  const isDetailsPanelOpen = useUIStore((s) => s.isDetailsPanelOpen);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
      if (e.key === "Escape") { setDetailsPanelOpen(false); return; }
      if (isInput) return;
      if ((e.ctrlKey || e.metaKey) && e.key === "k") { e.preventDefault(); navigate("/search"); }
      if (e.key === "/") { e.preventDefault(); navigate("/search"); }
      if ((e.ctrlKey || e.metaKey) && e.key === "b") { e.preventDefault(); toggleSidebarCollapsed(); }
      if ((e.ctrlKey || e.metaKey) && e.key === "d") { e.preventDefault(); setDetailsPanelOpen(!isDetailsPanelOpen); }
      if ((e.ctrlKey || e.metaKey) && e.key === "h") { e.preventDefault(); navigate("/home"); }
      if ((e.ctrlKey || e.metaKey) && e.key === "l") { e.preventDefault(); navigate("/library"); }
      if ((e.ctrlKey || e.metaKey) && e.key === "q") { e.preventDefault(); toggleQuickPanelOpen(); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate, setDetailsPanelOpen, toggleSidebarCollapsed, isDetailsPanelOpen, toggleQuickPanelOpen]);
}
