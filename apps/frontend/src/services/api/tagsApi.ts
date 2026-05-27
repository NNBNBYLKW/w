import { getApiBaseUrl, parseResponse } from "./client";
import type {
  BatchTagAttachResponseVM,
  TagFilesListResponseVM,
  TagFilesQueryInput,
  TagListResponseVM,
  TagResponseVM,
} from "../../entities/tag/types";


export class TagsApiError extends Error {
  code: string | null;

  constructor(message: string, code: string | null = null) {
    super(message);
    this.name = "TagsApiError";
    this.code = code;
  }
}

function p<T>(response: Response): Promise<T> {
  return parseResponse<T>(response, TagsApiError);
}

export async function listTags(): Promise<TagListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/tags`);
  return p<TagListResponseVM>(response);
}


export async function createTag(name: string): Promise<TagResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/tags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return p<TagResponseVM>(response);
}


export async function attachTagToFile(fileId: number, name: string): Promise<TagListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/tags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return p<TagListResponseVM>(response);
}


export async function attachTagToFilesBatch(fileIds: number[], name: string): Promise<BatchTagAttachResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/batch/tags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids: fileIds, name }),
  });
  return p<BatchTagAttachResponseVM>(response);
}


export async function removeTagFromFile(fileId: number, tagId: number): Promise<TagListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/tags/${tagId}`, {
    method: "DELETE",
  });
  return p<TagListResponseVM>(response);
}


export async function renameTag(tagId: number, name: string): Promise<TagResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/tags/${tagId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return p<TagResponseVM>(response);
}


export async function deleteTagApi(tagId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/tags/${tagId}`, {
    method: "DELETE",
  });
  await parseResponse<{ message: string }>(response);
}


export async function mergeTags(sourceId: number, targetId: number): Promise<TagResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/tags/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_id: sourceId, target_id: targetId }),
  });
  return p<TagResponseVM>(response);
}


export async function listFilesForTag(tagId: number, params: Omit<TagFilesQueryInput, "tagId">): Promise<TagFilesListResponseVM> {
  const searchParams = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.page_size),
    sort_by: params.sort_by,
    sort_order: params.sort_order,
  });
  const response = await fetch(`${getApiBaseUrl()}/tags/${tagId}/files?${searchParams.toString()}`);
  return p<TagFilesListResponseVM>(response);
}
