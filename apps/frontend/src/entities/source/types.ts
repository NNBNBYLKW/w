export type SourceVM = {
  id: number;
  path: string;
  display_name: string | null;
  is_enabled: boolean;
  scan_mode: string;
  last_scan_at: string | null;
  last_scan_status: string | null;
  last_scan_error_message: string | null;
  discovered_count: number | null;
  created_at: string;
  updated_at: string;
};

export type CreateSourceInput = {
  path: string;
  display_name: string | null;
};

export type UpdateSourceInput = {
  display_name?: string | null;
  is_enabled?: boolean;
};

export type ScanTaskVM = {
  id: number;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
};
