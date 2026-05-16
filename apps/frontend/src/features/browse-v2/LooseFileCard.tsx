import type { BrowseV2LooseFileCard } from "../../services/api/browseV2Api";
import { t } from "../../shared/text";

function fileKindLabel(fk: string | null): string {
  if (!fk) return "";
  return t(`features.browseV2.fileKind.${fk}` as Parameters<typeof t>[0]) || fk;
}

function storageStateLabel(ss: string | null): string {
  if (!ss) return "";
  return t(`features.browseV2.storageState.${ss}` as Parameters<typeof t>[0]) || ss;
}

interface Props {
  card: BrowseV2LooseFileCard;
  selected: boolean;
  onClick: () => void;
}

export function LooseFileCard({ card, selected, onClick }: Props) {
  const sizeStr = card.size_bytes != null
    ? card.size_bytes < 1024 * 1024
      ? `${(card.size_bytes / 1024).toFixed(1)} KB`
      : `${(card.size_bytes / (1024 * 1024)).toFixed(1)} MB`
    : null;
  const fkLabel = fileKindLabel(card.file_kind);
  const ssLabel = storageStateLabel(card.storage_state);
  const modStr = card.modified_at ? new Date(card.modified_at).toLocaleDateString() : null;

  return (
    <div
      className={`browse-v2-card browse-v2-card--file${selected ? " browse-v2-card--selected" : ""}`}
      onClick={onClick}
      style={{ cursor: "pointer" }}
    >
      <div className="browse-v2-card__header">
        <strong className="browse-v2-card__title">{card.name}</strong>
        {sizeStr && <span className="browse-v2-card__size">{sizeStr}</span>}
      </div>
      <div className="browse-v2-card__badges">
        <span className="status-badge status-badge--muted">{t("features.browseV2.badges.file")}</span>
        {fkLabel && <span className="status-badge status-badge--info">{fkLabel}</span>}
        {ssLabel && <span className="status-badge status-badge--secondary">{ssLabel}</span>}
      </div>
      <div className="browse-v2-card__meta">
        {sizeStr && <span>{sizeStr}</span>}
        {modStr && <span> &middot; {modStr}</span>}
      </div>
      <div className="browse-v2-card__path" title={card.path}>
        {card.path?.replace(/\\/g, "/").split("/").slice(-2).join("/") || ""}
      </div>
    </div>
  );
}
