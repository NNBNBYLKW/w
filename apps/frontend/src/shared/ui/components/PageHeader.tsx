import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  meta,
  className,
}: {
  title: string;
  description?: string;
  eyebrow?: string;
  actions?: ReactNode;
  meta?: ReactNode;
  className?: string;
}) {
  const cls = `page-header${className ? ` ${className}` : ""}`;
  return (
    <header className={cls}>
      <div className="page-header__main">
        {eyebrow ? <span className="page-header__eyebrow">{eyebrow}</span> : null}
        <h2 className="page-header__title">{title}</h2>
        {description ? <p className="page-header__desc">{description}</p> : null}
        {meta ? <div className="page-header__meta">{meta}</div> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}
