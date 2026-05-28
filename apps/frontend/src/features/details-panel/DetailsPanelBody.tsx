import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { t } from "../../shared/text";
import { ConfirmDialog, EmptyState, InspectorSection, LoadingState } from "../../shared/ui/components";
import { getSiblingFiles } from "../../services/api/fileDetailsApi";
import type { ColorTagValue, FileRatingValue, FileStatusValue } from "../../entities/file/types";
import { DetailsIdentitySection } from "./sections/DetailsIdentitySection";
import { DetailsPlacementSection } from "./sections/DetailsPlacementSection";
import { DetailsRatingSection } from "./sections/DetailsRatingSection";
import { DetailsGameStatusSection } from "./sections/DetailsGameStatusSection";
import { DetailsColorTagSection } from "./sections/DetailsColorTagSection";
import { DetailsTagsSection } from "./sections/DetailsTagsSection";
import { DetailsActionsSection } from "./sections/DetailsActionsSection";
import { DetailsFactListSection } from "./sections/DetailsFactListSection";
import { DetailsMetadataSection } from "./sections/DetailsMetadataSection";
import { DetailsStorageSection } from "./sections/DetailsStorageSection";
import { DetailsPreviewSection } from "./sections/DetailsPreviewSection";
import { DetailsBookInfoSection } from "./sections/DetailsBookInfoSection";
import { DetailsSoftwareInfoSection } from "./sections/DetailsSoftwareInfoSection";
import { DetailsMediaRetrievalSection } from "./sections/DetailsMediaRetrievalSection";
import { DetailsBookRetrievalSection } from "./sections/DetailsBookRetrievalSection";
import { DetailsSoftwareRetrievalSection } from "./sections/DetailsSoftwareRetrievalSection";
import { DetailsGameRetrievalSection } from "./sections/DetailsGameRetrievalSection";
import {
  COLOR_TAG_OPTIONS,
  GAME_STATUS_OPTIONS,
  PLACEMENT_OPTIONS,
  formatFavoriteLabel,
  formatPlacementLabel,
  formatRatingLabel,
  formatStatusLabel,
} from "./shared/detailsHelpers";
import type { RetrievalHint } from "./hooks/useDetailsMutations";

// Memoized section components for switching performance
const MemoizedIdentitySection = React.memo(DetailsIdentitySection);
const MemoizedPlacementSection = React.memo(DetailsPlacementSection);
const MemoizedRatingSection = React.memo(DetailsRatingSection);
const MemoizedGameStatusSection = React.memo(DetailsGameStatusSection);
const MemoizedColorTagSection = React.memo(DetailsColorTagSection);
const MemoizedTagsSection = React.memo(DetailsTagsSection);
const MemoizedActionsSection = React.memo(DetailsActionsSection);
const MemoizedFactListSection = React.memo(DetailsFactListSection);
const MemoizedMetadataSection = React.memo(DetailsMetadataSection);
const MemoizedStorageSection = React.memo(DetailsStorageSection);
const MemoizedPreviewSection = React.memo(DetailsPreviewSection);
const MemoizedBookInfoSection = React.memo(DetailsBookInfoSection);
const MemoizedSoftwareInfoSection = React.memo(DetailsSoftwareInfoSection);
const MemoizedMediaRetrievalSection = React.memo(DetailsMediaRetrievalSection);
const MemoizedBookRetrievalSection = React.memo(DetailsBookRetrievalSection);
const MemoizedSoftwareRetrievalSection = React.memo(DetailsSoftwareRetrievalSection);
const MemoizedGameRetrievalSection = React.memo(DetailsGameRetrievalSection);

