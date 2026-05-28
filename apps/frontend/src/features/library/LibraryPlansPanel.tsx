import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { t } from "../../shared/text";
import { queryKeys } from "../../services/query/queryKeys";
import type { OrganizePlanListQueryInput } from "../../entities/library/types";
import { listOrganizePlans } from "../../services/api/libraryObjectsApi";
import { EmptyState, LoadingState, PlanStatusPill } from "../../shared/ui/components";
import { formatTimestamp } from "./shared/helpers";
import { PlanDetail } from "./PlanDetailPanel";


export function LibraryPlansPanel() {
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [status, setStatus] = useState("");
  const queryParams = useMemo<OrganizePlanListQueryInput>(
    () => ({ page: 1, page_size: 30, status: status || undefined }),
    [status],
  );
  const plansQuery = useQuery({
    queryKey: queryKeys.organizePlans(queryParams),
    queryFn: () => listOrganizePlans(queryParams),
  });
  return (
    <section className="library-objects-panel library-design-panel library-design-panel--plans">
      <div className="library-panel-toolbar library-design-hero">
        <div>
          <span className="page-header__eyebrow">{t("features.library.plans.eyebrow")}</span>
          <h3>{t("features.library.organize.plansTitle")}</h3>
          <p>{t("features.library.organize.phase3Safety")}</p>
        </div>
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">{t("features.library.objects.allReviewStates")}</option>
          <option value="draft">draft</option>
          <option value="ready">ready</option>
          <option value="executing">executing</option>
          <option value="completed">completed</option>
          <option value="completed_with_errors">completed_with_errors</option>
          <option value="failed">failed</option>
          <option value="cancelled">cancelled</option>
        </select>
      </div>
      <div className="library-objects-layout library-plans-layout">
        <div className="library-object-list-panel library-design-card">
          {plansQuery.isLoading ? <LoadingState message={t("common.states.loading")} /> : null}
          {plansQuery.isError ? (
            <EmptyState title={t("features.library.scan.unableToLoad")} description={String(plansQuery.error)} />
          ) : null}
          {plansQuery.data && plansQuery.data.items.length === 0 ? (
            <EmptyState title={t("features.library.organize.noPlans")} description={t("features.library.organize.plansEmptyGuide")} />
          ) : null}
          <div className="library-object-list">
            {plansQuery.data?.items.map((plan) => (
              <button
                key={plan.id}
                className={`library-object-row${selectedPlanId === plan.id ? " library-object-row--selected" : ""}`}
                type="button"
                onClick={() => setSelectedPlanId(plan.id)}
              >
                <span className="library-object-row__type"><PlanStatusPill status={plan.status} /></span>
                <span className="library-object-row__main">
                  <strong>{plan.title}</strong>
                  <small>{formatTimestamp(plan.updated_at)}</small>
                </span>
                <span className="library-object-row__meta">
                  <span>{t("features.library.organize.actions")}: {plan.actions_count}</span>
                  <span>{t("features.library.organize.blocked")}: {plan.blocked_count}</span>
                  <span>{t("features.library.organize.warning")}: {plan.warning_count}</span>
                  <span>{t("features.library.organize.failed")}: {plan.failed_count}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
        <PlanDetail planId={selectedPlanId} onSelectPlan={setSelectedPlanId} />
      </div>
    </section>
  );
}
