import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import { listBrowseCards, type BrowseV2Card, type BrowseV2LooseFileCard, type BrowseV2ObjectCard } from "../../services/api/browseV2Api";
import { composeExternalFiles, composeInboxItems } from "../../services/api/importingApi";
import { createManagedComposePlan, createObjectAmendmentPlan } from "../../services/api/libraryOrganizeApi";
import { listLibraryRoots } from "../../services/api/libraryObjectsApi";
import type { LibraryRootVM } from "../../entities/library/types";
import { t } from "../../shared/text";
import { CATEGORY_TREE, DOMAINS } from "../../shared/browse-taxonomy";
import { CardSkeleton, MetricStrip, Pagination, WorkbenchFilterPanel, WorkbenchMasthead, WorkbenchPage, WorkbenchResultFrame, WorkbenchToolbar } from "../../shared/ui/components";
import { EmptyState } from "../../shared/ui/components/EmptyState";
import { asTextKey, getCategoryLabel } from "./helpers";
import { useBrowseV2SearchParams } from "./hooks/useBrowseV2SearchParams";
import { useBrowseV2Cards } from "./hooks/useBrowseV2Cards";
import { useBrowseV2ObjectDetail } from "./hooks/useBrowseV2ObjectDetail";
import { BrowseV2CardList } from "./BrowseV2CardList";
import { BrowseV2DetailPanel } from "./BrowseV2DetailPanel";
import { BrowseV2Modals } from "./BrowseV2Modals";


const PAGE_SIZE = 50;

type CategoryItem = { value: string; labelKey: string };

function isObjectCard(card: BrowseV2Card): card is BrowseV2ObjectCard {
  return card.card_kind === "object";
}

function isLooseFileCard(card: BrowseV2Card): card is BrowseV2LooseFileCard {
  return card.card_kind === "loose_file";
}

