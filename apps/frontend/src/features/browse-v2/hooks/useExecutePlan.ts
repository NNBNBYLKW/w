import { useState } from "react";
import { preparePlan, executePlan, type PreparePlanResponse } from "../../../services/api/libraryOrganizeApi";

export interface ExecutePlanState {
  loading: boolean; planId: number | null;
  preflight: PreparePlanResponse | null; error: string | null;
  executed: boolean; executionStatus: string | null;
}

export function useExecutePlan() {
  const [s, setS] = useState<ExecutePlanState>({ loading: false, planId: null, preflight: null, error: null, executed: false, executionStatus: null });

  const start = async (planId: number) => {
    setS({ loading: true, planId, preflight: null, error: null, executed: false, executionStatus: null });
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
      setS(prev => ({ ...prev, loading: false, executed: true, executionStatus: r.status }));
    } catch (e) { setS(prev => ({ ...prev, loading: false, error: String(e) })); }
  };

  const reset = () => setS({ loading: false, planId: null, preflight: null, error: null, executed: false, executionStatus: null });

  return { ...s, start, execute, reset };
}
