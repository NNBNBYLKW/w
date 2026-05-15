import { t } from "../../../shared/text";
import { KeyValueRow } from "../../../shared/ui/components/KeyValueRow";

type Props = {
  storageState?: string | null;
  path?: string;
  originalPath?: string | null;
  managedRootId?: number | null;
  managedAt?: string | null;
  inboxItemId?: number | null;
};

function stateLabel(state: string): string {
  if (state === "external") return t("details.storage.external");
  if (state === "inbox") return t("details.storage.inbox");
  if (state === "managed") return t("details.storage.managed");
  return state;
}

export function DetailsStorageSection({
  storageState,
  path,
  originalPath,
  managedRootId,
  managedAt,
  inboxItemId,
}: Props) {
  if (!storageState && !path && !originalPath) return null;

  return (
    <div className="kv-list details-panel__fact-list">
      {storageState && (
        <KeyValueRow
          label={t("details.storage.state")}
          value={<span className={`details-storage-badge details-storage-badge--${storageState}`}>{stateLabel(storageState)}</span>}
        />
      )}
      {path && (
        <KeyValueRow label={t("details.storage.currentPath")} value={path} />
      )}
      {originalPath && (
        <KeyValueRow label={t("details.storage.originalPath")} value={originalPath} />
      )}
      {storageState === "managed" && managedRootId != null && (
        <KeyValueRow label={t("details.storage.managedRoot")} value={`#${managedRootId}`} />
      )}
      {storageState === "managed" && managedAt && (
        <KeyValueRow label={t("details.storage.managedAt")} value={new Date(managedAt).toLocaleString()} />
      )}
      {inboxItemId != null && (
        <KeyValueRow label={t("details.storage.inboxItem")} value={`#${inboxItemId}`} />
      )}
    </div>
  );
}
