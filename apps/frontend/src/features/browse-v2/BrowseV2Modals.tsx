import type { LibraryRootVM } from "../../entities/library/types";
import type { BrowseV2Card, BrowseV2LooseFileCard } from "../../services/api/browseV2Api";
import { t } from "../../shared/text";
import { ComposeObjectModal } from "./ComposeObjectModal";
import { ExecutePlanPanel } from "./ExecutePlanPanel";

export interface BrowseV2ModalsProps {
  showComposeModal: boolean;
  selectedFiles: BrowseV2LooseFileCard[];
  roots: LibraryRootVM[];
  selectionSS: string;
  composing: boolean;
  composeError: string | null;
  composeSuccess: string | null;
  executingPlanId: number | null;
  showAddMembersModal: boolean;
  amending: boolean;
  selectedAddFileIds: Set<number>;
  looseCandidates: { items: BrowseV2Card[] } | undefined;
  showRemoveMemberModal: boolean;
  removeTargetMember: { member_id: number; name: string } | null;
  onCancelCompose: () => void;
  onConfirmCompose: (params: {
    inbox_item_ids?: number[];
    file_ids?: number[];
    object_name: string;
    suggested_object_type?: string;
    target_library_root_id?: number;
  }) => void;
  onDismissComposeError: () => void;
  onExecuteOrNavigateAfterCompose: () => void;
  onDismissComposeSuccess: () => void;
  onDismissAddMembersModal: () => void;
  onToggleAddFileId: (fileId: number) => void;
  onConfirmAddMembers: () => void;
  onCloseExecutePlan: () => void;
  onDismissRemoveMemberModal: () => void;
  onConfirmRemoveMember: () => void;
}

export function BrowseV2Modals({
  showComposeModal,
  selectedFiles,
  roots,
  selectionSS,
  composing,
  composeError,
  composeSuccess,
  executingPlanId,
  showAddMembersModal,
  amending,
  selectedAddFileIds,
  looseCandidates,
  showRemoveMemberModal,
  removeTargetMember,
  onCancelCompose,
  onConfirmCompose,
  onDismissComposeError,
  onExecuteOrNavigateAfterCompose,
  onDismissComposeSuccess,
  onDismissAddMembersModal,
  onToggleAddFileId,
  onConfirmAddMembers,
  onCloseExecutePlan,
  onDismissRemoveMemberModal,
  onConfirmRemoveMember,
}: BrowseV2ModalsProps) {
  return (
    <>
      {showComposeModal && (
        <ComposeObjectModal
          selectedFiles={selectedFiles}
          roots={roots}
          selectionSS={selectionSS}
          busy={composing}
          onCancel={onCancelCompose}
          onConfirm={onConfirmCompose}
        />
      )}

      {composeError && (
        <div className="browse-v2-inline-alert browse-v2-inline-alert--danger" role="alert">
          {t("features.browseV2.compose.error")}: {composeError}
          <button className="secondary-button" type="button" onClick={onDismissComposeError}>
            {t("features.library.inbox.cancel")}
          </button>
        </div>
      )}
      {composeSuccess && (
        <div className="browse-v2-inline-alert browse-v2-inline-alert--success" role="status">
          {composeSuccess}
          <p>
            {t("features.browseV2.amendment.filesHaveNotMoved")} /{" "}
            {t("features.browseV2.amendment.preflightExecuteRequired")}
          </p>
          <div className="browse-v2-inline-alert__actions">
            <button className="primary-button" type="button" onClick={onExecuteOrNavigateAfterCompose}>
              {executingPlanId
                ? "Review & Execute"
                : t("features.browseV2.amendment.goToPlans")}
            </button>
            <button className="secondary-button" type="button" onClick={onDismissComposeSuccess}>
              {t("features.library.inbox.cancel")}
            </button>
          </div>
        </div>
      )}

      {/* Phase 8D-D: Add Members Modal */}
      {showAddMembersModal && (
        <div
          className="library-inbox-modal-overlay"
          onClick={amending ? undefined : onDismissAddMembersModal}
        >
          <div
            className="library-inbox-modal browse-v2-amendment-modal browse-v2-amendment-modal--wide"
            role="dialog"
            onClick={(e) => e.stopPropagation()}
          >
            <h3>{t("features.browseV2.amendment.addMembersTitle")}</h3>
            <p className="library-inbox-modal-hint">
              {t("features.browseV2.amendment.addMembersDescription")}
            </p>
            <div className="browse-v2-amendment-candidates">
              {looseCandidates?.items.filter((c) => c.card_kind === "loose_file").length === 0 && (
                <p className="browse-v2-amendment-candidates__empty">
                  {t("features.browseV2.amendment.noManagedLooseCandidates")}
                </p>
              )}
              {looseCandidates?.items
                .filter((c) => c.card_kind === "loose_file")
                .map((card: any) => (
                  <label className="browse-v2-amendment-candidate" key={card.file_id}>
                    <input
                      type="checkbox"
                      checked={selectedAddFileIds.has(card.file_id)}
                      onChange={() => onToggleAddFileId(card.file_id)}
                      disabled={amending}
                    />
                    <span title={card.path}>{card.name}</span>
                  </label>
                ))}
            </div>
            <p className="library-review-notice">
              {t("features.browseV2.amendment.draftPlanOnlyNotice")}
            </p>
            <div className="library-inbox-modal-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={onDismissAddMembersModal}
                disabled={amending}
              >
                {t("features.library.inbox.cancel")}
              </button>
              <button
                className="primary-button"
                type="button"
                disabled={selectedAddFileIds.size === 0 || amending}
                onClick={onConfirmAddMembers}
              >
                {amending ? "…" : t("features.browseV2.amendment.createPlan")}
              </button>
            </div>
          </div>
        </div>
      )}

      {executingPlanId ? (
        <ExecutePlanPanel planId={executingPlanId} onClose={onCloseExecutePlan} />
      ) : null}

      {/* Phase 8D-D: Remove Member Modal */}
      {showRemoveMemberModal && removeTargetMember && (
        <div
          className="library-inbox-modal-overlay"
          onClick={amending ? undefined : onDismissRemoveMemberModal}
        >
          <div
            className="library-inbox-modal browse-v2-amendment-modal"
            role="dialog"
            onClick={(e) => e.stopPropagation()}
          >
            <h3>{t("features.browseV2.amendment.removeMemberTitle")}</h3>
            <p className="library-inbox-modal-hint">
              {t("features.browseV2.amendment.removeMemberDescription")}
            </p>
            <div className="browse-v2-amendment-target">
              <strong>{t("features.browseV2.overview.name")}:</strong> {removeTargetMember.name}
            </div>
            <p className="library-review-notice">
              {t("features.browseV2.amendment.noDeleteNotice")}
            </p>
            <div className="library-inbox-modal-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={onDismissRemoveMemberModal}
                disabled={amending}
              >
                {t("features.library.inbox.cancel")}
              </button>
              <button
                className="primary-button"
                type="button"
                disabled={amending}
                onClick={onConfirmRemoveMember}
              >
                {amending ? "…" : t("features.browseV2.amendment.createPlan")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
