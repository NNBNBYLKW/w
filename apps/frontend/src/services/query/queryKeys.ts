import type { BookListQueryInput } from "../../entities/book/types";
import type { FilesListQueryInput, SearchQueryInput } from "../../entities/file/types";
import type { GamesListQueryInput } from "../../entities/game/types";
import type { LibraryObjectListQueryInput, OrganizeCandidateListQueryInput, OrganizePlanListQueryInput } from "../../entities/library/types";
import type { MediaListQueryInput } from "../../entities/media/types";
import type { RecentListQueryInput } from "../../entities/recent/types";
import type { TagFilesQueryInput } from "../../entities/tag/types";
import type { CollectionFilesQueryInput } from "../../entities/collection/types";

import type { SoftwareListQueryInput } from "../../entities/software/types";


export const queryKeys = {
  systemStatus: ["system-status"] as const,
  sources: ["sources"] as const,
  tags: ["tags"] as const,
  tools: ["tools"] as const,
  toolRuns: (params: { page: number; page_size: number }) => ["tool-runs", params] as const,
  toolRun: (runId: number) => ["tool-run", runId] as const,
  libraryRoots: ["library-roots"] as const,
  libraryOverview: ["library-overview"] as const,
  libraryObjects: (params: LibraryObjectListQueryInput) => ["library-objects", params] as const,
  libraryObject: (objectId: number) => ["library-object", objectId] as const,
  libraryObjectMembers: (params: { objectId: number; page: number; page_size: number; role?: string }) =>
    ["library-object-members", params] as const,
  organizeStats: ["organize-stats"] as const,
  organizeCandidates: (params: OrganizeCandidateListQueryInput) => ["organize-candidates", params] as const,
  organizeCandidate: (candidateId: number) => ["organize-candidate", candidateId] as const,
  organizeSuggestions: (candidateId: number) => ["organize-suggestions", candidateId] as const,
  organizePlans: (params: OrganizePlanListQueryInput) => ["organize-plans", params] as const,
  organizePlan: (planId: number) => ["organize-plan", planId] as const,
  organizePlanLogs: (planId: number) => ["organize-plan-logs", planId] as const,
  collections: ["collections"] as const,
  booksList: (params: BookListQueryInput) => ["books-list", params] as const,
  gamesList: (params: GamesListQueryInput) => ["games-list", params] as const,
  softwareList: (params: SoftwareListQueryInput) => ["software-list", params] as const,
  fileDetail: (fileId: number) => ["file-detail", fileId] as const,
  collectionFiles: (params: CollectionFilesQueryInput) => ["collection-files", params] as const,
  collectionStats: (collectionId: number) => ["collection-stats", collectionId] as const,
  filesList: (params: FilesListQueryInput) => ["files-list", params] as const,
  mediaLibrary: (params: MediaListQueryInput) => ["media-library", params] as const,
  recent: (params: RecentListQueryInput) => ["recent", params] as const,
  recentTagged: (params: RecentListQueryInput) => ["recent-tagged", params] as const,
  recentColorTagged: (params: RecentListQueryInput) => ["recent-color-tagged", params] as const,
  recentAll: (params: RecentListQueryInput) => ["recent-all", params] as const,
  search: (params: SearchQueryInput) => ["search", params] as const,
  tagFiles: (params: TagFilesQueryInput) => ["tag-files", params] as const,
};
