import type { ColorTagValue } from "../../../entities/file/types";
import { t } from "../../../shared/text";

export interface DetailsColorTagSectionProps {
  colorTag: ColorTagValue | null;
  isPending: boolean;
  error: string | null;
  colorOptions: ReadonlyArray<ColorTagValue>;
  currentColorLabel: string;
  onChange: (value: ColorTagValue | null) => void;
}

export function DetailsColorTagSection({
  colorTag,
  isPending,
  error,
  colorOptions,
  currentColorLabel,
  onChange,
}: DetailsColorTagSectionProps) {
  return (
    <section className="color-tag-section">
      <div className="color-tag-section__header">
        <h4>{t("details.sections.colorTag")}</h4>
        {isPending ? <span className="status-pill">{t("details.actions.updating")}</span> : null}
      </div>
      <p>{t("details.fields.currentColorTag", { color: currentColorLabel })}</p>
      <div className="color-tag-actions">
        {colorOptions.map((color) => (
          <button
            key={color}
            className={`ghost-button color-tag-button color-tag-button--${color}${colorTag === color ? " color-tag-button--selected" : ""}`}
            type="button"
            onClick={() => onChange(colorTag === color ? null : color)}
            disabled={isPending}
          >
            {color}
          </button>
        ))}
        <button
          className={`ghost-button color-tag-button${colorTag === null ? " color-tag-button--selected" : ""}`}
          type="button"
          onClick={() => onChange(null)}
          disabled={isPending}
        >
          {t("details.actions.clear")}
        </button>
      </div>
      {error ? <p className="color-tag-section__error">{error}</p> : null}
    </section>
  );
}
