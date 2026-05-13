import type { ReactNode } from "react";

export function FileRow({
  name,
  path,
  meta,
  thumbnail,
  badges,
  selected,
  disabled,
  onClick,
  onDoubleClick,
  actions,
  className,
}: {
  name: string;
  path?: string;
  meta?: ReactNode;
  thumbnail?: ReactNode;
  badges?: ReactNode;
  selected?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  onDoubleClick?: () => void;
  actions?: ReactNode;
  className?: string;
}) {
  const cls = [
    "file-row",
    selected ? "file-row--selected" : "",
    disabled ? "file-row--disabled" : "",
    onClick || onDoubleClick ? "file-row--interactive" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={cls}
      onClick={disabled ? undefined : onClick}
      onDoubleClick={disabled ? undefined : onDoubleClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-disabled={disabled}
    >
      {thumbnail ? <div className="file-row__thumbnail">{thumbnail}</div> : null}
      <div className="file-row__info">
        <span className="file-row__name">{name}</span>
        {path ? <span className="file-row__path">{path}</span> : null}
        {meta ? <span className="file-row__meta">{meta}</span> : null}
      </div>
      {badges ? <div className="file-row__badges">{badges}</div> : null}
      {actions ? <div className="file-row__actions">{actions}</div> : null}
    </div>
  );
}
