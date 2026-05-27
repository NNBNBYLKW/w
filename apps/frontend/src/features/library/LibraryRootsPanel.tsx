import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { t } from "../../shared/text";
import { LoadingState } from "../../shared/ui/components/LoadingState";
import { queryKeys } from "../../services/query/queryKeys";
import { invalidateLibraryRootSurfaces } from "../../services/query/invalidation";
import type { LibraryRootVM, OrganizeCandidateItemVM, OrganizePlanListQueryInput, OrganizeTemplateItemVM, OrganizeSuggestionItemVM, ReconcilePlanResponseVM } from "../../entities/library/types";
import { listLibraryRoots, createLibraryRoot, updateLibraryRoot, setDefaultLibraryRoot, listOrganizeCandidates, scanOrganizeCandidates, generateOrganizePlan, listOrganizeTemplates, generateOrganizeSuggestions, listOrganizeSuggestions, acceptOrganizeSuggestion, rejectOrganizeSuggestion } from "../../services/api/libraryObjectsApi";
import { PlanStatusPill, StatusBadge, ActionButton, KeyValueRow } from "../../shared/ui/components";
import { FileBrowserFeature } from "../file-browser/FileBrowserFeature";
import { formatSuggestionPayloadSummary, formatTimestamp, formatBytes, normalizeObjectTypeLabel } from "./shared/helpers";

export function LibraryRootsPanel() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [showAdd, setShowAdd] = useState(false);
  const [addPath, setAddPath] = useState("");
  const [addDisplayName, setAddDisplayName] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [rootCreated, setRootCreated] = useState(false);

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
      invalidateLibraryRootSurfaces(queryClient);
      setShowAdd(false);
      setAddPath("");
      setAddDisplayName("");
      setAddError(null);
      setRootCreated(true);
    },
    onError: (err: Error) => setAddError(err.message),
  });

  const setDefaultMutation = useMutation({
    mutationFn: setDefaultLibraryRoot,
    onSuccess: () => invalidateLibraryRootSurfaces(queryClient),
  });

  const disableMutation = useMutation({
    mutationFn: (rootId: number) => updateLibraryRoot(rootId, { is_enabled: false }),
    onSuccess: () => invalidateLibraryRootSurfaces(queryClient),
  });

  const enableMutation = useMutation({
    mutationFn: (rootId: number) => updateLibraryRoot(rootId, { is_enabled: true }),
    onSuccess: () => invalidateLibraryRootSurfaces(queryClient),
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
        <LoadingState />
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
                  placeholder="D:\Library"
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
                  placeholder="D:\Library"
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
      {rootCreated && (
        <div className="library-next-step">
          <strong>{t("features.library.roots.nextStepTitle")}</strong>
          <p>{t("features.library.roots.nextStepDesc")}</p>
          <button className="primary-button" type="button" onClick={() => { setRootCreated(false); navigate("/library?tab=inbox"); }}>
            {t("features.library.roots.nextStepAction")}
          </button>
        </div>
      )}
    </section>
  );
}
