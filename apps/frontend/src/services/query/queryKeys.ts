import type { BookListQueryInput } from "../../entities/book/types";
import type { FilesListQueryInput, SearchQueryInput } from "../../entities/file/types";
import type { GamesListQueryInput } from "../../entities/game/types";
import type { MediaListQueryInput } from "../../entities/media/types";
import type { RecentListQueryInput } from "../../entities/recent/types";
import type { TagFilesQueryInput } from "../../entities/tag/types";
import type { CollectionFilesQueryInput } from "../../entities/collection/types";
import type { SoftwareListQueryInput } from "../../entities/software/types";


export const queryKeys = {
  systemStatus: ["system-status"] as const,
  sources: ["sources"] as const,
  tags: ["tags"] as const,
  collections: ["collections"] as const,
  booksList: (params: BookListQueryInput) => ["books-list", params] as const,
  gamesList: (params: GamesListQueryInput) => ["games-list", params] as const,
  softwareList: (params: SoftwareListQueryInput) => ["software-list", params] as const,
  fileDetail: (fileId: number) => ["file-detail", fileId] as const,
  collectionFiles: (params: CollectionFilesQueryInput) => ["collection-files", params] as const,
  filesList: (params: FilesListQueryInput) => ["files-list", params] as const,
  mediaLibrary: (params: MediaListQueryInput) => ["media-library", params] as const,
  recent: (params: RecentListQueryInput) => ["recent", params] as const,
  recentTagged: (params: RecentListQueryInput) => ["recent-tagged", params] as const,
  recentColorTagged: (params: RecentListQueryInput) => ["recent-color-tagged", params] as const,
  search: (params: SearchQueryInput) => ["search", params] as const,
  tagFiles: (params: TagFilesQueryInput) => ["tag-files", params] as const,
};
