import type { DragEvent } from "react";

const WORKBENCH_FILE_DRAG_MIME = "application/x-workbench-file";

export type WorkbenchFileDragPayload = {
  file_id: number;
  name: string;
  path: string;
  file_type: string;
};


export function setWorkbenchFileDragData(event: DragEvent<HTMLElement>, payload: WorkbenchFileDragPayload): void {
  event.dataTransfer.effectAllowed = "copy";
  event.dataTransfer.setData(WORKBENCH_FILE_DRAG_MIME, JSON.stringify(payload));
}


export function getWorkbenchFileDragData(event: DragEvent<HTMLElement>): WorkbenchFileDragPayload | null {
  const rawPayload = event.dataTransfer.getData(WORKBENCH_FILE_DRAG_MIME);
  if (!rawPayload) {
    return null;
  }
  try {
    const parsed = JSON.parse(rawPayload) as WorkbenchFileDragPayload;
    if (!parsed.file_id || !parsed.path || !parsed.name) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}
