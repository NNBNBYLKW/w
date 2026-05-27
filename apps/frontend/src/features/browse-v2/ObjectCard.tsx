import type { BrowseV2ObjectCard } from "../../services/api/browseV2Api";
import { t } from "../../shared/text";
import { asTextKey, objectSourceLabel, objectTypeLabel, storageStateLabel, confidenceLabel } from "./helpers";


function objectMark(objectType: string | null): string {
  if (!objectType) return "OBJ";
  return objectType.replace(/_/g, " ").slice(0, 3).toUpperCase();
}

function formatBadge(objectType: string | null): string {
  if (!objectType) return "";
  const parts = objectType.replace(/_/g, " ").split(" ");
  return parts.length > 1 ? parts[1].toUpperCase() : parts[0].toUpperCase();
}

interface Props {
  card: BrowseV2ObjectCard;
  selected: boolean;
  onClick: () => void;
}

export function ObjectCard({ card, selected, onClick }: Props) {
  const rawType = card.object_type?.toLowerCase() ?? "";
  const typeLabel = objectTypeLabel(card.object_type);
  const storageLabel = storageStateLabel(card.storage_state);
  const sourceLabel = objectSourceLabel(card.object_source);
  const confidence = confidenceLabel(card.confidence);

  const isVideo = rawType === "movie" || rawType === "video";
  const isGame = rawType === "game";
  const isBookLike = rawType === "book" || rawType === "document";

  if (isVideo) {
    return (
      <button
        className={`browse-v2-card browse-v2-card--video${selected ? " browse-v2-card--selected" : ""}`}
        type="button"
        onClick={onClick}
        aria-pressed={selected}
        title={card.namespaced_id}
      >
        <span className="browse-v2-card__poster browse-v2-card__poster--video">
          <span className="browse-v2-card__poster-icon">{objectMark(card.object_type)}</span>
        </span>
        <span className="browse-v2-card__body">
          <span className="browse-v2-card__header">
            <strong className="browse-v2-card__title">{card.display_title}</strong>
          </span>
          <span className="browse-v2-card__badges">
            <span className="status-badge status-badge--accent">{t("features.browseV2.badges.object")}</span>
            {typeLabel ? <span className="status-badge status-badge--info">{typeLabel}</span> : null}
            {storageLabel ? <span className="status-badge status-badge--secondary">{storageLabel}</span> : null}
            {card.needs_review ? <span className="status-badge status-badge--warning">{t("features.browseV2.needsReview")}</span> : null}
          </span>
          {card.member_count > 0 ? (
            <span className="browse-v2-card__meta">
              <span>{card.member_count} {t("features.browseV2.overview.members", { count: String(card.member_count) })}</span>
            </span>
          ) : null}
        </span>
      </button>
    );
  }

  if (isGame) {
    return (
      <button
        className={`browse-v2-card browse-v2-card--game${selected ? " browse-v2-card--selected" : ""}`}
        type="button"
        onClick={onClick}
        aria-pressed={selected}
        title={card.namespaced_id}
      >
        <span className="browse-v2-card__poster browse-v2-card__poster--game">
          <span className="browse-v2-card__poster-icon">GAME</span>
        </span>
        <span className="browse-v2-card__body">
          <span className="browse-v2-card__header">
            <strong className="browse-v2-card__title">{card.display_title}</strong>
            <span className="browse-v2-card__count">
              {card.member_count} executable{card.member_count !== 1 ? "s" : ""}
            </span>
          </span>
          <span className="browse-v2-card__badges">
            <span className="status-badge status-badge--accent">{t("features.browseV2.badges.object")}</span>
            {typeLabel ? <span className="status-badge status-badge--info">{typeLabel}</span> : null}
            {storageLabel ? <span className="status-badge status-badge--secondary">{storageLabel}</span> : null}
            {card.needs_review ? <span className="status-badge status-badge--warning">{t("features.browseV2.needsReview")}</span> : null}
            {confidence ? <span className="status-badge status-badge--muted">{confidence}</span> : null}
          </span>
        </span>
      </button>
    );
  }

  if (isBookLike) {
    return (
      <button
        className={`browse-v2-card browse-v2-card--book${selected ? " browse-v2-card--selected" : ""}`}
        type="button"
        onClick={onClick}
        aria-pressed={selected}
        title={card.namespaced_id}
      >
        <span className="browse-v2-card__poster browse-v2-card__poster--book">
          <span className="browse-v2-card__poster-icon">{formatBadge(card.object_type)}</span>
        </span>
        <span className="browse-v2-card__body">
          <span className="browse-v2-card__header">
            <strong className="browse-v2-card__title">{card.display_title}</strong>
          </span>
          <span className="browse-v2-card__badges">
            <span className="status-badge status-badge--accent">{t("features.browseV2.badges.object")}</span>
            {card.object_type ? <span className="browse-v2-card__format-badge">{formatBadge(card.object_type)}</span> : null}
            {storageLabel ? <span className="status-badge status-badge--secondary">{storageLabel}</span> : null}
            {card.needs_review ? <span className="status-badge status-badge--warning">{t("features.browseV2.needsReview")}</span> : null}
          </span>
          {confidence ? <span className="browse-v2-card__meta"><span>{confidence}</span></span> : null}
        </span>
      </button>
    );
  }

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
