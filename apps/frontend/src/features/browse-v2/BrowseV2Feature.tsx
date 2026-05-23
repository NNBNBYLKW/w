import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import { listBrowseCards, type BrowseV2Card, type BrowseV2LooseFileCard, type BrowseV2ObjectCard } from "../../services/api/browseV2Api";
import { composeExternalFiles, composeInboxItems } from "../../services/api/importingApi";
import { createManagedComposePlan, createObjectAmendmentPlan } from "../../services/api/libraryOrganizeApi";
import { listLibraryRoots, type LibraryRootVM } from "../../services/api/libraryObjectsApi";
import { t } from "../../shared/text";
import { type DomainValue } from "../../shared/browse-taxonomy";
import { InspectorSection, MetricStrip, WorkbenchFilterPanel, WorkbenchMasthead, WorkbenchPage, WorkbenchResultFrame, WorkbenchToolbar } from "../../shared/ui/components";
import { ComposeObjectModal } from "./ComposeObjectModal";
import { LooseFileCard } from "./LooseFileCard";
import { ObjectCard } from "./ObjectCard";
import { asTextKey, objectTypeLabel, objectSourceLabel, storageStateLabel, fileKindLabel, memberRoleLabel, confidenceLabel, formatBytes, getCategoryLabel } from "./helpers";
import { useBrowseV2SearchParams } from "./hooks/useBrowseV2SearchParams";
import { useBrowseV2Cards } from "./hooks/useBrowseV2Cards";
import { useBrowseV2ObjectDetail } from "./hooks/useBrowseV2ObjectDetail";


const PAGE_SIZE = 50;

type CategoryItem = { value: string; labelKey: string };

function isObjectCard(card: BrowseV2Card): card is BrowseV2ObjectCard {
  return card.card_kind === "object";
}

function isLooseFileCard(card: BrowseV2Card): card is BrowseV2LooseFileCard {
  return card.card_kind === "loose_file";
}

