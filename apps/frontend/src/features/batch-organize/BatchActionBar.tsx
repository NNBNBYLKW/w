import { useState } from "react";

import type { ColorTagValue } from "../../entities/file/types";


const COLOR_TAG_OPTIONS: Array<{ label: string; value: ColorTagValue }> = [
  { label: "Red", value: "red" },
  { label: "Yellow", value: "yellow" },
  { label: "Green", value: "green" },
  { label: "Blue", value: "blue" },
  { label: "Purple", value: "purple" },
];

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

  return (
    <section className="batch-action-bar">
      <div className="batch-action-bar__summary">
        <span className="page-header__eyebrow">Batch mode</span>
        <strong>{selectedCount} selected on this page</strong>
        <p>Apply tags or color tags to the current page selection, then return to normal browsing.</p>
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
            placeholder="Add tag to selected files"
            disabled={!hasSelection || isBusy}
          />
          <button className="secondary-button" type="submit" disabled={!hasSelection || !tagInput.trim() || isBusy}>
            {isApplyingTag ? "Adding..." : "Add tag"}
          </button>
        </form>
        <div className="batch-action-bar__color-group">
          {COLOR_TAG_OPTIONS.map((colorTag) => (
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
            Clear color tag
          </button>
        </div>
      </div>
      <div className="batch-action-bar__actions">
        <button className="ghost-button" type="button" onClick={onClearSelection} disabled={!hasSelection || isBusy}>
          Clear selection
        </button>
        <button className="ghost-button" type="button" onClick={onExitBatchMode} disabled={isBusy}>
          Exit batch mode
        </button>
      </div>
    </section>
  );
}
