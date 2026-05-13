import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import type {
  LibraryObjectListItemVM,
  LibraryObjectListQueryInput,
  LibraryRootVM,
  OrganizeActionLogItemVM,
  OrganizeActionItemVM,
  OrganizeCandidateItemVM,
  OrganizeCandidateListQueryInput,
  OrganizePlanListQueryInput,
  PreflightResponseVM,
  CopyFailedActionsResponseVM,
  GenerateAssetYamlMergeResponseVM,
  GenerateRollbackResponseVM,
  OrganizeSuggestionItemVM,
  OrganizeTemplateItemVM,
  ReconcilePlanResponseVM,
} from "../../entities/library/types";
import {
  acceptOrganizeSuggestion,
  cancelOrganizePlan,
  createLibraryRoot,
  executeOrganizePlan,
  generateOrganizePlan,
  generateOrganizeSuggestions,
  getLibraryObject,
  getLibraryOverview,
  getOrganizePlan,
  getOrganizePlanLogs,
  getOrganizeStats,
  ignoreOrganizeCandidate,
  listLibraryObjects,
  listOrganizeSuggestions,
  listLibraryRoots,
  listOrganizeCandidates,
  listOrganizePlans,
  markOrganizePlanReady,
  preflightOrganizePlan,
  copyFailedActions,
  generateAssetYamlMerge,
  generateRollbackPlan,
  listOrganizeTemplates,
  reconcileOrganizePlan,
  rejectOrganizeSuggestion,
  scanLibraryObjects,
  scanOrganizeCandidates,
  setDefaultLibraryRoot,
  updateLibraryRoot,
  updateOrganizeAction,
} from "../../services/api/libraryObjectsApi";
import { queryKeys } from "../../services/query/queryKeys";
import { t } from "../../shared/text";
import { PlanStatusPill, StatusBadge, ActionButton, KeyValueRow } from "../../shared/ui/components";
import { FileBrowserFeature } from "../file-browser/FileBrowserFeature";


type LibraryTab = "overview" | "roots" | "path" | "pending" | "objects" | "plans";

const libraryTabs: Array<{ value: LibraryTab; labelKey: Parameters<typeof t>[0] }> = [
  { value: "overview", labelKey: "features.library.tabs.overview" },
  { value: "roots", labelKey: "features.library.tabs.roots" },
  { value: "path", labelKey: "features.library.tabs.path" },
  { value: "pending", labelKey: "features.library.tabs.pending" },
  { value: "objects", labelKey: "features.library.tabs.objects" },
  { value: "plans", labelKey: "features.library.tabs.plans" },
];

const objectTypes = ["movie", "anime", "collection", "game", "course", "imgset", "docset", "project", "clip", "unknown_object"];
const organizeDetectedTypes = ["movie", "anime", "game", "course", "imgset", "docset", "clip", "unknown"];

function isLibraryTab(value: string | null): value is LibraryTab {
  return libraryTabs.some((tab) => tab.value === value);
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return t("common.states.unavailable");
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? t("common.states.unavailable") : date.toLocaleString();
}