export function BrowseV2Feature() {
  const { domain, category, storageState, cardKind, page, setPage, setScope, updateFilter } = useBrowseV2SearchParams();
  const cards = useBrowseV2Cards({ domain, category, storage_state: storageState, card_kind: cardKind, page });
  const navigate = useNavigate();
  const [selectedObject, setSelectedObject] = useState<BrowseV2ObjectCard | null>(null);
  const detail = useBrowseV2ObjectDetail(selectedObject);
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);

  const objectCards = cards.items.filter(isObjectCard);
  const looseFileCards = cards.items.filter(isLooseFileCard);
  const showObjects = cardKind !== "loose_file";
  const showLooseFiles = cardKind !== "object";
  const activeScope = getCategoryLabel(domain, category);

  // Phase 8C-2: Compose selection
  const [selectedFileIds, setSelectedFileIds] = useState<Set<number>>(new Set());
  const [showComposeModal, setShowComposeModal] = useState(false);
  const [composing, setComposing] = useState(false);
  const [composeError, setComposeError] = useState<string | null>(null);
  const [composeSuccess, setComposeSuccess] = useState<string | null>(null);

  // Phase 8D-D: Amendment state
  const [showAddMembersModal, setShowAddMembersModal] = useState(false);
  const [showRemoveMemberModal, setShowRemoveMemberModal] = useState(false);
  const [removeTargetMember, setRemoveTargetMember] = useState<{member_id: number; name: string} | null>(null);
  const [amending, setAmending] = useState(false);
  const [amendmentError, setAmendmentError] = useState<string | null>(null);
  const [amendmentSuccess, setAmendmentSuccess] = useState<string | null>(null);

  const { data: looseCandidates } = useQuery({
    queryKey: ["browse-v2-loose-candidates"],
    queryFn: () => listBrowseCards({ storage_state: "managed", card_kind: "loose_file", page_size: 50 }),
    enabled: showAddMembersModal,
  });
  const [selectedAddFileIds, setSelectedAddFileIds] = useState<Set<number>>(new Set());

  async function handleAddMembersConfirm() {
    if (!selectedObject || selectedAddFileIds.size === 0) return;
    setAmending(true); setAmendmentError(null); setAmendmentSuccess(null);
    try {
      const result = await createObjectAmendmentPlan(selectedObject.source_id, {
        add_file_ids: [...selectedAddFileIds], remove_member_ids: [],
        target_library_root_id: detail.detail.objectDetail?.managed_root_id ?? undefined,
        remove_target_policy: "managed_loose_area",
      });
      setAmendmentSuccess(t("features.browseV2.amendment.addPlanCreated", { planId: String(result.plan_id) }));
      setShowAddMembersModal(false); setSelectedAddFileIds(new Set());
    } catch (err) { setAmendmentError(String(err)); }
    finally { setAmending(false); }
  }

  async function handleRemoveMemberConfirm() {
    if (!selectedObject || !removeTargetMember || !detail.objectDetail) return;
    setAmending(true); setAmendmentError(null); setAmendmentSuccess(null);
    try {
      const result = await createObjectAmendmentPlan(selectedObject.source_id, {
        add_file_ids: [], remove_member_ids: [removeTargetMember.member_id],
        target_library_root_id: detail.detail.objectDetail.managed_root_id ?? undefined,
        remove_target_policy: "managed_loose_area",
      });
      setAmendmentSuccess(t("features.browseV2.amendment.removePlanCreated", { planId: String(result.plan_id) }));
      setShowRemoveMemberModal(false); setRemoveTargetMember(null);
    } catch (err) { setAmendmentError(String(err)); }
    finally { setAmending(false); }
  }

  const { data: roots } = useQuery({
    queryKey: ["library-roots"], queryFn: listLibraryRoots, staleTime: 60_000,
  });
  const queryClient = useQueryClient();

  function handleCardClick(card: BrowseV2Card) {
    if (isLooseFileCard(card)) {
      setSelectedObject(null);
      selectItem(String(card.file_id));
      return;
    }

    selectItem(null);
    setSelectedObject(card);
  }

  function handleCheckboxToggle(card: BrowseV2LooseFileCard) {
    setSelectedFileIds(prev => {
      const next = new Set(prev);
      if (next.has(card.file_id)) {
        next.delete(card.file_id);
      } else {
        const existingSS = prev.size > 0
          ? (looseFileCards.find(f => prev.has(f.file_id))?.storage_state ?? null)
          : null;
        if (existingSS && existingSS !== card.storage_state) {
          next.clear();
        }
        next.add(card.file_id);
      }
      return next;
    });
  }

  function clearSelection() {
    setSelectedFileIds(new Set());
  }

  const selectedFiles: BrowseV2LooseFileCard[] = looseFileCards.filter(
    f => selectedFileIds.has(f.file_id) && (f.storage_state === "inbox" || f.storage_state === "external" || f.storage_state === "managed")
  );
  const selectionSS = selectedFiles.length > 0 ? selectedFiles[0].storage_state : null;

  async function handleComposeConfirm(params: {
    inbox_item_ids?: number[];
    file_ids?: number[];
    object_name: string;
    suggested_object_type?: string;
    target_library_root_id?: number;
  }) {
    setComposing(true); setComposeError(null); setComposeSuccess(null);
    try {
      if (selectionSS === "inbox" && params.inbox_item_ids) {
        await composeInboxItems({
          inbox_item_ids: params.inbox_item_ids,
          object_name: params.object_name,
          suggested_object_type: params.suggested_object_type,
          target_library_root_id: params.target_library_root_id,
        });
      } else if (selectionSS === "external" && params.file_ids) {
        await composeExternalFiles({
          file_ids: params.file_ids,
          object_name: params.object_name,
          suggested_object_type: params.suggested_object_type,
          target_library_root_id: params.target_library_root_id,
        });
      } else if (selectionSS === "managed" && params.file_ids) {
        await createManagedComposePlan({
          file_ids: params.file_ids,
          object_name: params.object_name,
          object_type: params.suggested_object_type || "imgset",
          target_library_root_id: params.target_library_root_id,
        });
      }
      setShowComposeModal(false);
      clearSelection();
      await queryClient.invalidateQueries({ queryKey: ["browse-v2"] });
      if (selectionSS === "managed") {
        setComposeSuccess(t("features.browseV2.compose.planCreated"));
      } else {
        setComposeSuccess(t("features.browseV2.compose.success"));
      }
    } catch (err) {
      setComposeError(String(err));
    } finally { setComposing(false); }
  }

  // Helper to clear selection on nav change
  useEffect(() => {
    clearSelection();
  }, [domain, category, storageState, cardKind, page]);

  return (
    <WorkbenchPage className="browse-v2-page browse-surface browse-surface--browse-v2" variant="browse-v2">
      <WorkbenchMasthead
        eyebrow={t("features.browseV2.title")}
        title={activeScope}
        description={t("features.browseV2.subtitle")}
        meta={<span>{t("features.browseV2.sections.readModelNote")}</span>}
      />

      <MetricStrip
        className="browse-v2-metrics"
        items={[
          { label: t("features.browseV2.metrics.objects"), value: String(data?.summary.total_objects ?? 0), tone: "primary" },
          { label: t("features.browseV2.metrics.looseFiles"), value: String(data?.summary.total_loose_files ?? 0), tone: "info" },
          { label: t("features.browseV2.metrics.managed"), value: String(data?.summary.managed_objects ?? 0), tone: "success" },
          { label: t("features.browseV2.metrics.inbox"), value: String(data?.summary.inbox_objects ?? 0), tone: "warning" },
          { label: t("features.browseV2.metrics.externalLoose"), value: String(data?.summary.external_loose ?? 0) },
        ]}
      />

      <div className="browse-v2-layout">
        <main className="browse-v2-main" aria-live="polite">
          <div className="browse-v2-breadcrumb" aria-label={t("features.browseV2.taxonomyLabel")}>
            <span className="browse-v2-breadcrumb__item">{t("navigation.items.fileLibrary")}</span>
            <span className="browse-v2-breadcrumb__sep" aria-hidden="true">›</span>
            <span className="browse-v2-breadcrumb__item">{t(asTextKey(DOMAINS.find(d => d.value === domain)?.labelKey ?? ""))}</span>
            {category ? (
              <>
                <span className="browse-v2-breadcrumb__sep" aria-hidden="true">›</span>
                <span className="browse-v2-breadcrumb__item browse-v2-breadcrumb__item--current">{getCategoryLabel(domain, category)}</span>
              </>
            ) : null}
          </div>
          <WorkbenchFilterPanel className="browse-v2-filter-panel" label={t("features.browseV2.filters.title")}>
            <WorkbenchToolbar className="browse-v2-toolbar">
              <label className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.storageLabel")}</span>
                <select
                  className="select-input"
                  name="browse-v2-storage"
                  value={storageState}
                  onChange={(event) => updateFilter("storage", event.target.value)}
                >
                  <option value="all">{t("features.browseV2.filters.storageAll")}</option>
                  <option value="external">{t("features.browseV2.filters.external")}</option>
                  <option value="inbox">{t("features.browseV2.filters.inbox")}</option>
                  <option value="managed">{t("features.browseV2.filters.managed")}</option>
                </select>
              </label>
              <label className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.cardKindLabel")}</span>
                <select
                  className="select-input"
                  name="browse-v2-card-kind"
                  value={cardKind}
                  onChange={(event) => updateFilter("kind", event.target.value)}
                >
                  <option value="all">{t("features.browseV2.filters.cardKindAll")}</option>
                  <option value="object">{t("features.browseV2.filters.objectOnly")}</option>
                  <option value="loose_file">{t("features.browseV2.filters.fileOnly")}</option>
                </select>
              </label>
              <div className="browse-v2-toolbar__scope" aria-label={t("features.browseV2.sections.currentScope")}>
                <span>{t("features.browseV2.sections.currentScope")}</span>
                <strong>{activeScope}</strong>
              </div>
            </WorkbenchToolbar>
          </WorkbenchFilterPanel>

          {/* Phase 8C-2: Selection bar */}
          {selectedFileIds.size > 0 && (
            <div className="browse-v2-selection-bar" style={{display:"flex",alignItems:"center",gap:8,padding:"8px 12px",background:"#f0f4ff",borderRadius:4,marginBottom:4}}>
              <span style={{fontSize:13}}>
                {selectionSS === "inbox"
                  ? t("features.browseV2.compose.selectedInbox", { count: String(selectedFileIds.size) })
                  : selectionSS === "managed"
                  ? t("features.browseV2.compose.selectedManaged", { count: String(selectedFileIds.size) })
                  : t("features.browseV2.compose.selectedExternal", { count: String(selectedFileIds.size) })}
              </span>
              <button className="primary-button" type="button" disabled={composing} onClick={() => setShowComposeModal(true)}>
                {t("features.browseV2.compose.action")}
              </button>
              <button className="secondary-button" type="button" disabled={composing} onClick={clearSelection}>
                {t("features.browseV2.compose.clear")}
              </button>
            </div>
          )}

          <WorkbenchResultFrame
            className="browse-v2-result-frame"
            title={t("features.browseV2.sections.results")}
            meta={data ? t("features.browseV2.sections.resultMeta", {
              count: String(data.total),
              page: String(page),
              total: String(totalPages),
            }) : t("common.states.loading")}
          >
            {isLoading ? (
              <div className="browse-v2-state" role="status">
                {t("common.states.loading")}
              </div>
            ) : null}
            {isError ? (
              <div className="browse-v2-state browse-v2-state--error" role="alert">
                {t("features.browseV2.errors.loadFailed")}: {String(error)}
              </div>
            ) : null}
            {data && items.length === 0 ? (
              <div className="browse-v2-state browse-v2-state--empty">
                {t("features.browseV2.empty")}
              </div>
            ) : null}
            {data && items.length > 0 ? (
              <div className="browse-v2-result-sections">
                {showObjects ? (
                  <section className="browse-v2-result-section">
                    <header className="browse-v2-result-section__header">
                      <div>
                        <span className="workbench-eyebrow">{t("features.browseV2.badges.object")}</span>
                        <h4>{t("features.browseV2.sections.objects")}</h4>
                      </div>
                      <span>{t("features.browseV2.sections.currentPageCount", { count: String(objectCards.length) })}</span>
                    </header>
                    {objectCards.length > 0 ? (
                      <div className="browse-v2-card-grid browse-v2-card-grid--objects">
                        {objectCards.map((card) => (
                          <ObjectCard
                            key={card.namespaced_id}
                            card={card}
                            selected={selectedObject?.namespaced_id === card.namespaced_id}
                            onClick={() => handleCardClick(card)}
                          />
                        ))}
                      </div>
                    ) : (
                      <p className="browse-v2-result-section__empty">{t("features.browseV2.sections.noObjectsOnPage")}</p>
                    )}
                  </section>
                ) : null}
                {showLooseFiles ? (
                  <section className="browse-v2-result-section">
                    <header className="browse-v2-result-section__header">
                      <div>
                        <span className="workbench-eyebrow">{t("features.browseV2.badges.file")}</span>
                        <h4>{t("features.browseV2.sections.looseFiles")}</h4>
                      </div>
                      <span>{t("features.browseV2.sections.currentPageCount", { count: String(looseFileCards.length) })}</span>
                    </header>
                    {looseFileCards.length > 0 ? (
                      <div className="browse-v2-file-list">
                        {looseFileCards.map((card) => (
                          <LooseFileCard
                            key={`f${card.file_id}`}
                            card={card}
                            selected={selectedItemId === String(card.file_id)}
                            checked={selectedFileIds.has(card.file_id)}
                            onCheckboxToggle={
                              card.storage_state === "inbox" || card.storage_state === "external" || card.storage_state === "managed"
                                ? () => handleCheckboxToggle(card)
                                : undefined
                            }
                            onClick={() => handleCardClick(card)}
                          />
                        ))}
                      </div>
                    ) : (
                      <p className="browse-v2-result-section__empty">{t("features.browseV2.sections.noLooseFilesOnPage")}</p>
                    )}
                  </section>
                ) : null}
              </div>
            ) : null}
          </WorkbenchResultFrame>

          {data && data.total > PAGE_SIZE ? (
            <div className="files-pager browse-v2-pager">
              <button className="secondary-button" type="button" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
                {t("features.browseV2.pagination.previous")}
              </button>
              <span>{t("features.browseV2.pagination.pageInfo", { page: String(page), total: String(totalPages) })}</span>
              <button className="secondary-button" type="button" disabled={page * PAGE_SIZE >= data.total} onClick={() => setPage((current) => current + 1)}>
                {t("features.browseV2.pagination.next")}
              </button>
            </div>
          ) : null}
        </main>

        <aside className={`browse-v2-detail${selectedObject ? " browse-v2-detail--active" : ""}`} aria-label={t("features.browseV2.overview.title")}>
          {!selectedObject ? (
            <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
              <p className="browse-v2-detail__empty">{t("features.browseV2.noSelection")}</p>
            </InspectorSection>
          ) : null}
          {selectedObject && detail.objectDetailLoading ? (
            <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
              <p className="browse-v2-detail__empty">{t("common.states.loading")}</p>
            </InspectorSection>
          ) : null}
          {selectedObject && detail.objectDetailError ? (
            <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
              <p className="danger-text">{t("features.browseV2.errors.detailFailed")}</p>
            </InspectorSection>
          ) : null}
          {selectedObject && detail.objectDetail? (
            <>
              <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
                <div className="browse-v2-detail__identity">
                  <span className="status-badge status-badge--accent">{objectTypeLabel(detail.objectDetail.object_type)}</span>
                  <h4>{detail.objectDetail.display_title}</h4>
                  <p>{objectSourceLabel(detail.objectDetail.object_source)}</p>
                </div>
                <div className="browse-v2-detail__facts">
                  <div className="key-value-row">
                    <span className="key-value-row__label">{t("features.browseV2.overview.status")}</span>
                    <span className="key-value-row__value">{storageStateLabel(detail.objectDetail.storage_state)}{detail.objectDetail.needs_review ? ` / ${t("features.browseV2.needsReview")}` : ""}</span>
                  </div>
                  <div className="key-value-row">
                    <span className="key-value-row__label">{t("features.browseV2.overview.members", { count: String(detail.objectDetail.member_total) })}</span>
                    <span className="key-value-row__value">{detail.objectDetail.member_total}</span>
                  </div>
                  {detail.objectDetail.confidence ? (
                    <div className="key-value-row">
                      <span className="key-value-row__label">{t("features.browseV2.overview.confidence")}</span>
                      <span className="key-value-row__value">{confidenceLabel(detail.objectDetail.confidence)}</span>
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
                    <button className="primary-button" type="button" style={{marginTop:8}} onClick={() => setShowAddMembersModal(true)}>
                      {t("features.browseV2.amendment.addMembers")}
                    </button>
                  )}
                </div>
              </InspectorSection>

              {amendmentError && (
                <div className="danger-text" style={{padding:8}} role="alert">
                  {t("features.browseV2.amendment.failed")}: {amendmentError}
                  <button className="secondary-button" type="button" style={{marginLeft:8}} onClick={() => setAmendmentError(null)}>{t("features.library.inbox.cancel")}</button>
                </div>
              )}
              {amendmentSuccess && (
                <div style={{padding:8,background:"#e8f5e9",borderRadius:4}} role="status">
                  {amendmentSuccess}
                  <p style={{fontSize:12,marginTop:4}}>{t("features.browseV2.amendment.filesHaveNotMoved")} / {t("features.browseV2.amendment.preflightExecuteRequired")}</p>
                  <div style={{display:"flex",gap:8,marginTop:4}}>
                    <button className="primary-button" type="button" onClick={() => { setAmendmentSuccess(null); navigate("/library?tab=plans"); }}>
                      {t("features.browseV2.amendment.goToPlans")}
                    </button>
                    <button className="secondary-button" type="button" onClick={() => setAmendmentSuccess(null)}>{t("features.library.inbox.cancel")}</button>
                  </div>
                </div>
              )}

              <InspectorSection className="browse-v2-detail__section" title={`${t("features.browseV2.overview.membersTitle")} (${detail.objectDetail.member_total})`}>
                {detail.objectDetail.members.length === 0 ? (
                  <p className="browse-v2-detail__empty">{t("features.browseV2.overview.noMembers")}</p>
                ) : (
                  <div className="browse-v2-member-list">
                    {detail.objectDetail.members.map((member) => (
                      <div key={member.member_id} className="browse-v2-member-row" title={member.path || ""}>
                        <span className="browse-v2-member-row__name">{member.name || `#${member.file_id || member.member_id}`}</span>
                        <span className="browse-v2-member-row__meta">
                          <span className="status-badge status-badge--muted">{memberRoleLabel(member.role)}</span>
                          {member.file_kind ? <span className="status-badge status-badge--info">{fileKindLabel(member.file_kind)}</span> : null}
                          {member.storage_state ? <span className="status-badge status-badge--secondary">{storageStateLabel(member.storage_state)}</span> : null}
                          {member.missing ? <span className="status-badge status-badge--danger">{t("features.browseV2.overview.missing")}</span> : null}
                          {member.size_bytes !== null ? <span className="browse-v2-member-row__size">{formatBytes(member.size_bytes)}</span> : null}
                        </span>
                        {detail.objectDetail.object_source === "library_object" && (
                          <button
                            className="secondary-button"
                            type="button"
                            style={{fontSize:11,marginLeft:"auto"}}
                            onClick={(e) => { e.stopPropagation(); setRemoveTargetMember({member_id: member.member_id, name: member.name || `#${member.member_id}`}); setShowRemoveMemberModal(true); }}
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
                    <button className="secondary-button" type="button" disabled={detail.objectDetail.member_page <= 1} onClick={() => detail.setMemberPage((current) => current - 1)}>
                      {t("features.browseV2.pagination.previous")}
                    </button>
                    <span>
                      {t("features.browseV2.pagination.pageInfo", {
                        page: String(detail.objectDetail.member_page),
                        total: String(Math.ceil(detail.objectDetail.member_total / detail.objectDetail.member_page_size)),
                      })}
                    </span>
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={detail.objectDetail.member_page * detail.objectDetail.member_page_size >= detail.objectDetail.member_total}
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
      </div>

      {showComposeModal && (
        <ComposeObjectModal
          selectedFiles={selectedFiles}
          roots={(roots as LibraryRootVM[]) ?? []}
          selectionSS={selectionSS ?? ""}
          busy={composing}
          onCancel={() => { setShowComposeModal(false); setComposeError(null); }}
          onConfirm={handleComposeConfirm}
        />
      )}

      {composeError && (
        <div className="danger-text" style={{padding:8}} role="alert">
          {t("features.browseV2.compose.error")}: {composeError}
          <button className="secondary-button" type="button" style={{marginLeft:8}} onClick={() => setComposeError(null)}>
            {t("features.library.inbox.cancel")}
          </button>
        </div>
      )}
      {composeSuccess && (
        <div style={{padding:8,background:"#e8f5e9",borderRadius:4}} role="status">
          {composeSuccess}
          <p style={{fontSize:12,marginTop:4}}>{t("features.browseV2.amendment.filesHaveNotMoved")} / {t("features.browseV2.amendment.preflightExecuteRequired")}</p>
          <div style={{display:"flex",gap:8,marginTop:4}}>
            <button className="primary-button" type="button" onClick={() => { setComposeSuccess(null); navigate("/library?tab=plans"); }}>
              {t("features.browseV2.amendment.goToPlans")}
            </button>
            <button className="secondary-button" type="button" onClick={() => setComposeSuccess(null)}>
              {t("features.library.inbox.cancel")}
            </button>
          </div>
        </div>
      )}

      {/* Phase 8D-D: Add Members Modal */}
      {showAddMembersModal && (
        <div className="library-inbox-modal-overlay" onClick={amending ? undefined : () => { setShowAddMembersModal(false); setSelectedAddFileIds(new Set()); }}>
          <div className="library-inbox-modal" role="dialog" onClick={e => e.stopPropagation()} style={{maxWidth:520}}>
            <h3>{t("features.browseV2.amendment.addMembersTitle")}</h3>
            <p className="library-inbox-modal-hint">{t("features.browseV2.amendment.addMembersDescription")}</p>
            <div style={{maxHeight:200,overflowY:"auto",margin:"8px 0",border:"1px solid #e0e0e0",borderRadius:4,padding:4}}>
              {looseCandidates?.items.filter(c => c.card_kind === "loose_file").length === 0 && (
                <p style={{fontSize:12}}>{t("features.browseV2.amendment.noManagedLooseCandidates")}</p>
              )}
              {looseCandidates?.items.filter(c => c.card_kind === "loose_file").map((card: any) => (
                <label key={card.file_id} style={{display:"flex",alignItems:"center",gap:4,padding:"2px 4px",cursor:"pointer",fontSize:12}}>
                  <input type="checkbox" checked={selectedAddFileIds.has(card.file_id)} onChange={() => {
                    setSelectedAddFileIds(prev => { const n = new Set(prev); if (n.has(card.file_id)) n.delete(card.file_id); else n.add(card.file_id); return n; });
                  }} disabled={amending} />
                  <span style={{overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}} title={card.path}>{card.name}</span>
                </label>
              ))}
            </div>
            <p className="library-review-notice">{t("features.browseV2.amendment.draftPlanOnlyNotice")}</p>
            <div className="library-inbox-modal-actions">
              <button className="secondary-button" type="button" onClick={() => { setShowAddMembersModal(false); setSelectedAddFileIds(new Set()); }} disabled={amending}>{t("features.library.inbox.cancel")}</button>
              <button className="primary-button" type="button" disabled={selectedAddFileIds.size === 0 || amending} onClick={handleAddMembersConfirm}>
                {amending ? "…" : t("features.browseV2.amendment.createPlan")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Phase 8D-D: Remove Member Modal */}
      {showRemoveMemberModal && removeTargetMember && (
        <div className="library-inbox-modal-overlay" onClick={amending ? undefined : () => { setShowRemoveMemberModal(false); setRemoveTargetMember(null); }}>
          <div className="library-inbox-modal" role="dialog" onClick={e => e.stopPropagation()} style={{maxWidth:420}}>
            <h3>{t("features.browseV2.amendment.removeMemberTitle")}</h3>
            <p className="library-inbox-modal-hint">{t("features.browseV2.amendment.removeMemberDescription")}</p>
            <div style={{padding:8,margin:"8px 0",background:"#fafafa",borderRadius:4}}>
              <strong>{t("features.browseV2.overview.name")}:</strong> {removeTargetMember.name}
            </div>
            <p className="library-review-notice">{t("features.browseV2.amendment.noDeleteNotice")}</p>
            <div className="library-inbox-modal-actions">
              <button className="secondary-button" type="button" onClick={() => { setShowRemoveMemberModal(false); setRemoveTargetMember(null); }} disabled={amending}>{t("features.library.inbox.cancel")}</button>
              <button className="primary-button" type="button" disabled={amending} onClick={handleRemoveMemberConfirm}>
                {amending ? "…" : t("features.browseV2.amendment.createPlan")}
              </button>
            </div>
          </div>
        </div>
      )}
    </WorkbenchPage>
  );
}
