import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

import { createSource, getSources, triggerSourceScan } from "../../services/api/sourcesApi";
import { queryKeys } from "../../services/query/queryKeys";


export function SourceManagementFeature() {
  const queryClient = useQueryClient();
  const [path, setPath] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [lastTaskMessage, setLastTaskMessage] = useState<string | null>(null);

  const sourcesQuery = useQuery({
    queryKey: queryKeys.sources,
    queryFn: getSources,
  });

  const createSourceMutation = useMutation({
    mutationFn: createSource,
    onSuccess: async () => {
      setPath("");
      setDisplayName("");
      await queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      await queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus });
    },
  });

  const triggerScanMutation = useMutation({
    mutationFn: triggerSourceScan,
    onSuccess: async (result) => {
      setLastTaskMessage(`Scan task #${result.task_id} completed with status ${result.status}.`);
      await queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      await queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus });
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createSourceMutation.mutate({
      path,
      display_name: displayName || null,
    });
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
            onChange={(event) => setPath(event.target.value)}
            placeholder="D:\\Assets"
            required
          />
        </div>
        <div className="field-stack">
          <label htmlFor="source-display-name">Display name</label>
          <input
            id="source-display-name"
            className="text-input"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            placeholder="Optional"
          />
        </div>
        <div className="source-row__actions">
          <button className="primary-button" type="submit" disabled={createSourceMutation.isPending}>
            {createSourceMutation.isPending ? "Saving..." : "Add source"}
          </button>
        </div>
      </form>

      {createSourceMutation.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Create source failed</strong>
          <p>{createSourceMutation.error.message}</p>
        </div>
      ) : null}

      {lastTaskMessage ? (
        <div className="status-block page-card">
          <strong>Latest scan result</strong>
          <p>{lastTaskMessage}</p>
        </div>
      ) : null}

      <div className="feature-shell">
        <div className="feature-header">
          <span className="page-header__eyebrow">Persisted rows</span>
          <h3>Sources</h3>
        </div>
        {sourcesQuery.isLoading ? <p>Loading sources...</p> : null}
        {sourcesQuery.data?.length === 0 ? (
          <p>No sources yet. Add one above to validate backend persistence and the shared shell flow.</p>
        ) : null}
        <div className="source-list">
          {sourcesQuery.data?.map((source) => (
            <article className="source-row" key={source.id}>
              <div className="source-row__meta">
                <strong>{source.display_name || source.path}</strong>
                <p className="source-row__path">{source.path}</p>
              </div>
              <div className="source-row__actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => triggerScanMutation.mutate(source.id)}
                  disabled={triggerScanMutation.isPending}
                >
                  Run scan
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
