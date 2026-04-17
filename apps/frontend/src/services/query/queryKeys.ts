import type { FilesListQueryInput, SearchQueryInput } from "../../entities/file/types";
import type { MediaListQueryInput } from "../../entities/media/types";
import type { RecentListQueryInput } from "../../entities/recent/types";
import type { TagFilesQueryInput } from "../../entities/tag/types";
import type { CollectionFilesQueryInput } from "../../entities/collection/types";


export const queryKeys = {
  systemStatus: ["system-status"] as const,
  sources: ["sources"] as const,
  tags: ["tags"] as const,
  collections: ["collections"] as const,
  fileDetail: (fileId: number) => ["file-detail", fileId] as const,
  collectionFiles: (params: CollectionFilesQueryInput) => ["collection-files", params] as const,
  filesList: (params: FilesListQueryInput) => ["files-list", params] as const,
  mediaLibrary: (params: MediaListQueryInput) => ["media-library", params] as const,
  recent: (params: RecentListQueryInput) => ["recent", params] as const,
  search: (params: SearchQueryInput) => ["search", params] as const,
  tagFiles: (params: TagFilesQueryInput) => ["tag-files", params] as const,
};
