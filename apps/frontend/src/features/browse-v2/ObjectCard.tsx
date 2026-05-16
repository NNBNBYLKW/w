import type { BrowseV2ObjectCard } from "../../services/api/browseV2Api";
import { t } from "../../shared/text";

function objectSourceLabel(source: string): string {
  return t(`features.browseV2.objectSource.${source}` as Parameters<typeof t>[0])
    || source;
}

function objectTypeLabel(ot: string | null): string {
  if (!ot) return "";
  const keyMap: Record<string, string> = {
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
  const key = keyMap[ot] || `features.library.inbox.objectTypes.${ot}`;
  return t(key as Parameters<typeof t>[0]) || ot;
}

function storageStateLabel(ss: string | null): string {
  if (!ss) return "";
  return t(`features.browseV2.storageState.${ss}` as Parameters<typeof t>[0]) || ss;
}

function confidenceLabel(conf: string | null): string {
  if (!conf) return "";
  return t(`features.browseV2.confidence.${conf}` as Parameters<typeof t>[0]) || conf;
}

function needsReviewLabel(nr: boolean): string {
  return nr ? t("features.browseV2.needsReview") : "";
}

interface Props {
  card: BrowseV2ObjectCard;
  selected: boolean;
  onClick: () => void;
}

export function ObjectCard({ card, selected, onClick }: Props) {
  const typeLabel = objectTypeLabel(card.object_type);
  const ssLabel = storageStateLabel(card.storage_state);
  const srcLabel = objectSourceLabel(card.object_source);
  const reviewLabel = needsReviewLabel(card.needs_review);
  const confLabel = confidenceLabel(card.confidence);

  return (
    <div
      className={`browse-v2-card browse-v2-card--object${selected ? " browse-v2-card--selected" : ""}`}
      onClick={onClick}
      style={{ cursor: "pointer" }}
      title={card.namespaced_id}
    >
      <div className="browse-v2-card__header">
        <strong className="browse-v2-card__title">{card.display_title}</strong>
      </div>
      <div className="browse-v2-card__badges">
        <span className="status-badge status-badge--primary">{t("features.browseV2.badges.object")}</span>
        {typeLabel && <span className="status-badge status-badge--info">{typeLabel}</span>}
        {ssLabel && <span className="status-badge status-badge--secondary">{ssLabel}</span>}
        {reviewLabel && <span className="status-badge status-badge--warning">{reviewLabel}</span>}
        {confLabel && <span className="status-badge status-badge--muted">{confLabel}</span>}
      </div>
      <div className="browse-v2-card__meta">
        <span>{t("features.browseV2.overview.members", { count: String(card.member_count) })}</span>
        {srcLabel && <span> &middot; {t("features.browseV2.overview.source")}: {srcLabel}</span>}
        {ssLabel && <span> &middot; {ssLabel}</span>}
      </div>
      {card.root_path && (
        <div className="browse-v2-card__path" title={card.root_path}>
          {card.root_path.replace(/\\/g, "/").split("/").slice(-2).join("/")}
        </div>
      )}
    </div>
  );
}
