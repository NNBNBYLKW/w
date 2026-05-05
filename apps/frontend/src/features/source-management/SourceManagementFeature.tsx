import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

import { t } from "../../shared/text";
import { createSource, getSources, SourcesApiError, triggerSourceScan } from "../../services/api/sourcesApi";
import { queryKeys } from "../../services/query/queryKeys";


export function SourceManagementFeature() {
  const queryClient = useQueryClient();
  const [path, setPath] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [pendingSourceIds, setPendingSourceIds] = useState<number[]>([]);
  const [isSelectingFolder, setIsSelectingFolder] = useState(false);
  const [createFeedback, setCreateFeedback] = useState<string | null>(null);
  const [scanFeedback, setScanFeedback] = useState<{
    sourceId: number;
    kind: "success" | "error";
    message: string;
  } | null>(null);
  const selectFolder =
    (
      window as Window & {
        assetWorkbench?: {
          selectFolder?: () => Promise<string | null>;
        };
      }
    ).assetWorkbench?.selectFolder ?? null;

  const sourcesQuery = useQuery({
    queryKey: queryKeys.sources,
    queryFn: getSources,
  });

  const createSourceMutation = useMutation({
    mutationFn: createSource,
    onMutate: async () => {
      setCreateFeedback(null);
    },
    onSuccess: async () => {
      setPath("");
      setDisplayName("");
      setCreateFeedback(t("settings.sourceManagement.createSuccess"));
      await queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      await queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus });
    },
  });

  const triggerScanMutation = useMutation({
    mutationFn: triggerSourceScan,
    onMutate: async (sourceId) => {
      setPendingSourceIds((current) => [...current, sourceId]);
      setScanFeedback(null);
    },
    onSuccess: async (result, sourceId) => {
      setScanFeedback({
        sourceId,
        kind: "success",
        message: t("settings.sourceManagement.scanFeedback.success", {
          status: result.status,
          taskId: result.task_id,
        }),
      });
      await queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      await queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus });
    },
    onError: async (error, sourceId) => {
      const message =
        error instanceof SourcesApiError && error.code === "SCAN_ALREADY_RUNNING"
          ? t("settings.sourceManagement.scanFeedback.running")
          : error instanceof Error
            ? error.message
            : t("settings.sourceManagement.scanFeedback.failed");
      setScanFeedback({
        sourceId,
        kind: "error",
        message,
      });
      await queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      await queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus });
    },
    onSettled: async (_data, _error, sourceId) => {
      setPendingSourceIds((current) => current.filter((pendingId) => pendingId !== sourceId));
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createSourceMutation.mutate({
      path,
      display_name: displayName || null,
    });
  };

  const handleChooseFolder = async () => {
    if (!selectFolder || isSelectingFolder) {
      return;
    }

    setIsSelectingFolder(true);
    try {
      const selectedPath = await selectFolder();
      if (!selectedPath) {
        return;
      }

      resetCreatePresentation();
      setPath(selectedPath);
    } catch {
      // Gracefully keep the current manual-entry flow unchanged on picker failure.
    } finally {
      setIsSelectingFolder(false);
    }
  };

  const formatScanStatusLabel = (value: string | null) => {
    if (value === "running") {
      return t("settings.sourceManagement.scanStatus.running");
    }
    if (value === "failed") {
      return t("settings.sourceManagement.scanStatus.failed");
    }
    if (value === "succeeded") {
      return t("settings.sourceManagement.scanStatus.succeeded");
    }
    return t("settings.sourceManagement.scanStatus.none");
  };

  const getCreateErrorMessage = (error: unknown) => {
    if (error instanceof SourcesApiError) {
      if (error.code === "INVALID_SOURCE_PATH") {
        return t("settings.sourceManagement.addErrorInvalidPath");
      }
      if (error.code === "SOURCE_ALREADY_EXISTS") {
        return t("settings.sourceManagement.addErrorAlreadyExists");
      }
      if (error.code === "SOURCE_ROOT_OVERLAP") {
        return t("settings.sourceManagement.addErrorOverlap");
      }
      if (error.message) {
        return error.message;
      }
    }

    if (error instanceof Error && error.message) {
      return error.message;
    }

    return t("settings.sourceManagement.addErrorDefault");
  };

  const resetCreatePresentation = () => {
    setCreateFeedback(null);
    createSourceMutation.reset();
  };

  return (
    <section className="source-management">
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="field-stack">
          <label htmlFor="source-path">{t("settings.sourceManagement.sourcePath")}</label>
          <input
            id="source-path"
            className="text-input"
            value={path}
            onChange={(event) => {
              resetCreatePresentation();
              setPath(event.target.value);
            }}
            placeholder={t("settings.sourceManagement.sourcePathPlaceholder")}
            required
          />
          <p>{t("settings.sourceManagement.sourcePathHelp")}</p>
          <div className="source-row__actions">
            <button
              className="secondary-button"
              type="button"
              onClick={handleChooseFolder}
              disabled={!selectFolder || isSelectingFolder}
            >
              {isSelectingFolder ? t("settings.sourceManagement.choosingFolder") : t("settings.sourceManagement.chooseFolder")}
            </button>
          </div>
        </div>
        <div className="field-stack">
          <label htmlFor="source-display-name">{t("settings.sourceManagement.displayName")}</label>
          <input
            id="source-display-name"
            className="text-input"
            value={displayName}
            onChange={(event) => {
              resetCreatePresentation();
              setDisplayName(event.target.value);
            }}
            placeholder={t("settings.sourceManagement.displayNamePlaceholder")}
          />
        </div>
        <div className="source-row__actions">
          <button className="primary-button" type="submit" disabled={createSourceMutation.isPending}>
            {createSourceMutation.isPending ? t("common.actions.saving") : t("settings.sourceManagement.addSource")}
          </button>
        </div>
        {createFeedback ? <p>{createFeedback}</p> : null}
      </form>

      {createSourceMutation.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("settings.sourceManagement.createErrorTitle")}</strong>
          <p>{getCreateErrorMessage(createSourceMutation.error)}</p>
        </div>
      ) : null}

      <div className="feature-shell">
        <div className="feature-header">
          <span className="page-header__eyebrow">{t("settings.sourceManagement.savedSources.eyebrow")}</span>
          <h3>{t("settings.sourceManagement.savedSources.title")}</h3>
        </div>
        {sourcesQuery.isLoading ? <p>{t("settings.sourceManagement.savedSources.loading")}</p> : null}
        {sourcesQuery.data?.length === 0 ? (
          <p>{t("settings.sourceManagement.savedSources.empty")}</p>
        ) : null}
        <div className="source-list">
          {sourcesQuery.data?.map((source) => (
            <article className="source-row" key={source.id}>
              <div className="source-row__meta">
                <strong>{source.display_name || source.path}</strong>
                <p className="source-row__path">{source.path}</p>
                <p className="source-row__path">
                  {t("settings.sourceManagement.savedSources.statusLabel", {
                    status: formatScanStatusLabel(source.last_scan_status),
                  })}
                </p>
                {source.last_scan_status === null ? (
                  <p className="source-row__path">{t("settings.sourceManagement.savedSources.runScanHint")}</p>
                ) : null}
                {source.last_scan_status === "running" ? (
                  <p className="source-row__path">{t("settings.sourceManagement.savedSources.runningHint")}</p>
                ) : null}
                {source.last_scan_status === "failed" && source.last_scan_error_message ? (
                  <p className="source-row__path">
                    {t("settings.sourceManagement.savedSources.failedHint", {
                      message: source.last_scan_error_message,
                    })}
                  </p>
                ) : null}
                {scanFeedback?.sourceId === source.id ? (
                  <p className="source-row__path">
                    {t("settings.sourceManagement.savedSources.updateHint", {
                      message: scanFeedback.message,
                    })}
                  </p>
                ) : null}
              </div>
              <div className="source-row__actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => triggerScanMutation.mutate(source.id)}
                  disabled={pendingSourceIds.includes(source.id) || source.last_scan_status === "running"}
                >
                  {pendingSourceIds.includes(source.id)
                    ? t("settings.sourceManagement.savedSources.running")
                    : t("settings.sourceManagement.savedSources.runScan")}
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
