import { useEffect, useMemo, useState } from "react";

import { t } from "../text";

export type ViewMode = "details" | "icons";
export type ViewModeScope = "search" | "books" | "software" | "media" | "games";

const VIEW_MODE_STORAGE_KEY = "WORKBENCH_VIEW_MODE";

function isViewMode(value: unknown): value is ViewMode {
  return value === "details" || value === "icons";
}

function readStoredViewModes(): Partial<Record<ViewModeScope, ViewMode>> {
  if (typeof window === "undefined") {
    return {};
  }

  const rawValue = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);
  if (!rawValue) {
    return {};
  }

  try {
    const parsedValue = JSON.parse(rawValue) as Partial<Record<ViewModeScope, unknown>>;
    return Object.fromEntries(
      Object.entries(parsedValue).filter((entry): entry is [ViewModeScope, ViewMode] => isViewMode(entry[1])),
    ) as Partial<Record<ViewModeScope, ViewMode>>;
  } catch {
    return {};
  }
}

function writeStoredViewMode(scope: ViewModeScope, mode: ViewMode) {
  if (typeof window === "undefined") {
    return;
  }

  const storedModes = readStoredViewModes();
  window.localStorage.setItem(
    VIEW_MODE_STORAGE_KEY,
    JSON.stringify({
      ...storedModes,
      [scope]: mode,
    }),
  );
}

export function useViewMode(scope: ViewModeScope) {
  const [viewMode, setViewModeState] = useState<ViewMode>(() => readStoredViewModes()[scope] ?? "details");

  useEffect(() => {
    setViewModeState(readStoredViewModes()[scope] ?? "details");
  }, [scope]);

  const setViewMode = (mode: ViewMode) => {
    setViewModeState(mode);
    writeStoredViewMode(scope, mode);
  };

  return { viewMode, setViewMode };
}

function DetailsIcon() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M3 4.25h10M3 8h10M3 11.75h10" fill="none" stroke="currentColor" strokeLinecap="round" />
    </svg>
  );
}

function IconsIcon() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path
        d="M3 3.5h3.2v3.2H3zM9.8 3.5H13v3.2H9.8zM3 9.3h3.2v3.2H3zM9.8 9.3H13v3.2H9.8z"
        fill="none"
        stroke="currentColor"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ViewModeToggle({
  value,
  onChange,
}: {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
}) {
  return (
    <div className="view-mode-toggle" aria-label={t("common.viewModes.switchView")}>
      <span className="view-mode-toggle__label">{t("common.viewModes.view")}</span>
      <div className="view-mode-toggle__buttons">
        <button
          className={`view-mode-toggle__button${value === "details" ? " view-mode-toggle__button--selected" : ""}`}
          type="button"
          onClick={() => onChange("details")}
          aria-pressed={value === "details"}
          title={t("common.viewModes.detailsView")}
        >
          <span className="view-mode-toggle__icon">
            <DetailsIcon />
          </span>
          <span>{t("common.viewModes.details")}</span>
        </button>
        <button
          className={`view-mode-toggle__button${value === "icons" ? " view-mode-toggle__button--selected" : ""}`}
          type="button"
          onClick={() => onChange("icons")}
          aria-pressed={value === "icons"}
          title={t("common.viewModes.iconView")}
        >
          <span className="view-mode-toggle__icon">
            <IconsIcon />
          </span>
          <span>{t("common.viewModes.icons")}</span>
        </button>
      </div>
    </div>
  );
}

export type AssetIconCardItem = {
  id: number;
  title: string;
  path?: string;
  typeLabel: string;
  meta: string;
  mark: string;
  markTone?: string;
  thumbnailUrl?: string;
  thumbnailAlt?: string;
  thumbnailFit?: "cover" | "contain";
  signals?: string[];
  selected: boolean;
};

function AssetIconCard({ item, onOpen, onSelect }: {
  item: AssetIconCardItem;
  onOpen?: () => void;
  onSelect: () => void;
}) {
  const [thumbnailFailed, setThumbnailFailed] = useState(false);
  const showThumbnail = item.thumbnailUrl && !thumbnailFailed;

  return (
    <button
      className={`asset-icon-card${item.selected ? " asset-icon-card--selected" : ""}`}
      type="button"
      onClick={onSelect}
      onDoubleClick={() => {
        onOpen?.();
      }}
    >
      <span className="asset-icon-card__preview">
        {showThumbnail ? (
          <img
            className={`asset-icon-card__thumbnail asset-icon-card__thumbnail--${item.thumbnailFit ?? "cover"}`}
            src={item.thumbnailUrl}
            alt={item.thumbnailAlt ?? item.title}
            loading="lazy"
            onError={() => setThumbnailFailed(true)}
          />
        ) : (
          <span className={`asset-icon-card__mark${item.markTone ? ` asset-icon-card__mark--${item.markTone}` : ""}`}>
            {item.mark}
          </span>
        )}
      </span>
      <span className="asset-icon-card__body">
        <strong title={item.title}>{item.title}</strong>
        <span title={item.path ?? item.meta}>{item.meta}</span>
      </span>
      <span className="asset-icon-card__footer">
        <span className="asset-icon-card__type">{item.typeLabel}</span>
        {item.signals?.slice(0, 2).map((signal) => (
          <span className="asset-icon-card__signal" key={signal}>
            {signal}
          </span>
        ))}
      </span>
    </button>
  );
}

export function AssetIconGrid({
  ariaLabel,
  items,
  onOpen,
  onSelect,
}: {
  ariaLabel: string;
  items: AssetIconCardItem[];
  onOpen?: (item: AssetIconCardItem) => void;
  onSelect: (item: AssetIconCardItem) => void;
}) {
  const stableItems = useMemo(() => items, [items]);

  return (
    <div className="asset-icon-grid" aria-label={ariaLabel}>
      {stableItems.map((item) => (
        <AssetIconCard
          key={item.id}
          item={item}
          onOpen={onOpen ? () => onOpen(item) : undefined}
          onSelect={() => onSelect(item)}
        />
      ))}
    </div>
  );
}
