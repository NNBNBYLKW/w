import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { useUIStore } from "../../app/providers/uiStore";
import type { ColorTagValue, FileDetailResponseVM } from "../../entities/file/types";
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
import { attachTagToFile, removeTagFromFile } from "../../services/api/tagsApi";


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


export function DetailsPanelFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const queryClient = useQueryClient();
  const [tagInput, setTagInput] = useState("");
  const [tagMutationError, setTagMutationError] = useState<string | null>(null);
  const [colorTagMutationError, setColorTagMutationError] = useState<string | null>(null);
  const [openActionError, setOpenActionError] = useState<string | null>(null);
  const [pendingOpenAction, setPendingOpenAction] = useState<"file" | "folder" | null>(null);
  const [previewLoadFailed, setPreviewLoadFailed] = useState(false);
  const parsedFileId = selectedItemId !== null ? Number(selectedItemId) : null;
  const hasInvalidSelectedId =
    selectedItemId !== null && (!Number.isInteger(parsedFileId) || parsedFileId === null || parsedFileId <= 0);
  const hasDesktopOpenActions = hasDesktopOpenActionsBridge();

  const detailQuery = useQuery({
    queryKey: parsedFileId !== null ? queryKeys.fileDetail(parsedFileId) : ["file-detail", "idle"],
    queryFn: () => getFileDetails(parsedFileId as number),
    enabled: parsedFileId !== null && !hasInvalidSelectedId,
  });

  const addTagMutation = useMutation({
    mutationFn: (name: string) => attachTagToFile(parsedFileId as number, name),
    onMutate: () => setTagMutationError(null),
    onSuccess: async () => {
      setTagInput("");
      await queryClient.invalidateQueries({
        queryKey: queryKeys.fileDetail(parsedFileId as number),
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
    },
    onError: (error) => {
      setColorTagMutationError(error instanceof Error ? error.message : "Failed to update color tag.");
    },
  });

  useEffect(() => {
    setTagInput("");
    setTagMutationError(null);
    setColorTagMutationError(null);
    setOpenActionError(null);
    setPendingOpenAction(null);
    setPreviewLoadFailed(false);
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

  if (selectedItemId === null) {
    content = (
      <>
        <span className="placeholder-pill">Awaiting selection</span>
        <h3>Details panel</h3>
        <p>Select a search result to load its indexed-file details here.</p>
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
        <p>Loading indexed-file details...</p>
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
    const isOpenActionPending = pendingOpenAction !== null;
    const isImageFile = item.file_type === "image";
    const isVideoFile = item.file_type === "video";
    const isMediaFile = isImageFile || isVideoFile;
    const metadata = item.metadata;
    content = (
      <>
        <span className="placeholder-pill">Indexed file details</span>
        <h3>{item.name}</h3>
        <dl className="details-list">
          <div className="details-list__row">
            <dt>ID</dt>
            <dd>{item.id}</dd>
          </div>
          <div className="details-list__row">
            <dt>Path</dt>
            <dd className="details-list__value--break">{item.path}</dd>
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
        <section className="metadata-section">
          <div className="metadata-section__header">
            <h4>{isMediaFile ? "Media Info" : "Metadata"}</h4>
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
                <dt>Width</dt>
                <dd>{formatMetadataValue(item.metadata.width, "px")}</dd>
              </div>
              <div className="details-list__row">
                <dt>Height</dt>
                <dd>{formatMetadataValue(item.metadata.height, "px")}</dd>
              </div>
              <div className="details-list__row">
                <dt>Duration</dt>
                <dd>{formatMetadataValue(item.metadata.duration_ms, "ms")}</dd>
              </div>
              <div className="details-list__row">
                <dt>Page count</dt>
                <dd>{formatMetadataValue(item.metadata.page_count)}</dd>
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
              Open file
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
      </>
    );
  } else {
    content = (
      <>
        <span className="placeholder-pill">Unavailable</span>
        <h3>Details panel</h3>
        <p>No detail data is currently available.</p>
      </>
    );
  }

  return <section className="panel-card">{content}</section>;
}
