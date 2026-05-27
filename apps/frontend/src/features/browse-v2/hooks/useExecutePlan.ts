import { useState } from "react";
import { preparePlan, executePlan, getOrganizePlan, type PreparePlanResponse } from "../../../services/api/libraryOrganizeApi";

export interface ExecutePlanState {
  loading: boolean; planId: number | null;
  preflight: PreparePlanResponse | null; error: string | null;
  executed: boolean; executionStatus: string | null;
  summary: Record<string, unknown> | null;
}

export function useExecutePlan() {
  const [s, setS] = useState<ExecutePlanState>({
    loading: false, planId: null, preflight: null, error: null,
    executed: false, executionStatus: null, summary: null,
  });

  const start = async (planId: number) => {
    setS({ loading: true, planId, preflight: null, error: null, executed: false, executionStatus: null, summary: null });
    try {
      const pf = await preparePlan(planId);
      setS(prev => ({ ...prev, loading: false, preflight: pf }));
    } catch (e) { setS(prev => ({ ...prev, loading: false, error: String(e) })); }
  };

  const execute = async () => {
    if (!s.preflight?.can_execute || s.planId === null) return;
    setS(prev => ({ ...prev, loading: true }));
    try {
      const r = await executePlan(s.planId);
      let summary: Record<string, unknown> | null = null;
      try {
        const detail = await getOrganizePlan(s.planId);
        if (detail?.plan?.summary_json) {
          summary = JSON.parse(detail.plan.summary_json);
        }
      } catch { /* summary is optional */ }
      setS(prev => ({ ...prev, loading: false, executed: true, executionStatus: r.status, summary }));
    } catch (e) { setS(prev => ({ ...prev, loading: false, error: String(e) })); }
  };

  const reset = () => setS({
    loading: false, planId: null, preflight: null, error: null,
    executed: false, executionStatus: null, summary: null,
  });

  return { ...s, start, execute, reset };
}
