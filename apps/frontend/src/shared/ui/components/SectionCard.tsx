import type { ReactNode } from "react";

export function SectionCard({
  title,
  children,
  className,
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  const cls = `section-card${className ? ` ${className}` : ""}`;
  return (
    <section className={cls}>
      {title ? <h3 className="section-card__title">{title}</h3> : null}
      {children}
    </section>
  );
}
