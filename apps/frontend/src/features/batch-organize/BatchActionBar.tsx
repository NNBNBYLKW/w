import { useState } from "react";

import { t } from "../../shared/text";
import type { ColorTagValue } from "../../entities/file/types";

type BatchActionBarProps = {
  isApplyingColorTag: boolean;
  isApplyingTag: boolean;
  onApplyColorTag: (colorTag: ColorTagValue | null) => void;
  onApplyTag: (name: string) => void;
  onClearSelection: () => void;
  onExitBatchMode: () => void;
  selectedCount: number;
};

export function BatchActionBar({
  isApplyingColorTag,
  isApplyingTag,
  onApplyColorTag,
  onApplyTag,
  onClearSelection,
  onExitBatchMode,
  selectedCount,
}: BatchActionBarProps) {
  const [tagInput, setTagInput] = useState("");
  const hasSelection = selectedCount > 0;
  const isBusy = isApplyingTag || isApplyingColorTag;
  const colorTagOptions: Array<{ label: string; value: ColorTagValue }> = [
    { label: t("common.colors.red"), value: "red" },
    { label: t("common.colors.yellow"), value: "yellow" },
    { label: t("common.colors.green"), value: "green" },
    { label: t("common.colors.blue"), value: "blue" },
    { label: t("common.colors.purple"), value: "purple" },
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
