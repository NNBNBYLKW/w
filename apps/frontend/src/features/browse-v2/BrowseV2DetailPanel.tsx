import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";

import type { BrowseV2ObjectCard, ObjectDetailResponse } from "../../services/api/browseV2Api";
import { t } from "../../shared/text";
import { CardSkeleton, InspectorSection } from "../../shared/ui/components";
import { EmptyState } from "../../shared/ui/components/EmptyState";
import {
  confidenceLabel,
  fileKindLabel,
  formatBytes,
  memberRoleLabel,
  objectSourceLabel,
  objectTypeLabel,
  storageStateLabel,
} from "./helpers";

export interface BrowseV2DetailPanelProps {
  selectedObject: BrowseV2ObjectCard | null;
  detail: {
    objectDetail: ObjectDetailResponse | null | undefined;
    objectDetailLoading: boolean;
    objectDetailError: boolean;
    setMemberPage: (fn: (current: number) => number) => void;
  };
  amendmentError: string | null;
  amendmentSuccess: string | null;
  executingPlanId: number | null;
  onClearAmendmentError: () => void;
  onExecuteOrNavigateAfterAmendment: () => void;
  onDismissAmendmentSuccess: () => void;
  onAddMembersRequest: () => void;
  onRemoveMemberRequest: (memberId: number, name: string) => void;
}

function EditableTitle({ value, onSave }: { value: string; onSave: (v: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  const handleSave = useCallback(() => {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== value) {
      onSave(trimmed);
    } else {
      setDraft(value);
    }
    setEditing(false);
  }, [draft, value, onSave]);

  if (editing) {
    return (
      <input
        ref={inputRef}
        className="text-input"
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={handleSave}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSave();
          if (e.key === "Escape") { setDraft(value); setEditing(false); }
        }}
        style={{ fontSize: 16, fontWeight: 700, width: "100%" }}
      />
    );
  }

  return (
    <h4
      onDoubleClick={() => setEditing(true)}
      style={{ cursor: "pointer" }}
      title={t("features.browseV2.overview.doubleClickToEdit")}
    >
      {value}
    </h4>
  );
}

