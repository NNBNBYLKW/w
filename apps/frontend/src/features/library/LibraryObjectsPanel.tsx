import { useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { t } from "../../shared/text";
import { queryKeys } from "../../services/query/queryKeys";
import type { LibraryObjectListItemVM, LibraryObjectListQueryInput } from "../../entities/library/types";
import { listLibraryObjects, scanLibraryObjects, getLibraryObject } from "../../services/api/libraryObjectsApi";
import { normalizeObjectTypeLabel, formatTimestamp } from "./shared/helpers";


function ObjectList({
  objects,
  selectedObjectId,
  onSelect,
}: {
  objects: LibraryObjectListItemVM[];
  selectedObjectId: number | null;
  onSelect: (objectId: number) => void;
}) {
  return (
    <div className="library-object-list library-candidate-list" role="list">
      {objects.map((item) => (
        <button
          key={item.id}
          className={`library-object-row${selectedObjectId === item.id ? " library-object-row--selected" : ""}`}
          type="button"
          onClick={() => onSelect(item.id)}
        >
          <span className="library-object-row__type">{normalizeObjectTypeLabel(item.object_type)}</span>
          <span className="library-object-row__main">
            <strong className="library-object-row__title">{item.display_title}</strong>
            <small>{item.root_path}</small>
          </span>
          <span className="library-object-row__meta">
            <span>{item.year ?? t("common.states.unavailable")}</span>
            <span>{t("features.library.objects.membersCount", { count: String(item.members_count) })}</span>
            <span>{item.metadata_source}</span>
            {item.needs_review ? <span className="status-pill status-pill--warning">{t("features.library.labels.needsReview")}</span> : null}
          </span>
        </button>
      ))}
    </div>
  );
}

function ObjectDetail({ objectId }: { objectId: number | null }) {
  const detailQuery = useQuery({
    queryKey: objectId ? queryKeys.libraryObject(objectId) : ["library-object", "idle"],
    queryFn: () => getLibraryObject(objectId as number),
    enabled: objectId !== null,
  });

  if (objectId === null) {
    return <aside className="library-object-detail library-empty-state">{t("features.library.objects.selectObject")}</aside>;
  }
  if (detailQuery.isLoading) {
    return <aside className="library-object-detail">{t("common.states.loading")}</aside>;
  }
  if (detailQuery.isError || !detailQuery.data) {
    return <aside className="library-object-detail">{t("features.library.scan.unableToLoad")}</aside>;
  }
  const detail = detailQuery.data;
  return (
    <aside className="library-object-detail">
      <span className="page-header__eyebrow">{t("features.library.objects.detailEyebrow")}</span>
      <h4>{detail.object.display_title}</h4>
      <dl>
        <div>
          <dt>{t("features.library.labels.objectType")}</dt>
          <dd>{normalizeObjectTypeLabel(detail.object.object_type)}</dd>
        </div>
        <div>
          <dt>{t("features.library.labels.rootPath")}</dt>
          <dd title={detail.object.root_path}>{detail.object.root_path}</dd>
        </div>
        <div>
          <dt>{t("features.library.labels.metadataSource")}</dt>
          <dd>{detail.object.metadata_source}</dd>
        </div>
        <div>
          <dt>{t("features.library.labels.assetYaml")}</dt>
          <dd>{detail.asset_metadata?.parse_status ?? t("common.states.unavailable")}</dd>
        </div>
        <div>
          <dt>{t("features.library.labels.reviewReason")}</dt>
          <dd>{detail.object.review_reason ?? t("common.states.none")}</dd>
        </div>
      </dl>
      <h5>{t("features.library.labels.members")}</h5>
      <div className="library-member-list">
        {detail.members.map((member) => (
          <div key={member.id} className="library-member-row">
            <span>{member.member_role}</span>
            <strong title={member.relative_path}>{member.relative_path}</strong>
            <small>{formatBytes(member.size_bytes)}</small>
          </div>
        ))}
      </div>
      {detail.members_total > detail.members.length ? (
        <small>{t("features.library.objects.membersPreview", { count: String(detail.members.length), total: String(detail.members_total) })}</small>
      ) : null}
    </aside>
  );
}


export function LibraryObjectsPanel() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [objectType, setObjectType] = useState("");
  const [reviewFilter, setReviewFilter] = useState<"all" | "review" | "ok">("all");
  const [query, setQuery] = useState("");
  const [selectedObjectId, setSelectedObjectId] = useState<number | null>(null);

  const queryParams = useMemo<LibraryObjectListQueryInput>(
    () => ({
      page,
      page_size: 20,
      object_type: objectType || undefined,
      needs_review: reviewFilter === "all" ? undefined : reviewFilter === "review",
      query: query || undefined,
      sort_by: "last_scanned_at",
      sort_order: "desc",
    }),
    [objectType, page, query, reviewFilter],
  );

  const objectsQuery = useQuery({
    queryKey: queryKeys.libraryObjects(queryParams),
    queryFn: () => listLibraryObjects(queryParams),
  });
  const scanMutation = useMutation({
    mutationFn: () => scanLibraryObjects({ dry_run: false }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.libraryOverview }),
        queryClient.invalidateQueries({ queryKey: ["library-objects"] }),
      ]);
    },
  });

  return (
    <section className="library-objects-panel library-design-panel library-design-panel--objects">
      <div className="library-panel-toolbar library-design-hero">
        <div>
          <span className="page-header__eyebrow">{t("features.library.objects.eyebrow")}</span>
          <h3>{t("features.library.objects.title")}</h3>
          <p>{t("features.library.scan.description")}</p>
        </div>
        <button className="primary-button" type="button" onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
          {scanMutation.isPending ? t("features.library.scan.running") : t("features.library.scan.action")}
        </button>
      </div>
      <div className="library-filter-row">
        <input
          value={query}
          placeholder={t("features.library.objects.searchPlaceholder")}
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(1);
          }}
        />
        <select
          value={objectType}
          onChange={(event) => {
            setObjectType(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t("features.library.objects.allTypes")}</option>
          {objectTypes.map((type) => (
            <option key={type} value={type}>
              {normalizeObjectTypeLabel(type)}
            </option>
          ))}
        </select>
        <select
          value={reviewFilter}
          onChange={(event) => {
            setReviewFilter(event.target.value as "all" | "review" | "ok");
            setPage(1);
          }}
        >
          <option value="all">{t("features.library.objects.allReviewStates")}</option>
          <option value="review">{t("features.library.labels.needsReview")}</option>
          <option value="ok">{t("features.library.objects.reviewed")}</option>
        </select>
      </div>
      {scanMutation.isError ? <p className="danger-text">{(scanMutation.error as Error).message}</p> : null}
      <div className="library-objects-layout">
        <div className="library-object-list-panel">
          {objectsQuery.isLoading ? <p>{t("common.states.loading")}</p> : null}
          {objectsQuery.isError ? <p>{t("features.library.scan.unableToLoad")}</p> : null}
          {objectsQuery.data && objectsQuery.data.items.length === 0 ? (
            <p className="library-empty-state">{t("features.library.objects.empty")}</p>
          ) : null}
          {objectsQuery.data ? (
            <ObjectList objects={objectsQuery.data.items} selectedObjectId={selectedObjectId} onSelect={setSelectedObjectId} />
          ) : null}
          {objectsQuery.data ? (
            <div className="pagination-controls">
              <button className="secondary-button" type="button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>
                {t("common.actions.previous")}
              </button>
              <span>{t("common.labels.page", { page: String(page), total: String(Math.max(1, Math.ceil(objectsQuery.data.total / objectsQuery.data.page_size))) })}</span>
              <button
                className="secondary-button"
                type="button"
                disabled={page >= Math.ceil(objectsQuery.data.total / objectsQuery.data.page_size)}
                onClick={() => setPage((value) => value + 1)}
              >
                {t("common.actions.next")}
              </button>
            </div>
          ) : null}
        </div>
        <ObjectDetail objectId={selectedObjectId} />
      </div>
    </section>
  );
}

