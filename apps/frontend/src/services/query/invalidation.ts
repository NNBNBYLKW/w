import type { QueryClient } from "@tanstack/react-query";
import { queryKeys } from "./queryKeys";

/** All surfaces that display file organization data.
 *  Used by file-metadata mutations (tags, color, placement, rating, favorite). */
export function invalidateFileOrganizationSurfaces(queryClient: QueryClient) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: queryKeys.tags }),
    queryClient.invalidateQueries({ queryKey: ["tag-files"] }),
    queryClient.invalidateQueries({ queryKey: ["media-library"] }),
    queryClient.invalidateQueries({ queryKey: ["books-list"] }),
    queryClient.invalidateQueries({ queryKey: ["games-list"] }),
    queryClient.invalidateQueries({ queryKey: ["software-list"] }),
    queryClient.invalidateQueries({ queryKey: ["recent"] }),
    queryClient.invalidateQueries({ queryKey: ["recent-tagged"] }),
    queryClient.invalidateQueries({ queryKey: ["recent-color-tagged"] }),
    queryClient.invalidateQueries({ queryKey: ["recent-all"] }),
    queryClient.invalidateQueries({ queryKey: ["search"] }),
    queryClient.invalidateQueries({ queryKey: ["files-list"] }),
    queryClient.invalidateQueries({ queryKey: queryKeys.collections }),
    queryClient.invalidateQueries({ queryKey: ["collection-files"] }),
  ]);
}

/** File detail query for a single file. */
export function invalidateDetailsPanelFileDetail(queryClient: QueryClient, fileId: number) {
  return queryClient.invalidateQueries({ queryKey: queryKeys.fileDetail(fileId) });
}

/** Organize plan detail + optional logs, stats, and plan list. */
export function invalidateLibraryOrganizeSurfaces(
  queryClient: QueryClient,
  planId: number,
  opts?: { logs?: boolean; stats?: boolean; plansList?: boolean },
) {
  const { logs = false, stats = false, plansList = true } = opts ?? {};
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: queryKeys.organizePlan(planId) }),
    ...(logs ? [queryClient.invalidateQueries({ queryKey: queryKeys.organizePlanLogs(planId) })] : []),
    ...(stats ? [queryClient.invalidateQueries({ queryKey: queryKeys.organizeStats })] : []),
    ...(plansList ? [queryClient.invalidateQueries({ queryKey: ["organize-plans"] })] : []),
  ]);
}

/** Organize candidate list + optional stats and plan list. */
export function invalidateLibraryCandidateSurfaces(
  queryClient: QueryClient,
  opts?: { stats?: boolean; plansList?: boolean },
) {
  const { stats = false, plansList = false } = opts ?? {};
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["organize-candidates"] }),
    ...(stats ? [queryClient.invalidateQueries({ queryKey: queryKeys.organizeStats })] : []),
    ...(plansList ? [queryClient.invalidateQueries({ queryKey: ["organize-plans"] })] : []),
  ]);
}

/** Organize suggestions for a single candidate. */
export function invalidateLibrarySuggestionSurfaces(queryClient: QueryClient, candidateId: number) {
  return queryClient.invalidateQueries({ queryKey: queryKeys.organizeSuggestions(candidateId) });
}

/** Library roots list. */
export function invalidateLibraryRootSurfaces(queryClient: QueryClient) {
  return queryClient.invalidateQueries({ queryKey: queryKeys.libraryRoots });
}

/** Library overview + objects list. */
export function invalidateLibraryObjectSurfaces(queryClient: QueryClient) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: queryKeys.libraryOverview }),
    queryClient.invalidateQueries({ queryKey: ["library-objects"] }),
  ]);
}

/** Collections list + collection files list. */
export function invalidateCollectionSurfaces(queryClient: QueryClient) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: queryKeys.collections }),
    queryClient.invalidateQueries({ queryKey: ["collection-files"] }),
  ]);
}

/** Tags list + tag-files list. */
export function invalidateTagSurfaces(queryClient: QueryClient) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: queryKeys.tags }),
    queryClient.invalidateQueries({ queryKey: ["tag-files"] }),
  ]);
}

/** Browse-specific surfaces (media, books, games, software, recent, search, files). */
export function invalidateBrowseSurfaces(queryClient: QueryClient) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["media-library"] }),
    queryClient.invalidateQueries({ queryKey: ["books-list"] }),
    queryClient.invalidateQueries({ queryKey: ["games-list"] }),
    queryClient.invalidateQueries({ queryKey: ["software-list"] }),
    queryClient.invalidateQueries({ queryKey: ["recent"] }),
    queryClient.invalidateQueries({ queryKey: ["search"] }),
    queryClient.invalidateQueries({ queryKey: ["files-list"] }),
  ]);
}

/** Source management: sources list + system status. */
export function invalidateSourceSurfaces(queryClient: QueryClient) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: queryKeys.sources }),
    queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus }),
  ]);
}

/** Tool run history (first page). */
export function invalidateToolRunSurfaces(queryClient: QueryClient) {
  return queryClient.invalidateQueries({ queryKey: queryKeys.toolRuns({ page: 1, page_size: 10 }) });
}
