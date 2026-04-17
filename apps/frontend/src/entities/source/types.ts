export type SourceVM = {
  id: number;
  path: string;
  display_name: string | null;
  is_enabled: boolean;
  scan_mode: string;
  last_scan_at: string | null;
  last_scan_status: string | null;
  last_scan_error_message: string | null;
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
