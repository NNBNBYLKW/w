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
import { DOMAINS } from "../../shared/browse-taxonomy";
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
            {isLoading ? <CardSkeleton count={8} variant="card" /> : null}
            {isError ? (
              <div className="browse-v2-state browse-v2-state--error" role="alert">
                {t("features.browseV2.errors.loadFailed")}: {String(error)}
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
      />
    </WorkbenchPage>
  );
}
