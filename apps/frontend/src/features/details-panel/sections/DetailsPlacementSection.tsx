import { t } from "../../../shared/text";

export interface DetailsPlacementSectionProps {
  manualPlacement: string | null;
  fileKind: string;
  autoPlacementLabel: string;
  effectivePlacementLabel: string;
  isPending: boolean;
  error: string | null;
  placementOptions: ReadonlyArray<{ labelKey: Parameters<typeof t>[0]; value: string }>;
  onChange: (value: string) => void;
}

export function DetailsPlacementSection({
  manualPlacement,
  fileKind,
  autoPlacementLabel,
  effectivePlacementLabel,
  isPending,
  error,
  placementOptions,
  onChange,
}: DetailsPlacementSectionProps) {
  return (
    <section className="details-placement-section">
      <div className="details-placement-section__header">
        <h4>{t("details.sections.libraryPlacement")}</h4>
        {isPending ? <span className="status-pill">{t("details.actions.updating")}</span> : null}
      </div>
      <label className="field-stack">
        <span>{t("details.fields.libraryPlacement")}</span>
        <select
          className="select-input"
          value={manualPlacement ?? "auto"}
          onChange={(event) => onChange(event.target.value)}
          disabled={isPending}
        >
          {placementOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {t(option.labelKey)}
            </option>
          ))}
        </select>
      </label>
      <p className="details-placement-section__note">
        {t("details.placement.summary", {
          kind: fileKind,
          auto: autoPlacementLabel,
          effective: effectivePlacementLabel,
        })}
      </p>
      {error ? <p className="color-tag-section__error">{error}</p> : null}
    </section>
  );
}
