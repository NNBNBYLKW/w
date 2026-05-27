import type { FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import type { SourceVM } from "../../entities/source/types";
import type { TagItemVM } from "../../entities/tag/types";
import type { CollectionVM } from "../../entities/collection/types";
import { t } from "../../shared/text";
import { LoadingState, Pagination } from "../../shared/ui/components";
import { buildCollectionSummary, formatBytes } from "./collectionsHelpers";

export interface CollectionResultsProps {
  selectedCollection: CollectionVM | null;
  collectionFilesQuery: {
    isLoading: boolean;
    error: unknown;
    data:
      | {
          items: Array<{
            id: number;
            name: string;
            path: string;
            file_type: string;
            modified_at: string;
            size_bytes: number | null;
          }>;
          total: number;
          page_size: number;
        }
      | undefined;
  };
  page: number;
  totalPages: number;
  sortBy: FileListSortBy;
  sortOrder: FileListSortOrder;
  selectedItemId: string | null;
  tagsData: TagItemVM[] | undefined;
  sourcesData: SourceVM[] | undefined;
  mediaLink: string | null;
  booksLink: string | null;
  gamesLink: string | null;
  softwareLink: string | null;
  onPageChange: (page: number) => void;
  onSortByChange: (value: FileListSortBy) => void;
  onSortOrderChange: (value: FileListSortOrder) => void;
  onSelectItem: (id: string) => void;
  onNavigate: (url: string) => void;
}

export function CollectionResults({
  selectedCollection,
  collectionFilesQuery,
  page,
  totalPages,
  sortBy,
  sortOrder,
  selectedItemId,
  tagsData,
  sourcesData,
  mediaLink,
  booksLink,
  gamesLink,
  softwareLink,
  onPageChange,
  onSortByChange,
  onSortOrderChange,
  onSelectItem,
  onNavigate,
}: CollectionResultsProps) {
  return (
    <div className="collections-results">
      <div className="collections-results__header">
        <div className="feature-header">
          <span className="page-header__eyebrow">{t("features.collections.resultsEyebrow")}</span>
          <h3>{selectedCollection?.name ?? t("features.collections.chooseCollection")}</h3>
          <p>
            {selectedCollection
              ? buildCollectionSummary(selectedCollection, tagsData, sourcesData)
              : t("features.collections.chooseCollectionDescription")}
          </p>
        </div>
        <div className="files-meta-row__actions">
          {mediaLink ? (
            <button className="ghost-button" type="button" onClick={() => onNavigate(mediaLink)}>
              {t("common.actions.openMatchingMedia")}
            </button>
          ) : null}
          {booksLink ? (
            <button className="ghost-button" type="button" onClick={() => onNavigate(booksLink)}>
              {t("common.actions.openMatchingBooks")}
            </button>
          ) : null}
          {gamesLink ? (
            <button className="ghost-button" type="button" onClick={() => onNavigate(gamesLink)}>
              {t("common.actions.openMatchingGames")}
            </button>
          ) : null}
          {softwareLink ? (
            <button className="ghost-button" type="button" onClick={() => onNavigate(softwareLink)}>
              {t("common.actions.openMatchingSoftware")}
            </button>
          ) : null}
        </div>
      </div>

      {selectedCollection ? (
        <>
          <div className="files-toolbar">
            <label className="field-stack files-toolbar__field">
              <span>{t("common.labels.sortBy")}</span>
              <select
                className="select-input"
                value={sortBy}
                onChange={(event) => {
                  onSortByChange(event.target.value as FileListSortBy);
                  onPageChange(1);
                }}
              >
                <option value="modified_at">{t("common.sortBy.modified")}</option>
                <option value="name">{t("common.sortBy.name")}</option>
                <option value="discovered_at">{t("common.sortBy.discovered")}</option>
              </select>
            </label>
            <label className="field-stack files-toolbar__field">
              <span>{t("common.labels.order")}</span>
              <select
                className="select-input"
                value={sortOrder}
                onChange={(event) => {
                  onSortOrderChange(event.target.value as FileListSortOrder);
                  onPageChange(1);
                }}
              >
                <option value="desc">{t("common.sortOrder.descending")}</option>
                <option value="asc">{t("common.sortOrder.ascending")}</option>
              </select>
            </label>
          </div>

          <div className="files-meta-row">
            <p>{t("features.collections.resultsMeta")}</p>
            {collectionFilesQuery.data ? <span>{t("common.labels.files", { count: collectionFilesQuery.data.total })}</span> : null}
          </div>

          {collectionFilesQuery.isLoading ? <LoadingState /> : null}

          {collectionFilesQuery.error instanceof Error ? (
            <div className="status-block page-card">
              <strong>{t("features.collections.resultsUnavailableTitle")}</strong>
              <p>{collectionFilesQuery.error.message}</p>
            </div>
          ) : null}

          {collectionFilesQuery.data && collectionFilesQuery.data.items.length === 0 ? (
            <div className="future-frame">{t("features.collections.resultsEmpty")}</div>
          ) : null}

          {collectionFilesQuery.data && collectionFilesQuery.data.items.length > 0 ? (
            <>
              <div className="files-list">
                {collectionFilesQuery.data.items.map((item) => (
                  <button
                    key={item.id}
                    className={`files-list-row${selectedItemId === String(item.id) ? " files-list-row--selected" : ""}`}
                    type="button"
                    onClick={() => onSelectItem(String(item.id))}
                  >
                    <div className="files-list-row__meta">
                      <strong title={item.name}>{item.name}</strong>
                      <p title={item.path}>{item.path}</p>
                    </div>
                    <div className="files-list-row__badges">
                      <span className="status-pill">{item.file_type}</span>
                      <span className="status-pill">{new Date(item.modified_at).toLocaleString()}</span>
                      <span className="status-pill">{formatBytes(item.size_bytes)}</span>
                    </div>
                  </button>
                ))}
              </div>

              <Pagination page={page} totalPages={totalPages} onPageChange={onPageChange} />
            </>
          ) : null}
        </>
      ) : (
        <div className="future-frame">{t("features.collections.emptyFallback")}</div>
      )}
    </div>
  );
}
