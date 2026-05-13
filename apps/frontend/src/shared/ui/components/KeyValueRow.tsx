import type { ReactNode } from "react";

export function KeyValueRow({
  label,
  value,
  mono,
  emptyText,
  action,
  className,
}: {
  label: string;
  value?: ReactNode;
  mono?: boolean;
  emptyText?: string;
  action?: ReactNode;
  className?: string;
}) {
  const cls = `key-value-row${className ? ` ${className}` : ""}`;
  const fallback = value ?? emptyText ?? "—";
  return (
    <div className={cls}>
      <span className="key-value-row__label">{label}</span>
      <span className={`key-value-row__value${mono ? " key-value-row__value--mono" : ""}`}>
        {fallback}
      </span>
      {action ? <span className="key-value-row__action">{action}</span> : null}
    </div>
  );
}
