import { useEffect } from "react";
import { useUIStore } from "../providers/uiStore";

export function ToastContainer() {
  const toasts = useUIStore((s) => s.toasts);
  const removeToast = useUIStore((s) => s.removeToast);

  return (
    <div style={{ position: "fixed", bottom: 20, right: 20, zIndex: 2000, display: "flex", flexDirection: "column", gap: 8 }}>
      {toasts.map((toast: { id: string; message: string }) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={() => removeToast(toast.id)} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }: { toast: { id: string; message: string }; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  const bg = "#eff6ff";
  const border = "#bfdbfe";
  return (
    <div
      style={{ padding: "12px 20px", borderRadius: 8, background: bg, border: `1px solid ${border}`, boxShadow: "0 4px 12px rgba(0,0,0,0.1)", fontSize: 14, cursor: "pointer", minWidth: 280 }}
      onClick={onDismiss}
    >
      {toast.message}
    </div>
  );
}