export function BrowseV2Feature() {
  const {
    domain, category, storageState, cardKind, sort, order,
    fileType, needsReview, minConfidence, dateFrom, dateTo, minSize,
    viewMode, page, selected, setPage, setScope, updateFilter, clearAllFilters,
  } = useBrowseV2SearchParams();
  const cards = useBrowseV2Cards({
    domain, category, storage_state: storageState, card_kind: cardKind,
    page, sort_by: sort, sort_order: order,
    file_type: fileType || undefined, needs_review: needsReview || undefined,
  });
  const { data, error, isError, isLoading, items, totalPages } = cards;
  const navigate = useNavigate();
  const [selectedObject, setSelectedObject] = useState<BrowseV2ObjectCard | null>(null);
  const detail = useBrowseV2ObjectDetail(selectedObject);
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);

  // C15: Toast message when filters reset page
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => setToastMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  // A4: Client-side browse search (must be before filtered item usage)
  const [searchQuery, setSearchQuery] = useState("");
  const filteredItems = searchQuery.trim()
    ? cards.items.filter(card => {
        const title = card.card_kind === "object" ? card.display_title : card.name;
        return title.toLowerCase().includes(searchQuery.toLowerCase());
      })
    : cards.items;

  const objectCards = filteredItems.filter(isObjectCard);
  const looseFileCards = filteredItems.filter(isLooseFileCard);
  const showObjects = cardKind !== "loose_file";
  const showLooseFiles = cardKind !== "object";
  const activeScope = getCategoryLabel(domain, category);

  // Compose selection state
  const [selectedFileIds, setSelectedFileIds] = useState<Set<number>>(new Set());
  const [showComposeModal, setShowComposeModal] = useState(false);
  const [composing, setComposing] = useState(false);
  const [composeError, setComposeError] = useState<string | null>(null);
  const [composeSuccess, setComposeSuccess] = useState<string | null>(null);
  const [executingPlanId, setExecutingPlanId] = useState<number | null>(null);

  // Amendment state (add/remove members)
  const [showAddMembersModal, setShowAddMembersModal] = useState(false);
  const [showRemoveMemberModal, setShowRemoveMemberModal] = useState(false);
  const [removeTargetMember, setRemoveTargetMember] = useState<{member_id: number; name: string} | null>(null);
  const [amending, setAmending] = useState(false);
  const [amendmentError, setAmendmentError] = useState<string | null>(null);
  const [amendmentSuccess, setAmendmentSuccess] = useState<string | null>(null);
  const [addMembersPage, setAddMembersPage] = useState(1);
  const addMembersPageSize = 20;

  const { data: looseCandidates } = useQuery({
    queryKey: ["browse-v2-loose-candidates"],
    queryFn: () => listBrowseCards({ storage_state: "managed", card_kind: "loose_file", page_size: 50 }),
    enabled: showAddMembersModal,
  });
  const addMembersTotalPages = looseCandidates?.items
    ? Math.max(1, Math.ceil((looseCandidates.items.filter(c => c.card_kind === "loose_file").length) / addMembersPageSize))
    : 1;
  const [selectedAddFileIds, setSelectedAddFileIds] = useState<Set<number>>(new Set());

  // B13: Select All
  const allSelected = looseFileCards.length > 0 && looseFileCards.every(f => selectedFileIds.has(f.file_id));
  function handleSelectAll() {
    const allIds = looseFileCards.map(f => f.file_id);
    setSelectedFileIds(new Set(allIds));
  }

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

  function handleCardClick(card: BrowseV2Card, event?: { ctrlKey?: boolean; shiftKey?: boolean }) {
    // C3: Ctrl+Click toggle selection for loose files
    if (isLooseFileCard(card) && event?.ctrlKey) {
      handleCheckboxToggle(card);
      return;
    }

    // C3: Shift+Click range select for loose files
    if (isLooseFileCard(card) && event?.shiftKey && selectedFileIds.size > 0) {
      const allFiles = looseFileCards;
      const lastSelectedId = [...selectedFileIds].pop() ?? card.file_id;
      const lastIdx = allFiles.findIndex(f => f.file_id === lastSelectedId);
      const currentIdx = allFiles.findIndex(f => f.file_id === card.file_id);
      if (lastIdx >= 0 && currentIdx >= 0) {
        const start = Math.min(lastIdx, currentIdx);
        const end = Math.max(lastIdx, currentIdx);
        const newIds = new Set(selectedFileIds);
        for (let i = start; i <= end; i++) {
          newIds.add(allFiles[i].file_id);
        }
        setSelectedFileIds(newIds);
        return;
      }
    }

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
      const msg = selectionSS === "managed"
        ? t("features.browseV2.compose.planCreated")
        : t("features.browseV2.compose.success");
      setComposeSuccess(msg);
      localStorage.setItem("browse-v2-compose-success", msg);
    } catch (err) {
      setComposeError(String(err));
    } finally { setComposing(false); }
  }

  // C16: localStorage for compose/amendment success messages
  useEffect(() => {
    const savedCompose = localStorage.getItem("browse-v2-compose-success");
    if (savedCompose) { setComposeSuccess(savedCompose); localStorage.removeItem("browse-v2-compose-success"); }
    const savedAmendment = localStorage.getItem("browse-v2-amendment-success");
    if (savedAmendment) { setAmendmentSuccess(savedAmendment); localStorage.removeItem("browse-v2-amendment-success"); }
  }, []);
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

      <div className="browse-v2-layout">
        <nav className="browse-v2-taxonomy" aria-label="Browse categories">
          <div className="browse-v2-taxonomy__domain">
            {DOMAINS.map(d => (
              <button
                key={d.value}
                className={`browse-v2-taxonomy__domain-button${d.value === domain ? " browse-v2-taxonomy__domain-button--active" : ""}`}
                onClick={() => updateFilter("domain", d.value)}
              >
                {t(asTextKey(d.labelKey))}
              </button>
            ))}
          </div>
          {domain && CATEGORY_TREE[domain]?.length > 0 && (
            <div className="browse-v2-taxonomy__groups">
              {CATEGORY_TREE[domain].map(group => (
                <div key={group.groupKey ?? group.items[0]?.value ?? "default"} className="browse-v2-taxonomy__group">
                  {group.groupKey && (
                    <h4 className="browse-v2-taxonomy__group-label">{t(asTextKey(group.groupKey))}</h4>
                  )}
                  {group.items.map(cat => (
                    <button
                      key={cat.value}
                      className={`browse-v2-taxonomy__item${cat.value === category ? " browse-v2-taxonomy__item--active" : ""}`}
                      onClick={() => updateFilter("category", cat.value)}
                    >
                      {t(asTextKey(cat.labelKey))}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </nav>
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
            {/* C10: Breadcrumb shows context (page) */}
            <span className="browse-v2-breadcrumb__sep" aria-hidden="true">|</span>
            <span className="browse-v2-breadcrumb__item">{t("features.browseV2.pagination.pageInfo", { page: String(page), total: String(totalPages) })}</span>
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
              {/* C6: File type filter dropdown */}
              <label className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.fileType")}</span>
                <select className="select-input" value={fileType} onChange={(e) => updateFilter("fileType", e.target.value)}>
                  <option value="">{t("features.browseV2.filters.all")}</option>
                  <option value="image">Image</option>
                  <option value="video">Video</option>
                  <option value="audio">Audio</option>
                  <option value="document">Document</option>
                  <option value="archive">Archive</option>
                </select>
              </label>
              {/* C7: Needs-review filter */}
              <label className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.needsReview")}</span>
                <select className="select-input" value={needsReview} onChange={(e) => updateFilter("needsReview", e.target.value)}>
                  <option value="">{t("features.browseV2.filters.all")}</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </label>
              {/* C7: Min confidence filter */}
              <label className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.minConfidence")}</span>
                <select className="select-input" value={minConfidence} onChange={(e) => updateFilter("minConfidence", e.target.value)}>
                  <option value="">{t("features.browseV2.filters.all")}</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </label>
              <div className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.sort")}</span>
                <div style={{ display: "flex", gap: 4 }}>
                  <select className="select-input" value={sort} onChange={e => updateFilter("sort", e.target.value)} aria-label="Sort by" style={{ flex: 1 }}>
                    <option value="title">{t("features.browseV2.filters.sortTitle")}</option>
                    <option value="modified_at">{t("features.browseV2.filters.sortModified")}</option>
                    <option value="file_type">{t("features.browseV2.filters.sortType")}</option>
                  </select>
                  {/* C19: Sort column indicator (↑/↓) */}
                  <button className="secondary-button" onClick={() => updateFilter("order", order === "asc" ? "desc" : "asc")} aria-label="Toggle sort order" style={{ minWidth: 44 }}>
                    {order === "asc" ? "↑" : "↓"}
                  </button>
                </div>
              </div>
              {/* C9: View mode toggle */}
              <div className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.view")}</span>
                <div style={{ display: "flex", gap: 4 }}>
                  <button className={`secondary-button${viewMode === "grid" ? " browse-v2-view-active" : ""}`} onClick={() => updateFilter("view", "grid")} aria-label="Grid view">▦</button>
                  <button className={`secondary-button${viewMode === "list" ? " browse-v2-view-active" : ""}`} onClick={() => updateFilter("view", "list")} aria-label="List view">☰</button>
                  <button className={`secondary-button${viewMode === "table" ? " browse-v2-view-active" : ""}`} onClick={() => updateFilter("view", "table")} aria-label="Table view">⊞</button>
                </div>
              </div>
              {/* C8: Date range filter */}
              <label className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.dateFrom")}</span>
                <input className="text-input" type="date" value={dateFrom} onChange={(e) => updateFilter("dateFrom", e.target.value)} style={{ fontSize: 11 }} />
              </label>
              <label className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.dateTo")}</span>
                <input className="text-input" type="date" value={dateTo} onChange={(e) => updateFilter("dateTo", e.target.value)} style={{ fontSize: 11 }} />
              </label>
              {/* C8: Min file size filter */}
              <label className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.minSize")}</span>
                <select className="select-input" value={minSize} onChange={(e) => updateFilter("minSize", e.target.value)}>
                  <option value="">{t("features.browseV2.filters.all")}</option>
                  <option value="1048576">1 MB</option>
                  <option value="10485760">10 MB</option>
                  <option value="104857600">100 MB</option>
                  <option value="1073741824">1 GB</option>
                </select>
              </label>
              {/* C18: Clear all filters */}
              {(storageState !== "all" || cardKind !== "all" || category || fileType || needsReview || minConfidence || dateFrom || dateTo || minSize) ? (
                <div className="field-stack browse-v2-toolbar__field">
                  <span>&nbsp;</span>
                  <button className="secondary-button" onClick={() => { clearAllFilters(); }} aria-label="Clear all filters">
                    {t("features.browseV2.filters.clearAll")}
                  </button>
                </div>
              ) : null}
              <input type="search" placeholder="Search in browse..." value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)} className="browse-v2-search" aria-label="Search in browse" />
              <div className="browse-v2-toolbar__scope" aria-label={t("features.browseV2.sections.currentScope")}>
                <span>{t("features.browseV2.sections.currentScope")}</span>
                <strong>{activeScope}</strong>
              </div>
            </WorkbenchToolbar>
          </WorkbenchFilterPanel>

          {toastMessage ? (
            <div className="browse-v2-inline-alert browse-v2-inline-alert--info" role="status" style={{ animation: "fadeIn 0.3s ease" }}>
              {toastMessage}
            </div>
          ) : null}

          {/* Selection bar with compose, batch actions, and drag-over compose zone */}
          {selectedFileIds.size > 0 && (
            <div
              className="browse-v2-selection-bar"
              onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add("browse-v2-selection-bar--dragover"); }}
              onDragLeave={(e) => { e.currentTarget.classList.remove("browse-v2-selection-bar--dragover"); }}
              onDrop={(e) => { e.preventDefault(); e.currentTarget.classList.remove("browse-v2-selection-bar--dragover"); setShowComposeModal(true); }}
            >
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
              {/* C17: Batch tag/move in selection bar */}
              <button className="secondary-button" type="button" disabled>
                {t("features.browseV2.compose.batchTag")}
              </button>
              <button className="secondary-button" type="button" disabled>
                {t("features.browseV2.compose.batchMove")}
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
            {isLoading ? <CardSkeleton count={8} variant="card" /> : null}
            {isError ? (
              <div className="browse-v2-state browse-v2-state--error" role="alert">
                {t("features.browseV2.errors.loadFailed")}: {String(error)}
                <button className="secondary-button" type="button" onClick={() => queryClient.invalidateQueries({ queryKey: ["browse-v2"] })} style={{ marginLeft: 8 }}>
                  {t("common.states.retry")}
                </button>
              </div>
            ) : null}
            {data && items.length === 0 ? (
              <EmptyState title={t("features.browseV2.empty")}
                action={{ label: t("features.homeOverview.scanCardAction"), onClick: () => navigate("/library?tab=sources") }} />
            ) : null}
            <BrowseV2CardList
              showObjects={showObjects}
              showLooseFiles={showLooseFiles}
              objectCards={objectCards}
              looseFileCards={looseFileCards}
              hasData={!!data && items.length > 0}
              selectedObject={selectedObject}
              selectedItemId={selectedItemId}
              selectedFileIds={selectedFileIds}
              onCardClick={handleCardClick}
              onCheckboxToggle={handleCheckboxToggle}
              onSelectAll={handleSelectAll}
              onClearSelection={clearSelection}
              allSelected={allSelected}
            />
          </WorkbenchResultFrame>

          {data && data.total > PAGE_SIZE ? (
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          ) : null}
        </main>

        <BrowseV2DetailPanel
          selectedObject={selectedObject}
          detail={detail}
          amendmentError={amendmentError}
          amendmentSuccess={amendmentSuccess}
          executingPlanId={executingPlanId}
          onClearAmendmentError={() => setAmendmentError(null)}
          onExecuteOrNavigateAfterAmendment={() => {
            const pid = executingPlanId;
            setAmendmentSuccess(null);
            if (pid) { setExecutingPlanId(pid); }
            else { navigate("/library?tab=plans"); }
          }}
          onDismissAmendmentSuccess={() => setAmendmentSuccess(null)}
          onAddMembersRequest={() => setShowAddMembersModal(true)}
          onRemoveMemberRequest={(memberId, name) => {
            setRemoveTargetMember({ member_id: memberId, name });
            setShowRemoveMemberModal(true);
          }}
        />
      </div>

      <BrowseV2Modals
        showComposeModal={showComposeModal}
        selectedFiles={selectedFiles}
        roots={(roots as LibraryRootVM[]) ?? []}
        selectionSS={selectionSS ?? ""}
        composing={composing}
        composeError={composeError}
        composeSuccess={composeSuccess}
        executingPlanId={executingPlanId}
        showAddMembersModal={showAddMembersModal}
        amending={amending}
        selectedAddFileIds={selectedAddFileIds}
        looseCandidates={looseCandidates}
        showRemoveMemberModal={showRemoveMemberModal}
        removeTargetMember={removeTargetMember}
        onCancelCompose={() => { setShowComposeModal(false); setComposeError(null); }}
        onConfirmCompose={handleComposeConfirm}
        onDismissComposeError={() => setComposeError(null)}
        onExecuteOrNavigateAfterCompose={() => {
          const pid = executingPlanId;
          setComposeSuccess(null);
          if (pid) { setExecutingPlanId(pid); }
          else { navigate("/library?tab=plans"); }
        }}
        onDismissComposeSuccess={() => setComposeSuccess(null)}
        onDismissAddMembersModal={() => { setShowAddMembersModal(false); setSelectedAddFileIds(new Set()); }}
        onToggleAddFileId={(fileId) => {
          setSelectedAddFileIds(prev => { const n = new Set(prev); if (n.has(fileId)) n.delete(fileId); else n.add(fileId); return n; });
        }}
        onConfirmAddMembers={handleAddMembersConfirm}
        onCloseExecutePlan={() => setExecutingPlanId(null)}
        onDismissRemoveMemberModal={() => { setShowRemoveMemberModal(false); setRemoveTargetMember(null); }}
        onConfirmRemoveMember={handleRemoveMemberConfirm}
        addMembersPage={addMembersPage}
        addMembersTotalPages={addMembersTotalPages}
        onAddMembersPageChange={setAddMembersPage}
      />
    </WorkbenchPage>
  );
}
