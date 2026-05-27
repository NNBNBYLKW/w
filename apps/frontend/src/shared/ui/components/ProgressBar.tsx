interface ProgressBarProps {
  done: number;
  total: number;
  showLabel?: boolean;
}

export function ProgressBar({ done, total, showLabel = false }: ProgressBarProps) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  const indeterminate = total <= 0;
  return (
    <div>
      <div style={{ height: 8, borderRadius: 4, background: "var(--color-border, #ddd)", overflow: "hidden" }}>
        <div
          style={{
            height: "100%", width: indeterminate ? "40%" : `${pct}%`,
            borderRadius: 4, background: "var(--color-accent, #3b82f6)",
            transition: "width 0.3s ease",
            animation: indeterminate ? "progress-indeterminate 1.4s infinite ease-in-out" : undefined,
          }}
        />
      </div>
      {showLabel && <p style={{ fontSize: 12, textAlign: "center", marginTop: 4, color: "var(--color-text-secondary, #666)" }}>{done} / {total}</p>}
    </div>
  );
}
