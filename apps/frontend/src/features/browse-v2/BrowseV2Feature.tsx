import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { t } from "../../shared/text";
import { listBrowseCards, type BrowseV2Card, type BrowseV2ObjectCard, type BrowseV2Response } from "../../services/api/browseV2Api";
import { useUIStore } from "../../app/providers/uiStore";
import { ObjectCard } from "./ObjectCard";
import { LooseFileCard } from "./LooseFileCard";

// ── navigation data ─────────────────────────────────────

const DOMAINS = [
  { value: "media", labelKey: "features.browseV2.domains.media" },
  { value: "documents", labelKey: "features.browseV2.domains.documents" },
  { value: "apps", labelKey: "features.browseV2.domains.apps" },
  { value: "assets", labelKey: "features.browseV2.domains.assets" },
] as const;

type CategoryItem = { value: string; labelKey: string };
type CategoryGroup = { groupKey?: string; items: CategoryItem[] };

const CATEGORY_TREE: Record<string, CategoryGroup[]> = {
  media: [
    { groupKey: "features.browseV2.categoryGroups.video", items: [
      { value: "movie", labelKey: "features.browseV2.categories.movie" },
      { value: "series_anime", labelKey: "features.browseV2.categories.series_anime" },
      { value: "course", labelKey: "features.browseV2.categories.course" },
      { value: "video_collection", labelKey: "features.browseV2.categories.video_collection" },
      { value: "video_clip", labelKey: "features.browseV2.categories.video_clip" },
    ]},
    { groupKey: "features.browseV2.categoryGroups.image", items: [
      { value: "image_album", labelKey: "features.browseV2.categories.image_album" },
      { value: "comic", labelKey: "features.browseV2.categories.comic" },
    ]},
    { groupKey: "features.browseV2.categoryGroups.audio", items: [
      { value: "audio", labelKey: "features.browseV2.categories.audio" },
    ]},
  ],
  documents: [
    { items: [{ value: "docset", labelKey: "features.browseV2.categories.docset" }]},
  ],
  apps: [
    { items: [
      { value: "software", labelKey: "features.browseV2.categories.software" },
      { value: "game", labelKey: "features.browseV2.categories.game" },
    ]},
  ],
  assets: [
    { items: [{ value: "asset_pack", labelKey: "features.browseV2.categories.asset_pack" }]},
  ],
};

// ── label helpers ────────────────────────────────────────

function objectTypeLabel(ot: string | null): string {
  if (!ot) return "";
  const map: Record<string, string> = {
    movie: "features.browseV2.categories.movie", anime: "features.browseV2.categories.series_anime",
    course: "features.browseV2.categories.course", video_collection: "features.browseV2.categories.video_collection",
    clip: "features.browseV2.categories.video_clip", clip_set: "features.browseV2.categories.video_clip",
    imgset: "features.browseV2.categories.image_album", photo_event: "features.browseV2.categories.image_album",
    web_image_set: "features.browseV2.categories.image_album", comic: "features.browseV2.categories.comic",
    audio: "features.browseV2.categories.audio", docset: "features.browseV2.categories.docset",
    software: "features.browseV2.categories.software", game: "features.browseV2.categories.game",
    asset_pack: "features.browseV2.categories.asset_pack",
  };
  const k = map[ot] || `features.library.inbox.objectTypes.${ot}`;
  return t(k as Parameters<typeof t>[0]) || ot;
}

function objSourceLabel(source: string): string {
  return t(`features.browseV2.objectSource.${source}` as Parameters<typeof t>[0]) || source;
}

function ssLabel(ss: string | null): string {
  if (!ss) return "";
  return t(`features.browseV2.storageState.${ss}` as Parameters<typeof t>[0]) || ss;
}

// ── component ────────────────────────────────────────────

