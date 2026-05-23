import type { BrowseV2ObjectCard } from "../../services/api/browseV2Api";
import { t } from "../../shared/text";
import { asTextKey, objectSourceLabel, objectTypeLabel, storageStateLabel, confidenceLabel } from "./helpers";


function objectMark(objectType: string | null): string {
  if (!objectType) return "OBJ";
  return objectType.replace(/_/g, " ").slice(0, 3).toUpperCase();
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
