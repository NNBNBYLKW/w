import { t } from "../../../shared/text";
import { ActionButton } from "../../../shared/ui/components";

export interface DetailsActionsSectionProps {
  isOpenActionPending: boolean;
  hasDesktopOpenActions: boolean;
  openActionError: string | null;
  onOpenFile: () => void;
  onOpenFolder: () => void;
  openFileLabel: string;
}

export function DetailsActionsSection({
  isOpenActionPending,
  hasDesktopOpenActions,
  openActionError,
  onOpenFile,
  onOpenFolder,
  openFileLabel,
}: DetailsActionsSectionProps) {
  return (
    <section className="open-actions-section">
      <div className="open-actions-section__header">
        <h4>{t("details.sections.openActions")}</h4>
        {isOpenActionPending ? <span className="status-pill">{t("details.actions.opening")}</span> : null}
      </div>
      <div className="open-actions-buttons">
        <ActionButton variant="primary" size="sm" onClick={onOpenFile} disabled={isOpenActionPending || !hasDesktopOpenActions}>
          {openFileLabel}
        </ActionButton>
        <ActionButton variant="secondary" size="sm" onClick={onOpenFolder} disabled={isOpenActionPending || !hasDesktopOpenActions}>
          {t("details.actions.openContainingFolder")}
        </ActionButton>
      </div>
      {!hasDesktopOpenActions ? (
        <p className="open-actions-section__note">{t("details.actions.openActionUnavailable")}</p>
      ) : null}
      {openActionError ? <p className="open-actions-section__error">{openActionError}</p> : null}
    </section>
  );
}