function formatBytes(value: number | null): string {
  if (value === null) return t("common.states.sizeUnavailable");
  if (value < 1024) return `${value.toLocaleString()} bytes`;
  const units = ["KB", "MB", "GB", "TB"];
  let current = value / 1024;
  let unitIndex = 0;
  while (current >= 1024 && unitIndex < units.length - 1) {
    current /= 1024;
    unitIndex += 1;
  }
  return `${current.toFixed(current >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatSuggestionPayloadSummary(suggestion: OrganizeSuggestionItemVM): string {
  try {
    const payload = JSON.parse(suggestion.payload_json) as Record<string, unknown>;
    if (suggestion.suggestion_type === "title") return String(payload.title ?? "");
    if (suggestion.suggestion_type === "object_type") return String(payload.object_type ?? "");
    if (suggestion.suggestion_type === "template_key") return String(payload.template_key ?? "");
    if (suggestion.suggestion_type === "tags") {
      return Array.isArray(payload.tags) ? payload.tags.map(String).join(", ") || "—" : "—";
    }
    if (suggestion.suggestion_type === "asset_yaml") {
      return [`type: ${payload.type ?? "—"}`, `title: ${payload.title ?? "—"}`, `year: ${payload.year ?? "—"}`].join(" · ");
    }
    return suggestion.payload_json.slice(0, 160);
  } catch {
    return suggestion.payload_json.slice(0, 160);
  }
}

function normalizeObjectTypeLabel(value: string): string {
  return value.replace(/_/g, " ").toUpperCase();
}

function LibraryPlaceholderPanel({
  eyebrow,
  title,
  body,
  note,
}: {
  eyebrow: string;
  title: string;
  body: string;
  note: string;
}) {
  return (
    <section className="library-placeholder-panel">
      <div className="feature-header">
        <span className="page-header__eyebrow">{eyebrow}</span>
        <h3>{title}</h3>
        <p>{body}</p>
      </div>
      <div className="library-safety-note">
        <strong>{t("features.library.readOnlyBadge")}</strong>
        <p>{note}</p>
      </div>
    </section>
  );
}

function ScanObjectsButton() {
  const queryClient = useQueryClient();
  const [scanResult, setScanResult] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => scanLibraryObjects({ dry_run: false }),
    onSuccess: async (result) => {
      setScanResult(
        t("features.library.scan.result", {
          found: String(result.objects_found),
          review: String(result.needs_review),
        }),
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.libraryOverview }),
        queryClient.invalidateQueries({ queryKey: ["library-objects"] }),
      ]);
    },
  });

  return (
    <div className="library-scan-card">
      <div>
        <strong>{t("features.library.scan.title")}</strong>
        <p>{t("features.library.scan.description")}</p>
      </div>
      <button className="primary-button" type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
        {mutation.isPending ? t("features.library.scan.running") : t("features.library.scan.action")}
      </button>
      {scanResult ? <small>{scanResult}</small> : null}
      {mutation.isError ? <small className="danger-text">{(mutation.error as Error).message}</small> : null}
    </div>
  );
}

function LibraryOverviewPanel() {
  const overviewQuery = useQuery({
    queryKey: queryKeys.libraryOverview,
    queryFn: getLibraryOverview,
  });
  const organizeStatsQuery = useQuery({
    queryKey: queryKeys.organizeStats,
    queryFn: getOrganizeStats,
  });
  const stats = overviewQuery.data;
  const organizeStats = organizeStatsQuery.data;
  return (
    <section className="library-overview-grid library-design-panel library-design-panel--overview">
      <LibraryPlaceholderPanel
        eyebrow={t("features.library.overview.eyebrow")}
        title={t("features.library.overview.title")}
        body={t("features.library.overview.description")}
        note={t("features.library.overview.safety")}
      />
      <div className="library-overview-card">
        <span className="page-header__eyebrow">{t("features.library.overview.statsEyebrow")}</span>
        {overviewQuery.isLoading ? <p>{t("common.states.loading")}</p> : null}
        {overviewQuery.isError ? <p>{t("features.library.scan.unableToLoad")}</p> : null}
        {stats ? (
          <div className="library-stat-grid">
            <div className="library-stat-card">
              <span>{t("features.library.stats.totalObjects")}</span>
              <strong>{stats.total_objects.toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.stats.needsReview")}</span>
              <strong>{stats.needs_review_count.toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.stats.unknownObjects")}</span>
              <strong>{stats.unknown_object_count.toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.stats.invalidYaml")}</span>
              <strong>{stats.asset_yaml_invalid_count.toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.organize.stats.pendingCandidates")}</span>
              <strong>{(organizeStats?.pending_candidates ?? 0).toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.organize.stats.draftPlans")}</span>
              <strong>{(organizeStats?.draft_plans ?? 0).toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.organize.stats.readyPlans")}</span>
              <strong>{(organizeStats?.ready_plans ?? 0).toLocaleString()}</strong>
            </div>
            <div className="library-stat-card">
              <span>{t("features.library.organize.stats.blockedActions")}</span>
              <strong>{(organizeStats?.blocked_actions ?? 0).toLocaleString()}</strong>
            </div>
          </div>
        ) : null}
        <p className="library-muted-line">
          {t("features.library.stats.lastScan")}: {formatTimestamp(stats?.last_object_scan_at)}
        </p>
      </div>
      <ScanObjectsButton />
    </section>
  );
}

function LibraryRootsPanel() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [addPath, setAddPath] = useState("");
  const [addDisplayName, setAddDisplayName] = useState("");
  const [addError, setAddError] = useState<string | null>(null);

  const { data: roots, isLoading } = useQuery({
    queryKey: queryKeys.libraryRoots,
    queryFn: listLibraryRoots,
  });

  const selectFolder =
    (window as Window & { assetWorkbench?: { selectFolder?: () => Promise<string | null> } })
      .assetWorkbench?.selectFolder ?? null;

  const handleChooseFolder = async () => {
    if (!selectFolder) return;
    const selected = await selectFolder();
    if (selected) {
      setAddPath(selected);
      if (!addDisplayName.trim()) {
        setAddDisplayName(selected.replace(/[/\\]$/, "").split(/[/\\]/).pop() ?? selected);
      }
    }
  };

  const createMutation = useMutation({
    mutationFn: createLibraryRoot,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.libraryRoots });
      setShowAdd(false);
      setAddPath("");
      setAddDisplayName("");
      setAddError(null);
    },
    onError: (err: Error) => setAddError(err.message),
  });

  const setDefaultMutation = useMutation({
    mutationFn: setDefaultLibraryRoot,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.libraryRoots }),
  });

  const disableMutation = useMutation({
    mutationFn: (rootId: number) => updateLibraryRoot(rootId, { is_enabled: false }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.libraryRoots }),
  });

  const enableMutation = useMutation({
    mutationFn: (rootId: number) => updateLibraryRoot(rootId, { is_enabled: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.libraryRoots }),
  });

  const managedRoots = (roots ?? []).filter((r) => r.root_kind === "managed");

  return (
    <section className="library-roots-panel library-design-panel library-design-panel--roots">
      <div className="library-roots-panel__intro library-design-hero">
        <span className="page-header__eyebrow">{t("features.library.roots.eyebrow")}</span>
        <h3>{t("features.library.roots.add")}</h3>
        <p>
          {t("features.library.roots.descriptionNew")}
        </p>
      </div>

      {isLoading ? (
        <p className="library-muted-line">{t("common.states.loading")}</p>
      ) : managedRoots.length === 0 ? (
        <p className="library-muted-line">{t("features.library.roots.empty")}</p>
      ) : (
        <ul className="library-roots-list library-design-card-list" role="list">
          {managedRoots.map((root) => (
            <li key={root.id} className={`library-root-card library-design-card${root.is_enabled ? " library-root-card--enabled" : " library-root-card--disabled"}`}>
              <div className="library-root-card__info">
                <div className="library-root-card__row">
                  <strong>{root.display_name ?? root.root_path}</strong>
                </div>
                <div className="library-root-card__row">
                  <span className="library-root-card__path">{root.root_path}</span>
                </div>
                <div className="library-root-card__row library-root-card__badges">
                  <StatusBadge variant="muted">managed</StatusBadge>
                  {root.is_enabled ? <StatusBadge variant="success">enabled</StatusBadge> : null}
                  {root.is_default ? <StatusBadge variant="accent">default</StatusBadge> : null}
                  {root.is_enabled ? null : <StatusBadge variant="danger">disabled</StatusBadge>}
                </div>
              </div>
              <div className="library-root-card__actions">
                {!root.is_default && root.is_enabled ? (
                  <ActionButton variant="secondary" size="sm" onClick={() => setDefaultMutation.mutate(root.id)} disabled={setDefaultMutation.isPending}>
                    {t("features.library.roots.setDefault")}
                  </ActionButton>
                ) : null}
                {root.is_enabled ? (
                  <ActionButton variant="secondary" size="sm" onClick={() => disableMutation.mutate(root.id)} disabled={disableMutation.isPending}>
                    {t("features.library.roots.disable")}
                  </ActionButton>
                ) : (
                  <ActionButton variant="success" size="sm" onClick={() => enableMutation.mutate(root.id)} disabled={enableMutation.isPending}>
                    {t("features.library.roots.enable")}
                  </ActionButton>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <button
        className="secondary-button library-root-add-toggle"
        type="button"
        onClick={() => setShowAdd(true)}
      >
        + {t("features.library.roots.add")}
      </button>

      {showAdd ? (
        <div className="library-root-add-form library-design-card">
          {selectFolder ? (
            <div className="library-root-add-form__path-row">
              <label>
                {t("features.library.roots.addPathLabel")}
                <input
                  type="text"
                  value={addPath}
                  onChange={(e) => setAddPath(e.target.value)}
                  placeholder="G:\Library"
                  readOnly
                />
              </label>
              <button className="secondary-button" type="button" onClick={handleChooseFolder}>
                {t("features.library.roots.chooseFolder")}
              </button>
            </div>
          ) : (
            <>
              <p className="library-muted-line">{t("features.library.roots.browserFallbackInput")}</p>
              <label>
                {t("features.library.roots.addPathLabel")}
                <input
                  type="text"
                  value={addPath}
                  onChange={(e) => setAddPath(e.target.value)}
                  placeholder="G:\Library"
                />
              </label>
            </>
          )}
          <label>
            {t("features.library.roots.addDisplayNameLabel")}
            <input
              type="text"
              value={addDisplayName}
              onChange={(e) => setAddDisplayName(e.target.value)}
              placeholder={t("features.library.roots.addDisplayNamePlaceholder")}
            />
          </label>
          {addError ? <p className="form-error">{addError}</p> : null}
          <div className="library-root-add-form__actions">
            <button
              className="primary-button"
              type="button"
              onClick={() =>
                createMutation.mutate({
                  root_path: addPath,
                  display_name: addDisplayName || undefined,
                })
              }
              disabled={!addPath.trim() || createMutation.isPending}
            >
              {t("features.library.roots.addConfirm")}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                setShowAdd(false);
                setAddPath("");
                setAddDisplayName("");
                setAddError(null);
              }}
            >
              {t("common.actions.cancel")}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function LibraryPathBrowserPanel() {
  return (
    <section className="library-path-panel library-design-panel library-design-panel--path">
      <div className="library-path-panel__intro library-design-hero">
        <span className="page-header__eyebrow">{t("features.library.path.eyebrow")}</span>
        <p>{t("features.library.path.description")}</p>
      </div>
      <FileBrowserFeature />
    </section>
  );
}

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
            <strong>{item.display_title}</strong>
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

function LibraryObjectsPanel() {
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

function CandidateList({
  candidates,
  selectedIds,
  selectedCandidateId,
  onToggle,
  onSelect,
}: {
  candidates: OrganizeCandidateItemVM[];
  selectedIds: number[];
  selectedCandidateId: number | null;
  onToggle: (candidateId: number) => void;
  onSelect: (candidateId: number) => void;
}) {
  return (
    <div className="library-object-list" role="list">
      {candidates.map((item) => (
        <button
          key={item.id}
          className={`library-object-row library-candidate-row${selectedCandidateId === item.id ? " library-object-row--selected" : ""}`}
          type="button"
          onClick={() => onSelect(item.id)}
        >
          <span className="library-candidate-check" onClick={(event) => event.stopPropagation()}>
            <input
              type="checkbox"
              checked={selectedIds.includes(item.id)}
              onChange={() => onToggle(item.id)}
              aria-label={item.display_name}
            />
          </span>
          <span className="library-object-row__main">
            <strong>{item.display_name}</strong>
            <small>{item.source_path}</small>
          </span>
          <span className="library-object-row__meta">
            <span>{item.candidate_type}</span>
            <span>{item.detected_type}</span>
            <span>{item.confidence}</span>
            <span className="status-pill">{item.status}</span>
          </span>
        </button>
      ))}
    </div>
  );
}

function CandidateDetail({
  candidate,
  onIgnore,
  isIgnoring,
}: {
  candidate: OrganizeCandidateItemVM | null;
  onIgnore: (candidateId: number) => void;
  isIgnoring: boolean;
}) {
  const queryClient = useQueryClient();
  const candidateId = candidate?.id ?? 0;
  const suggestionsQuery = useQuery({
    queryKey: queryKeys.organizeSuggestions(candidateId),
    queryFn: () => listOrganizeSuggestions(candidateId),
    enabled: candidate !== null,
  });
  const generateSuggestionsMutation = useMutation({
    mutationFn: generateOrganizeSuggestions,
    onSuccess: async (_data, id) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.organizeSuggestions(id) });
    },
  });
  const acceptSuggestionMutation = useMutation({
    mutationFn: acceptOrganizeSuggestion,
    onSuccess: async () => {
      if (candidate) await queryClient.invalidateQueries({ queryKey: queryKeys.organizeSuggestions(candidate.id) });
    },
  });
  const rejectSuggestionMutation = useMutation({
    mutationFn: rejectOrganizeSuggestion,
    onSuccess: async () => {
      if (candidate) await queryClient.invalidateQueries({ queryKey: queryKeys.organizeSuggestions(candidate.id) });
    },
  });
  if (!candidate) {
    return <aside className="library-object-detail library-empty-state">{t("features.library.organize.selectCandidate")}</aside>;
  }
  const suggestions = suggestionsQuery.data?.items ?? [];
  const acceptedTemplate = suggestions.find((item) => item.suggestion_type === "template_key" && item.status === "accepted");
  const mutationError = (
    generateSuggestionsMutation.error || acceptSuggestionMutation.error || rejectSuggestionMutation.error
  ) as Error | null;
  return (
    <aside className="library-object-detail library-candidate-detail library-design-card">
      <div className="library-detail-heading">
        <span className="placeholder-pill">{t("features.library.organize.candidate")}</span>
        <h4>{candidate.display_name}</h4>
      </div>
      <div className="library-candidate-meta">
        <KeyValueRow label={t("features.library.organize.suggestedType")} value={candidate.detected_type} />
        <KeyValueRow label={t("features.library.organize.confidence")} value={candidate.confidence} />
        <KeyValueRow label={t("features.library.organize.reason")} value={candidate.reason} />
        <KeyValueRow label={t("features.library.organize.sourcePath")} value={candidate.source_path} mono />
      </div>
      <section className="library-suggestions-section library-design-card">
        <div className="library-toolbar-actions">
          <ActionButton variant="primary" size="sm" onClick={() => generateSuggestionsMutation.mutate(candidate.id)} disabled={generateSuggestionsMutation.isPending}>
            {generateSuggestionsMutation.isPending ? t("features.library.organize.generatingSuggestions") : t("features.library.organize.generateSuggestions")}
          </ActionButton>
          <StatusBadge variant="muted">rule_based · local only</StatusBadge>
        </div>
        {mutationError ? <p className="danger-text">{mutationError.message}</p> : null}
        {acceptedTemplate ? (
          <p className="library-muted-line">
            {t("features.library.organize.acceptedTemplateSuggestion")}: <strong>{formatSuggestionPayloadSummary(acceptedTemplate)}</strong>. {t("features.library.organize.selectSuggestedTemplateBeforeGenerate")}
          </p>
        ) : null}
        {suggestionsQuery.isLoading ? <p className="library-muted-line">{t("common.states.loading")}</p> : null}
        {!suggestionsQuery.isLoading && suggestions.length === 0 ? <p className="library-muted-line">{t("features.library.organize.noSuggestions")}</p> : null}
        {suggestions.map((suggestion) => (
          <div className="library-suggestion-card" key={suggestion.id}>
            <div className="library-suggestion-card__header">
              <span className="library-suggestion-card__type">{suggestion.suggestion_type}</span>
              <StatusBadge variant={suggestion.status === "accepted" ? "success" : suggestion.status === "rejected" ? "danger" : "warning"}>{suggestion.status}</StatusBadge>
              <span className="library-suggestion-card__confidence">{(suggestion.confidence ?? 0).toFixed(2)}</span>
            </div>
            <span className="library-suggestion-card__reason">{suggestion.reason}</span>
            <span className="library-suggestion-card__payload">{formatSuggestionPayloadSummary(suggestion)}</span>
            {suggestion.status === "pending" ? (
              <div className="library-suggestion-card__actions">
                <ActionButton variant="success" size="sm" onClick={() => acceptSuggestionMutation.mutate(suggestion.id)}>
                  {t("features.library.organize.acceptSuggestion")}
                </ActionButton>
                <ActionButton variant="danger" size="sm" onClick={() => rejectSuggestionMutation.mutate(suggestion.id)}>
                  {t("features.library.organize.rejectSuggestion")}
                </ActionButton>
              </div>
            ) : null}
          </div>
        ))}
      </section>
      <ActionButton variant="secondary" size="sm" onClick={() => onIgnore(candidate.id)} disabled={isIgnoring || candidate.status === "ignored"}>
        {t("features.library.organize.ignore")}
      </ActionButton>
    </aside>
  );
}

function LibraryPendingPanel() {
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const [detectedType, setDetectedType] = useState("");
  const [status, setStatus] = useState("pending");
  const [showRootSelector, setShowRootSelector] = useState(false);
  const [pendingGenerateIds, setPendingGenerateIds] = useState<number[]>([]);
  const [selectedTargetRootId, setSelectedTargetRootId] = useState<number | null>(null);
  const [selectedTemplateKey, setSelectedTemplateKey] = useState<string>("");
  const templatesQuery = useQuery({
    queryKey: ["organize-templates"],
    queryFn: listOrganizeTemplates,
  });

  const queryParams = useMemo<OrganizeCandidateListQueryInput>(
    () => ({
      page: 1,
      page_size: 50,
      status: status || undefined,
      detected_type: detectedType || undefined,
    }),
    [detectedType, status],
  );
  const candidatesQuery = useQuery({
    queryKey: queryKeys.organizeCandidates(queryParams),
    queryFn: () => listOrganizeCandidates(queryParams),
  });
  const { data: roots } = useQuery({
    queryKey: queryKeys.libraryRoots,
    queryFn: listLibraryRoots,
  });
  const enabledRoots = useMemo(
    () => (roots ?? []).filter((r) => r.is_enabled && r.root_kind === "managed"),
    [roots],
  );
  const defaultRoot = useMemo(
    () => enabledRoots.find((r) => r.is_default) ?? null,
    [enabledRoots],
  );
  const effectiveTargetRootId = useMemo<number | null>(() => {
    if (selectedTargetRootId !== null) return selectedTargetRootId;
    if (enabledRoots.length === 1) return enabledRoots[0].id;
    if (defaultRoot) return defaultRoot.id;
    return null;
  }, [selectedTargetRootId, enabledRoots, defaultRoot]);
  const needsRootSelection = enabledRoots.length > 1 && !defaultRoot && selectedTargetRootId === null;
  const effectiveTargetRoot = enabledRoots.find((r) => r.id === effectiveTargetRootId) ?? null;
  const scanMutation = useMutation({
    mutationFn: scanOrganizeCandidates,
    onSuccess: async () => {
      setSelectedIds([]);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["organize-candidates"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.organizeStats }),
      ]);
    },
  });
  const ignoreMutation = useMutation({
    mutationFn: ignoreOrganizeCandidate,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["organize-candidates"] });
    },
  });
  const generateMutation = useMutation({
    mutationFn: ({ ids, rootId, tplKey }: { ids: number[]; rootId?: number; tplKey?: string }) =>
      generateOrganizePlan(ids, rootId, tplKey),
    onSuccess: async () => {
      setSelectedIds([]);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["organize-candidates"] }),
        queryClient.invalidateQueries({ queryKey: ["organize-plans"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.organizeStats }),
      ]);
    },
  });
  const handleGenerateClick = () => {
    if (selectedIds.length === 0) return;
    if (needsRootSelection) {
      setPendingGenerateIds(selectedIds);
      setShowRootSelector(true);
      return;
    }
    generateMutation.mutate({ ids: selectedIds, rootId: effectiveTargetRootId ?? undefined, tplKey: selectedTemplateKey || undefined });
  };
  const handleConfirmRootSelection = (rootId: number | null) => {
    setSelectedTargetRootId(rootId);
    setShowRootSelector(false);
    generateMutation.mutate({ ids: pendingGenerateIds, rootId: rootId ?? undefined, tplKey: selectedTemplateKey || undefined });
  };
  const selectedCandidate = candidatesQuery.data?.items.find((item) => item.id === selectedCandidateId) ?? null;
  const toggleCandidate = (candidateId: number) => {
    setSelectedIds((current) =>
      current.includes(candidateId) ? current.filter((value) => value !== candidateId) : [...current, candidateId],
    );
  };
  return (
    <section className="library-objects-panel library-design-panel library-design-panel--pending">
      <div className="library-panel-toolbar library-design-hero">
        <div>
          <span className="page-header__eyebrow">{t("features.library.pending.eyebrow")}</span>
          <h3>{t("features.library.organize.candidatesTitle")}</h3>
          <p>{t("features.library.organize.phase3Safety")}</p>
        </div>
        <div className="library-toolbar-actions">
          <ActionButton variant="secondary" size="sm" onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
            {scanMutation.isPending ? t("features.library.organize.scanningCandidates") : t("features.library.organize.scanCandidates")}
          </ActionButton>
          {templatesQuery.data?.items.length ? (
            <select className="library-template-select" value={selectedTemplateKey} onChange={(event) => setSelectedTemplateKey(event.target.value)} aria-label={t("features.library.organize.selectTemplate")}>
              <option value="">{t("features.library.organize.templateDefault")}</option>
              {templatesQuery.data.items.map((tpl) => (
                <option key={tpl.template_key} value={tpl.template_key}>
                  {tpl.name}
                </option>
              ))}
            </select>
          ) : null}
          <ActionButton variant="primary" size="sm" onClick={handleGenerateClick} disabled={selectedIds.length === 0 || generateMutation.isPending}>
            {t("features.library.organize.generatePlan")}
          </ActionButton>
        </div>
        {enabledRoots.length > 0 ? (
          <p className="library-muted-line">
            {t("features.library.organize.targetRoot")}:{" "}
            {effectiveTargetRoot ? (
              <strong>
                {effectiveTargetRoot.display_name ?? effectiveTargetRoot.root_path}
                {effectiveTargetRoot.is_default ? ` (${t("features.library.roots.defaultBadge")})` : ""}
              </strong>
            ) : needsRootSelection ? (
              <button
                className="link-button"
                type="button"
                onClick={() => {
                  setPendingGenerateIds(selectedIds);
                  setShowRootSelector(true);
                }}
              >
                {t("features.library.organize.selectRoot")}
              </button>
            ) : (
              <span>{t("features.library.organize.targetRootNone")}</span>
            )}
          </p>
        ) : null}
      </div>
      <div className="library-filter-row">
        <select value={detectedType} onChange={(event) => setDetectedType(event.target.value)}>
          <option value="">{t("features.library.objects.allTypes")}</option>
          {organizeDetectedTypes.map((type) => (
            <option key={type} value={type}>
              {type.toUpperCase()}
            </option>
          ))}
        </select>
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="pending">{t("features.library.organize.statusPending")}</option>
          <option value="added_to_plan">{t("features.library.organize.statusAdded")}</option>
          <option value="ignored">{t("features.library.organize.statusIgnored")}</option>
          <option value="">{t("features.library.objects.allReviewStates")}</option>
        </select>
      </div>
      {scanMutation.isSuccess ? <p className="library-muted-line">{t("features.library.organize.scanResult", { count: String(scanMutation.data.scanned_count) })}</p> : null}
      {scanMutation.isError || generateMutation.isError || ignoreMutation.isError ? (
        <p className="danger-text">{((scanMutation.error || generateMutation.error || ignoreMutation.error) as Error).message}</p>
      ) : null}
      <div className="library-objects-layout library-pending-layout">
        <div className="library-object-list-panel library-design-card">
          {candidatesQuery.isLoading ? <p>{t("common.states.loading")}</p> : null}
          {candidatesQuery.isError ? <p>{t("features.library.scan.unableToLoad")}</p> : null}
          {candidatesQuery.data && candidatesQuery.data.items.length === 0 ? (
            <p className="library-empty-state">{t("features.library.pending.empty")}</p>
          ) : null}
          {candidatesQuery.data ? (
            <CandidateList
              candidates={candidatesQuery.data.items}
              selectedIds={selectedIds}
              selectedCandidateId={selectedCandidateId}
              onToggle={toggleCandidate}
              onSelect={setSelectedCandidateId}
            />
          ) : null}
        </div>
        <CandidateDetail candidate={selectedCandidate} onIgnore={(id) => ignoreMutation.mutate(id)} isIgnoring={ignoreMutation.isPending} />
      </div>
      {showRootSelector ? (
        <div className="library-confirm-panel" role="dialog" aria-modal="true">
          <strong>{t("features.library.organize.selectRoot")}</strong>
          <ul className="library-root-selector-list" role="listbox">
            {enabledRoots.map((root) => (
              <li key={root.id}>
                <label className="library-root-selector-option">
                  <input
                    type="radio"
                    name="targetLibraryRoot"
                    checked={selectedTargetRootId === root.id}
                    onChange={() => setSelectedTargetRootId(root.id)}
                  />
                  <span>
                    {root.display_name ? `${root.display_name} — ` : ""}
                    {root.root_path}
                    {root.is_default ? ` (${t("features.library.roots.defaultBadge")})` : ""}
                  </span>
                </label>
              </li>
            ))}
            <li>
              <label className="library-root-selector-option">
                <input
                  type="radio"
                  name="targetLibraryRoot"
                  checked={selectedTargetRootId === null}
                  onChange={() => setSelectedTargetRootId(null)}
                />
                <span>{t("features.library.organize.targetSourceRoot")}</span>
              </label>
            </li>
          </ul>
          <div className="library-toolbar-actions">
            <button
              className="primary-button"
              type="button"
              onClick={() => handleConfirmRootSelection(selectedTargetRootId)}
            >
              {t("features.library.organize.generatePlan")}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                setShowRootSelector(false);
                setPendingGenerateIds([]);
              }}
            >
              {t("features.library.organize.dismiss")}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function PlanDetail({
  planId,
}: {
  planId: number | null;
}) {
  const queryClient = useQueryClient();
  const [preflightResult, setPreflightResult] = useState<PreflightResponseVM | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmChecked, setConfirmChecked] = useState(false);
  const detailQuery = useQuery({
    queryKey: planId ? queryKeys.organizePlan(planId) : ["organize-plan", "idle"],
    queryFn: () => getOrganizePlan(planId as number),
    enabled: planId !== null,
    refetchInterval: (query) => (query.state.data?.plan.status === "executing" ? 1500 : false),
  });
  const logsQuery = useQuery({
    queryKey: planId ? queryKeys.organizePlanLogs(planId) : ["organize-plan-logs", "idle"],
    queryFn: () => getOrganizePlanLogs(planId as number),
    enabled: planId !== null,
    refetchInterval: () => (detailQuery.data?.plan.status === "executing" ? 1500 : false),
  });
  const markReadyMutation = useMutation({
    mutationFn: markOrganizePlanReady,
    onSuccess: async (detail) => {
      setPreflightResult(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlan(detail.plan.id) }),
        queryClient.invalidateQueries({ queryKey: ["organize-plans"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.organizeStats }),
      ]);
    },
  });
  const preflightMutation = useMutation({
    mutationFn: preflightOrganizePlan,
    onSuccess: async (result) => {
      setPreflightResult(result);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlan(result.plan_id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlanLogs(result.plan_id) }),
        queryClient.invalidateQueries({ queryKey: ["organize-plans"] }),
      ]);
    },
  });
  const executeMutation = useMutation({
    mutationFn: executeOrganizePlan,
    onSuccess: async (result) => {
      setConfirmOpen(false);
      setConfirmChecked(false);
      setPreflightResult(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlan(result.plan_id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlanLogs(result.plan_id) }),
        queryClient.invalidateQueries({ queryKey: ["organize-plans"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.organizeStats }),
      ]);
    },
  });
  const cancelMutation = useMutation({
    mutationFn: cancelOrganizePlan,
    onSuccess: async (detail) => {
      setPreflightResult(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlan(detail.plan.id) }),
        queryClient.invalidateQueries({ queryKey: ["organize-plans"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.organizeStats }),
      ]);
    },
  });
  const updateActionMutation = useMutation({
    mutationFn: ({ actionId, targetPath }: { actionId: number; targetPath: string }) =>
      updateOrganizeAction(actionId, { target_path: targetPath }),
    onSuccess: async (detail) => {
      setPreflightResult(null);
      await queryClient.invalidateQueries({ queryKey: queryKeys.organizePlan(detail.plan.id) });
    },
  });
  const [reconcileResult, setReconcileResult] = useState<ReconcilePlanResponseVM | null>(null);
  const reconcileMutation = useMutation({
    mutationFn: reconcileOrganizePlan,
    onSuccess: async (result) => {
      setReconcileResult(result);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlan(result.plan_id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlanLogs(result.plan_id) }),
        queryClient.invalidateQueries({ queryKey: ["organize-plans"] }),
      ]);
    },
  });
  const [copyFailedResult, setCopyFailedResult] = useState<CopyFailedActionsResponseVM | null>(null);
  const copyFailedMutation = useMutation({
    mutationFn: copyFailedActions,
    onSuccess: async (result) => {
      setCopyFailedResult(result);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlan(detail.plan.id) }),
        queryClient.invalidateQueries({ queryKey: ["organize-plans"] }),
      ]);
    },
  });
  const [generateRollbackResult, setGenerateRollbackResult] = useState<GenerateRollbackResponseVM | null>(null);
  const generateRollbackMutation = useMutation({
    mutationFn: generateRollbackPlan,
    onSuccess: async (result) => {
      setGenerateRollbackResult(result);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlan(detail.plan.id) }),
        queryClient.invalidateQueries({ queryKey: ["organize-plans"] }),
      ]);
    },
  });

  const [mergeResult, setMergeResult] = useState<GenerateAssetYamlMergeResponseVM | null>(null);
  const mergeMutation = useMutation({
    mutationFn: generateAssetYamlMerge,
    onSuccess: async (result) => {
      setMergeResult(result);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.organizePlan(detail.plan.id) }),
        queryClient.invalidateQueries({ queryKey: ["organize-plans"] }),
      ]);
    },
  });

  useEffect(() => {
    setPreflightResult(null);
    setConfirmOpen(false);
    setConfirmChecked(false);
    setReconcileResult(null);
    setCopyFailedResult(null);
    setGenerateRollbackResult(null);
    setMergeResult(null);
  }, [planId]);

  if (planId === null) {
    return <aside className="library-object-detail library-empty-state">{t("features.library.organize.selectPlan")}</aside>;
  }
  if (detailQuery.isLoading) return <aside className="library-object-detail">{t("common.states.loading")}</aside>;
  if (detailQuery.isError || !detailQuery.data) return <aside className="library-object-detail">{t("features.library.scan.unableToLoad")}</aside>;

  const detail = detailQuery.data;
  const canExecute = detail.plan.status === "ready" && preflightResult?.can_execute === true;
  const isExecuting = detail.plan.status === "executing";
  const mutationError = (
    markReadyMutation.error ||
    preflightMutation.error ||
    executeMutation.error ||
    cancelMutation.error ||
    updateActionMutation.error ||
    reconcileMutation.error ||
    copyFailedMutation.error ||
    generateRollbackMutation.error ||
    mergeMutation.error
  ) as Error | null;
  return (
    <aside className="library-object-detail library-plan-detail library-design-card">
      <div className="library-detail-heading">
        <span className="page-header__eyebrow">{t("features.library.organize.planDetail")}</span>
        <h4>{detail.plan.title}</h4>
        <PlanStatusPill status={detail.plan.status} />
      </div>
      <p className="library-muted-line">
        {t("features.library.organize.targetRoot")}:{" "}
        {detail.plan.target_root_path ? (
          <strong>{detail.plan.target_root_path}</strong>
        ) : (
          <span>{t("features.library.organize.targetRootNone")}</span>
        )}
      </p>
      {detail.plan.template_key ? (
        <p className="library-muted-line">{t("features.library.organize.selectTemplate")}: <strong>{detail.plan.template_key}</strong></p>
      ) : null}
      <p className="library-muted-line">{t("features.library.organize.markReadyNotice")}</p>
      <div className="library-toolbar-actions library-plan-command-bar">
        <button
          className="primary-button"
          type="button"
          disabled={detail.plan.status !== "draft" || markReadyMutation.isPending || isExecuting}
          onClick={() => markReadyMutation.mutate(detail.plan.id)}
        >
          {t("features.library.organize.markReady")}
        </button>
        <button
          className="secondary-button"
          type="button"
          disabled={detail.plan.status !== "ready" || preflightMutation.isPending || isExecuting}
          onClick={() => preflightMutation.mutate(detail.plan.id)}
        >
          {preflightMutation.isPending ? t("features.library.organize.preflightRunning") : t("features.library.organize.preflight")}
        </button>
        <button
          className="primary-button"
          type="button"
          disabled={!canExecute || executeMutation.isPending || isExecuting}
          onClick={() => setConfirmOpen(true)}
        >
          {t("features.library.organize.executePlan")}
        </button>
        <button
          className="secondary-button"
          type="button"
          disabled={!["draft", "ready"].includes(detail.plan.status) || cancelMutation.isPending || isExecuting}
          onClick={() => cancelMutation.mutate(detail.plan.id)}
        >
          {t("features.library.organize.cancelPlan")}
        </button>
      </div>
      {mutationError ? (
        <p className="danger-text">{mutationError.message}</p>
      ) : null}
      {preflightResult ? (
        <div className={`library-execution-notice${preflightResult.can_execute ? " library-execution-notice--ok" : " library-execution-notice--blocked"}`}>
          <strong>{preflightResult.can_execute ? t("features.library.organize.preflightPassed") : t("features.library.organize.preflightBlocked")}</strong>
          <span>
            {t("features.library.organize.blocked")}: {preflightResult.blocked_count} · {t("features.library.organize.warning")}: {preflightResult.warning_count}
          </span>
        </div>
      ) : null}
      <dl className="library-plan-meta-grid">
        <div>
          <dt>{t("common.labels.status")}</dt>
          <dd><PlanStatusPill status={detail.plan.status} /></dd>
        </div>
        <div>
          <dt>{t("features.library.organize.actions")}</dt>
          <dd>{detail.plan.actions_count}</dd>
        </div>
        <div>
          <dt>{t("features.library.organize.blocked")}</dt>
          <dd>{detail.plan.blocked_count}</dd>
        </div>
        <div>
          <dt>{t("features.library.organize.failed")}</dt>
          <dd>{detail.plan.failed_count}</dd>
        </div>
        <div>
          <dt>{t("features.library.organize.skipped")}</dt>
          <dd>{detail.plan.skipped_count}</dd>
        </div>
        <div>
          <dt>{t("features.library.organize.executionStarted")}</dt>
          <dd>{formatTimestamp(detail.plan.execution_started_at)}</dd>
        </div>
        <div>
          <dt>{t("features.library.organize.executionFinished")}</dt>
          <dd>{formatTimestamp(detail.plan.execution_finished_at)}</dd>
        </div>
      </dl>
      {["completed", "completed_with_errors", "failed"].includes(detail.plan.status) ? (
        <section className="library-reconcile-section">
          <h5>{t("features.library.organize.executionFollowUp")}</h5>
          {detail.plan.execution_summary_json ? (() => {
            try {
              const execSummary = JSON.parse(detail.plan.execution_summary_json);
              return (
                <div className="library-exec-summary">
                  {execSummary.affected_source_ids?.length > 0 ? (
                    <p>{t("features.library.organize.affectedSources")}: {execSummary.affected_source_ids.join(", ")}</p>
                  ) : null}
                  {execSummary.affected_library_root_ids?.length > 0 ? (
                    <p>{t("features.library.organize.affectedRoots")}: {execSummary.affected_library_root_ids.join(", ")}</p>
                  ) : null}
                </div>
              );
            } catch {
              return null;
            }
          })() : null}
          <div className="library-toolbar-actions">
            <button
              className="secondary-button"
              type="button"
              onClick={() => scanLibraryObjects({})}
            >
              {t("features.library.organize.rescanLibraryObjects")}
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={reconcileMutation.isPending}
              onClick={() => reconcileMutation.mutate(detail.plan.id)}
            >
              {reconcileMutation.isPending
                ? t("features.library.organize.reconciling")
                : t("features.library.organize.reconcilePlan")}
            </button>
            {(detail.plan.status === "completed_with_errors" || detail.plan.status === "failed") &&
             (detail.plan.failed_count > 0 || detail.plan.blocked_count > 0 || detail.plan.skipped_count > 0) ? (
              <button
                className="secondary-button"
                type="button"
                disabled={copyFailedMutation.isPending}
                onClick={() => copyFailedMutation.mutate(detail.plan.id)}
              >
                {copyFailedMutation.isPending
                  ? "..."
                  : t("features.library.organize.copyFailedActions")}
              </button>
            ) : null}
            {["completed", "completed_with_errors", "failed"].includes(detail.plan.status) &&
             detail.actions.some((a) => a.action_type === "move" || a.action_type === "rename") ? (
              <button
                className="secondary-button"
                type="button"
                disabled={generateRollbackMutation.isPending}
                onClick={() => generateRollbackMutation.mutate(detail.plan.id)}
              >
                {generateRollbackMutation.isPending
                  ? "..."
                  : t("features.library.organize.generateRollback")}
              </button>
            ) : null}
            {detail.actions.some((a) => a.action_type === "write_asset_yaml" && (a.conflict_status === "blocked" || a.conflict_status === "warning")) ? (
              <button
                className="secondary-button"
                type="button"
                disabled={mergeMutation.isPending}
                onClick={() => {
                  const blockedAssetYaml = detail.actions.find((a) => a.action_type === "write_asset_yaml" && (a.conflict_status === "blocked" || a.conflict_status === "warning"));
                  if (blockedAssetYaml) mergeMutation.mutate(blockedAssetYaml.id);
                }}
              >
                {mergeMutation.isPending
                  ? "..."
                  : t("features.library.organize.mergeAssetYaml")}
              </button>
            ) : null}
          </div>
          {detail.plan.target_library_root_id ? (
            <p className="library-muted-line">{t("features.library.organize.addTargetAsSourceHint")}</p>
          ) : null}
          {reconcileResult ? (
            <div className="library-reconcile-results">
              <h6>{t("features.library.organize.reconcileResults")}</h6>
              <p>{t("features.library.organize.reconcileStatus")}: {t(`features.library.organize.reconcileStatuses.${reconcileResult.reconcile_status}` as never)}</p>
              <ul className="library-reconcile-summary">
                {Object.entries(reconcileResult.summary).map(([status, count]) => (
                  <li key={status}>
                    {t(`features.library.organize.reconcileStatuses.${status}` as never)}: {count}
                  </li>
                ))}
              </ul>
              <div className="library-action-list library-action-list--scroll">
                {reconcileResult.actions.map((ra) => (
                  <div key={ra.action_id} className="library-action-row">
                    <span className="library-action-type">{ra.action_type}</span>
                    {ra.source_path ? <span className="library-action-path">{ra.source_path}</span> : null}
                    {ra.target_path ? <span className="library-action-path">{ra.target_path}</span> : null}
                    <span className={`library-conflict-badge library-conflict-badge--${ra.reconcile_status.includes("missing") || ra.reconcile_status === "both_missing" || ra.reconcile_status === "unknown" ? "blocked" : "ok"}`}>
                      {t(`features.library.organize.reconcileStatuses.${ra.reconcile_status}` as never)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {copyFailedResult ? (
            <div className="library-reconcile-results">
              <h6>{t("features.library.organize.copyFailedActions")}</h6>
              <p>{t("features.library.organize.copyFailedActionsSuccess", { id: copyFailedResult.new_plan_id, count: copyFailedResult.copied_actions_count })}</p>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setSelectedPlanId(copyFailedResult.new_plan_id)}
              >
                {t("features.library.organize.openNewPlan")}
              </button>
            </div>
          ) : null}
          {generateRollbackResult ? (
            <div className="library-reconcile-results">
              <h6>{t("features.library.organize.generateRollback")}</h6>
              <p>{t("features.library.organize.generateRollbackSuccess", { id: generateRollbackResult.rollback_plan_id, count: generateRollbackResult.rollback_actions_count, blocked: generateRollbackResult.blocked_actions_count })}</p>
              {generateRollbackResult.blocked_actions.length > 0 ? (
                <div className="library-reconcile-summary">
                  <strong>{t("features.library.organize.blockedActions")}:</strong>
                  {generateRollbackResult.blocked_actions.map((ba) => (
                    <div key={ba.source_action_id} className="library-action-row">
                      <span>{t("features.library.organize.actions")} #{ba.source_action_id}</span>
                      <small>{ba.reason}</small>
                    </div>
                  ))}
                </div>
              ) : null}
              <button
                className="secondary-button"
                type="button"
                onClick={() => setSelectedPlanId(generateRollbackResult.rollback_plan_id)}
              >
                {t("features.library.organize.openRollbackPlan")}
              </button>
            </div>
          ) : null}
          {mergeResult ? (
            <div className="library-reconcile-results">
              <h6>{t("features.library.organize.mergeAssetYaml")}</h6>
              <p>{t("features.library.organize.mergeAssetYamlSuccess", { id: mergeResult.merge_plan_id, diff_count: mergeResult.field_diff.length })}</p>
              {mergeResult.field_diff.length > 0 ? (
                <div className="library-reconcile-summary">
                  <strong>{t("features.library.organize.fieldDiff")}:</strong>
                  {mergeResult.field_diff.map((fd) => (
                    <div key={fd.field} className="library-action-row">
                      <span className="library-field-diff-field">{fd.field}</span>
                      <span className={`status-pill status-pill--${fd.status === "conflict" || fd.status === "kept_current" ? "danger" : fd.status === "added" ? "ok" : "neutral"}`}>
                        {fd.status}
                      </span>
                      {fd.current !== null ? <small>current: {fd.current}</small> : null}
                      {fd.proposed !== null ? <small>proposed: {fd.proposed}</small> : null}
                    </div>
                  ))}
                </div>
              ) : null}
              <button
                className="secondary-button"
                type="button"
                onClick={() => setSelectedPlanId(mergeResult.merge_plan_id)}
              >
                {t("features.library.organize.openMergePlan")}
              </button>
            </div>
          ) : null}
        </section>
      ) : null}
      <h5>{t("features.library.organize.pathPreview")}</h5>
      <div className="library-action-list">
        {detail.actions.map((action) => (
          <PlanActionRow
            key={action.id}
            action={action}
            editable={detail.plan.status === "draft"}
            onUpdateTarget={(targetPath) => updateActionMutation.mutate({ actionId: action.id, targetPath })}
          />
        ))}
      </div>
      <h5>{t("features.library.organize.executionLogs")}</h5>
      <PlanLogList logs={logsQuery.data?.items ?? []} isLoading={logsQuery.isLoading} />
      {confirmOpen ? (
        <div className="library-confirm-panel" role="dialog" aria-modal="true">
          <strong>{t("features.library.organize.realFilesystemOperations")}</strong>
          <p>{t("features.library.organize.executeWarning")}</p>
          <label>
            <input type="checkbox" checked={confirmChecked} onChange={(event) => setConfirmChecked(event.target.checked)} />
            {t("features.library.organize.confirmExecute")}
          </label>
          <div className="library-toolbar-actions">
            <button className="primary-button" type="button" disabled={!confirmChecked || executeMutation.isPending} onClick={() => executeMutation.mutate(detail.plan.id)}>
              {executeMutation.isPending ? t("features.library.organize.executing") : t("features.library.organize.executePlan")}
            </button>
            <button className="secondary-button" type="button" onClick={() => setConfirmOpen(false)}>
              {t("features.library.organize.dismiss")}
            </button>
          </div>
        </div>
      ) : null}
    </aside>
  );
}

function PlanLogList({ logs, isLoading }: { logs: OrganizeActionLogItemVM[]; isLoading: boolean }) {
  if (isLoading) {
    return <p>{t("common.states.loading")}</p>;
  }
  if (logs.length === 0) {
    return <p className="library-empty-state">{t("features.library.organize.noLogs")}</p>;
  }
  return (
    <div className="library-log-list">
      {logs.map((log) => (
        <div key={log.id} className="library-log-row">
          <span>{formatTimestamp(log.created_at)}</span>
          <strong>{log.event_type}</strong>
          <small>{log.error_message ?? log.message}</small>
        </div>
      ))}
    </div>
  );
}

function PlanActionRow({
  action,
  editable,
  onUpdateTarget,
}: {
  action: OrganizeActionItemVM;
  editable: boolean;
  onUpdateTarget: (targetPath: string) => void;
}) {
  const [targetPath, setTargetPath] = useState(action.target_path ?? "");
  useEffect(() => {
    setTargetPath(action.target_path ?? "");
  }, [action.target_path]);
  return (
    <div className="library-action-row">
      <div>
        <strong>{action.action_type}</strong>
        <span className={`status-pill status-pill--${action.conflict_status === "blocked" || action.conflict_status === "stale" ? "danger" : "neutral"}`}>
          {action.conflict_status}
        </span>
        <span className="status-pill status-pill--neutral">{action.status}</span>
      </div>
      {action.source_path ? <small title={action.source_path}>{t("features.library.organize.sourcePath")}: {action.source_path}</small> : null}
      {editable ? (
        <div className="library-action-edit">
          <input value={targetPath} onChange={(event) => setTargetPath(event.target.value)} />
          <button className="secondary-button" type="button" onClick={() => onUpdateTarget(targetPath)}>
            {t("common.actions.save")}
          </button>
        </div>
      ) : (
        <small title={action.target_path ?? undefined}>{t("features.library.organize.targetPath")}: {action.target_path ?? t("common.states.unavailable")}</small>
      )}
      {action.conflict_message ? <small>{action.conflict_message}</small> : null}
      {action.before_path ? <small title={action.before_path}>{t("features.library.organize.beforePath")}: {action.before_path}</small> : null}
      {action.after_path ? <small title={action.after_path}>{t("features.library.organize.afterPath")}: {action.after_path}</small> : null}
      {action.error_message ? <small className="danger-text">{action.error_message}</small> : null}
      {action.payload_json ? <pre className="library-payload-preview">{action.payload_json}</pre> : null}
    </div>
  );
}

function LibraryPlansPanel() {
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [status, setStatus] = useState("");
  const queryParams = useMemo<OrganizePlanListQueryInput>(
    () => ({ page: 1, page_size: 30, status: status || undefined }),
    [status],
  );
  const plansQuery = useQuery({
    queryKey: queryKeys.organizePlans(queryParams),
    queryFn: () => listOrganizePlans(queryParams),
  });
  return (
    <section className="library-objects-panel library-design-panel library-design-panel--plans">
      <div className="library-panel-toolbar library-design-hero">
        <div>
          <span className="page-header__eyebrow">{t("features.library.plans.eyebrow")}</span>
          <h3>{t("features.library.organize.plansTitle")}</h3>
          <p>{t("features.library.organize.phase3Safety")}</p>
        </div>
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">{t("features.library.objects.allReviewStates")}</option>
          <option value="draft">draft</option>
          <option value="ready">ready</option>
          <option value="executing">executing</option>
          <option value="completed">completed</option>
          <option value="completed_with_errors">completed_with_errors</option>
          <option value="failed">failed</option>
          <option value="cancelled">cancelled</option>
        </select>
      </div>
      <div className="library-objects-layout library-plans-layout">
        <div className="library-object-list-panel library-design-card">
          {plansQuery.isLoading ? <p>{t("common.states.loading")}</p> : null}
          {plansQuery.isError ? <p>{t("features.library.scan.unableToLoad")}</p> : null}
          {plansQuery.data && plansQuery.data.items.length === 0 ? (
            <p className="library-empty-state">{t("features.library.organize.noPlans")}</p>
          ) : null}
          <div className="library-object-list">
            {plansQuery.data?.items.map((plan) => (
              <button
                key={plan.id}
                className={`library-object-row${selectedPlanId === plan.id ? " library-object-row--selected" : ""}`}
                type="button"
                onClick={() => setSelectedPlanId(plan.id)}
              >
                <span className="library-object-row__type"><PlanStatusPill status={plan.status} /></span>
                <span className="library-object-row__main">
                  <strong>{plan.title}</strong>
                  <small>{formatTimestamp(plan.updated_at)}</small>
                </span>
                <span className="library-object-row__meta">
                  <span>{t("features.library.organize.actions")}: {plan.actions_count}</span>
                  <span>{t("features.library.organize.blocked")}: {plan.blocked_count}</span>
                  <span>{t("features.library.organize.warning")}: {plan.warning_count}</span>
                  <span>{t("features.library.organize.failed")}: {plan.failed_count}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
        <PlanDetail planId={selectedPlanId} />
      </div>
    </section>
  );
}

export function LibraryFeature() {
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get("tab");
  const activeTab: LibraryTab = isLibraryTab(rawTab) ? rawTab : "overview";

  useEffect(() => {
    if (rawTab !== activeTab) {
      setSearchParams({ tab: activeTab }, { replace: true });
    }
  }, [activeTab, rawTab, setSearchParams]);

  const setActiveTab = (tab: LibraryTab) => {
    setSearchParams({ tab });
  };

  return (
    <section className="feature-shell library-feature">
      <div className="feature-header">
        <span className="page-header__eyebrow">{t("features.library.eyebrow")}</span>
        <h3>{t("features.library.title")}</h3>
        <p>{t("features.library.description")}</p>
      </div>

      <div className="settings-segmented-control library-tabs" role="tablist" aria-label={t("features.library.tabsAriaLabel")}>
        {libraryTabs.map((tab) => (
          <button
            key={tab.value}
            className={`secondary-button settings-segmented-button${activeTab === tab.value ? " settings-segmented-button--selected" : ""}`}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.value}
            onClick={() => setActiveTab(tab.value)}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      <div className="library-tab-panel" role="tabpanel">
        {activeTab === "overview" ? <LibraryOverviewPanel /> : null}
        {activeTab === "roots" ? <LibraryRootsPanel /> : null}
        {activeTab === "path" ? <LibraryPathBrowserPanel /> : null}
        {activeTab === "pending" ? <LibraryPendingPanel /> : null}
        {activeTab === "objects" ? <LibraryObjectsPanel /> : null}
        {activeTab === "plans" ? <LibraryPlansPanel /> : null}
      </div>
    </section>
  );
}
