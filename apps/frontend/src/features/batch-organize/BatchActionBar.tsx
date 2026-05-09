import { useState } from "react";

import { t } from "../../shared/text";
import type { ColorTagValue, ManualPlacementValue } from "../../entities/file/types";

type BatchActionBarProps = {
  isApplyingColorTag: boolean;
  isApplyingPlacement: boolean;
  isApplyingTag: boolean;
  onApplyColorTag: (colorTag: ColorTagValue | null) => void;
  onApplyPlacement: (manualPlacement: ManualPlacementValue | null) => void;
  onApplyTag: (name: string) => void;
  onClearSelection: () => void;
  onExitBatchMode: () => void;
  selectedCount: number;
};

export function BatchActionBar({
  isApplyingColorTag,
  isApplyingPlacement,
  isApplyingTag,
  onApplyColorTag,
  onApplyPlacement,
  onApplyTag,
  onClearSelection,
  onExitBatchMode,
  selectedCount,
}: BatchActionBarProps) {
  const [tagInput, setTagInput] = useState("");
  const hasSelection = selectedCount > 0;
  const isBusy = isApplyingTag || isApplyingColorTag || isApplyingPlacement;
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
