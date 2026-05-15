import type { ReactNode } from "react";

export type ActionButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "success" | "warning";

const variantClass: Record<ActionButtonVariant, string> = {
  primary: "action-button--primary",
  secondary: "action-button--secondary",
  ghost: "action-button--ghost",
  danger: "action-button--danger",
  success: "action-button--success",
  warning: "action-button--warning",
};

export function ActionButton({
  children,
  icon,
  variant = "secondary",
  size = "md",
  disabled,
  onClick,
  type = "button",
  className,
  ariaLabel,
}: {
  children?: ReactNode;
  icon?: ReactNode;
  variant?: ActionButtonVariant;
  size?: "sm" | "md";
  disabled?: boolean;
  onClick?: () => void;
  type?: "button" | "submit";
  className?: string;
  ariaLabel?: string;
}) {
  const cls = [
    "action-button",
    variantClass[variant],
    size === "sm" ? "action-button--sm" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={cls} type={type} disabled={disabled} onClick={onClick} aria-label={ariaLabel}>
      {icon ? <span className="action-button__icon">{icon}</span> : null}
      {children ? <span className="action-button__label">{children}</span> : null}
    </button>
  );
}
