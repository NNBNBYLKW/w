import type { ReactNode } from "react";

type WorkbenchPageProps = {
  children: ReactNode;
  className?: string;
  variant?: string;
};

type WorkbenchMastheadProps = {
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
  description?: ReactNode;
  eyebrow?: ReactNode;
  meta?: ReactNode;
  title: ReactNode;
};

type WorkbenchSectionProps = {
  children: ReactNode;
  className?: string;
  label?: string;
};

type WorkbenchResultFrameProps = {
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  meta?: ReactNode;
  title?: ReactNode;
};

type MetricStripProps = {
  className?: string;
  items: Array<{
    label: ReactNode;
    value: ReactNode;
    tone?: "default" | "primary" | "success" | "warning" | "danger" | "info";
  }>;
};

type InspectorSectionProps = {
  children: ReactNode;
  className?: string;
  title?: ReactNode;
};

function joinClasses(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function WorkbenchPage({ children, className, variant }: WorkbenchPageProps) {
  return (
    <section
      className={joinClasses("workbench-page", variant ? `workbench-page--${variant}` : null, className)}
    >
      {children}
    </section>
  );
}

export function WorkbenchMasthead({
  actions,
  children,
  className,
  description,
  eyebrow,
  meta,
  title,
}: WorkbenchMastheadProps) {
  return (
    <header className={joinClasses("workbench-masthead", className)}>
      <div className="workbench-masthead__copy">
        {eyebrow ? <span className="workbench-eyebrow">{eyebrow}</span> : null}
        <h3>{title}</h3>
        {description ? <p>{description}</p> : null}
        {meta ? <div className="workbench-masthead__meta">{meta}</div> : null}
      </div>
      {actions ? <div className="workbench-masthead__actions">{actions}</div> : null}
      {children ? <div className="workbench-masthead__body">{children}</div> : null}
    </header>
  );
}

export function WorkbenchToolbar({ children, className, label }: WorkbenchSectionProps) {
  return (
    <div className={joinClasses("workbench-toolbar", className)} aria-label={label}>
      {children}
    </div>
  );
}

export function WorkbenchFilterPanel({ children, className, label }: WorkbenchSectionProps) {
  return (
    <section className={joinClasses("workbench-filter-panel", className)} aria-label={label}>
      {children}
    </section>
  );
}

export function WorkbenchResultFrame({
  actions,
  children,
  className,
  meta,
  title,
}: WorkbenchResultFrameProps) {
  return (
    <section className={joinClasses("workbench-result-frame", className)}>
      {title || meta || actions ? (
        <div className="workbench-result-frame__header">
          <div className="workbench-result-frame__copy">
            {title ? <h4>{title}</h4> : null}
            {meta ? <div className="workbench-result-frame__meta">{meta}</div> : null}
          </div>
          {actions ? <div className="workbench-result-frame__actions">{actions}</div> : null}
        </div>
      ) : null}
      <div className="workbench-result-frame__body">{children}</div>
    </section>
  );
}

export function MetricStrip({ className, items }: MetricStripProps) {
  return (
    <dl className={joinClasses("metric-strip", className)}>
      {items.map((item, index) => (
        <div
          className={joinClasses("metric-strip__item", item.tone ? `metric-strip__item--${item.tone}` : null)}
          key={index}
        >
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function InspectorSection({ children, className, title }: InspectorSectionProps) {
  return (
    <section className={joinClasses("inspector-section", className)}>
      {title ? <h4 className="inspector-section__title">{title}</h4> : null}
      {children}
    </section>
  );
}
