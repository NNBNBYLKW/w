import type { FileStatusValue } from "../../../entities/file/types";
import { t } from "../../../shared/text";

export interface DetailsGameStatusSectionProps {
  status: FileStatusValue | null;
  isPending: boolean;
  error: string | null;
  statusLabel: string;
  statusOptions: ReadonlyArray<FileStatusValue>;
  onChange: (value: FileStatusValue) => void;
}

export function DetailsGameStatusSection({
  status,
  isPending,
  error,
  statusLabel,
  statusOptions,
  onChange,
}: DetailsGameStatusSectionProps) {
  return (
    <section className="details-game-status-section">
      <div className="details-game-status-section__header">
        <h4>{t("details.sections.gameStatus")}</h4>
        {isPending ? <span className="status-pill">{t("details.actions.updating")}</span> : null}
      </div>
      <p>{t("details.fields.currentStatus", { status: status ? statusLabel : t("details.values.none") })}</p>
      <div className="details-game-status-actions">
        {statusOptions.map((value) => (
          <button
            key={value}
            className={`ghost-button details-game-status-button${status === value ? " details-game-status-button--selected" : ""}`}
            type="button"
            onClick={() => onChange(value)}
            disabled={isPending}
          >
            {value}
          </button>
        ))}
      </div>
      {error ? <p className="color-tag-section__error">{error}</p> : null}
    </section>
  );
}
