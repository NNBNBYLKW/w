import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import type { ColorTagValue, FileDetailResponseVM, FileRatingValue, FileStatusValue } from "../../entities/file/types";
import { updateFileColorTag } from "../../services/api/colorTagsApi";
import { getFileThumbnailUrl } from "../../services/api/fileDetailsApi";
import {
  hasDesktopOpenActionsBridge,
  normalizeIndexedFilePath,
  openIndexedContainingFolder,
  openIndexedFile,
} from "../../services/desktop/openActions";
import { getFileDetails } from "../../services/api/fileDetailsApi";
import { queryKeys } from "../../services/query/queryKeys";
import { updateFileStatus } from "../../services/api/statusApi";
import { attachTagToFile, removeTagFromFile } from "../../services/api/tagsApi";
import { updateFileUserMeta } from "../../services/api/userMetaApi";


function formatTimestamp(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Unavailable";
}


function formatBytes(value: number | null): string {
  return value === null ? "Unavailable" : `${value.toLocaleString()} bytes`;
}

function formatMetadataValue(value: number | null, suffix?: string): string {
  if (value === null) {
    return "Unavailable";
  }

  return suffix ? `${value.toLocaleString()} ${suffix}` : value.toLocaleString();
}

function formatDimensions(width: number | null, height: number | null): string {
  if (width === null && height === null) {
    return "Unavailable";
  }

  const widthLabel = width === null ? "?" : width.toLocaleString();
  const heightLabel = height === null ? "?" : height.toLocaleString();
  return `${widthLabel} × ${heightLabel} px`;
}


const COLOR_TAG_OPTIONS: ColorTagValue[] = ["red", "yellow", "green", "blue", "purple"];
const GAME_STATUS_OPTIONS: FileStatusValue[] = ["playing", "completed", "shelved"];

function formatStatusLabel(value: FileStatusValue): string {
  return value === "playing" ? "Playing" : value === "completed" ? "Completed" : "Shelved";
}

function inferBookFormat(name: string, path: string): "epub" | "pdf" | null {
  const candidate = `${name} ${path}`.toLowerCase();
  if (candidate.includes(".epub")) {
    return "epub";
  }
  if (candidate.includes(".pdf")) {
    return "pdf";
  }
  return null;
}

function buildBookDisplayTitle(name: string): string {
  const withoutExtension = name.replace(/\.(epub|pdf)$/i, "");
  const normalized = withoutExtension.replace(/_/g, " ").replace(/\s+/g, " ").trim();
  return normalized || name;
}

function formatBookFormatLabel(value: "epub" | "pdf"): string {
  return value.toUpperCase();
}

function inferSoftwareFormat(name: string, path: string): "exe" | "msi" | "zip" | null {
  const candidate = `${name} ${path}`.toLowerCase();
  if (candidate.includes(".exe")) {
    return "exe";
  }
  if (candidate.includes(".msi")) {
    return "msi";
  }
  if (candidate.includes(".zip")) {
    return "zip";
  }
  return null;
}

function buildSoftwareDisplayTitle(name: string): string {
  const withoutExtension = name.replace(/\.(exe|msi|zip)$/i, "");
  const normalized = withoutExtension.replace(/_/g, " ").replace(/\s+/g, " ").trim();
  return normalized || name;
}

function formatSoftwareFormatLabel(value: "exe" | "msi" | "zip"): string {
  return value.toUpperCase();
}

function buildSoftwareEntryTypeLabel(value: "exe" | "msi" | "zip"): string {
  if (value === "exe") {
    return "Executable entry";
  }
  if (value === "msi") {
    return "Installer package";
  }
  return "Archive package";
}

function inferGameEntry(name: string, path: string): boolean {
  const candidate = `${name} ${path}`.toLowerCase();
  if (candidate.includes(".lnk")) {
    return true;
  }
  if (!candidate.includes(".exe")) {
    return false;
  }
  return [
    "\\games\\",
    "\\game\\",
    "\\steam\\",
    "\\steamapps\\",
    "\\gog\\",
    "\\epic games\\",
    "\\itch\\",
    "\\riot games\\",
    "\\blizzard\\",
    "\\battle.net\\",
    "\\ubisoft\\",
    "\\rockstar games\\",
    "\\ea games\\",
  ].some((hint) => candidate.includes(hint));
}

function formatFavoriteLabel(isFavorite: boolean): string {
  return isFavorite ? "Marked favorite" : "Not marked";
}

