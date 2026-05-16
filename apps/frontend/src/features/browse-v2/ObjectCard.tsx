import type { BrowseV2ObjectCard } from "../../services/api/browseV2Api";
import { t } from "../../shared/text";


function asTextKey(key: string): Parameters<typeof t>[0] {
  return key as Parameters<typeof t>[0];
}

function objectSourceLabel(source: string): string {
  return t(asTextKey(`features.browseV2.objectSource.${source}`)) || source;
}

function objectTypeLabel(objectType: string | null): string {
  if (!objectType) {
    return "";
  }
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
  const key = keyMap[objectType] || `features.library.inbox.objectTypes.${objectType}`;
  return t(asTextKey(key)) || objectType;
}

function storageStateLabel(storageState: string | null): string {
  if (!storageState) {
    return "";
  }
  return t(asTextKey(`features.browseV2.storageState.${storageState}`)) || storageState;
}

function confidenceLabel(confidence: string | null): string {
  if (!confidence) {
    return "";
  }
  return t(asTextKey(`features.browseV2.confidence.${confidence}`)) || confidence;
}

function objectMark(objectType: string | null): string {
  if (!objectType) {
    return "OBJ";
  }
  const normalized = objectType.replace(/_/g, " ");
  return normalized.slice(0, 3).toUpperCase();
}

interface Props {
  card: BrowseV2ObjectCard;
  selected: boolean;
  onClick: () => void;
}

export function ObjectCard({ card, selected, onClick }: Props) {
  const typeLabel = objectTypeLabel(card.object_type);
  const storageLabel = storageStateLabel(card.storage_state);
  const sourceLabel = objectSourceLabel(card.object_source);
  const confidence = confidenceLabel(card.confidence);

  return (
    <button
      className={`browse-v2-card browse-v2-card--object${selected ? " browse-v2-card--selected" : ""}`}
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      title={card.namespaced_id}
    >
      <span className="browse-v2-card__mark" aria-hidden="true">
        {objectMark(card.object_type)}
      </span>
      <span className="browse-v2-card__body">
        <span className="browse-v2-card__header">
          <strong className="browse-v2-card__title">{card.display_title}</strong>
          <span className="browse-v2-card__count">
            {t("features.browseV2.overview.members", { count: String(card.member_count) })}
          </span>
        </span>
        <span className="browse-v2-card__badges">
          <span className="status-badge status-badge--accent">{t("features.browseV2.badges.object")}</span>
          {typeLabel ? <span className="status-badge status-badge--info">{typeLabel}</span> : null}
          {storageLabel ? <span className="status-badge status-badge--secondary">{storageLabel}</span> : null}
          {card.needs_review ? <span className="status-badge status-badge--warning">{t("features.browseV2.needsReview")}</span> : null}
          {confidence ? <span className="status-badge status-badge--muted">{confidence}</span> : null}
        </span>
        <span className="browse-v2-card__meta">
          <span>{t("features.browseV2.overview.source")}: {sourceLabel}</span>
          {storageLabel ? <span>{storageLabel}</span> : null}
        </span>
        {card.root_path ? (
          <span className="browse-v2-card__path" title={card.root_path} translate="no">
            {card.root_path.replace(/\\/g, "/").split("/").slice(-2).join("/")}
          </span>
        ) : null}
      </span>
    </button>
  );
}
