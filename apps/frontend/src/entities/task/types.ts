export type TaskStatus = "pending" | "running" | "succeeded" | "failed";

export type TaskType = "scan_source" | "rescan_source" | "extract_metadata" | "generate_thumbnail";

export type TriggerScanResult = {
  task_id: number;
  status: TaskStatus;
};
