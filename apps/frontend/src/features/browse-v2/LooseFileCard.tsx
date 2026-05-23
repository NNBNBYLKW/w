import type { BrowseV2LooseFileCard } from "../../services/api/browseV2Api";
import { t } from "../../shared/text";
import { asTextKey, fileKindLabel, storageStateLabel, formatBytes } from "./helpers";


function formatDate(value: string | null): string {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

function fileMark(fileKind: string | null): string {
  if (!fileKind) return "FILE";
  if (fileKind === "image") return "IMG";
  if (fileKind === "video") return "VID";
  if (fileKind === "audio") return "AUD";
  if (fileKind === "document") return "DOC";
  if (fileKind === "archive") return "ZIP";
  if (fileKind === "executable") return "EXE";
  return fileKind.slice(0, 4).toUpperCase();
}

interface Props {
  card: BrowseV2LooseFileCard;
  selected: boolean;
  checked?: boolean;
  onCheckboxToggle?: () => void;
  onClick: () => void;
}

export function LooseFileCard({ card, selected, checked, onCheckboxToggle, onClick }: Props) {
  const sizeLabel = formatBytes(card.size_bytes);
  const fileKind = fileKindLabel(card.file_kind);
  const storageLabel = storageStateLabel(card.storage_state);
  const modifiedAt = formatDate(card.modified_at);

  return (
    <button
      className={`browse-v2-card browse-v2-card--file${selected ? " browse-v2-card--selected" : ""}`}
      type="button"
      onClick={onClick}
      aria-pressed={selected}
    >
      {onCheckboxToggle && (
        <span className="browse-v2-card__check" onClick={e => { e.stopPropagation(); onCheckboxToggle(); }} style={{display:"flex",alignItems:"center",padding:"0 8px 0 0"}}>
          <input type="checkbox" checked={!!checked} readOnly tabIndex={-1} style={{cursor:"pointer",pointerEvents:"none"}} />
        </span>
      )}
      <span className="browse-v2-card__mark browse-v2-card__mark--file" aria-hidden="true">
        {fileMark(card.file_kind)}
      </span>
      <span className="browse-v2-card__body">
        <span className="browse-v2-card__header">
          <strong className="browse-v2-card__title">{card.name}</strong>
          {sizeLabel ? <span className="browse-v2-card__size">{sizeLabel}</span> : null}
        </span>
        <span className="browse-v2-card__badges">
          <span className="status-badge status-badge--muted">{t("features.browseV2.badges.file")}</span>
          {fileKind ? <span className="status-badge status-badge--info">{fileKind}</span> : null}
          {storageLabel ? <span className="status-badge status-badge--secondary">{storageLabel}</span> : null}
        </span>
        <span className="browse-v2-card__meta">
          {modifiedAt ? <span>{modifiedAt}</span> : null}
          {sizeLabel ? <span>{sizeLabel}</span> : null}
        </span>
        <span className="browse-v2-card__path" title={card.path} translate="no">
          {card.path?.replace(/\\/g, "/").split("/").slice(-2).join("/") || ""}
        </span>
      </span>
    </button>
  );
}
