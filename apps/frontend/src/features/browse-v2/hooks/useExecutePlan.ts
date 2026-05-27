import { useEffect, useRef, useState } from "react";
import { preparePlan, executePlan, getOrganizePlan, type PreparePlanResponse } from "../../../services/api/libraryOrganizeApi";

export interface ExecutePlanState {
  loading: boolean; planId: number | null;
  preflight: PreparePlanResponse | null; error: string | null;
  executed: boolean; executionStatus: string | null;
  summary: Record<string, unknown> | null;
  progress: { total: number; done: number } | null;
}

export function useExecutePlan() {
  const [s, setS] = useState<ExecutePlanState>({
    loading: false, planId: null, preflight: null, error: null,
    executed: false, executionStatus: null, summary: null,
    progress: null,
  });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current !== null) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

  const start = async (planId: number) => {
    setS({ loading: true, planId, preflight: null, error: null, executed: false, executionStatus: null, summary: null, progress: null });
    try {
      const pf = await preparePlan(planId);
      setS(prev => ({ ...prev, loading: false, preflight: pf }));
    } catch (e) { setS(prev => ({ ...prev, loading: false, error: String(e) })); }
  };

  const execute = async () => {
    if (!s.preflight?.can_execute || s.planId === null) return;
    if (pollRef.current !== null) return;
    setS(prev => ({ ...prev, loading: true }));
    try {
      const planId = s.planId;
      await executePlan(planId);
      const poll = setInterval(async () => {
        try {
          const detail = await getOrganizePlan(planId);
          const actions = detail.actions as Array<{status: string}>;
          const done = actions.filter(a => a.status === "succeeded" || a.status === "failed").length;
          setS(prev => ({ ...prev, progress: { total: actions.length, done } }));
          if (["completed", "completed_with_errors", "failed"].includes(detail.plan.status)) {
            clearInterval(poll);
            pollRef.current = null;
            let summary: Record<string, unknown> | null = null;
            try { if (detail.plan.summary_json) summary = JSON.parse(detail.plan.summary_json); } catch {}
            setS(prev => ({ ...prev, loading: false, executed: true, executionStatus: detail.plan.status, summary, progress: null }));
          }
        } catch { /* keep polling */ }
      }, 2000);
      pollRef.current = poll;
    } catch (e) { setS(prev => ({ ...prev, loading: false, error: String(e) })); }
  };

  const reset = () => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setS({
      loading: false, planId: null, preflight: null, error: null,
      executed: false, executionStatus: null, summary: null, progress: null,
    });
  };

  return { ...s, start, execute, reset };
}
