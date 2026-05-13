import { useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { t } from "../../shared/text";
import { queryKeys } from "../../services/query/queryKeys";
import type { OrganizeCandidateItemVM, OrganizeCandidateListQueryInput, OrganizeSuggestionItemVM } from "../../entities/library/types";
import { listOrganizeCandidates, scanOrganizeCandidates, generateOrganizePlan, ignoreOrganizeCandidate, listLibraryRoots, listOrganizeTemplates, generateOrganizeSuggestions, listOrganizeSuggestions, acceptOrganizeSuggestion, rejectOrganizeSuggestion } from "../../services/api/libraryObjectsApi";
import { StatusBadge, ActionButton, KeyValueRow } from "../../shared/ui/components";
import { formatSuggestionPayloadSummary } from "./shared/helpers";


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


export function LibraryPendingPanel() {
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

