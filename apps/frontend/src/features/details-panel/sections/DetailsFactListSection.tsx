import type { ReactNode } from "react";
import { t } from "../../../shared/text";
import { KeyValueRow } from "../../../shared/ui/components";
import { formatBytes, formatTimestamp } from "../shared/detailsHelpers";

export interface DetailsFactListSectionProps {
  path: string;
  fileType: string;
  sizeBytes: number | null;
  id: number;
  sourceId: number;
  modifiedAtFs: string | null;
  createdAtFs: string | null;
  discoveredAt: string;
  lastSeenAt: string;
  isDeleted: boolean;
  pathAction?: ReactNode;
}

export function DetailsFactListSection({
  path,
  fileType,
  sizeBytes,
  id,
  sourceId,
  modifiedAtFs,
  createdAtFs,
  discoveredAt,
  lastSeenAt,
  isDeleted,
  pathAction,
}: DetailsFactListSectionProps) {
  return (
    <div className="kv-list details-panel__fact-list">
      <KeyValueRow label={t("details.fields.path")} value={path} mono action={pathAction} />
      <KeyValueRow label={t("details.fields.type")} value={fileType} />
      <KeyValueRow label={t("details.fields.size")} value={formatBytes(sizeBytes)} />
      <KeyValueRow label={t("details.fields.id")} value={String(id)} mono />
      <KeyValueRow label={t("details.fields.sourceId")} value={String(sourceId)} />
      <KeyValueRow label={t("details.fields.modified")} value={formatTimestamp(modifiedAtFs)} />
      <KeyValueRow label={t("details.fields.created")} value={formatTimestamp(createdAtFs)} />
      <KeyValueRow label={t("details.fields.discovered")} value={formatTimestamp(discoveredAt)} />
      <KeyValueRow label={t("details.fields.lastSeen")} value={formatTimestamp(lastSeenAt)} />
      <KeyValueRow label={t("details.fields.deleted")} value={isDeleted ? t("details.values.yes") : t("details.values.no")} />
    </div>
  );
}
