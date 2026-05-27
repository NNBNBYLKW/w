import { getApiBaseUrl, parseResponse } from "./client";
import type {
  ToolListResponseVM,
  ToolRunCreateResponseVM,
  ToolRunListResponseVM,
  ToolRunVM,
  VideoMergeRunCreateInput,
} from "../../entities/tool/types";


export async function listTools(): Promise<ToolListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/tools`);
  return parseResponse<ToolListResponseVM>(response);
}


export async function createVideoMergeRun(input: VideoMergeRunCreateInput): Promise<ToolRunCreateResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/tools/video-merge/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<ToolRunCreateResponseVM>(response);
}


export async function getToolRun(runId: number): Promise<ToolRunVM> {
  const response = await fetch(`${getApiBaseUrl()}/tools/runs/${runId}`);
  return parseResponse<ToolRunVM>(response);
}


export async function listToolRuns(input: { page: number; page_size: number }): Promise<ToolRunListResponseVM> {
  const params = new URLSearchParams();
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  const response = await fetch(`${getApiBaseUrl()}/tools/runs?${params.toString()}`);
  return parseResponse<ToolRunListResponseVM>(response);
}