export function BrowseV2DetailPanel({
  selectedObject,
  detail,
  amendmentError,
  amendmentSuccess,
  executingPlanId,
  onClearAmendmentError,
  onExecuteOrNavigateAfterAmendment,
  onDismissAmendmentSuccess,
  onAddMembersRequest,
  onRemoveMemberRequest,
}: BrowseV2DetailPanelProps) {
  const navigate = useNavigate();
  const [editingTitle, setEditingTitle] = useState(false);

  const handleTitleSave = useCallback((newTitle: string) => {
    // B12: Auto-save on blur would call an API; for now update local state
    setEditingTitle(false);
  }, []);

  return (
    <aside
      className={`browse-v2-detail${selectedObject ? " browse-v2-detail--active" : ""}`}
      aria-label={t("features.browseV2.overview.title")}
    >
      {!selectedObject ? (
        <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
          <EmptyState title={t("features.browseV2.noSelection")}
            action={{ label: t("features.homeOverview.scanCardAction"), onClick: () => navigate("/library?tab=sources") }} />
        </InspectorSection>
      ) : null}
      {selectedObject && detail.objectDetailLoading ? (
        <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
          <CardSkeleton count={3} variant="row" />
        </InspectorSection>
      ) : null}
      {selectedObject && detail.objectDetailError ? (
        <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
          <p className="danger-text">{t("features.browseV2.errors.detailFailed")}</p>
          <button className="secondary-button" type="button" onClick={() => detail.setMemberPage((c) => c)} style={{ marginTop: 8 }}>
            {t("common.states.retry")}
          </button>
        </InspectorSection>
      ) : null}
      {selectedObject && detail.objectDetail ? (
        <>
          <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
            <div className="browse-v2-detail__identity">
              <span className="status-badge status-badge--accent">{objectTypeLabel(detail.objectDetail.object_type)}</span>
              <EditableTitle value={detail.objectDetail.display_title} onSave={handleTitleSave} />
              <p>{objectSourceLabel(detail.objectDetail.object_source)}</p>
            </div>

            {/* B11: Warnings banner */}
            {detail.objectDetail.warnings && detail.objectDetail.warnings.length > 0 ? (
              <div className="browse-v2-inline-alert browse-v2-inline-alert--warning" role="alert">
                {detail.objectDetail.warnings.map((w, i) => <p key={i} style={{ margin: "2px 0" }}>{w}</p>)}
              </div>
            ) : null}

            <div className="browse-v2-detail__facts">
              <div className="key-value-row">
                <span className="key-value-row__label">{t("features.browseV2.overview.status")}</span>
                <span className="key-value-row__value">
                  {storageStateLabel(detail.objectDetail.storage_state)}
                  {detail.objectDetail.needs_review ? ` / ${t("features.browseV2.needsReview")}` : ""}
                </span>
              </div>
              <div className="key-value-row">
                <span className="key-value-row__label">
                  {t("features.browseV2.overview.members", { count: String(detail.objectDetail.member_total) })}
                </span>
                <span className="key-value-row__value">{detail.objectDetail.member_total}</span>
              </div>
              {detail.objectDetail.confidence ? (
                <div className="key-value-row">
                  <span className="key-value-row__label">{t("features.browseV2.overview.confidence")}</span>
                  <span className="key-value-row__value">{confidenceLabel(detail.objectDetail.confidence)}</span>
                </div>
              ) : null}
              {detail.objectDetail.object_type ? (
                <div className="key-value-row">
                  <span className="key-value-row__label">{t("features.browseV2.overview.type")}</span>
                  <span className="key-value-row__value">{objectTypeLabel(detail.objectDetail.object_type)}</span>
                </div>
              ) : null}
              {detail.objectDetail.status ? (
                <div className="key-value-row">
                  <span className="key-value-row__label">{t("features.browseV2.overview.status")}</span>
                  <span className="key-value-row__value">{detail.objectDetail.status}</span>
                </div>
              ) : null}
              {detail.objectDetail.root_path ? (
                <div className="key-value-row">
                  <span className="key-value-row__label">{t("features.browseV2.overview.rootPath")}</span>
                  <span className="key-value-row__value browse-v2-detail__path" title={detail.objectDetail.root_path}>
                    {detail.objectDetail.root_path.replace(/\\/g, "/").split("/").slice(-2).join("/")}
                  </span>
                </div>
              ) : null}
              {detail.objectDetail.object_source === "library_object" && (
                <button
                  className="primary-button browse-v2-detail__action"
                  type="button"
                  onClick={onAddMembersRequest}
                >
                  {t("features.browseV2.amendment.addMembers")}
                </button>
              )}
            </div>
          </InspectorSection>

          {amendmentError && (
            <div className="browse-v2-inline-alert browse-v2-inline-alert--danger" role="alert">
              {t("features.browseV2.amendment.failed")}: {amendmentError}
              <button className="secondary-button" type="button" onClick={onClearAmendmentError}>
                {t("features.library.inbox.cancel")}
              </button>
            </div>
          )}
          {amendmentSuccess && (
            <div className="browse-v2-inline-alert browse-v2-inline-alert--success" role="status">
              {amendmentSuccess}
              <p>
                {t("features.browseV2.amendment.filesHaveNotMoved")} /{" "}
                {t("features.browseV2.amendment.preflightExecuteRequired")}
              </p>
              <div className="browse-v2-inline-alert__actions">
                <button className="primary-button" type="button" onClick={onExecuteOrNavigateAfterAmendment}>
                  {executingPlanId
                    ? "Review & Execute"
                    : t("features.browseV2.amendment.goToPlans")}
                </button>
                <button className="secondary-button" type="button" onClick={onDismissAmendmentSuccess}>
                  {t("features.library.inbox.cancel")}
                </button>
              </div>
            </div>
          )}

          <InspectorSection
            className="browse-v2-detail__section"
            title={`${t("features.browseV2.overview.membersTitle")} (${detail.objectDetail.member_total})`}
          >
            {detail.objectDetail.members.length === 0 ? (
              <p className="browse-v2-detail__empty">{t("features.browseV2.overview.noMembers")}</p>
            ) : (
              <div className="browse-v2-member-list">
                {detail.objectDetail.members.map((member) => (
                  <div key={member.member_id} className="browse-v2-member-row" title={member.path || ""}>
                    <span className="browse-v2-member-row__name">
                      {member.name || `#${member.file_id || member.member_id}`}
                    </span>
                    <span className="browse-v2-member-row__meta">
                      <span className="status-badge status-badge--muted">{memberRoleLabel(member.role)}</span>
                      {member.file_kind ? (
                        <span className="status-badge status-badge--info">{fileKindLabel(member.file_kind)}</span>
                      ) : null}
                      {member.storage_state ? (
                        <span className="status-badge status-badge--secondary">
                          {storageStateLabel(member.storage_state)}
                        </span>
                      ) : null}
                      {member.missing ? (
                        <span className="status-badge status-badge--danger">
                          {t("features.browseV2.overview.missing")}
                        </span>
                      ) : null}
                      {member.size_bytes !== null ? (
                        <span className="browse-v2-member-row__size">{formatBytes(member.size_bytes)}</span>
                      ) : null}
                    </span>
                    {detail.objectDetail?.object_source === "library_object" && (
                      <button
                        className="secondary-button"
                        type="button"
                        data-density="compact"
                        onClick={(e) => {
                          e.stopPropagation();
                          onRemoveMemberRequest(
                            member.member_id,
                            member.name || `#${member.member_id}`,
                          );
                        }}
                      >
                        {t("features.browseV2.amendment.removeFromObject")}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
            {detail.objectDetail.member_total > detail.objectDetail.member_page_size ? (
              <div className="browse-v2-member-pager">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={detail.objectDetail.member_page <= 1}
                  onClick={() => detail.setMemberPage((current) => current - 1)}
                >
                  {t("features.browseV2.pagination.previous")}
                </button>
                <span>
                  {t("features.browseV2.pagination.pageInfo", {
                    page: String(detail.objectDetail.member_page),
                    total: String(
                      Math.ceil(detail.objectDetail.member_total / detail.objectDetail.member_page_size),
                    ),
                  })}
                </span>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={
                    detail.objectDetail.member_page * detail.objectDetail.member_page_size >=
                    detail.objectDetail.member_total
                  }
                  onClick={() => detail.setMemberPage((current) => current + 1)}
                >
                  {t("features.browseV2.pagination.next")}
                </button>
              </div>
            ) : null}
          </InspectorSection>

          <p className="browse-v2-detail__notice">{t("features.browseV2.overview.readOnlyNotice")}</p>
        </>
      ) : null}
    </aside>
  );
}