export interface DetailsPanelBodyProps {
  batchSelectionSummary: { pageLabel: string; selectedCount: number } | null;
  selectedItemId: string | null;
  hasInvalidSelectedId: boolean;
  detailQuery: {
    isLoading: boolean;
    error: unknown;
    data: { item: any } | undefined;
  };
  // Route context
  isGamesRoute: boolean;
  isBooksRoute: boolean;
  isSoftwareRoute: boolean;
  // Mutation state & handlers
  tagInput: string;
  onTagInputChange: (value: string) => void;
  tagMutationError: string | null;
  colorTagMutationError: string | null;
  statusMutationError: string | null;
  userMetaMutationError: string | null;
  placementMutationError: string | null;
  isTagMutationPending: boolean;
  isColorTagMutationPending: boolean;
  isStatusMutationPending: boolean;
  isUserMetaMutationPending: boolean;
  isPlacementMutationPending: boolean;
  onAddTag: (event: React.FormEvent) => void;
  onRemoveTag: (tagId: number) => void;
  onToggleFavorite: () => void;
  onSetRating: (value: FileRatingValue) => void;
  onClearRating: () => void;
  onNotesSave: (notes: string | null) => void;
  onPlacementChange: (value: string) => void;
  onStatusChange: (value: FileStatusValue) => void;
  onColorTagChange: (value: ColorTagValue | null) => void;
  onOpenFile: () => void;
  onOpenFolder: () => void;
  onShowInFolder: () => void;
  isOpenActionPending: boolean;
  hasDesktopOpenActions: boolean;
  openActionError: string | null;
  // Copy
  copied: boolean;
  onCopyPath: () => void;
  // Preview
  previewLoadFailed: boolean;
  previewImageSrc: string | undefined;
  isVideoPreviewActive: boolean;
  isImageFile: boolean;
  isVideoFile: boolean;
  isMediaFile: boolean;
  isExeSoftwareFile: boolean;
  isPdfBookFile: boolean;
  isBookContext: boolean;
  isGameContext: boolean;
  isSoftwareContext: boolean;
  inferredBookFormat: string | null;
  inferredSoftwareFormat: "exe" | "msi" | "zip" | null;
  metadata: any;
  firstTag: any;
  previewRef: React.RefCallback<HTMLDivElement>;
  onPreviewImageError: () => void;
  onPreviewImageLoad: () => void;
  // Confirm remove tag
  confirmRemoveTag: { id: number; name: string } | null;
  onConfirmRemoveTag: () => void;
  onCancelRemoveTag: () => void;
  // Retrieval
  retrievalHint: RetrievalHint;
  // UI labels
  openFileLabel: string;
  // Navigation
  onSelectFile: (fileId: number) => void;
}

function SiblingFilesSection({ fileId, onSelectFile }: { fileId: number; onSelectFile: (id: number) => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["siblings", fileId],
    queryFn: () => getSiblingFiles(fileId),
    enabled: fileId > 0,
  });
  if (isLoading) return <LoadingState />;
  if (!data?.items.length) return null;
  return (
    <InspectorSection title="Files in same directory">
      {data.items.map((f) => (
        <button key={f.id} onClick={() => onSelectFile(f.id)} className="sibling-file-link">
          {f.name}
        </button>
      ))}
    </InspectorSection>
  );
}

