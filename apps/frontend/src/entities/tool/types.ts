export type ToolRunStatus = "pending" | "running" | "succeeded" | "failed" | "cancelled";
export type VideoMergeMode = "copy" | "reencode";
export type VideoMergeSourceKind = "indexed_file" | "external_path";

export type ToolItemVM = {
  key: string;
  title_key: string;
  description_key: string;
  category: string;
};

export type ToolListResponseVM = {
  items: ToolItemVM[];
};

export type VideoMergeInputItemVM = {
  source_kind: VideoMergeSourceKind;
  file_id?: number;
  path?: string;
};

export type VideoMergeRunCreateInput = {
  inputs: VideoMergeInputItemVM[];
  output_name: string;
  output_dir?: string;
  mode: VideoMergeMode;
};

export type ToolRunCreateResponseVM = {
  run_id: number;
  status: ToolRunStatus;
};

export type ToolRunVM = {
  id: number;
  tool_key: string;
  status: ToolRunStatus;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  output_path: string | null;
  final_output_name: string | null;
  log_tail: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ToolRunListResponseVM = {
  items: ToolRunVM[];
  page: number;
  page_size: number;
  total: number;
};
