import { getApiBaseUrl, parseResponse } from "./client";
import type { CreateSourceInput, SourceVM, UpdateSourceInput } from "../../entities/source/types";
import type { TriggerScanResult } from "../../entities/task/types";


type SourceListResponse = {
  items: SourceVM[];
};


export class SourcesApiError extends Error {
  code: string | null;

  constructor(message: string, code: string | null = null) {
    super(message);
    this.name = "SourcesApiError";
    this.code = code;
  }
}


export async function getSources(): Promise<SourceVM[]> {
  const response = await fetch(`${getApiBaseUrl()}/sources`);
  const payload = await parseResponse<SourceListResponse>(response, SourcesApiError);
  return payload.items;
}


export async function getSource(sourceId: number): Promise<SourceVM> {
  const response = await fetch(`${getApiBaseUrl()}/sources/${sourceId}`);
  return parseResponse<SourceVM>(response, SourcesApiError);
}


export async function createSource(input: CreateSourceInput): Promise<SourceVM> {
  const response = await fetch(`${getApiBaseUrl()}/sources`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  return parseResponse<SourceVM>(response, SourcesApiError);
}


export async function updateSource(sourceId: number, input: UpdateSourceInput): Promise<SourceVM> {
  const response = await fetch(`${getApiBaseUrl()}/sources/${sourceId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  return parseResponse<SourceVM>(response, SourcesApiError);
}


export async function deleteSource(sourceId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/sources/${sourceId}`, {
    method: "DELETE",
  });
  await parseResponse<{ message: string }>(response, SourcesApiError);
}


export async function triggerSourceScan(sourceId: number): Promise<TriggerScanResult> {
  const response = await fetch(`${getApiBaseUrl()}/sources/${sourceId}/scan`, {
    method: "POST",
  });
  return parseResponse<TriggerScanResult>(response, SourcesApiError);
}
