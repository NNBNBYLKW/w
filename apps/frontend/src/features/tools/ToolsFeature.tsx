import type { DragEvent } from "react";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { t } from "../../shared/text";
import { EmptyState } from "../../shared/ui/components";
import type { FilesListItemVM } from "../../entities/file/types";
import type { ToolRunVM, VideoMergeMode, VideoMergeInputItemVM } from "../../entities/tool/types";
import { listIndexedFiles } from "../../services/api/filesApi";
import { createVideoMergeRun, getToolRun, listToolRuns, listTools } from "../../services/api/toolsApi";
import { getDroppedFilePath, hasDesktopDropPathBridge } from "../../services/desktop/dropPaths";
import { queryKeys } from "../../services/query/queryKeys";
import { invalidateToolRunSurfaces } from "../../services/query/invalidation";
import { getWorkbenchFileDragData } from "../../services/tools/videoMergeDrag";


type VideoMergeInput = {
  id: string;
  sourceKind: "indexed_file" | "external_path";
  fileId?: number;
  path: string;
  name: string;
  sizeBytes?: number | null;
};

type ToolsTab = "currentTool" | "inProgress" | "completed";


function formatBytes(value: number | null | undefined): string {
  return value === null || value === undefined ? t("common.states.unavailable") : `${value.toLocaleString()} bytes`;
}


function getNameFromPath(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).pop() ?? path;
}


function getDirectoryFromPath(path: string): string {
  const separatorIndex = Math.max(path.lastIndexOf("\\"), path.lastIndexOf("/"));
  return separatorIndex > 0 ? path.slice(0, separatorIndex) : "";
}


function isVideoPath(path: string): boolean {
  return /\.(mp4|mkv|mov|avi|webm|m4v|ts)$/i.test(path);
}


function toVideoMergePayload(inputs: VideoMergeInput[]): VideoMergeInputItemVM[] {
  return inputs.map((item) =>
    item.sourceKind === "indexed_file"
      ? { source_kind: "indexed_file", file_id: item.fileId }
      : { source_kind: "external_path", path: item.path }
  );
}


function runStatusLabel(run: ToolRunVM | undefined): string {
  if (!run) {
    return t("features.tools.videoMerge.status.idle");
  }
  if (run.status === "pending") {
    return t("features.tools.videoMerge.status.pending");
  }
  if (run.status === "running") {
    return t("features.tools.videoMerge.status.running");
  }
  if (run.status === "succeeded") {
    return t("features.tools.videoMerge.status.succeeded");
  }
  if (run.status === "failed") {
    return t("features.tools.videoMerge.status.failed");
  }
  return run.status;
}

function isActiveRun(run: ToolRunVM): boolean {
  return run.status === "pending" || run.status === "running";
}


function isCompletedRun(run: ToolRunVM): boolean {
  return run.status === "succeeded" || run.status === "failed" || run.status === "cancelled";
}


function formatRunTime(value: string | null): string {
  return value ? new Date(value).toLocaleString() : t("common.states.unavailable");
}


function getPlannedOutputPath(run: ToolRunVM): string | null {
  const plannedOutputPath = run.input["planned_output_path"];
  return typeof plannedOutputPath === "string" ? plannedOutputPath : null;
}


function ToolRunCard({
  run,
  selected,
  onSelect,
}: {
  run: ToolRunVM;
  selected: boolean;
  onSelect: () => void;
}) {
  const plannedOutputPath = getPlannedOutputPath(run);
  return (
    <button
      className={`tool-run-card${selected ? " tool-run-card--selected" : ""}`}
      type="button"
      onClick={onSelect}
    >
      <span className="tool-run-card__id">#{run.id}</span>
      <div className="tool-run-card__main">
        <strong>{run.final_output_name ?? t("features.tools.videoMerge.title")}</strong>
        <small>
          {run.status} · {formatRunTime(run.started_at ?? run.created_at)}
        </small>
        {plannedOutputPath ? <code>{plannedOutputPath}</code> : null}
        {run.output_path ? <code>{run.output_path}</code> : null}
        {run.error_message ? <span className="video-merge-error">{run.error_message}</span> : null}
      </div>
      <span className="status-pill">{runStatusLabel(run)}</span>
    </button>
  );
}


function ToolRunDetail({ run }: { run: ToolRunVM | undefined }) {
  if (!run) {
    return null;
  }
  return (
    <div className="tool-run-detail">
      <div className="tools-section-header">
        <strong>{t("features.tools.videoMerge.currentRun")}</strong>
        <span className="status-pill">{runStatusLabel(run)}</span>
      </div>
      {run.output_path ? (
        <div className="tool-run-output">
          <strong>{t("features.tools.videoMerge.outputFile")}</strong>
          <code>{run.output_path}</code>
          <p>{t("features.tools.videoMerge.rescanHint")}</p>
        </div>
      ) : null}
      {run.error_message ? <div className="video-merge-error">{run.error_message}</div> : null}
      {run.log_tail ? <pre className="tool-run-log">{run.log_tail}</pre> : null}
    </div>
  );
}


