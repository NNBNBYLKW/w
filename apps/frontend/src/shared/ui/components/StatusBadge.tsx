import type { ReactNode } from "react";

export type StatusBadgeVariant = "accent" | "secondary" | "info" | "success" | "warning" | "danger" | "muted";

const variantClass: Record<StatusBadgeVariant, string> = {
  accent: "status-badge--accent",
  secondary: "status-badge--secondary",
  info: "status-badge--info",
  success: "status-badge--success",
  warning: "status-badge--warning",
  danger: "status-badge--danger",
  muted: "status-badge--muted",
};

export function StatusBadge({
  children,
  variant = "muted",
  className,
}: {
  children: ReactNode;
  variant?: StatusBadgeVariant;
  className?: string;
}) {
  const cls = `status-badge ${variantClass[variant]}${className ? ` ${className}` : ""}`;
  return <span className={cls}>{children}</span>;
}