export function DetailsPanelBody({
  batchSelectionSummary,
  selectedItemId,
  hasInvalidSelectedId,
  detailQuery,
  isGamesRoute,
  isBooksRoute,
  isSoftwareRoute,
  tagInput,
  onTagInputChange,
  tagMutationError,
  colorTagMutationError,
  statusMutationError,
  userMetaMutationError,
  placementMutationError,
  isTagMutationPending,
  isColorTagMutationPending,
  isStatusMutationPending,
  isUserMetaMutationPending,
  isPlacementMutationPending,
  onAddTag,
  onRemoveTag,
  onToggleFavorite,
  onSetRating,
  onClearRating,
  onNotesSave,
  onPlacementChange,
  onStatusChange,
  onColorTagChange,
  onOpenFile,
  onOpenFolder,
  onShowInFolder,
  isOpenActionPending,
  hasDesktopOpenActions,
  openActionError,
  copied,
  onCopyPath,
  previewLoadFailed,
  previewImageSrc,
  isVideoPreviewActive,
  isImageFile,
  isVideoFile,
  isMediaFile,
  isExeSoftwareFile,
  isPdfBookFile,
  isBookContext,
  isGameContext,
  isSoftwareContext,
  inferredBookFormat,
  inferredSoftwareFormat,
  metadata,
  firstTag,
  previewRef,
  onPreviewImageError,
  onPreviewImageLoad,
  confirmRemoveTag,
  onConfirmRemoveTag,
  onCancelRemoveTag,
  retrievalHint,
  openFileLabel,
  onSelectFile,
}: DetailsPanelBodyProps) {
  if (batchSelectionSummary) {
    return (
      <div className="details-panel details-inspector details-panel--batch">
        <InspectorSection>
          <span className="placeholder-pill">{t("details.placeholders.batch.eyebrow")}</span>
          <h3>{batchSelectionSummary.pageLabel}</h3>
          <p>{t("details.placeholders.batch.selectedCount", { count: batchSelectionSummary.selectedCount })}</p>
          <p>{t("details.placeholders.batch.description")}</p>
        </InspectorSection>
      </div>
    );
  }

  if (selectedItemId === null) {
    return (
      <div className="details-panel details-inspector details-panel--state">
        <EmptyState
          title={t("details.placeholders.awaitingSelection.title")}
          description={t("details.placeholders.awaitingSelection.description")}
        />
      </div>
    );
  }

  if (hasInvalidSelectedId) {
    return (
      <div className="details-panel details-inspector details-panel--state">
        <EmptyState
          title={t("details.placeholders.selectionError.title")}
          description={t("details.placeholders.selectionError.description")}
        />
      </div>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <div className="details-panel details-inspector details-panel--state">
        <LoadingState message={t("details.placeholders.loading.description")} />
      </div>
    );
  }

  if (detailQuery.error instanceof Error) {
    return (
      <div className="details-panel details-inspector details-panel--state">
        <EmptyState
          title={t("details.placeholders.error.title")}
          description={detailQuery.error.message}
        />
      </div>
    );
  }

  if (detailQuery.data) {
    const item = detailQuery.data.item;
    const [notes, setNotes] = useState<string>(item.notes ?? "");

    return (
      <>
        <div className="details-panel details-inspector details-panel--file" key={item.id}>
          <div className="details-inspector__group details-inspector__group--identity">
            <MemoizedIdentitySection name={item.name} fileType={item.file_type} id={item.id} />
            <MemoizedFactListSection
              path={item.path}
              fileType={item.file_type}
              sizeBytes={item.size_bytes}
              id={item.id}
              sourceId={item.source_id}
              modifiedAtFs={item.modified_at_fs}
              createdAtFs={item.created_at_fs}
              discoveredAt={item.discovered_at}
              lastSeenAt={item.last_seen_at}
              isDeleted={item.is_deleted}
              pathAction={
                <button
                  className="secondary-button"
                  onClick={onCopyPath}
                  style={{ fontSize: 12, padding: "2px 8px" }}
                  type="button"
                >
                  {copied ? t("features.detailsPanel.pathCopied") : t("features.detailsPanel.copyPath")}
                </button>
              }
            />
          </div>
          {item.storage_state && (
            <div className="details-inspector__group details-inspector__group--storage">
              <InspectorSection title={t("details.storage.title")}>
                <MemoizedStorageSection
                  storageState={item.storage_state}
                  path={item.path}
                  originalPath={item.original_path}
                  managedRootId={item.managed_root_id}
                  managedAt={item.managed_at}
                  inboxItemId={item.inbox_item_id}
                />
              </InspectorSection>
            </div>
          )}
          <div className="details-inspector__group details-inspector__group--organization">
            <MemoizedPlacementSection
              manualPlacement={item.manual_placement}
              fileKind={item.file_kind}
              autoPlacementLabel={formatPlacementLabel(item.auto_placement)}
              effectivePlacementLabel={formatPlacementLabel(item.effective_placement)}
              isPending={isPlacementMutationPending}
              error={placementMutationError}
              placementOptions={PLACEMENT_OPTIONS}
              onChange={onPlacementChange}
            />
            {isBookContext && inferredBookFormat ? (
              <MemoizedBookInfoSection
                name={item.name}
                format={inferredBookFormat}
                pageCount={metadata?.page_count ?? null}
              />
            ) : null}
            {isSoftwareContext && inferredSoftwareFormat ? (
              <MemoizedSoftwareInfoSection
                name={item.name}
                format={inferredSoftwareFormat}
              />
            ) : null}
            <MemoizedMetadataSection
              isMediaFile={isMediaFile}
              isVideoFile={isVideoFile}
              isBookContext={isBookContext}
              metadata={
                metadata
                  ? {
                      width: metadata.width ?? null,
                      height: metadata.height ?? null,
                      duration_ms: metadata.duration_ms ?? null,
                      page_count: metadata.page_count ?? null,
                      codec: metadata.codec ?? null,
                      bitrate: metadata.bitrate ?? null,
                      stream_count: metadata.stream_count ?? null,
                      author: metadata.author ?? null,
                      title: metadata.title ?? null,
                    }
                  : null
              }
            />
          </div>
          {isImageFile || isVideoFile || isExeSoftwareFile || isPdfBookFile ? (
            <div className="details-inspector__group details-inspector__group--preview">
              <MemoizedPreviewSection
                isImageFile={isImageFile}
                isVideoFile={isVideoFile}
                isExeSoftwareFile={isExeSoftwareFile}
                isPdfBookFile={isPdfBookFile}
                isVideoPreviewActive={isVideoPreviewActive}
                previewLoadFailed={previewLoadFailed}
                previewImageSrc={previewImageSrc}
                name={item.name}
                itemId={item.id}
                metadata={metadata}
                previewRef={previewRef}
                onImageError={onPreviewImageError}
                onImageLoad={onPreviewImageLoad}
              />
            </div>
          ) : null}
          <div className="details-inspector__group details-inspector__group--signals">
            <MemoizedRatingSection
              isFavorite={item.is_favorite}
              rating={item.rating}
              isPending={isUserMetaMutationPending}
              error={userMetaMutationError}
              favoriteLabel={formatFavoriteLabel(item.is_favorite)}
              ratingLabel={formatRatingLabel(item.rating)}
              onToggleFavorite={onToggleFavorite}
              onSetRating={onSetRating}
              onClearRating={onClearRating}
            />
            {isGameContext ? (
              <MemoizedGameStatusSection
                status={item.status}
                isPending={isStatusMutationPending}
                error={statusMutationError}
                statusLabel={item.status ? formatStatusLabel(item.status) : t("details.values.none")}
                statusOptions={GAME_STATUS_OPTIONS}
                onChange={onStatusChange}
              />
            ) : null}
            <MemoizedColorTagSection
              colorTag={item.color_tag}
              isPending={isColorTagMutationPending}
              error={colorTagMutationError}
              colorOptions={COLOR_TAG_OPTIONS}
              currentColorLabel={item.color_tag ?? t("details.values.none")}
              onChange={onColorTagChange}
            />
            <MemoizedTagsSection
              tags={item.tags}
              tagInput={tagInput}
              isPending={isTagMutationPending}
              error={tagMutationError}
              onTagInputChange={onTagInputChange}
              onAddTag={onAddTag}
              onRemoveTag={onRemoveTag}
            />
            <InspectorSection title="Notes">
              <textarea
                className="details-notes-textarea"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                onBlur={() => onNotesSave(notes || null)}
                maxLength={2000}
                rows={3}
                style={{ width: "100%", resize: "vertical" }}
              />
            </InspectorSection>
          </div>
          {isMediaFile && (firstTag || item.color_tag || (retrievalHint !== null && retrievalHint.kind !== "status")) ? (
            <MemoizedMediaRetrievalSection
              fileId={item.id}
              firstTag={firstTag}
              colorTag={item.color_tag}
              retrievalMessage={retrievalHint?.message ?? null}
            />
          ) : null}
          {isBookContext && (firstTag || item.color_tag || retrievalHint?.kind === "tag" || retrievalHint?.kind === "color") ? (
            <MemoizedBookRetrievalSection
              fileId={item.id}
              firstTag={firstTag}
              colorTag={item.color_tag}
              retrievalHintKind={retrievalHint?.kind ?? null}
              retrievalHintMessage={retrievalHint?.message ?? null}
            />
          ) : null}
          {isSoftwareContext &&
          (firstTag || item.color_tag || retrievalHint?.kind === "tag" || retrievalHint?.kind === "color") ? (
            <MemoizedSoftwareRetrievalSection
              fileId={item.id}
              firstTag={firstTag}
              colorTag={item.color_tag}
              retrievalHintKind={retrievalHint?.kind ?? null}
              retrievalHintMessage={retrievalHint?.message ?? null}
            />
          ) : null}
          {isGameContext ? (
            <MemoizedGameRetrievalSection
              fileId={item.id}
              firstTag={firstTag}
              colorTag={item.color_tag}
              status={item.status}
              retrievalHintKind={retrievalHint?.kind ?? null}
              retrievalHintMessage={retrievalHint?.message ?? null}
            />
          ) : null}
          <div className="details-inspector__group details-inspector__group--actions">
            <MemoizedActionsSection
              isOpenActionPending={isOpenActionPending}
              hasDesktopOpenActions={hasDesktopOpenActions}
              openActionError={openActionError}
              onOpenFile={onOpenFile}
              onOpenFolder={onOpenFolder}
              onShowInFolder={onShowInFolder}
              openFileLabel={openFileLabel}
            />
          </div>
          <div className="details-inspector__group details-inspector__group--siblings">
            <SiblingFilesSection fileId={item.id} onSelectFile={onSelectFile} />
          </div>
        </div>
        {confirmRemoveTag !== null ? (
          <ConfirmDialog
            open={confirmRemoveTag !== null}
            title={t("details.tags.removeConfirmTitle")}
            message={t("details.tags.removeConfirmMessage", { tag: confirmRemoveTag.name })}
            confirmLabel={t("details.actions.remove")}
            onConfirm={onConfirmRemoveTag}
            onCancel={onCancelRemoveTag}
          />
        ) : null}
      </>
    );
  }

  return (
    <div className="details-panel details-inspector details-panel--state">
      <EmptyState
        title={t("details.placeholders.unavailable.title")}
        description={t("details.placeholders.unavailable.description")}
      />
    </div>
  );
}
