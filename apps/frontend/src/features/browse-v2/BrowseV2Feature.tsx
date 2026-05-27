import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import { listBrowseCards, type BrowseV2Card, type BrowseV2LooseFileCard, type BrowseV2ObjectCard } from "../../services/api/browseV2Api";
import { composeExternalFiles, composeInboxItems } from "../../services/api/importingApi";
import { createManagedComposePlan, createObjectAmendmentPlan } from "../../services/api/libraryOrganizeApi";
import { listLibraryRoots } from "../../services/api/libraryObjectsApi";
import type { LibraryRootVM } from "../../entities/library/types";
import { t } from "../../shared/text";
import { DOMAINS } from "../../shared/browse-taxonomy";
import { InspectorSection, MetricStrip, Pagination, WorkbenchFilterPanel, WorkbenchMasthead, WorkbenchPage, WorkbenchResultFrame, WorkbenchToolbar } from "../../shared/ui/components";
import { LoadingState } from "../../shared/ui/components/LoadingState";
import { EmptyState } from "../../shared/ui/components/EmptyState";
import { ComposeObjectModal } from "./ComposeObjectModal";
import { LooseFileCard } from "./LooseFileCard";
import { ObjectCard } from "./ObjectCard";
import { asTextKey, objectTypeLabel, objectSourceLabel, storageStateLabel, fileKindLabel, memberRoleLabel, confidenceLabel, formatBytes, getCategoryLabel } from "./helpers";
import { useBrowseV2SearchParams } from "./hooks/useBrowseV2SearchParams";
import { useBrowseV2Cards } from "./hooks/useBrowseV2Cards";
import { useBrowseV2ObjectDetail } from "./hooks/useBrowseV2ObjectDetail";
import { ExecutePlanPanel } from "./ExecutePlanPanel";
import { useVirtualList } from "../../shared/hooks/useVirtualList";


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
  const { data, error, isError, isLoading, items, totalPages } = cards;
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

  // Virtual list for card rendering
  const totalCardCount = objectCards.length + looseFileCards.length;
  const cardContainerRef = useRef<HTMLDivElement>(null);
  const { startIndex, endIndex, offsetY, totalHeight, onScroll } = useVirtualList(
    cardContainerRef,
    { itemHeight: 80, totalItems: totalCardCount },
  );
  const allCards = [...(showObjects ? objectCards : []), ...(showLooseFiles ? looseFileCards : [])];
  const visibleCards = allCards.slice(startIndex, endIndex);
  const visibleObjectCards = visibleCards.filter(isObjectCard);
  const visibleLooseFileCards = visibleCards.filter(isLooseFileCard);

  // Phase 8C-2: Compose selection
  const [selectedFileIds, setSelectedFileIds] = useState<Set<number>>(new Set());
  const [showComposeModal, setShowComposeModal] = useState(false);
  const [composing, setComposing] = useState(false);
  const [composeError, setComposeError] = useState<string | null>(null);
  const [composeSuccess, setComposeSuccess] = useState<string | null>(null);
  const [executingPlanId, setExecutingPlanId] = useState<number | null>(null);

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
        target_library_root_id: detail.objectDetail?.managed_root_id ?? undefined,
        remove_target_policy: "managed_loose_area",
      });
      setAmendmentSuccess(t("features.browseV2.amendment.addPlanCreated", { planId: String(result.plan_id) }));
      if (result.plan_id) setExecutingPlanId(result.plan_id);
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
        target_library_root_id: detail.objectDetail.managed_root_id ?? undefined,
        remove_target_policy: "managed_loose_area",
      });
      setAmendmentSuccess(t("features.browseV2.amendment.removePlanCreated", { planId: String(result.plan_id) }));
      if (result.plan_id) setExecutingPlanId(result.plan_id);
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
        const result = await createManagedComposePlan({
          file_ids: params.file_ids,
          object_name: params.object_name,
          object_type: params.suggested_object_type || "imgset",
          target_library_root_id: params.target_library_root_id,
        });
        if (result.plan_id) setExecutingPlanId(result.plan_id);
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
            <div className="browse-v2-selection-bar">
              <span className="browse-v2-selection-bar__label">
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

          {data ? (
            <MetricStrip
              className="browse-v2-summary-strip"
              items={[
                { label: t("features.browseV2.metrics.objects"), value: String(data.object_count ?? objectCards.length) },
                { label: t("features.browseV2.metrics.looseFiles"), value: String(data.loose_file_count ?? looseFileCards.length) },
                { label: t("features.browseV2.metrics.total"), value: String(data.total) },
              ]}
            />
          ) : null}

          <WorkbenchResultFrame
            className="browse-v2-result-frame"
            title={t("features.browseV2.sections.results")}
            meta={data ? t("features.browseV2.sections.resultMeta", {
              count: String(data.total),
              page: String(page),
              total: String(totalPages),
            }) : t("common.states.loading")}
          >
            {isLoading ? <LoadingState /> : null}
            {isError ? (
              <div className="browse-v2-state browse-v2-state--error" role="alert">
                {t("features.browseV2.errors.loadFailed")}: {String(error)}
              </div>
            ) : null}
            {data && items.length === 0 ? (
              <EmptyState title={t("features.browseV2.empty")} />
            ) : null}
            {data && items.length > 0 ? (
              <div ref={cardContainerRef} onScroll={onScroll} style={{ height: "100%", overflow: "auto" }}>
                <div style={{ height: totalHeight, position: "relative" }}>
                  <div style={{ position: "absolute", top: offsetY, width: "100%" }}>
                    <div className="browse-v2-result-sections">
                      {showObjects && (objectCards.length === 0 || visibleObjectCards.length > 0) ? (
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
                              {visibleObjectCards.map((card) => (
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
                      {showLooseFiles && (looseFileCards.length === 0 || visibleLooseFileCards.length > 0) ? (
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
                              {visibleLooseFileCards.map((card) => (
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
                  </div>
                </div>
              </div>
            ) : null}
          </WorkbenchResultFrame>

          {data && data.total > PAGE_SIZE ? (
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
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
                    <button className="primary-button browse-v2-detail__action" type="button" onClick={() => setShowAddMembersModal(true)}>
                      {t("features.browseV2.amendment.addMembers")}
                    </button>
                  )}
                </div>
              </InspectorSection>

              {amendmentError && (
                <div className="browse-v2-inline-alert browse-v2-inline-alert--danger" role="alert">
                  {t("features.browseV2.amendment.failed")}: {amendmentError}
                  <button className="secondary-button" type="button" onClick={() => setAmendmentError(null)}>{t("features.library.inbox.cancel")}</button>
                </div>
              )}
              {amendmentSuccess && (
                <div className="browse-v2-inline-alert browse-v2-inline-alert--success" role="status">
                  {amendmentSuccess}
                  <p>{t("features.browseV2.amendment.filesHaveNotMoved")} / {t("features.browseV2.amendment.preflightExecuteRequired")}</p>
                  <div className="browse-v2-inline-alert__actions">
                    <button
                      className="primary-button"
                      type="button"
                      onClick={() => {
                        const pid = executingPlanId;
                        setAmendmentSuccess(null);
                        if (pid) { setExecutingPlanId(pid); }
                        else { navigate("/library?tab=plans"); }
                      }}
                    >
                      {executingPlanId ? "Review & Execute" : t("features.browseV2.amendment.goToPlans")}
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
                        {detail.objectDetail?.object_source === "library_object" && (
                          <button
                            className="secondary-button"
                            type="button"
                            data-density="compact"
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
        <div className="browse-v2-inline-alert browse-v2-inline-alert--danger" role="alert">
          {t("features.browseV2.compose.error")}: {composeError}
          <button className="secondary-button" type="button" onClick={() => setComposeError(null)}>
            {t("features.library.inbox.cancel")}
          </button>
        </div>
      )}
      {composeSuccess && (
        <div className="browse-v2-inline-alert browse-v2-inline-alert--success" role="status">
          {composeSuccess}
          <p>{t("features.browseV2.amendment.filesHaveNotMoved")} / {t("features.browseV2.amendment.preflightExecuteRequired")}</p>
          <div className="browse-v2-inline-alert__actions">
            <button
              className="primary-button"
              type="button"
              onClick={() => {
                const pid = executingPlanId;
                setComposeSuccess(null);
                if (pid) { setExecutingPlanId(pid); }
                else { navigate("/library?tab=plans"); }
              }}
            >
              {executingPlanId ? "Review & Execute" : t("features.browseV2.amendment.goToPlans")}
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
          <div className="library-inbox-modal browse-v2-amendment-modal browse-v2-amendment-modal--wide" role="dialog" onClick={e => e.stopPropagation()}>
            <h3>{t("features.browseV2.amendment.addMembersTitle")}</h3>
            <p className="library-inbox-modal-hint">{t("features.browseV2.amendment.addMembersDescription")}</p>
            <div className="browse-v2-amendment-candidates">
              {looseCandidates?.items.filter(c => c.card_kind === "loose_file").length === 0 && (
                <p className="browse-v2-amendment-candidates__empty">{t("features.browseV2.amendment.noManagedLooseCandidates")}</p>
              )}
              {looseCandidates?.items.filter(c => c.card_kind === "loose_file").map((card: any) => (
                <label className="browse-v2-amendment-candidate" key={card.file_id}>
                  <input type="checkbox" checked={selectedAddFileIds.has(card.file_id)} onChange={() => {
                    setSelectedAddFileIds(prev => { const n = new Set(prev); if (n.has(card.file_id)) n.delete(card.file_id); else n.add(card.file_id); return n; });
                  }} disabled={amending} />
                  <span title={card.path}>{card.name}</span>
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

      {executingPlanId ? (
        <ExecutePlanPanel planId={executingPlanId} onClose={() => setExecutingPlanId(null)} />
      ) : null}

      {/* Phase 8D-D: Remove Member Modal */}
      {showRemoveMemberModal && removeTargetMember && (
        <div className="library-inbox-modal-overlay" onClick={amending ? undefined : () => { setShowRemoveMemberModal(false); setRemoveTargetMember(null); }}>
          <div className="library-inbox-modal browse-v2-amendment-modal" role="dialog" onClick={e => e.stopPropagation()}>
            <h3>{t("features.browseV2.amendment.removeMemberTitle")}</h3>
            <p className="library-inbox-modal-hint">{t("features.browseV2.amendment.removeMemberDescription")}</p>
            <div className="browse-v2-amendment-target">
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
