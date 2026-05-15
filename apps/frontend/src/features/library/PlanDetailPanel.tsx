import { useEffect, useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { t } from "../../shared/text";
import { queryKeys } from "../../services/query/queryKeys";
import { invalidateLibraryOrganizeSurfaces } from "../../services/query/invalidation";
import type { OrganizePlanListQueryInput, PreflightResponseVM, CopyFailedActionsResponseVM, GenerateAssetYamlMergeResponseVM, GenerateRollbackResponseVM, ReconcilePlanResponseVM, OrganizeActionItemVM, OrganizeActionLogItemVM } from "../../entities/library/types";
import { getOrganizePlan, markOrganizePlanReady, preflightOrganizePlan, executeOrganizePlan, cancelOrganizePlan, getOrganizePlanLogs, reconcileOrganizePlan, copyFailedActions, generateRollbackPlan, generateAssetYamlMerge, updateOrganizeAction } from "../../services/api/libraryObjectsApi";
import { EmptyState, LoadingState, PlanStatusPill, StatusBadge, ActionButton, KeyValueRow } from "../../shared/ui/components";
import { formatTimestamp } from "./shared/helpers";


const PATH_LENGTH_WARN = 240;
const PATH_LENGTH_MAX = 260;

function planActionSeverity(action: OrganizeActionItemVM): string {
  const s = action.conflict_status ?? "unchecked";
  if (s === "blocked") return "danger";
  if (s === "stale") return "danger";
  if (s === "warning") return "warning";
  return "neutral";
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
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

  const severity = planActionSeverity(action);
  const isProblem = severity === "danger" || severity === "warning";
  const rowClass = [
    "library-action-row",
    severity === "danger" ? "library-action-row--blocked" : "",
    severity === "warning" ? "library-action-row--warning" : "",
  ].filter(Boolean).join(" ");

  const targetLen = action.target_path ? action.target_path.length : 0;
  const pathLenClass = targetLen >= PATH_LENGTH_WARN ? "danger-text" : targetLen >= 220 ? "warning-text" : "";

  return (
    <div className={rowClass}>
      <div>
        <strong>{action.action_type}</strong>
        <span className={`status-pill status-pill--${severity === "danger" ? "danger" : severity === "warning" ? "warning" : "neutral"}`}>
          {action.conflict_status}
        </span>
        <span className="status-pill status-pill--neutral">{action.status}</span>
      </div>
      {isProblem && action.conflict_message ? (
        <small className={severity === "danger" ? "danger-text" : "warning-text"}>{action.conflict_message}</small>
      ) : null}
      {action.source_path ? (
        <div className="library-action-row__path">
          <small title={action.source_path}>{t("features.library.organize.sourcePath")}: {action.source_path}</small>
          <button className="library-action-row__copy-btn" type="button" title={t("features.library.organize.copyPath")} onClick={() => copyToClipboard(action.source_path!)}>
            {t("features.library.organize.copy")}
          </button>
        </div>
      ) : null}
      {editable ? (
        <div className="library-action-edit">
          <input value={targetPath} onChange={(event) => setTargetPath(event.target.value)} />
          <button className="secondary-button" type="button" onClick={() => onUpdateTarget(targetPath)}>
            {t("common.actions.save")}
          </button>
        </div>
      ) : (
        <div className="library-action-row__path">
          <small title={action.target_path ?? undefined}>{t("features.library.organize.targetPath")}: {action.target_path ?? t("common.states.unavailable")}</small>
          {action.target_path ? (
            <button className="library-action-row__copy-btn" type="button" title={t("features.library.organize.copyPath")} onClick={() => copyToClipboard(action.target_path!)}>
              {t("features.library.organize.copy")}
            </button>
          ) : null}
        </div>
      )}
      {action.target_path ? (
        <small className={pathLenClass}>{t("features.library.organize.pathLength")}: {targetLen} / {PATH_LENGTH_MAX}</small>
      ) : null}
      {!isProblem && action.conflict_message ? <small>{action.conflict_message}</small> : null}
      {action.before_path ? <small title={action.before_path}>{t("features.library.organize.beforePath")}: {action.before_path}</small> : null}
      {action.after_path ? <small title={action.after_path}>{t("features.library.organize.afterPath")}: {action.after_path}</small> : null}
      {action.error_message ? <small className="danger-text">{action.error_message}</small> : null}
      {action.payload_json ? <pre className="library-payload-preview">{action.payload_json}</pre> : null}
    </div>
  );
}


function PlanLogList({ logs, isLoading }: { logs: OrganizeActionLogItemVM[]; isLoading: boolean }) {
  if (isLoading) {
    return <LoadingState message={t("common.states.loading")} />;
  }
  if (logs.length === 0) {
    return <EmptyState title={t("features.library.organize.noLogs")} />;
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


export function PlanDetail({
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
      await invalidateLibraryOrganizeSurfaces(queryClient, detail.plan.id, { stats: true });
    },
  });
  const preflightMutation = useMutation({
    mutationFn: preflightOrganizePlan,
    onSuccess: async (result) => {
      setPreflightResult(result);
      await invalidateLibraryOrganizeSurfaces(queryClient, result.plan_id, { logs: true });
    },
  });
  const executeMutation = useMutation({
    mutationFn: executeOrganizePlan,
    onSuccess: async (result) => {
      setConfirmOpen(false);
      setConfirmChecked(false);
      setPreflightResult(null);
      await invalidateLibraryOrganizeSurfaces(queryClient, result.plan_id, { logs: true, stats: true });
    },
  });
  const cancelMutation = useMutation({
    mutationFn: cancelOrganizePlan,
    onSuccess: async (detail) => {
      setPreflightResult(null);
      await invalidateLibraryOrganizeSurfaces(queryClient, detail.plan.id, { stats: true });
    },
  });
  const updateActionMutation = useMutation({
    mutationFn: ({ actionId, targetPath }: { actionId: number; targetPath: string }) =>
      updateOrganizeAction(actionId, { target_path: targetPath }),
    onSuccess: async (detail) => {
      setPreflightResult(null);
      await invalidateLibraryOrganizeSurfaces(queryClient, detail.plan.id, { plansList: false });
    },
  });
  const [reconcileResult, setReconcileResult] = useState<ReconcilePlanResponseVM | null>(null);
  const reconcileMutation = useMutation({
    mutationFn: reconcileOrganizePlan,
    onSuccess: async (result) => {
      setReconcileResult(result);
      await invalidateLibraryOrganizeSurfaces(queryClient, result.plan_id, { logs: true });
    },
  });
  const [copyFailedResult, setCopyFailedResult] = useState<CopyFailedActionsResponseVM | null>(null);
  const copyFailedMutation = useMutation({
    mutationFn: copyFailedActions,
    onSuccess: async (result) => {
      setCopyFailedResult(result);
      await invalidateLibraryOrganizeSurfaces(queryClient, detail.plan.id);
    },
  });
  const [generateRollbackResult, setGenerateRollbackResult] = useState<GenerateRollbackResponseVM | null>(null);
  const generateRollbackMutation = useMutation({
    mutationFn: generateRollbackPlan,
    onSuccess: async (result) => {
      setGenerateRollbackResult(result);
      await invalidateLibraryOrganizeSurfaces(queryClient, detail.plan.id);
    },
  });

  const [mergeResult, setMergeResult] = useState<GenerateAssetYamlMergeResponseVM | null>(null);
  const mergeMutation = useMutation({
    mutationFn: generateAssetYamlMerge,
    onSuccess: async (result) => {
      setMergeResult(result);
      await invalidateLibraryOrganizeSurfaces(queryClient, detail.plan.id);
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

  const severityOrder = useMemo(() => ({ blocked: 0, stale: 1, warning: 2, ok: 3, unchecked: 4 } as Record<string, number>), []);
  const sortedActions = useMemo(() => {
    const actions = detailQuery.data?.actions ?? [];
    return [...actions].sort((a, b) => {
      const sa = severityOrder[a.conflict_status ?? "unchecked"] ?? 4;
      const sb = severityOrder[b.conflict_status ?? "unchecked"] ?? 4;
      if (sa !== sb) return sa - sb;
      if (a.action_order !== b.action_order) return a.action_order - b.action_order;
      return String(a.target_path ?? "").localeCompare(String(b.target_path ?? ""));
    });
  }, [detailQuery.data?.actions, severityOrder]);

  if (planId === null) {
    return (
      <aside className="library-object-detail">
        <EmptyState title={t("features.library.organize.selectPlan")} />
      </aside>
    );
  }
  if (detailQuery.isLoading) {
    return (
      <aside className="library-object-detail">
        <LoadingState message={t("common.states.loading")} />
      </aside>
    );
  }
  if (detailQuery.isError || !detailQuery.data) {
    return (
      <aside className="library-object-detail">
        <EmptyState title={t("features.library.scan.unableToLoad")} description={detailQuery.error instanceof Error ? detailQuery.error.message : undefined} />
      </aside>
    );
  }

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
          <strong>
            {preflightResult.can_execute
              ? preflightResult.warning_count > 0
                ? t("features.library.organize.preflightWarnings")
                : t("features.library.organize.preflightAllOk")
              : t("features.library.organize.preflightCannotExecute")}
          </strong>
          <span>
            {preflightResult.can_execute
              ? preflightResult.warning_count > 0
                ? t("features.library.organize.preflightWarningsHint")
                : t("features.library.organize.preflightAllOkHint")
              : t("features.library.organize.preflightCannotExecuteHint")}
          </span>
        </div>
      ) : null}
      {preflightResult ? (
        <div className="library-preflight-summary">
          <span className="library-preflight-summary__chip library-preflight-summary__chip--blocked">
            {t("features.library.organize.blocked")}: {preflightResult.blocked_count}
          </span>
          <span className="library-preflight-summary__chip library-preflight-summary__chip--stale">
            {t("features.library.organize.stale")}: {preflightResult.actions.filter(a => a.conflict_status === "stale").length}
          </span>
          <span className="library-preflight-summary__chip library-preflight-summary__chip--warning">
            {t("features.library.organize.warning")}: {preflightResult.warning_count}
          </span>
          <span className="library-preflight-summary__chip library-preflight-summary__chip--ready">
            {t("features.library.organize.readyChip")}: {preflightResult.actions.filter(a => a.conflict_status === "ok").length}
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
      <h5>{t("features.library.organize.pathPreview")}</h5>
      <div className="library-action-list">
        {sortedActions.map((action) => (
          <PlanActionRow
            key={action.id}
            action={action}
            editable={detail.plan.status === "draft" || detail.plan.status === "ready"}
            onUpdateTarget={(targetPath) => updateActionMutation.mutate({ actionId: action.id, targetPath })}
          />
        ))}
      </div>
      <h5>{t("features.library.organize.executionLogs")}</h5>
      <PlanLogList logs={logsQuery.data?.items ?? []} isLoading={logsQuery.isLoading} />
    </aside>
  );
}