function formatRatingLabel(value: FileRatingValue | null): string {
  return value === null ? "None" : `${value} / 5`;
}


export function DetailsPanelFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const batchSelectionSummary = useUIStore((state) => state.batchSelectionSummary);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const [tagInput, setTagInput] = useState("");
  const [tagMutationError, setTagMutationError] = useState<string | null>(null);
  const [colorTagMutationError, setColorTagMutationError] = useState<string | null>(null);
  const [statusMutationError, setStatusMutationError] = useState<string | null>(null);
  const [userMetaMutationError, setUserMetaMutationError] = useState<string | null>(null);
  const [openActionError, setOpenActionError] = useState<string | null>(null);
  const [pendingOpenAction, setPendingOpenAction] = useState<"file" | "folder" | null>(null);
  const [previewLoadFailed, setPreviewLoadFailed] = useState(false);
  const [retrievalHint, setRetrievalHint] = useState<
    | { kind: "tag"; message: string }
    | { kind: "color"; message: string }
    | { kind: "status"; message: string }
    | null
  >(null);
  const parsedFileId = selectedItemId !== null ? Number(selectedItemId) : null;
  const hasInvalidSelectedId =
    selectedItemId !== null && (!Number.isInteger(parsedFileId) || parsedFileId === null || parsedFileId <= 0);
  const hasDesktopOpenActions = hasDesktopOpenActionsBridge();
  const isGamesRoute = location.pathname.startsWith("/library/games");
  const isBooksRoute = location.pathname.startsWith("/library/books");
  const isSoftwareRoute = location.pathname.startsWith("/library/software");

  const invalidateRetrievalQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.tags }),
      queryClient.invalidateQueries({ queryKey: ["tag-files"] }),
      queryClient.invalidateQueries({ queryKey: ["media-library"] }),
      queryClient.invalidateQueries({ queryKey: ["books-list"] }),
      queryClient.invalidateQueries({ queryKey: ["games-list"] }),
      queryClient.invalidateQueries({ queryKey: ["software-list"] }),
      queryClient.invalidateQueries({ queryKey: ["recent"] }),
      queryClient.invalidateQueries({ queryKey: ["search"] }),
      queryClient.invalidateQueries({ queryKey: ["files-list"] }),
      queryClient.invalidateQueries({ queryKey: queryKeys.collections }),
      queryClient.invalidateQueries({ queryKey: ["collection-files"] }),
    ]);
  };

  const detailQuery = useQuery({
    queryKey: parsedFileId !== null ? queryKeys.fileDetail(parsedFileId) : ["file-detail", "idle"],
    queryFn: () => getFileDetails(parsedFileId as number),
    enabled: parsedFileId !== null && !hasInvalidSelectedId,
  });
  const currentItem = detailQuery.data?.item;
  const currentInferredBookFormat =
    currentItem !== undefined ? inferBookFormat(currentItem.name, currentItem.path) : null;
  const currentInferredSoftwareFormat =
    currentItem !== undefined ? inferSoftwareFormat(currentItem.name, currentItem.path) : null;
  const currentInferredGameEntry =
    currentItem !== undefined ? inferGameEntry(currentItem.name, currentItem.path) : false;
  const isBookContextForMutations = isBooksRoute || currentInferredBookFormat !== null;
  const isGameContextForMutations = isGamesRoute || currentInferredGameEntry || (currentItem?.status ?? null) !== null;
  const isSoftwareContextForMutations =
    !isGameContextForMutations && (isSoftwareRoute || currentInferredSoftwareFormat !== null);

  const addTagMutation = useMutation({
    mutationFn: (name: string) => attachTagToFile(parsedFileId as number, name),
    onMutate: () => setTagMutationError(null),
    onSuccess: async () => {
      setTagInput("");
      await queryClient.invalidateQueries({
        queryKey: queryKeys.fileDetail(parsedFileId as number),
      });
      await invalidateRetrievalQueries();
      setRetrievalHint({
        kind: "tag",
        message: isGameContextForMutations
          ? "Tags updated. Use Tags or Games to re-find this game entry naturally."
          : isSoftwareContextForMutations
            ? "Tags updated. Use Tags or Software to re-find this software-related file naturally."
            : "Tags updated. You can use Tags to re-find this file naturally.",
      });
    },
    onError: (error) => {
      setTagMutationError(error instanceof Error ? error.message : "Failed to add tag.");
    },
  });

  const removeTagMutation = useMutation({
    mutationFn: (tagId: number) => removeTagFromFile(parsedFileId as number, tagId),
    onMutate: () => setTagMutationError(null),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.fileDetail(parsedFileId as number),
      });
      await invalidateRetrievalQueries();
      setRetrievalHint({
        kind: "tag",
        message: isGameContextForMutations
          ? "Tags updated. Use Tags or Games to re-find this game entry naturally."
          : isSoftwareContextForMutations
            ? "Tags updated. Use Tags or Software to re-find this software-related file naturally."
            : "Tags updated. You can use Tags to re-find this file naturally.",
      });
    },
    onError: (error) => {
      setTagMutationError(error instanceof Error ? error.message : "Failed to remove tag.");
    },
  });

  const colorTagMutation = useMutation({
    mutationFn: (colorTag: ColorTagValue | null) => updateFileColorTag(parsedFileId as number, colorTag),
    onMutate: () => setColorTagMutationError(null),
    onSuccess: (response) => {
      queryClient.setQueryData<FileDetailResponseVM | undefined>(
        queryKeys.fileDetail(parsedFileId as number),
        (current) => {
          if (!current || current.item.id !== response.item.id) {
            return current;
          }
          return {
            item: {
              ...current.item,
              color_tag: response.item.color_tag,
            },
          };
        },
      );
      void invalidateRetrievalQueries();
      setRetrievalHint({
        kind: "color",
        message: response.item.color_tag
          ? isGameContextForMutations
            ? "Color tag updated. You can jump back into Games with the new color filter."
            : isBookContextForMutations
              ? "Color tag updated. You can jump back into Books with the new color filter."
              : isSoftwareContextForMutations
                ? "Color tag updated. You can jump back into Software with the new color filter."
                : "Color tag updated. You can jump back into Media with the new color filter."
          : isGameContextForMutations
            ? "Color tag cleared. Games, Recent, Tags, and Collections will refresh on the shared retrieval chain."
            : isBookContextForMutations
              ? "Color tag cleared. Books, Recent, Tags, and Collections will refresh on the shared retrieval chain."
              : isSoftwareContextForMutations
                ? "Color tag cleared. Software, Recent, Tags, and Collections will refresh on the shared retrieval chain."
                : "Color tag cleared. Media, Recent, Tags, and Collections will refresh on the shared retrieval chain.",
      });
    },
    onError: (error) => {
      setColorTagMutationError(error instanceof Error ? error.message : "Failed to update color tag.");
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: FileStatusValue | null) => updateFileStatus(parsedFileId as number, status),
    onMutate: () => setStatusMutationError(null),
    onSuccess: (response) => {
      queryClient.setQueryData<FileDetailResponseVM | undefined>(
        queryKeys.fileDetail(parsedFileId as number),
        (current) => {
          if (!current || current.item.id !== response.item.id) {
            return current;
          }
          return {
            item: {
              ...current.item,
              status: response.item.status,
            },
          };
        },
      );
      void queryClient.invalidateQueries({ queryKey: ["games-list"] });
      setRetrievalHint({
        kind: "status",
        message: response.item.status
          ? `Game status updated to ${formatStatusLabel(response.item.status)}. You can jump back into Games with the same status filter.`
          : "Game status cleared. Games results will refresh on the current subset surface.",
      });
    },
    onError: (error) => {
      setStatusMutationError(error instanceof Error ? error.message : "Failed to update game status.");
    },
  });

  const userMetaMutation = useMutation({
    mutationFn: (payload: { is_favorite?: boolean; rating?: FileRatingValue | null }) =>
      updateFileUserMeta(parsedFileId as number, payload),
    onMutate: () => setUserMetaMutationError(null),
    onSuccess: (response) => {
      queryClient.setQueryData<FileDetailResponseVM | undefined>(
        queryKeys.fileDetail(parsedFileId as number),
        (current) => {
          if (!current || current.item.id !== response.item.id) {
            return current;
          }
          return {
            item: {
              ...current.item,
              is_favorite: response.item.is_favorite,
              rating: response.item.rating,
            },
          };
        },
      );
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: ["media-library"] }),
        queryClient.invalidateQueries({ queryKey: ["books-list"] }),
        queryClient.invalidateQueries({ queryKey: ["games-list"] }),
        queryClient.invalidateQueries({ queryKey: ["software-list"] }),
        queryClient.invalidateQueries({ queryKey: ["recent"] }),
        queryClient.invalidateQueries({ queryKey: ["recent-tagged"] }),
        queryClient.invalidateQueries({ queryKey: ["recent-color-tagged"] }),
        queryClient.invalidateQueries({ queryKey: ["search"] }),
        queryClient.invalidateQueries({ queryKey: ["files-list"] }),
        queryClient.invalidateQueries({ queryKey: ["tag-files"] }),
        queryClient.invalidateQueries({ queryKey: ["collection-files"] }),
      ]);
    },
    onError: (error) => {
      setUserMetaMutationError(error instanceof Error ? error.message : "Failed to update favorite or rating.");
    },
  });

  useEffect(() => {
    setTagInput("");
    setTagMutationError(null);
    setColorTagMutationError(null);
    setStatusMutationError(null);
    setUserMetaMutationError(null);
    setOpenActionError(null);
    setPendingOpenAction(null);
    setPreviewLoadFailed(false);
    setRetrievalHint(null);
  }, [selectedItemId]);

  const handleOpenAction = async (action: "file" | "folder", filePath: string | null | undefined) => {
    const normalizedPath = normalizeIndexedFilePath(filePath);
    if (!normalizedPath) {
      setOpenActionError("This indexed file does not have a usable path for open actions.");
      return;
    }

    setOpenActionError(null);
    setPendingOpenAction(action);

    try {
      const result =
        action === "file"
          ? await openIndexedFile(normalizedPath)
          : await openIndexedContainingFolder(normalizedPath);

      if (!result.ok) {
        setOpenActionError(result.reason);
      }
    } catch (error) {
      setOpenActionError(error instanceof Error ? error.message : "Failed to complete the open action.");
    } finally {
      setPendingOpenAction(null);
    }
  };

  let content: JSX.Element;

  if (batchSelectionSummary) {
    content = (
      <>
        <span className="placeholder-pill">Batch mode</span>
        <h3>{batchSelectionSummary.pageLabel}</h3>
        <p>{batchSelectionSummary.selectedCount} files are selected on this page.</p>
        <p>Use the page-level batch bar to apply tags or color tags, then exit batch mode to return to shared details.</p>
      </>
    );
  } else if (selectedItemId === null) {
    content = (
      <>
        <span className="placeholder-pill">Awaiting selection</span>
        <h3>Details panel</h3>
        <p>Select an item to load its shared details here.</p>
      </>
    );
  } else if (hasInvalidSelectedId) {
    content = (
      <>
        <span className="placeholder-pill">Selection error</span>
        <h3>Details panel</h3>
        <p>The selected item id is not a valid file identifier.</p>
      </>
    );
  } else if (detailQuery.isLoading) {
    content = (
      <>
        <span className="placeholder-pill">Loading</span>
        <h3>Details panel</h3>
        <p>Loading shared details...</p>
      </>
    );
  } else if (detailQuery.error instanceof Error) {
    content = (
      <>
        <span className="placeholder-pill">Error</span>
        <h3>Details panel</h3>
        <p>{detailQuery.error.message}</p>
      </>
    );
  } else if (detailQuery.data) {
    const { item } = detailQuery.data;
    const isTagMutationPending = addTagMutation.isPending || removeTagMutation.isPending;
    const isColorTagMutationPending = colorTagMutation.isPending;
    const isStatusMutationPending = statusMutation.isPending;
    const isUserMetaMutationPending = userMetaMutation.isPending;
    const isOpenActionPending = pendingOpenAction !== null;
    const isImageFile = item.file_type === "image";
    const isVideoFile = item.file_type === "video";
    const isMediaFile = isImageFile || isVideoFile;
    const inferredBookFormat = inferBookFormat(item.name, item.path);
    const inferredSoftwareFormat = inferSoftwareFormat(item.name, item.path);
    const inferredGameEntry = inferGameEntry(item.name, item.path);
    const isBookContext = isBooksRoute || inferredBookFormat !== null;
    const isGameContext = isGamesRoute || inferredGameEntry || item.status !== null;
    const isSoftwareContext = !isGameContext && (isSoftwareRoute || inferredSoftwareFormat !== null);
    const metadata = item.metadata;
    const firstTag = item.tags[0] ?? null;
    content = (
      <>
        <span className="placeholder-pill">Indexed file details</span>
        <h3 className="details-panel__title" title={item.name}>
          {item.name}
        </h3>
        <dl className="details-list">
          <div className="details-list__row">
            <dt>ID</dt>
            <dd>{item.id}</dd>
          </div>
          <div className="details-list__row">
            <dt>Path</dt>
            <dd className="details-list__value--truncate" title={item.path}>
              {item.path}
            </dd>
          </div>
          <div className="details-list__row">
            <dt>Type</dt>
            <dd>{item.file_type}</dd>
          </div>
          <div className="details-list__row">
            <dt>Size</dt>
            <dd>{formatBytes(item.size_bytes)}</dd>
          </div>
          <div className="details-list__row">
            <dt>Source ID</dt>
            <dd>{item.source_id}</dd>
          </div>
          <div className="details-list__row">
            <dt>Created</dt>
            <dd>{formatTimestamp(item.created_at_fs)}</dd>
          </div>
          <div className="details-list__row">
            <dt>Modified</dt>
            <dd>{formatTimestamp(item.modified_at_fs)}</dd>
          </div>
          <div className="details-list__row">
            <dt>Discovered</dt>
            <dd>{formatTimestamp(item.discovered_at)}</dd>
          </div>
          <div className="details-list__row">
            <dt>Last seen</dt>
            <dd>{formatTimestamp(item.last_seen_at)}</dd>
          </div>
          <div className="details-list__row">
            <dt>Deleted</dt>
            <dd>{item.is_deleted ? "Yes" : "No"}</dd>
          </div>
        </dl>
        {isBookContext && inferredBookFormat ? (
          <section className="details-book-info-section">
            <div className="details-book-info-section__header">
              <h4>Book Info</h4>
            </div>
            <p className="details-book-info-section__note">
              This file is being presented through the Books subset surface as a recognized ebook entry.
            </p>
            <dl className="details-list">
              <div className="details-list__row">
                <dt>Display title</dt>
                <dd>{buildBookDisplayTitle(item.name)}</dd>
              </div>
              <div className="details-list__row">
                <dt>Format</dt>
                <dd>{formatBookFormatLabel(inferredBookFormat)}</dd>
              </div>
              <div className="details-list__row">
                <dt>Page count</dt>
                <dd>{formatMetadataValue(metadata?.page_count ?? null)}</dd>
              </div>
            </dl>
          </section>
        ) : null}
        {isSoftwareContext && inferredSoftwareFormat ? (
          <section className="details-software-info-section">
            <div className="details-software-info-section__header">
              <h4>Software Info</h4>
            </div>
            <p className="details-software-info-section__note">
              This file is being presented through the Software subset surface as a recognized software-related entry.
            </p>
            <dl className="details-list">
              <div className="details-list__row">
                <dt>Display title</dt>
                <dd>{buildSoftwareDisplayTitle(item.name)}</dd>
              </div>
              <div className="details-list__row">
                <dt>Format</dt>
                <dd>{formatSoftwareFormatLabel(inferredSoftwareFormat)}</dd>
              </div>
              <div className="details-list__row">
                <dt>Entry type</dt>
                <dd>{buildSoftwareEntryTypeLabel(inferredSoftwareFormat)}</dd>
              </div>
            </dl>
          </section>
        ) : null}
        <section className="metadata-section">
          <div className="metadata-section__header">
            <h4>{isMediaFile ? "Media Info" : isBookContext ? "Document Metadata" : "Metadata"}</h4>
          </div>
          {isMediaFile ? (
            <dl className="details-list">
              <div className="details-list__row">
                <dt>Dimensions</dt>
                <dd>{formatDimensions(metadata?.width ?? null, metadata?.height ?? null)}</dd>
              </div>
              {isVideoFile ? (
                <div className="details-list__row">
                  <dt>Duration</dt>
                  <dd>{formatMetadataValue(metadata?.duration_ms ?? null, "ms")}</dd>
                </div>
              ) : null}
            </dl>
          ) : item.metadata === null ? (
            <p>No extracted metadata available yet.</p>
          ) : (
            <dl className="details-list">
              <div className="details-list__row">
                <dt>Page count</dt>
                <dd>{formatMetadataValue(item.metadata.page_count)}</dd>
              </div>
              {isBookContext ? null : (
                <div className="details-list__row">
                  <dt>Width</dt>
                  <dd>{formatMetadataValue(item.metadata.width, "px")}</dd>
                </div>
              )}
              {isBookContext ? null : (
                <div className="details-list__row">
                  <dt>Height</dt>
                  <dd>{formatMetadataValue(item.metadata.height, "px")}</dd>
                </div>
              )}
              <div className="details-list__row">
                <dt>Duration</dt>
                <dd>{formatMetadataValue(item.metadata.duration_ms, "ms")}</dd>
              </div>
            </dl>
          )}
        </section>
        {isImageFile || isVideoFile ? (
          <section className="details-preview-section">
            <div className="details-preview-section__header">
              <h4>Preview</h4>
            </div>
            {isImageFile && !previewLoadFailed ? (
              <div className="details-preview-frame">
                <img
                  className="details-preview-image"
                  src={getFileThumbnailUrl(item.id)}
                  alt={`Preview for ${item.name}`}
                  onError={() => setPreviewLoadFailed(true)}
                />
              </div>
            ) : (
              <div className="details-preview-frame details-preview-frame--empty">
                <p className="details-preview-state">
                  {isImageFile
                    ? "Preview is unavailable for this image right now."
                    : "Preview is not available for this video yet."}
                </p>
              </div>
            )}
          </section>
        ) : null}
        <section className="details-user-meta-section">
          <div className="details-user-meta-section__header">
            <h4>Favorite & Rating</h4>
            {isUserMetaMutationPending ? <span className="status-pill">Updating…</span> : null}
          </div>
          <dl className="details-list">
            <div className="details-list__row">
              <dt>Favorite</dt>
              <dd>{formatFavoriteLabel(item.is_favorite)}</dd>
            </div>
            <div className="details-list__row">
              <dt>Rating</dt>
              <dd>{formatRatingLabel(item.rating)}</dd>
            </div>
          </dl>
          <div className="details-user-meta-actions">
            <button
              className={`ghost-button details-user-meta-button${item.is_favorite ? " details-user-meta-button--selected" : ""}`}
              type="button"
              onClick={() => userMetaMutation.mutate({ is_favorite: !item.is_favorite })}
              disabled={isUserMetaMutationPending}
            >
              {item.is_favorite ? "Remove favorite" : "Mark favorite"}
            </button>
          </div>
          <div className="details-user-meta-rating-actions">
            {[1, 2, 3, 4, 5].map((value) => (
              <button
                key={value}
                className={`ghost-button details-user-meta-button${item.rating === value ? " details-user-meta-button--selected" : ""}`}
                type="button"
                onClick={() => userMetaMutation.mutate({ rating: value as FileRatingValue })}
                disabled={isUserMetaMutationPending}
              >
                ★ {value}
              </button>
            ))}
            <button
              className={`ghost-button details-user-meta-button${item.rating === null ? " details-user-meta-button--selected" : ""}`}
              type="button"
              onClick={() => userMetaMutation.mutate({ rating: null })}
              disabled={isUserMetaMutationPending}
            >
              Clear rating
            </button>
          </div>
          {userMetaMutationError ? <p className="color-tag-section__error">{userMetaMutationError}</p> : null}
        </section>
        {isGameContext ? (
          <section className="details-game-status-section">
            <div className="details-game-status-section__header">
              <h4>Game Status</h4>
              {isStatusMutationPending ? <span className="status-pill">Updating…</span> : null}
            </div>
            <p>
              Current status: <strong>{item.status ? formatStatusLabel(item.status) : "None"}</strong>
            </p>
            <div className="details-game-status-actions">
              {GAME_STATUS_OPTIONS.map((status) => (
                <button
                  key={status}
                  className={`ghost-button details-game-status-button${item.status === status ? " details-game-status-button--selected" : ""}`}
                  type="button"
                  onClick={() => statusMutation.mutate(status)}
                  disabled={isStatusMutationPending}
                >
                  {formatStatusLabel(status)}
                </button>
              ))}
              <button
                className={`ghost-button details-game-status-button${item.status === null ? " details-game-status-button--selected" : ""}`}
                type="button"
                onClick={() => statusMutation.mutate(null)}
                disabled={isStatusMutationPending}
              >
                Clear
              </button>
            </div>
            {statusMutationError ? <p className="color-tag-section__error">{statusMutationError}</p> : null}
          </section>
        ) : null}
        <section className="color-tag-section">
          <div className="color-tag-section__header">
            <h4>Color Tag</h4>
            {isColorTagMutationPending ? <span className="status-pill">Updating…</span> : null}
          </div>
          <p>
            Current color tag: <strong>{item.color_tag ?? "None"}</strong>
          </p>
          <div className="color-tag-actions">
            {COLOR_TAG_OPTIONS.map((colorTag) => (
              <button
                key={colorTag}
                className={`ghost-button color-tag-button color-tag-button--${colorTag}${item.color_tag === colorTag ? " color-tag-button--selected" : ""}`}
                type="button"
                onClick={() => colorTagMutation.mutate(colorTag)}
                disabled={isColorTagMutationPending}
              >
                {colorTag}
              </button>
            ))}
            <button
              className={`ghost-button color-tag-button${item.color_tag === null ? " color-tag-button--selected" : ""}`}
              type="button"
              onClick={() => colorTagMutation.mutate(null)}
              disabled={isColorTagMutationPending}
            >
              Clear
            </button>
          </div>
          {colorTagMutationError ? <p className="color-tag-section__error">{colorTagMutationError}</p> : null}
        </section>
        <section className="tag-section">
          <div className="tag-section__header">
            <h4>Tags</h4>
            {isTagMutationPending ? <span className="status-pill">Updating…</span> : null}
          </div>
          <form
            className="tag-form"
            onSubmit={(event) => {
              event.preventDefault();
              addTagMutation.mutate(tagInput);
            }}
          >
            <input
              className="text-input"
              value={tagInput}
              onChange={(event) => setTagInput(event.target.value)}
              placeholder="Add a normal tag"
              disabled={isTagMutationPending}
            />
            <button className="secondary-button" type="submit" disabled={isTagMutationPending}>
              Add tag
            </button>
          </form>
          {tagMutationError ? <p className="tag-section__error">{tagMutationError}</p> : null}
          {item.tags.length === 0 ? (
            <p>No normal tags are attached to this file yet.</p>
          ) : (
            <div className="tag-chip-list">
              {item.tags.map((tag) => (
                <div key={tag.id} className="tag-chip">
                  <span>{tag.name}</span>
                  <button
                    className="ghost-button tag-chip__remove"
                    type="button"
                    onClick={() => removeTagMutation.mutate(tag.id)}
                    disabled={isTagMutationPending}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
        {isMediaFile && (firstTag || item.color_tag || (retrievalHint !== null && retrievalHint.kind !== "status")) ? (
          <section className="details-retrieval-section">
            <div className="details-retrieval-section__header">
              <h4>Re-find this media</h4>
            </div>
            <p>{retrievalHint?.message ?? "Use the shared retrieval surfaces to come back to this media after organizing it."}</p>
            <div className="details-retrieval-actions">
              {firstTag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      tag_id: String(firstTag.id),
                      focus: String(item.id),
                    });
                    navigate(`/tags?${params.toString()}`);
                  }}
                >
                  Find in Tags
                </button>
              ) : null}
              {item.color_tag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      color_tag: item.color_tag,
                      focus: String(item.id),
                      entry: "details",
                    });
                    navigate(`/library/media?${params.toString()}`);
                  }}
                >
                  Filter in Media
                </button>
              ) : null}
            </div>
          </section>
        ) : null}
        {isBookContext && (firstTag || item.color_tag || retrievalHint?.kind === "tag" || retrievalHint?.kind === "color") ? (
          <section className="details-retrieval-section">
            <div className="details-retrieval-section__header">
              <h4>Re-find this book</h4>
            </div>
            <p>
              {retrievalHint?.kind === "color"
                ? retrievalHint.message
                : retrievalHint?.kind === "tag"
                  ? "Tags updated. Use Tags or Books to land back on this ebook naturally."
                  : "Use the shared retrieval surfaces to come back to this ebook after organizing it."}
            </p>
            <div className="details-retrieval-actions">
              {firstTag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      tag_id: String(firstTag.id),
                      focus: String(item.id),
                    });
                    navigate(`/tags?${params.toString()}`);
                  }}
                >
                  Find in Tags
                </button>
              ) : null}
              {firstTag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      tag_id: String(firstTag.id),
                      focus: String(item.id),
                      entry: "details",
                    });
                    navigate(`/library/books?${params.toString()}`);
                  }}
                >
                  Open matching books
                </button>
              ) : null}
              {item.color_tag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      color_tag: item.color_tag,
                      focus: String(item.id),
                      entry: "details",
                    });
                    navigate(`/library/books?${params.toString()}`);
                  }}
                >
                  Filter in Books
                </button>
              ) : null}
            </div>
          </section>
        ) : null}
        {isSoftwareContextForMutations &&
        (firstTag || item.color_tag || retrievalHint?.kind === "tag" || retrievalHint?.kind === "color") ? (
          <section className="details-retrieval-section">
            <div className="details-retrieval-section__header">
              <h4>Re-find this software</h4>
            </div>
            <p>
              {retrievalHint?.kind === "color"
                ? retrievalHint.message
                : retrievalHint?.kind === "tag"
                  ? "Tags updated. Use Tags or Software to land back on this software-related file naturally."
                  : "Use the shared retrieval surfaces to come back to this software-related file after organizing it."}
            </p>
            <div className="details-retrieval-actions">
              {firstTag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      tag_id: String(firstTag.id),
                      focus: String(item.id),
                    });
                    navigate(`/tags?${params.toString()}`);
                  }}
                >
                  Find in Tags
                </button>
              ) : null}
              {firstTag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      tag_id: String(firstTag.id),
                      focus: String(item.id),
                      entry: "details",
                    });
                    navigate(`/library/software?${params.toString()}`);
                  }}
                >
                  Open matching software
                </button>
              ) : null}
              {item.color_tag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      color_tag: item.color_tag,
                      focus: String(item.id),
                      entry: "details",
                    });
                    navigate(`/library/software?${params.toString()}`);
                  }}
                >
                  Filter in Software
                </button>
              ) : null}
            </div>
          </section>
        ) : null}
        {isGameContext ? (
          <section className="details-retrieval-section">
            <div className="details-retrieval-section__header">
              <h4>Re-find this game</h4>
            </div>
            <p>
              {retrievalHint?.kind === "status"
                ? retrievalHint.message
                : retrievalHint?.kind === "color"
                  ? retrievalHint.message
                  : retrievalHint?.kind === "tag"
                    ? "Tags updated. Use Tags or Games to land back on this game entry naturally."
                : "Use the Games subset to come back to this game entry after opening or lightly organizing it."}
            </p>
            <div className="details-retrieval-actions">
              {firstTag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      tag_id: String(firstTag.id),
                      focus: String(item.id),
                    });
                    navigate(`/tags?${params.toString()}`);
                  }}
                >
                  Find in Tags
                </button>
              ) : null}
              {firstTag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      tag_id: String(firstTag.id),
                      focus: String(item.id),
                      entry: "details",
                    });
                    if (item.status) {
                      params.set("status", item.status);
                    }
                    navigate(`/library/games?${params.toString()}`);
                  }}
                >
                  Open matching games
                </button>
              ) : null}
              {item.color_tag ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    const params = new URLSearchParams({
                      color_tag: item.color_tag,
                      focus: String(item.id),
                      entry: "details",
                    });
                    if (item.status) {
                      params.set("status", item.status);
                    }
                    navigate(`/library/games?${params.toString()}`);
                  }}
                >
                  Filter in Games
                </button>
              ) : null}
              <button
                className="ghost-button"
                type="button"
                onClick={() => {
                  const params = new URLSearchParams({
                    focus: String(item.id),
                    entry: "details",
                  });
                  if (item.status) {
                    params.set("status", item.status);
                  }
                  navigate(`/library/games?${params.toString()}`);
                }}
              >
                Back to Games
              </button>
            </div>
          </section>
        ) : null}
        <section className="open-actions-section">
          <div className="open-actions-section__header">
            <h4>Open Actions</h4>
            {isOpenActionPending ? <span className="status-pill">Opening...</span> : null}
          </div>
          <div className="open-actions-buttons">
            <button
              className="secondary-button"
              type="button"
              onClick={() => void handleOpenAction("file", item.path)}
              disabled={isOpenActionPending || !hasDesktopOpenActions}
            >
              {isGameContext ? "Open game entry" : isSoftwareContext ? "Open software file" : "Open file"}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => void handleOpenAction("folder", item.path)}
              disabled={isOpenActionPending || !hasDesktopOpenActions}
            >
              Open containing folder
            </button>
          </div>
          {!hasDesktopOpenActions ? (
            <p className="open-actions-section__note">
              Desktop open actions are unavailable outside the desktop shell.
            </p>
          ) : null}
          {openActionError ? <p className="open-actions-section__error">{openActionError}</p> : null}
        </section>
      </>
    );
  } else {
    content = (
      <>
        <span className="placeholder-pill">Unavailable</span>
        <h3>Details panel</h3>
        <p>No shared details are currently available.</p>
      </>
    );
  }

  return <section className="panel-card">{content}</section>;
}
