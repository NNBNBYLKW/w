import type { FilesListQueryInput, SearchQueryInput } from "../../entities/file/types";
import type { MediaListQueryInput } from "../../entities/media/types";
import type { RecentListQueryInput } from "../../entities/recent/types";


export const queryKeys = {
  systemStatus: ["system-status"] as const,
  sources: ["sources"] as const,
  fileDetail: (fileId: number) => ["file-detail", fileId] as const,
  filesList: (params: FilesListQueryInput) => ["files-list", params] as const,
  mediaLibrary: (params: MediaListQueryInput) => ["media-library", params] as const,
  recent: (params: RecentListQueryInput) => ["recent", params] as const,
  search: (params: SearchQueryInput) => ["search", params] as const,
};
