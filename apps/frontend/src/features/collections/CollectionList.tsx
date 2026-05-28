import { useState, useRef, useEffect } from "react";
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
  onMoveCollection: (id: number, direction: "up" | "down") => void;
  onRenameCollection: (id: number, name: string) => void;
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
  onMoveCollection,
  onRenameCollection,
  onNavigateBrowse,
}: CollectionListProps) {
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const renameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (renamingId !== null) {
      renameRef.current?.focus();
      renameRef.current?.select();
    }
  }, [renamingId]);

  const items = collectionsQuery.data?.items ?? [];
  const grouped = new Map<string | null, CollectionVM[]>();
  for (const col of items) {
    const key = col.group_name ?? "";
    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key)!.push(col);
  }
  const groupKeys = [...grouped.keys()].sort((a, b) => {
    if (a === "") return 1;
    if (b === "") return -1;
    return (a ?? "").localeCompare(b ?? "");
  });

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
          {groupKeys.map((groupKey) => {
            const group = grouped.get(groupKey)!;
            return (
              <div key={groupKey ?? "__ungrouped"}>
                {groupKey ? (
                  <div className="collections-list__group-header">
                    <span className="page-header__eyebrow">{groupKey}</span>
                  </div>
                ) : null}
                {group.map((collection, idx) => (
                  <div
                    key={collection.id}
                    className={`collections-list__item${selectedCollectionId === collection.id ? " collections-list__item--selected" : ""}`}
                  >
                    {renamingId === collection.id ? (
                      <div style={{ display: "flex", gap: 4, padding: 4, alignItems: "center", flex: 1 }}>
                        <input
                          ref={renameRef}
                          className="text-input"
                          style={{ flex: 1, fontSize: 13 }}
                          value={renameValue}
                          onChange={(e) => setRenameValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && renameValue.trim()) {
                              onRenameCollection(collection.id, renameValue.trim());
                              setRenamingId(null);
                              setRenameValue("");
                            }
                            if (e.key === "Escape") {
                              setRenamingId(null);
                              setRenameValue("");
                            }
                          }}
                        />
                        <button
                          className="primary-button"
                          style={{ padding: "2px 8px", fontSize: 13 }}
                          type="button"
                          disabled={!renameValue.trim()}
                          onClick={() => {
                            onRenameCollection(collection.id, renameValue.trim());
                            setRenamingId(null);
                            setRenameValue("");
                          }}
                        >
                          {t("common.actions.save")}
                        </button>
                      </div>
                    ) : (
                      <>
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
                            className="ghost-button"
                            type="button"
                            title={t("common.actions.moveUp")}
                            disabled={idx === 0}
                            onClick={() => onMoveCollection(collection.id, "up")}
                          >
                            &uarr;
                          </button>
                          <button
                            className="ghost-button"
                            type="button"
                            title={t("common.actions.moveDown")}
                            disabled={idx === group.length - 1}
                            onClick={() => onMoveCollection(collection.id, "down")}
                          >
                            &darr;
                          </button>
                          <button
                            className="ghost-button"
                            type="button"
                            title={t("common.actions.rename")}
                            onClick={() => {
                              setRenameValue(collection.name);
                              setRenamingId(collection.id);
                            }}
                          >
                            {t("common.actions.rename")}
                          </button>
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
                      </>
                    )}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
