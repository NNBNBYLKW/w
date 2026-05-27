import type { CollectionVM } from "../../entities/collection/types";
import type { SourceVM } from "../../entities/source/types";
import type { TagItemVM } from "../../entities/tag/types";
import { t } from "../../shared/text";
import { EmptyState, LoadingState } from "../../shared/ui/components";
import { buildCollectionSummary } from "./collectionsHelpers";

export interface CollectionListProps {
  collectionsQuery: {
    isLoading: boolean;
    error: unknown;
    data: { items: CollectionVM[] } | undefined;
  };
  selectedCollectionId: number | null;
  tagsData: TagItemVM[] | undefined;
  sourcesData: SourceVM[] | undefined;
  deleteCollectionPending: boolean;
  onSelectCollection: (id: number) => void;
  onEditCollection: (collection: CollectionVM) => void;
  onDeleteCollection: (id: number) => void;
  onNavigateBrowse: () => void;
}

export function CollectionList({
  collectionsQuery,
  selectedCollectionId,
  tagsData,
  sourcesData,
  deleteCollectionPending,
  onSelectCollection,
  onEditCollection,
  onDeleteCollection,
  onNavigateBrowse,
}: CollectionListProps) {
  return (
    <div className="collections-list-shell">
      <div className="collections-list-shell__header">
        <span className="page-header__eyebrow">{t("features.collections.listEyebrow")}</span>
        {collectionsQuery.data ? (
          <p>{t("common.labels.collections", { count: collectionsQuery.data.items.length })}</p>
        ) : (
          <p>{t("features.collections.listFallback")}</p>
        )}
      </div>

      {collectionsQuery.isLoading ? <LoadingState /> : null}

      {collectionsQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.collections.listUnavailableTitle")}</strong>
          <p>{collectionsQuery.error.message}</p>
        </div>
      ) : null}

      {collectionsQuery.data && collectionsQuery.data.items.length === 0 ? (
        <EmptyState
          title={t("features.collections.listEmpty")}
          description={t("features.collections.emptyGuide")}
          action={{ label: t("features.homeOverview.browseCardAction"), onClick: onNavigateBrowse }}
        />
      ) : null}

      {collectionsQuery.data && collectionsQuery.data.items.length > 0 ? (
        <div className="collections-list">
          {collectionsQuery.data.items.map((collection) => (
            <div
              key={collection.id}
              className={`collections-list__item${selectedCollectionId === collection.id ? " collections-list__item--selected" : ""}`}
            >
              <button
                className="collections-list__select"
                type="button"
                onClick={() => onSelectCollection(collection.id)}
              >
                <div className="collections-list__meta">
                  <strong title={collection.name}>{collection.name}</strong>
                  <p title={buildCollectionSummary(collection, tagsData, sourcesData)}>
                    {buildCollectionSummary(collection, tagsData, sourcesData)}
                  </p>
                </div>
              </button>
              <div className="collections-list__actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => onEditCollection(collection)}
                >
                  {t("common.actions.edit")}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => onDeleteCollection(collection.id)}
                  disabled={deleteCollectionPending}
                >
                  {t("common.actions.delete")}
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
