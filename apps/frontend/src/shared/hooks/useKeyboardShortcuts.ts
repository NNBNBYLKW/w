import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useUIStore } from "../../app/providers/uiStore";

export function useKeyboardShortcuts() {
  const navigate = useNavigate();
  const setDetailsPanelOpen = useUIStore((s) => s.setDetailsPanelOpen);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
      if (e.key === "Escape") { setDetailsPanelOpen(false); return; }
      if (isInput) return;
      if ((e.ctrlKey || e.metaKey) && e.key === "k") { e.preventDefault(); navigate("/search"); }
      if (e.key === "/") { e.preventDefault(); navigate("/search"); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate, setDetailsPanelOpen]);
}