export function ToolsFeature() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [inputs, setInputs] = useState<VideoMergeInput[]>([]);
  const [outputName, setOutputName] = useState("merged-video");
  const [outputDir, setOutputDir] = useState("");
  const [mode, setMode] = useState<VideoMergeMode>("copy");
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<ToolsTab>("currentTool");
  const [dropError, setDropError] = useState<string | null>(null);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const toolsQuery = useQuery({
    queryKey: queryKeys.tools,
    queryFn: listTools,
  });
  const indexedVideosQuery = useQuery({
    queryKey: queryKeys.filesList({
      file_kind: "video",
      page: 1,
      page_size: 20,
      sort_by: "modified_at",
      sort_order: "desc",
    }),
    queryFn: () =>
      listIndexedFiles({
        file_kind: "video",
        page: 1,
        page_size: 20,
        sort_by: "modified_at",
        sort_order: "desc",
      }),
  });
  const runHistoryQuery = useQuery({
    queryKey: queryKeys.toolRuns({ page: 1, page_size: 10 }),
    queryFn: () => listToolRuns({ page: 1, page_size: 10 }),
    refetchInterval: (query) => {
      const hasActiveRuns = query.state.data?.items.some(isActiveRun) ?? false;
      return hasActiveRuns ? 1500 : false;
    },
  });
  const activeRunQuery = useQuery({
    queryKey: activeRunId ? queryKeys.toolRun(activeRunId) : ["tool-run", "none"],
    queryFn: () => getToolRun(activeRunId ?? 0),
    enabled: activeRunId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "succeeded" || status === "failed" ? false : 1500;
    },
  });
  const createRunMutation = useMutation({
    mutationFn: createVideoMergeRun,
    onSuccess: (response) => {
      setActiveRunId(response.run_id);
      setActiveTab("inProgress");
      void invalidateToolRunSurfaces(queryClient);
    },
  });

  const canStart = inputs.length >= 2 && outputName.trim().length > 0 && !createRunMutation.isPending;
  const firstInputDirectory = inputs[0] ? getDirectoryFromPath(inputs[0].path) : "";
  const effectiveOutputDir = outputDir.trim() || firstInputDirectory;
  const selectedTool = toolsQuery.data?.items.find((item) => item.key === "video_merge");
  const allRuns = runHistoryQuery.data?.items ?? [];
  const activeRuns = allRuns.filter(isActiveRun);
  const completedRuns = allRuns.filter(isCompletedRun);

  const addIndexedVideo = (item: FilesListItemVM) => {
    setInputs((current) => {
      if (current.some((input) => input.sourceKind === "indexed_file" && input.fileId === item.id)) {
        return current;
      }
      return [
        ...current,
        {
          id: `indexed-${item.id}`,
          sourceKind: "indexed_file",
          fileId: item.id,
          path: item.path,
          name: item.name,
          sizeBytes: item.size_bytes,
        },
      ];
    });
    if (!outputDir && inputs.length === 0) {
      setOutputDir(getDirectoryFromPath(item.path));
    }
  };

  const addExternalPath = (path: string) => {
    if (!isVideoPath(path)) {
      setDropError(t("features.tools.videoMerge.onlyVideo"));
      return;
    }
    setInputs((current) => {
      if (current.some((input) => input.sourceKind === "external_path" && input.path === path)) {
        return current;
      }
      return [
        ...current,
        {
          id: `external-${path}`,
          sourceKind: "external_path",
          path,
          name: getNameFromPath(path),
        },
      ];
    });
    if (!outputDir && inputs.length === 0) {
      setOutputDir(getDirectoryFromPath(path));
    }
  };

  const moveInput = (fromIndex: number, toIndex: number) => {
    setInputs((current) => {
      if (toIndex < 0 || toIndex >= current.length) {
        return current;
      }
      const next = [...current];
      const [removed] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, removed);
      return next;
    });
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDropError(null);

    const workbenchPayload = getWorkbenchFileDragData(event);
    if (workbenchPayload) {
      if (workbenchPayload.file_type !== "video" && !isVideoPath(workbenchPayload.path)) {
        setDropError(t("features.tools.videoMerge.onlyVideo"));
        return;
      }
      addIndexedVideo({
        id: workbenchPayload.file_id,
        name: workbenchPayload.name,
        path: workbenchPayload.path,
        file_type: "video",
        file_kind: "video",
        auto_placement: "media",
        manual_placement: null,
        effective_placement: "media",
        modified_at: new Date().toISOString(),
        size_bytes: null,
      });
      return;
    }

    if (event.dataTransfer.files.length > 0) {
      if (!hasDesktopDropPathBridge()) {
        setDropError(t("features.tools.videoMerge.externalDropUnsupported"));
        return;
      }
      Array.from(event.dataTransfer.files).forEach((file) => {
        const path = getDroppedFilePath(file);
        if (!path) {
          setDropError(t("features.tools.videoMerge.externalDropUnsupported"));
          return;
        }
        addExternalPath(path);
      });
    }
  };

  const startMerge = () => {
    createRunMutation.mutate({
      inputs: toVideoMergePayload(inputs),
      output_name: outputName,
      output_dir: effectiveOutputDir || undefined,
      mode,
    });
  };

  const sortedInputs = useMemo(() => inputs, [inputs]);

  return (
    <section className="feature-shell tools-workbench utility-surface utility-surface--tools">
      <div className="feature-header utility-surface__header">
        <div>
          <span className="page-header__eyebrow">{t("features.tools.eyebrow")}</span>
          <h3>{t("features.tools.title")}</h3>
          <p>{t("features.tools.description")}</p>
        </div>
      </div>

      <div className="tools-layout">
        <aside className="tools-list-panel page-card">
          <span className="page-header__eyebrow">{t("features.tools.availableTools")}</span>
          <strong>{selectedTool ? t("features.tools.videoMerge.title") : t("features.tools.videoMerge.title")}</strong>
          <p>{selectedTool ? t("features.tools.videoMerge.description") : t("features.tools.videoMerge.description")}</p>
        </aside>

        <div className="tools-main-panel">
          <div className="tools-tab-switch" role="tablist" aria-label={t("features.tools.tabs.ariaLabel")}>
            {[
              { value: "currentTool" as const, label: t("features.tools.tabs.currentTool") },
              { value: "inProgress" as const, label: t("features.tools.tabs.inProgress") },
              { value: "completed" as const, label: t("features.tools.tabs.completed") },
            ].map((tab) => (
              <button
                key={tab.value}
                className={`secondary-button tools-tab-button${activeTab === tab.value ? " tools-tab-button--selected" : ""}`}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.value}
                onClick={() => setActiveTab(tab.value)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === "currentTool" ? (
          <div className="page-card video-merge-panel" role="tabpanel">
            <div className="tools-section-header">
              <div>
                <span className="page-header__eyebrow">{t("features.tools.videoMerge.inputVideos")}</span>
                <h4>{t("features.tools.videoMerge.title")}</h4>
              </div>
              <button className="secondary-button" type="button" onClick={() => setInputs([])} disabled={inputs.length === 0}>
                {t("features.tools.videoMerge.clear")}
              </button>
            </div>

            <div
              className="video-merge-dropzone"
              onDragOver={(event) => event.preventDefault()}
              onDrop={handleDrop}
            >
              <strong>{t("features.tools.videoMerge.dropVideos")}</strong>
              <p>{t("features.tools.videoMerge.dropHint")}</p>
              {dropError ? <span className="video-merge-error">{dropError}</span> : null}
            </div>

            <div className="video-merge-grid">
              <div className="video-merge-picker">
                <strong>{t("features.tools.videoMerge.indexedVideos")}</strong>
                {indexedVideosQuery.isLoading ? <p>{t("common.states.loading")}</p> : null}
                {indexedVideosQuery.error instanceof Error ? <p>{indexedVideosQuery.error.message}</p> : null}
                <div className="video-merge-picker__list">
                  {indexedVideosQuery.data?.items.map((item) => (
                    <button key={item.id} className="video-merge-picker__item" type="button" onClick={() => addIndexedVideo(item)}>
                      <span>{item.name}</span>
                      <small>{formatBytes(item.size_bytes)}</small>
                    </button>
                  ))}
                </div>
              </div>

              <div className="video-merge-inputs">
                <strong>{t("features.tools.videoMerge.mergeOrder")}</strong>
                {sortedInputs.length === 0 ? (
                  <EmptyState title={t("features.tools.videoMerge.noInputs")} description={t("features.tools.videoMerge.emptyGuide")}
                    action={{ label: t("navigation.items.browseMedia"), onClick: () => navigate("/browse-v2?domain=media") }} />
                ) : null}
                {sortedInputs.map((item, index) => (
                  <div
                    key={item.id}
                    className="video-merge-input-row"
                    draggable
                    onDragStart={() => setDraggedIndex(index)}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={() => {
                      if (draggedIndex !== null) {
                        moveInput(draggedIndex, index);
                        setDraggedIndex(null);
                      }
                    }}
                  >
                    <span className="video-merge-input-row__handle">#{index + 1}</span>
                    <div>
                      <strong>{item.name}</strong>
                      <small>
                        {item.sourceKind === "indexed_file"
                          ? t("features.tools.videoMerge.indexed")
                          : t("features.tools.videoMerge.external")}
                        {" · "}
                        {formatBytes(item.sizeBytes)}
                      </small>
                    </div>
                    <div className="video-merge-input-row__actions">
                      <button className="ghost-button" type="button" onClick={() => moveInput(index, index - 1)} disabled={index === 0}>
                        {t("features.tools.videoMerge.moveUp")}
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => moveInput(index, index + 1)}
                        disabled={index === sortedInputs.length - 1}
                      >
                        {t("features.tools.videoMerge.moveDown")}
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => setInputs((current) => current.filter((input) => input.id !== item.id))}
                      >
                        {t("features.tools.videoMerge.delete")}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="video-merge-settings">
              <label className="field-stack">
                <span>{t("features.tools.videoMerge.outputName")}</span>
                <input className="text-input" value={outputName} onChange={(event) => setOutputName(event.target.value)} />
              </label>
              <label className="field-stack">
                <span>{t("features.tools.videoMerge.outputDir")}</span>
                <div className="video-merge-output-dir">
                  <input className="text-input" value={effectiveOutputDir} onChange={(event) => setOutputDir(event.target.value)} />
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      const selectedPath = await (
                        window as typeof window & {
                          assetWorkbench?: { selectFolder?: () => Promise<string | null> };
                        }
                      ).assetWorkbench?.selectFolder?.();
                      if (selectedPath) {
                        setOutputDir(selectedPath);
                      }
                    }}
                  >
                    {t("common.actions.chooseFolder")}
                  </button>
                </div>
              </label>
              <fieldset className="video-merge-mode">
                <legend>{t("features.tools.videoMerge.mode")}</legend>
                <label>
                  <input type="radio" checked={mode === "copy"} onChange={() => setMode("copy")} />
                  <span>{t("features.tools.videoMerge.copyMode")}</span>
                  <small>{t("features.tools.videoMerge.copyHint")}</small>
                </label>
                <label>
                  <input type="radio" checked={mode === "reencode"} onChange={() => setMode("reencode")} />
                  <span>{t("features.tools.videoMerge.reencodeMode")}</span>
                  <small>{t("features.tools.videoMerge.reencodeHint")}</small>
                </label>
              </fieldset>
              <button className="primary-button" type="button" onClick={startMerge} disabled={!canStart}>
                {createRunMutation.isPending ? t("features.tools.videoMerge.starting") : t("features.tools.videoMerge.start")}
              </button>
            </div>

            {createRunMutation.error instanceof Error ? (
              <div className="status-block page-card">
                <strong>{t("features.tools.videoMerge.failed")}</strong>
                <p>{createRunMutation.error.message}</p>
              </div>
            ) : null}
          </div>
          ) : null}

          {activeTab === "inProgress" ? (
            <div className="page-card tool-run-panel" role="tabpanel">
              <div className="tools-section-header">
                <strong>{t("features.tools.tabs.inProgress")}</strong>
                <span className="status-pill">{activeRuns.length}</span>
              </div>
              {activeRuns.length === 0 ? (
                <div className="future-frame">{t("features.tools.empty.inProgress")}</div>
              ) : (
                <div className="tool-run-card-list">
                  {activeRuns.map((run) => (
                    <ToolRunCard
                      key={run.id}
                      run={run}
                      selected={activeRunId === run.id}
                      onSelect={() => setActiveRunId(run.id)}
                    />
                  ))}
                </div>
              )}
              <ToolRunDetail run={activeRunQuery.data} />
            </div>
          ) : null}

          {activeTab === "completed" ? (
            <div className="page-card tool-run-panel" role="tabpanel">
              <div className="tools-section-header">
                <strong>{t("features.tools.tabs.completed")}</strong>
                <span className="status-pill">{completedRuns.length}</span>
              </div>
              {completedRuns.length === 0 ? (
                <div className="future-frame">{t("features.tools.empty.completed")}</div>
              ) : (
                <div className="tool-run-card-list">
                  {completedRuns.map((run) => (
                    <ToolRunCard
                      key={run.id}
                      run={run}
                      selected={activeRunId === run.id}
                      onSelect={() => setActiveRunId(run.id)}
                    />
                  ))}
                </div>
              )}
              <ToolRunDetail run={activeRunQuery.data} />
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
