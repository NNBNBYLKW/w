import { useEffect } from "react";
import { t } from "../../shared/text";
import { LoadingState } from "../../shared/ui/components/LoadingState";
import { useExecutePlan } from "./hooks/useExecutePlan";

interface Props { planId: number; onClose: () => void; }

export function ExecutePlanPanel({ planId, onClose }: Props) {
  const { loading, preflight, error, executed, start, execute, reset } = useExecutePlan();

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
          </>
        )}
        {executed && (
          <div className="browse-v2-inline-alert browse-v2-inline-alert--success">
            {t("features.browseV2.executePanel.completed")}
          </div>
        )}
      </div>
    </div>
  );
}
