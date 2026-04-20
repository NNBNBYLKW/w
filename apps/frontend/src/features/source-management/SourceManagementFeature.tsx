import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

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
      setCreateFeedback("Source added. Next, run a scan for this source.");
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
        message: `Task #${result.task_id} finished with status ${result.status}.`,
      });
      await queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      await queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus });
    },
    onError: async (error, sourceId) => {
      const message =
        error instanceof SourcesApiError && error.code === "SCAN_ALREADY_RUNNING"
          ? "A scan is already running for this source."
          : error instanceof Error
            ? error.message
            : "Scan could not be completed.";
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
      return "Scan running";
    }
    if (value === "failed") {
      return "Last scan failed";
    }
    if (value === "succeeded") {
      return "Last scan succeeded";
    }
    return "No scan yet";
  };

  const getCreateErrorMessage = (error: unknown) => {
    if (error instanceof SourcesApiError) {
      if (error.code === "INVALID_SOURCE_PATH") {
        return "Enter a local folder path before adding the source.";
      }
      if (error.code === "SOURCE_ALREADY_EXISTS") {
        return "This folder is already added as a source.";
      }
      if (error.code === "SOURCE_ROOT_OVERLAP") {
        return "This folder overlaps with an existing source root.";
      }
      if (error.message) {
        return error.message;
      }
    }

    if (error instanceof Error && error.message) {
      return error.message;
    }

    return "Source could not be added right now.";
  };

  const resetCreatePresentation = () => {
    setCreateFeedback(null);
    createSourceMutation.reset();
  };

  return (
    <section className="source-management">
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="field-stack">
          <label htmlFor="source-path">Source path</label>
          <input
            id="source-path"
            className="text-input"
            value={path}
            onChange={(event) => {
              resetCreatePresentation();
              setPath(event.target.value);
            }}
            placeholder="D:\\Assets"
            required
          />
          <p>Choose a local folder to scan and index. Desktop shell can use Choose folder; browser mode can type the path.</p>
          <div className="source-row__actions">
            <button
              className="secondary-button"
              type="button"
              onClick={handleChooseFolder}
              disabled={!selectFolder || isSelectingFolder}
            >
              {isSelectingFolder ? "Choosing..." : "Choose folder"}
            </button>
          </div>
        </div>
        <div className="field-stack">
          <label htmlFor="source-display-name">Display name</label>
          <input
            id="source-display-name"
            className="text-input"
            value={displayName}
            onChange={(event) => {
              resetCreatePresentation();
              setDisplayName(event.target.value);
            }}
            placeholder="Optional"
          />
        </div>
        <div className="source-row__actions">
          <button className="primary-button" type="submit" disabled={createSourceMutation.isPending}>
            {createSourceMutation.isPending ? "Saving..." : "Add source"}
          </button>
        </div>
        {createFeedback ? <p>{createFeedback}</p> : null}
      </form>

      {createSourceMutation.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Source could not be added</strong>
          <p>{getCreateErrorMessage(createSourceMutation.error)}</p>
        </div>
      ) : null}

      <div className="feature-shell">
        <div className="feature-header">
          <span className="page-header__eyebrow">Source setup and scan control</span>
          <h3>Saved sources</h3>
        </div>
        {sourcesQuery.isLoading ? <p>Loading source rows...</p> : null}
        {sourcesQuery.data?.length === 0 ? (
          <p>No sources yet. Add a local source first, then run a scan to index files.</p>
        ) : null}
        <div className="source-list">
          {sourcesQuery.data?.map((source) => (
            <article className="source-row" key={source.id}>
              <div className="source-row__meta">
                <strong>{source.display_name || source.path}</strong>
                <p className="source-row__path">{source.path}</p>
                <p className="source-row__path">Scan status: {formatScanStatusLabel(source.last_scan_status)}</p>
                {source.last_scan_status === null ? (
                  <p className="source-row__path">Run scan indexes files from this folder so they appear in search and browse.</p>
                ) : null}
                {source.last_scan_status === "running" ? (
                  <p className="source-row__path">Scan running for this source.</p>
                ) : null}
                {source.last_scan_status === "failed" && source.last_scan_error_message ? (
                  <p className="source-row__path">Last scan failed: {source.last_scan_error_message}</p>
                ) : null}
                {scanFeedback?.sourceId === source.id ? (
                  <p className="source-row__path">
                    Scan update: 
                    {scanFeedback.message}
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
                  {pendingSourceIds.includes(source.id) ? "Running..." : "Run scan"}
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
