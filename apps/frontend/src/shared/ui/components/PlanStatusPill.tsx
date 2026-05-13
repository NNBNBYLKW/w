import { StatusBadge, type StatusBadgeVariant } from "./StatusBadge";

const statusVariant: Record<string, StatusBadgeVariant> = {
  draft: "info",
  ready: "success",
  executing: "accent",
  completed: "success",
  completed_with_errors: "warning",
  failed: "danger",
  cancelled: "muted",
};

export function PlanStatusPill({ status }: { status: string }) {
  return <StatusBadge variant={statusVariant[status] ?? "muted"}>{status}</StatusBadge>;
}
