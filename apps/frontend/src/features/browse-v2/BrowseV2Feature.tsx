import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import { getBrowseObjectDetail, listBrowseCards, type BrowseV2Card, type BrowseV2LooseFileCard, type BrowseV2ObjectCard, type BrowseV2Response } from "../../services/api/browseV2Api";
import { composeExternalFiles, composeInboxItems } from "../../services/api/importingApi";
import { createManagedComposePlan } from "../../services/api/libraryOrganizeApi";
import { listLibraryRoots, type LibraryRootVM } from "../../services/api/libraryObjectsApi";
import { t } from "../../shared/text";
import { InspectorSection, MetricStrip, WorkbenchFilterPanel, WorkbenchMasthead, WorkbenchPage, WorkbenchResultFrame, WorkbenchToolbar } from "../../shared/ui/components";
import { ComposeObjectModal } from "./ComposeObjectModal";
import { LooseFileCard } from "./LooseFileCard";
import { ObjectCard } from "./ObjectCard";


const PAGE_SIZE = 50;

const DOMAINS = [
  { value: "media", labelKey: "features.browseV2.domains.media" },
  { value: "documents", labelKey: "features.browseV2.domains.documents" },
  { value: "apps", labelKey: "features.browseV2.domains.apps" },
  { value: "assets", labelKey: "features.browseV2.domains.assets" },
] as const;

type DomainValue = (typeof DOMAINS)[number]["value"];
type CategoryItem = { value: string; labelKey: string };
type CategoryGroup = { groupKey?: string; items: CategoryItem[] };

const CATEGORY_TREE: Record<DomainValue, CategoryGroup[]> = {
  media: [
    {
      groupKey: "features.browseV2.categoryGroups.video",
      items: [
        { value: "movie", labelKey: "features.browseV2.categories.movie" },
        { value: "series_anime", labelKey: "features.browseV2.categories.series_anime" },
        { value: "course", labelKey: "features.browseV2.categories.course" },
        { value: "video_collection", labelKey: "features.browseV2.categories.video_collection" },
        { value: "video_clip", labelKey: "features.browseV2.categories.video_clip" },
      ],
    },
    {
      groupKey: "features.browseV2.categoryGroups.image",
      items: [
        { value: "image_album", labelKey: "features.browseV2.categories.image_album" },
        { value: "comic", labelKey: "features.browseV2.categories.comic" },
      ],
    },
    {
      groupKey: "features.browseV2.categoryGroups.audio",
      items: [
        { value: "audio", labelKey: "features.browseV2.categories.audio" },
      ],
    },
  ],
  documents: [
    { items: [{ value: "docset", labelKey: "features.browseV2.categories.docset" }] },
  ],
  apps: [
    {
      items: [
        { value: "software", labelKey: "features.browseV2.categories.software" },
        { value: "game", labelKey: "features.browseV2.categories.game" },
      ],
    },
  ],
  assets: [
    { items: [{ value: "asset_pack", labelKey: "features.browseV2.categories.asset_pack" }] },
  ],
};

function asTextKey(key: string): Parameters<typeof t>[0] {
  return key as Parameters<typeof t>[0];
}

function objectTypeLabel(objectType: string | null): string {
  if (!objectType) {
    return "";
  }
  const map: Record<string, string> = {
    movie: "features.browseV2.categories.movie",
    anime: "features.browseV2.categories.series_anime",
    course: "features.browseV2.categories.course",
    video_collection: "features.browseV2.categories.video_collection",
    clip: "features.browseV2.categories.video_clip",
    clip_set: "features.browseV2.categories.video_clip",
    movie_collection: "features.browseV2.categories.video_collection",
    imgset: "features.browseV2.categories.image_album",
    photo_event: "features.browseV2.categories.image_album",
    web_image_set: "features.browseV2.categories.image_album",
    comic: "features.browseV2.categories.comic",
    audio: "features.browseV2.categories.audio",
    docset: "features.browseV2.categories.docset",
    software: "features.browseV2.categories.software",
    game: "features.browseV2.categories.game",
    asset_pack: "features.browseV2.categories.asset_pack",
  };
  const key = map[objectType] || `features.library.inbox.objectTypes.${objectType}`;
  return t(asTextKey(key)) || objectType;
}

function objectSourceLabel(source: string): string {
  return t(asTextKey(`features.browseV2.objectSource.${source}`)) || source;
}

function storageStateLabel(storageState: string | null): string {
  if (!storageState) {
    return "";
  }
  return t(asTextKey(`features.browseV2.storageState.${storageState}`)) || storageState;
}

function fileKindLabel(fileKind: string | null): string {
  if (!fileKind) {
    return "";
  }
  return t(asTextKey(`features.browseV2.fileKind.${fileKind}`)) || fileKind;
}

function confidenceLabel(confidence: string | null): string {
  if (!confidence) {
    return "";
  }
  return t(asTextKey(`features.browseV2.confidence.${confidence}`)) || confidence;
}

