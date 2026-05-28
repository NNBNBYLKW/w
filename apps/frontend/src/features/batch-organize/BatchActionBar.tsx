import { useState } from "react";

import { t } from "../../shared/text";
import type { ColorTagValue, FileRatingValue, ManualPlacementValue } from "../../entities/file/types";

type BatchActionBarProps = {
  isApplyingColorTag: boolean;
  isApplyingPlacement: boolean;
  isApplyingTag: boolean;
  isApplyingBatchMeta?: boolean;
  onApplyColorTag: (colorTag: ColorTagValue | null) => void;
  onApplyPlacement: (manualPlacement: ManualPlacementValue | null) => void;
  onApplyTag: (name: string) => void;
  onApplyBatchMeta?: (isFavorite: boolean | null, rating: FileRatingValue | number | null) => void;
  onClearSelection: () => void;
  onExitBatchMode: () => void;
  selectedCount: number;
};

export function BatchActionBar({
  isApplyingColorTag,
  isApplyingPlacement,
  isApplyingTag,
  isApplyingBatchMeta = false,
  onApplyColorTag,
  onApplyPlacement,
  onApplyTag,
  onApplyBatchMeta,
  onClearSelection,
  onExitBatchMode,
  selectedCount,
}: BatchActionBarProps) {
  const [tagInput, setTagInput] = useState("");
  const hasSelection = selectedCount > 0;
  const isBusy = isApplyingTag || isApplyingColorTag || isApplyingPlacement || isApplyingBatchMeta;
  const colorTagOptions: Array<{ label: string; value: ColorTagValue }> = [
    { label: t("common.colors.red"), value: "red" },
    { label: t("common.colors.yellow"), value: "yellow" },
    { label: t("common.colors.green"), value: "green" },
    { label: t("common.colors.blue"), value: "blue" },
    { label: t("common.colors.purple"), value: "purple" },
  ];
  const placementOptions: Array<{ label: string; value: ManualPlacementValue | "auto" }> = [
    { label: t("features.batch.placementOptions.auto"), value: "auto" },
    { label: t("features.batch.placementOptions.media"), value: "media" },
    { label: t("features.batch.placementOptions.books"), value: "books" },
    { label: t("features.batch.placementOptions.games"), value: "games" },
    { label: t("features.batch.placementOptions.software"), value: "software" },
    { label: t("features.batch.placementOptions.filesOnly"), value: "files_only" },
  ];
  const ratingOptions: Array<{ label: string; value: number }> = [
    { label: t("common.ratings.unset"), value: 0 },
    { label: t("common.ratings.star1"), value: 1 },
    { label: t("common.ratings.star2"), value: 2 },
    { label: t("common.ratings.star3"), value: 3 },
    { label: t("common.ratings.star4"), value: 4 },
    { label: t("common.ratings.star5"), value: 5 },
  ];

  return (
    <section className="batch-action-bar">
      <div className="batch-action-bar__summary">
        <span className="page-header__eyebrow">{t("features.batch.eyebrow")}</span>
        <strong>{t("features.batch.summary", { count: selectedCount })}</strong>
        <p>{t("features.batch.description")}</p>
      </div>
      <div className="batch-action-bar__controls">
        <form
          className="batch-action-bar__tag-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!tagInput.trim() || !hasSelection) {
              return;
            }
            onApplyTag(tagInput.trim());
            setTagInput("");
          }}
        >
          <input
            className="text-input"
            value={tagInput}
            onChange={(event) => setTagInput(event.target.value)}
            placeholder={t("features.batch.placeholder")}
            disabled={!hasSelection || isBusy}
          />
          <button className="secondary-button" type="submit" disabled={!hasSelection || !tagInput.trim() || isBusy}>
            {isApplyingTag ? t("common.actions.addingTag") : t("common.actions.addTag")}
          </button>
        </form>
        <div className="batch-action-bar__color-group">
          {colorTagOptions.map((colorTag) => (
            <button
              key={colorTag.value}
              className={`ghost-button color-tag-button color-tag-button--${colorTag.value}`}
              type="button"
              onClick={() => onApplyColorTag(colorTag.value)}
              disabled={!hasSelection || isBusy}
            >
              {colorTag.label}
            </button>
          ))}
          <button
            className="ghost-button color-tag-button"
            type="button"
            onClick={() => onApplyColorTag(null)}
            disabled={!hasSelection || isBusy}
          >
            {t("features.batch.clearColorTag")}
          </button>
        </div>
        <label className="field-stack">
          <span>{t("features.batch.placementLabel")}</span>
          <select
            className="select-input"
            defaultValue=""
            disabled={!hasSelection || isBusy}
            onChange={(event) => {
              const value = event.target.value;
              if (!value) {
                return;
              }
              onApplyPlacement(value === "auto" ? null : (value as ManualPlacementValue));
              event.currentTarget.value = "";
            }}
          >
            <option value="">{t("features.batch.placementPlaceholder")}</option>
            {placementOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        {onApplyBatchMeta ? (
          <>
            <div className="batch-action-bar__fav-group">
              <button
                className="ghost-button"
                type="button"
                onClick={() => onApplyBatchMeta(true, null)}
                disabled={!hasSelection || isBusy}
              >
                {t("common.actions.favorite")}
              </button>
              <button
                className="ghost-button"
                type="button"
                onClick={() => onApplyBatchMeta(false, null)}
                disabled={!hasSelection || isBusy}
              >
                {t("common.actions.unfavorite")}
              </button>
            </div>
            <label className="field-stack">
              <span>{t("common.labels.rating")}</span>
              <select
                className="select-input"
                defaultValue=""
                disabled={!hasSelection || isBusy}
                onChange={(event) => {
                  const value = event.target.value;
                  if (!value) {
                    return;
                  }
                  const numValue = Number(value);
                  onApplyBatchMeta(null, numValue === 0 ? null : (numValue as FileRatingValue));
                  event.currentTarget.value = "";
                }}
              >
                <option value="">{t("features.batch.ratingPlaceholder")}</option>
                {ratingOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </>
        ) : null}
      </div>
      <div className="batch-action-bar__actions">
        <button className="ghost-button" type="button" onClick={onClearSelection} disabled={!hasSelection || isBusy}>
          {t("features.batch.clearSelection")}
        </button>
        <button className="ghost-button" type="button" onClick={onExitBatchMode} disabled={isBusy}>
          {t("features.batch.exit")}
        </button>
      </div>
    </section>
  );
}