export function BrowseV2Feature() {
  const [domain, setDomain] = useState("media");
  const [category, setCategory] = useState("");
  const [storageState, setStorageState] = useState("all");
  const [cardKind, setCardKind] = useState("all");
  const [page, setPage] = useState(1);
  const [selectedObject, setSelectedObject] = useState<BrowseV2ObjectCard | null>(null);
  const PS = 50;

  const qp = useMemo(() => ({
    domain, category: category || undefined,
    storage_state: storageState, card_kind: cardKind,
    page, page_size: PS,
  }), [domain, category, storageState, cardKind, page]);

  const { data, isLoading, isError, error } = useQuery<BrowseV2Response>({
    queryKey: ["browse-v2", qp],
    queryFn: () => listBrowseCards(qp),
  });

  const setSelectedItemId = useUIStore((s) => s.setSelectedItemId);

  function handleClick(card: BrowseV2Card) {
    if (card.card_kind === "loose_file") {
      setSelectedObject(null);
      setSelectedItemId(card.file_id);
    } else {
      setSelectedItemId(null as unknown as number);
      setSelectedObject(card as BrowseV2ObjectCard);
    }
  }

  const tree = CATEGORY_TREE[domain] || [];

  return (
    <div className="browse-v2-layout">
      {/* ── Left sidebar ── */}
      <nav className="browse-v2-sidebar">
        <div className="browse-v2-domain-tabs">
          {DOMAINS.map((d) => (
            <button
              key={d.value}
              className={`browse-v2-domain-tab${domain === d.value ? " browse-v2-domain-tab--active" : ""}`}
              onClick={() => { setDomain(d.value); setCategory(""); setPage(1); }}
            >
              {t(d.labelKey as Parameters<typeof t>[0])}
            </button>
          ))}
        </div>
        <div className="browse-v2-category-tree">
          <button
            className={`browse-v2-cat-btn${!category ? " browse-v2-cat-btn--active" : ""}`}
            onClick={() => { setCategory(""); setPage(1); }}
          >
            {t("features.browseV2.categories.all")}
          </button>
          {tree.map((group, gi) => (
            <div key={gi} className="browse-v2-cat-group">
              {group.groupKey && (
                <span className="browse-v2-cat-group-label">
                  {t(group.groupKey as Parameters<typeof t>[0])}
                </span>
              )}
              {group.items.map((it) => (
                <button
                  key={it.value}
                  className={`browse-v2-cat-btn browse-v2-cat-btn--sub${category === it.value ? " browse-v2-cat-btn--active" : ""}`}
                  onClick={() => { setCategory(it.value); setPage(1); }}
                >
                  {t(it.labelKey as Parameters<typeof t>[0])}
                </button>
              ))}
            </div>
          ))}
        </div>
      </nav>

      {/* ── Main panel ── */}
      <main className="browse-v2-main">
        <div className="workbench-toolbar browse-v2-toolbar">
          <label className="field-stack">
            <span>{t("features.browseV2.filters.storageLabel")}</span>
            <select className="select-input" value={storageState} onChange={(e) => { setStorageState(e.target.value); setPage(1); }}>
              <option value="all">{t("features.browseV2.filters.storageAll")}</option>
              <option value="external">{t("features.browseV2.filters.external")}</option>
              <option value="inbox">{t("features.browseV2.filters.inbox")}</option>
              <option value="managed">{t("features.browseV2.filters.managed")}</option>
            </select>
          </label>
          <label className="field-stack">
            <span>{t("features.browseV2.filters.cardKindLabel")}</span>
            <select className="select-input" value={cardKind} onChange={(e) => { setCardKind(e.target.value); setPage(1); }}>
              <option value="all">{t("features.browseV2.filters.cardKindAll")}</option>
              <option value="object">{t("features.browseV2.filters.objectOnly")}</option>
              <option value="loose_file">{t("features.browseV2.filters.fileOnly")}</option>
            </select>
          </label>
          {data && (
            <div className="browse-v2-summary">
              <span>{t("features.browseV2.summary.objects", { count: String(data.summary.total_objects) })}</span>
              <span className="browse-v2-summary__sep">|</span>
              <span>{t("features.browseV2.summary.looseFiles", { count: String(data.summary.total_loose_files) })}</span>
              <span className="browse-v2-summary__sep">|</span>
              <span>{t("features.browseV2.summary.managed", { count: String(data.summary.managed_objects) })}</span>
              <span className="browse-v2-summary__sep">|</span>
              <span>{t("features.browseV2.summary.inbox", { count: String(data.summary.inbox_objects) })}</span>
            </div>
          )}
        </div>

        {isLoading && <p className="browse-v2-loading">{t("common.states.loading")}</p>}
        {isError && <p className="danger-text">{t("features.browseV2.errors.loadFailed")}: {String(error)}</p>}
        {data && data.items.length === 0 && <p className="browse-v2-empty">{t("features.browseV2.empty")}</p>}

        <div className="browse-v2-cards">
          {data?.items.map((card) =>
            card.card_kind === "object" ? (
              <ObjectCard
                key={card.namespaced_id}
                card={card}
                selected={selectedObject?.namespaced_id === card.namespaced_id}
                onClick={() => handleClick(card)}
              />
            ) : (
              <LooseFileCard
                key={`f${card.file_id}`}
                card={card}
                selected={false}
                onClick={() => handleClick(card)}
              />
            )
          )}
        </div>

        {data && data.total > PS && (
          <div className="files-pager">
            <button className="secondary-button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              {t("features.browseV2.pagination.previous")}
            </button>
            <span>{t("features.browseV2.pagination.pageInfo", { page: String(page), total: String(Math.ceil(data.total / PS)) })}</span>
            <button className="secondary-button" disabled={page * PS >= data.total} onClick={() => setPage((p) => p + 1)}>
              {t("features.browseV2.pagination.next")}
            </button>
          </div>
        )}
      </main>

      {/* ── Object overview (right) ── */}
      <aside className={`browse-v2-detail${selectedObject ? " browse-v2-detail--active" : ""}`}>
        {selectedObject ? (
          <div className="browse-v2-detail__card">
            <h4 className="browse-v2-detail__title">{t("features.browseV2.overview.title")}</h4>
            <div className="key-value-row">
              <span className="key-value-row__label">{t("features.browseV2.overview.name")}</span>
              <span className="key-value-row__value">{selectedObject.display_title}</span>
            </div>
            <div className="key-value-row">
              <span className="key-value-row__label">{t("features.browseV2.overview.type")}</span>
              <span className="key-value-row__value">{objectTypeLabel(selectedObject.object_type)}</span>
            </div>
            <div className="key-value-row">
              <span className="key-value-row__label">{t("features.browseV2.overview.members", { count: String(selectedObject.member_count) })}</span>
              <span className="key-value-row__value">{selectedObject.member_count}</span>
            </div>
            <div className="key-value-row">
              <span className="key-value-row__label">{t("features.browseV2.overview.source")}</span>
              <span className="key-value-row__value">{objSourceLabel(selectedObject.object_source)}</span>
            </div>
            <div className="key-value-row">
              <span className="key-value-row__label">{t("features.browseV2.overview.status")}</span>
              <span className="key-value-row__value">
                {ssLabel(selectedObject.storage_state)}
                {selectedObject.needs_review && <> &middot; {t("features.browseV2.needsReview")}</>}
              </span>
            </div>
            <p className="browse-v2-detail__notice">{t("features.browseV2.overview.comingSoon")}</p>
          </div>
        ) : (
          <div className="browse-v2-detail__card">
            <p className="browse-v2-detail__empty">{t("features.browseV2.noSelection")}</p>
          </div>
        )}
      </aside>
    </div>
  );
}