function formatBytes(value: number | null): string {
  if (value === null) {
    return "";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  const formatted = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: size >= 10 || unitIndex === 0 ? 0 : 1,
  }).format(size);

  return `${formatted} ${units[unitIndex]}`;
}

function getCategoryLabel(domain: DomainValue, category: string): string {
  if (!category) {
    const domainLabel = DOMAINS.find((item) => item.value === domain)?.labelKey;
    return domainLabel ? t(asTextKey(domainLabel)) : domain;
  }

  for (const group of CATEGORY_TREE[domain]) {
    const item = group.items.find((candidate) => candidate.value === category);
    if (item) {
      return t(asTextKey(item.labelKey));
    }
  }

  return category;
}

function isObjectCard(card: BrowseV2Card): card is BrowseV2ObjectCard {
  return card.card_kind === "object";
}

function isLooseFileCard(card: BrowseV2Card): card is BrowseV2LooseFileCard {
  return card.card_kind === "loose_file";
}

export function BrowseV2Feature() {
  const [domain, setDomain] = useState<DomainValue>("media");
  const [category, setCategory] = useState("");
  const [storageState, setStorageState] = useState("all");
  const [cardKind, setCardKind] = useState("all");
  const [page, setPage] = useState(1);
  const [selectedObject, setSelectedObject] = useState<BrowseV2ObjectCard | null>(null);
  const [memberPage, setMemberPage] = useState(1);
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);

  // Phase 8C-2: Compose selection
  const [selectedFileIds, setSelectedFileIds] = useState<Set<number>>(new Set());
  const [showComposeModal, setShowComposeModal] = useState(false);
  const [composing, setComposing] = useState(false);
  const [composeError, setComposeError] = useState<string | null>(null);
  const [composeSuccess, setComposeSuccess] = useState<string | null>(null);

  const { data: roots } = useQuery({
    queryKey: ["library-roots"],
    queryFn: listLibraryRoots,
    staleTime: 60_000,
  });

  const queryClient = useQueryClient();

  const queryParams = useMemo(() => ({
    domain,
    category: category || undefined,
    storage_state: storageState,
    card_kind: cardKind,
    page,
    page_size: PAGE_SIZE,
  }), [domain, category, storageState, cardKind, page]);

  const { data, isLoading, isError, error } = useQuery<BrowseV2Response>({
    queryKey: ["browse-v2", queryParams],
    queryFn: () => listBrowseCards(queryParams),
  });

  const { data: objectDetail, isLoading: objectDetailLoading, isError: objectDetailError } = useQuery({
    queryKey: ["browse-v2-obj-detail", selectedObject?.object_source, selectedObject?.source_id, memberPage],
    queryFn: () => getBrowseObjectDetail({
      object_source: selectedObject!.object_source,
      source_id: selectedObject!.source_id,
      member_page: memberPage,
      member_page_size: PAGE_SIZE,
    }),
    enabled: selectedObject !== null,
  });

  const items = data?.items ?? [];
  const objectCards = items.filter(isObjectCard);
  const looseFileCards = items.filter(isLooseFileCard);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const showObjects = cardKind !== "loose_file";
  const showLooseFiles = cardKind !== "object";
  const activeScope = getCategoryLabel(domain, category);

  useEffect(() => {
    setMemberPage(1);
  }, [selectedObject?.object_source, selectedObject?.source_id]);

  function setScope(nextDomain: DomainValue, nextCategory = "") {
    setDomain(nextDomain);
    setCategory(nextCategory);
    setPage(1);
  }

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
        <nav className="browse-v2-taxonomy" aria-label={t("features.browseV2.taxonomyLabel")}>
          {DOMAINS.map((domainItem) => {
            const isActiveDomain = domain === domainItem.value;

            return (
              <section className={`browse-v2-taxonomy__domain${isActiveDomain ? " browse-v2-taxonomy__domain--active" : ""}`} key={domainItem.value}>
                <button
                  className={`browse-v2-taxonomy__domain-button${isActiveDomain && !category ? " browse-v2-taxonomy__domain-button--active" : ""}`}
                  type="button"
                  onClick={() => setScope(domainItem.value)}
                >
                  <span>{t(asTextKey(domainItem.labelKey))}</span>
                  <small>{t("features.browseV2.categories.all")}</small>
                </button>
                <div className="browse-v2-taxonomy__groups">
                  {CATEGORY_TREE[domainItem.value].map((group, groupIndex) => (
                    <div className="browse-v2-taxonomy__group" key={`${domainItem.value}-${group.groupKey ?? groupIndex}`}>
                      {group.groupKey ? (
                        <span className="browse-v2-taxonomy__group-label">
                          {t(asTextKey(group.groupKey))}
                        </span>
                      ) : null}
                      {group.items.map((item) => {
                        const isActiveCategory = isActiveDomain && category === item.value;

                        return (
                          <button
                            className={`browse-v2-taxonomy__item${isActiveCategory ? " browse-v2-taxonomy__item--active" : ""}`}
                            type="button"
                            key={item.value}
                            onClick={() => setScope(domainItem.value, item.value)}
                          >
                            {t(asTextKey(item.labelKey))}
                          </button>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </nav>

        <main className="browse-v2-main" aria-live="polite">
          <WorkbenchFilterPanel className="browse-v2-filter-panel" label={t("features.browseV2.filters.title")}>
            <WorkbenchToolbar className="browse-v2-toolbar">
              <label className="field-stack browse-v2-toolbar__field">
                <span>{t("features.browseV2.filters.storageLabel")}</span>
                <select
                  className="select-input"
                  name="browse-v2-storage"
                  value={storageState}
                  onChange={(event) => {
                    setStorageState(event.target.value);
                    setPage(1);
                  }}
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
                  onChange={(event) => {
                    setCardKind(event.target.value);
                    setPage(1);
                  }}
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
          {selectedObject && objectDetailLoading ? (
            <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
              <p className="browse-v2-detail__empty">{t("common.states.loading")}</p>
            </InspectorSection>
          ) : null}
          {selectedObject && objectDetailError ? (
            <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
              <p className="danger-text">{t("features.browseV2.errors.detailFailed")}</p>
            </InspectorSection>
          ) : null}
          {selectedObject && objectDetail ? (
            <>
              <InspectorSection className="browse-v2-detail__section" title={t("features.browseV2.overview.title")}>
                <div className="browse-v2-detail__identity">
                  <span className="status-badge status-badge--accent">{objectTypeLabel(objectDetail.object_type)}</span>
                  <h4>{objectDetail.display_title}</h4>
                  <p>{objectSourceLabel(objectDetail.object_source)}</p>
                </div>
                <div className="browse-v2-detail__facts">
                  <div className="key-value-row">
                    <span className="key-value-row__label">{t("features.browseV2.overview.status")}</span>
                    <span className="key-value-row__value">{storageStateLabel(objectDetail.storage_state)}{objectDetail.needs_review ? ` / ${t("features.browseV2.needsReview")}` : ""}</span>
                  </div>
                  <div className="key-value-row">
                    <span className="key-value-row__label">{t("features.browseV2.overview.members", { count: String(objectDetail.member_total) })}</span>
                    <span className="key-value-row__value">{objectDetail.member_total}</span>
                  </div>
                  {objectDetail.confidence ? (
                    <div className="key-value-row">
                      <span className="key-value-row__label">{t("features.browseV2.overview.confidence")}</span>
                      <span className="key-value-row__value">{confidenceLabel(objectDetail.confidence)}</span>
                    </div>
                  ) : null}
                  {objectDetail.root_path ? (
                    <div className="key-value-row">
                      <span className="key-value-row__label">{t("features.browseV2.overview.rootPath")}</span>
                      <span className="key-value-row__value browse-v2-detail__path" title={objectDetail.root_path}>
                        {objectDetail.root_path.replace(/\\/g, "/").split("/").slice(-2).join("/")}
                      </span>
                    </div>
                  ) : null}
                </div>
              </InspectorSection>

              <InspectorSection className="browse-v2-detail__section" title={`${t("features.browseV2.overview.membersTitle")} (${objectDetail.member_total})`}>
                {objectDetail.members.length === 0 ? (
                  <p className="browse-v2-detail__empty">{t("features.browseV2.overview.noMembers")}</p>
                ) : (
                  <div className="browse-v2-member-list">
                    {objectDetail.members.map((member) => (
                      <div key={member.member_id} className="browse-v2-member-row" title={member.path || ""}>
                        <span className="browse-v2-member-row__name">{member.name || `#${member.file_id || member.member_id}`}</span>
                        <span className="browse-v2-member-row__meta">
                          <span className="status-badge status-badge--muted">{member.role}</span>
                          {member.file_kind ? <span className="status-badge status-badge--info">{fileKindLabel(member.file_kind)}</span> : null}
                          {member.storage_state ? <span className="status-badge status-badge--secondary">{storageStateLabel(member.storage_state)}</span> : null}
                          {member.missing ? <span className="status-badge status-badge--danger">{t("features.browseV2.overview.missing")}</span> : null}
                          {member.size_bytes !== null ? <span className="browse-v2-member-row__size">{formatBytes(member.size_bytes)}</span> : null}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {objectDetail.member_total > objectDetail.member_page_size ? (
                  <div className="browse-v2-member-pager">
                    <button className="secondary-button" type="button" disabled={objectDetail.member_page <= 1} onClick={() => setMemberPage((current) => current - 1)}>
                      {t("features.browseV2.pagination.previous")}
                    </button>
                    <span>
                      {t("features.browseV2.pagination.pageInfo", {
                        page: String(objectDetail.member_page),
                        total: String(Math.ceil(objectDetail.member_total / objectDetail.member_page_size)),
                      })}
                    </span>
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={objectDetail.member_page * objectDetail.member_page_size >= objectDetail.member_total}
                      onClick={() => setMemberPage((current) => current + 1)}
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
          <button className="secondary-button" type="button" style={{marginLeft:8}} onClick={() => setComposeSuccess(null)}>
            {t("features.library.inbox.cancel")}
          </button>
        </div>
      )}
    </WorkbenchPage>
  );
}
