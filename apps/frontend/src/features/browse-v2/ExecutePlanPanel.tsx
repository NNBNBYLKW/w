import { useEffect } from "react";
import { t } from "../../shared/text";
import { LoadingState } from "../../shared/ui/components/LoadingState";
import { ProgressBar } from "../../shared/ui/components/ProgressBar";
import { useExecutePlan } from "./hooks/useExecutePlan";

interface Props { planId: number; onClose: () => void; }

export function ExecutePlanPanel({ planId, onClose }: Props) {
  const { loading, preflight, error, executed, executionStatus, summary, progress, start, execute, reset } = useExecutePlan();
  const memberCount = summary ? (summary.finalized_member_count ?? summary.finalized_add_count ?? summary.finalized_remove_count) : null;
  const objectName = summary ? (summary.object_name as string) : null;

  useEffect(() => { start(planId); }, [planId]); // eslint-disable-line

  const close = () => { reset(); onClose(); };

  return (
    <div className="execute-plan-panel" role="dialog" aria-label={t("features.browseV2.executePanel.title")}>
      <div className="execute-plan-panel__header">
        <h3>{t("features.browseV2.executePanel.title")}</h3>
        <button className="ghost-button" type="button" onClick={close}>&times;</button>
      </div>
      <div className="execute-plan-panel__body">
        {loading && <LoadingState />}
        {error && <div className="browse-v2-state browse-v2-state--error" role="alert">{error}</div>}
        {preflight && !executed && (
          <>
            {preflight.can_execute ? (
              <div className="browse-v2-inline-alert browse-v2-inline-alert--success">
                {t("features.browseV2.executePanel.ready")}
              </div>
            ) : (
              <div className="browse-v2-inline-alert browse-v2-inline-alert--error">
                <strong>{t("features.browseV2.executePanel.blocked")}</strong>
                <p>{t("features.browseV2.executePanel.blockedHint")}</p>
                {preflight.messages?.map((m, i) => <p key={i} className="muted-text">{m}</p>)}
              </div>
            )}
            {preflight.can_execute && (
              <button className="primary-button" type="button" onClick={execute} disabled={loading} style={{marginTop:12}}>
                {loading ? t("features.browseV2.executePanel.executing") : t("features.browseV2.executePanel.execute")}
              </button>
            )}
            {progress && !executed && (
              <div style={{marginTop:12}}>
                <div style={{fontSize:13,color:"var(--color-text-muted)",marginBottom:4}}>
                  Executing action {progress.done}/{progress.total}...
                </div>
                <ProgressBar done={progress.done} total={progress.total} showLabel />
              </div>
            )}
          </>
        )}
        {executed && (
          <div className="browse-v2-inline-alert browse-v2-inline-alert--success">
            <strong>{t("features.browseV2.executePanel.completed")}</strong>
            {executionStatus ? <p style={{margin: "8px 0"}}>{executionStatus}</p> : null}
            {summary ? (
              <div className="execute-plan-panel__summary" style={{fontSize: 13, lineHeight: 1.8, marginTop: 8}}>
                {objectName ? <div>{t("features.browseV2.executePanel.objectNameLabel")}: {objectName}</div> : null}
                {memberCount != null ? <div>{t("features.browseV2.executePanel.membersLabel")}: {memberCount}</div> : null}
              </div>
            ) : null}
            <button className="primary-button" type="button" onClick={close} style={{marginTop: 12}}>
              {t("features.browseV2.executePanel.close")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
