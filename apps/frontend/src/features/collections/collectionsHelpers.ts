import type { CollectionVM } from "../../entities/collection/types";
import type { ColorTagValue, FileType } from "../../entities/file/types";
import type { SourceVM } from "../../entities/source/types";
import type { TagItemVM } from "../../entities/tag/types";
import { t } from "../../shared/text";

export function formatBytes(value: number | null): string {
  return value === null ? t("common.states.sizeUnavailable") : `${value.toLocaleString()} bytes`;
}

function getTagLabel(tagId: number | null, tags: TagItemVM[] | undefined): string | null {
  if (tagId === null) {
    return null;
  }
  const match = tags?.find((tag) => tag.id === tagId);
  return match?.name ?? t("common.labels.tagId", { id: tagId });
}

function getSourceLabel(sourceId: number | null, sources: SourceVM[] | undefined): string | null {
  if (sourceId === null) {
    return null;
  }

  const match = sources?.find((source) => source.id === sourceId);
  if (!match) {
    return `${t("common.labels.source")} #${sourceId}`;
  }

  return match.display_name?.trim() || match.path;
}

function getFileTypeLabel(fileType: FileType): string {
  if (fileType === "image") {
    return t("common.fileTypes.image");
  }
  if (fileType === "video") {
    return t("common.fileTypes.video");
  }
  if (fileType === "document") {
    return t("common.fileTypes.document");
  }
  if (fileType === "archive") {
    return t("common.fileTypes.archive");
  }
  return t("common.fileTypes.other");
}

function getColorTagLabel(colorTag: ColorTagValue): string {
  if (colorTag === "red") {
    return t("common.colors.red");
  }
  if (colorTag === "yellow") {
    return t("common.colors.yellow");
  }
  if (colorTag === "green") {
    return t("common.colors.green");
  }
  if (colorTag === "blue") {
    return t("common.colors.blue");
  }
  return t("common.colors.purple");
}

export function buildCollectionSummary(
  collection: CollectionVM,
  tags: TagItemVM[] | undefined,
  sources: SourceVM[] | undefined,
): string {
  const parts: string[] = [];

  if (collection.file_type) {
    parts.push(t("features.collections.summary.type", { value: getFileTypeLabel(collection.file_type) }));
  }

  const tagLabel = getTagLabel(collection.tag_id, tags);
  if (tagLabel) {
    parts.push(t("features.collections.summary.tag", { value: tagLabel }));
  }

  if (collection.color_tag) {
    parts.push(t("features.collections.summary.color", { value: getColorTagLabel(collection.color_tag) }));
  }

  const sourceLabel = getSourceLabel(collection.source_id, sources);
  if (sourceLabel) {
    parts.push(t("features.collections.summary.source", { value: sourceLabel }));
  }

  if (collection.parent_path) {
    parts.push(t("features.collections.summary.path", { value: collection.parent_path }));
  }

  return parts.length > 0 ? parts.join(" | ") : t("features.collections.summary.all");
}

export function getEntryNote(entry: string | null): string | null {
  if (entry === "media") {
    return t("features.collections.saveFrom.media");
  }
  if (entry === "books") {
    return t("features.collections.saveFrom.books");
  }
  if (entry === "software") {
    return t("features.collections.saveFrom.software");
  }
  if (entry === "games") {
    return t("features.collections.saveFrom.games");
  }
  return null;
}

export function buildCollectionNavLinks(
  collection: CollectionVM | null,
): { mediaLink: string | null; booksLink: string | null; softwareLink: string | null; gamesLink: string | null } {
  if (!collection) {
    return { mediaLink: null, booksLink: null, softwareLink: null, gamesLink: null };
  }

  const hasSourceOrPath = collection.source_id !== null || collection.parent_path !== null;
  const noFileTypeSourcePath = collection.file_type === null && !hasSourceOrPath;

  const baseParams = new URLSearchParams({ entry: "collections" });
  if (collection.tag_id !== null) baseParams.set("tag_id", String(collection.tag_id));
  if (collection.color_tag !== null) baseParams.set("color_tag", collection.color_tag);

  let mediaLink: string | null = null;
  let booksLink: string | null = null;
  let softwareLink: string | null = null;
  let gamesLink: string | null = null;

  if (
    !hasSourceOrPath &&
    (collection.file_type === null || collection.file_type === "image" || collection.file_type === "video")
  ) {
    const p = new URLSearchParams(baseParams);
    if (collection.file_type === "image" || collection.file_type === "video") {
      p.set("view_scope", collection.file_type);
    }
    mediaLink = `/browse-v2?domain=media&${p.toString()}`;
  }

  if (!hasSourceOrPath && (collection.file_type === null || collection.file_type === "document")) {
    booksLink = `/browse-v2?domain=documents&${baseParams.toString()}`;
  }

  if (noFileTypeSourcePath) {
    const p = new URLSearchParams(baseParams);
    p.set("category", "software");
    softwareLink = `/browse-v2?domain=apps&${p.toString()}`;
  }

  if (noFileTypeSourcePath) {
    const p = new URLSearchParams(baseParams);
    p.set("category", "game");
    gamesLink = `/browse-v2?domain=apps&${p.toString()}`;
  }

  return { mediaLink, booksLink, softwareLink, gamesLink };
}
