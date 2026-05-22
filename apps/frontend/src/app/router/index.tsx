import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../shell/AppShell";
import { BrowseV2Page } from "../../pages/browse-v2/BrowseV2Page";
import { BooksPage } from "../../pages/books/BooksPage";
import { CollectionsPage } from "../../pages/collections/CollectionsPage";
import { GamesPage } from "../../pages/games/GamesPage";
import { HomePage } from "../../pages/home/HomePage";
import { LibraryPage } from "../../pages/library/LibraryPage";
import { MediaLibraryPage } from "../../pages/media-library/MediaLibraryPage";
import { OnboardingPage } from "../../pages/onboarding/OnboardingPage";
import { RecentImportsPage } from "../../pages/recent/RecentImportsPage";
import { SearchPage } from "../../pages/search/SearchPage";
import { SettingsPage } from "../../pages/settings/SettingsPage";
import { SoftwarePage } from "../../pages/software/SoftwarePage";
import { TagsPage } from "../../pages/tags/TagsPage";
import { ToolsPage } from "../../pages/tools/ToolsPage";
import { getSources } from "../../services/api/sourcesApi";
import { queryKeys } from "../../services/query/queryKeys";


function StartupRedirect() {
  const sourcesQuery = useQuery({
    queryKey: queryKeys.sources,
    queryFn: getSources,
  });

  if (sourcesQuery.isLoading) {
    return null;
  }

  const hasSavedSources = (sourcesQuery.data?.length ?? 0) > 0;

  return <Navigate to={hasSavedSources ? "/home" : "/onboarding"} replace />;
}


export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<StartupRedirect />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/files" element={<Navigate to="/library?tab=path" replace />} />
        <Route path="/books" element={<Navigate to="/browse-v2?domain=documents" replace />} />
        <Route path="/software" element={<Navigate to="/browse-v2?domain=apps&category=software" replace />} />
        <Route path="/library/games" element={<Navigate to="/browse-v2?domain=apps&category=game" replace />} />
        <Route path="/browse-v2" element={<BrowseV2Page />} />
        <Route path="/library/media" element={<Navigate to="/browse-v2?domain=media" replace />} />
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/recent" element={<RecentImportsPage />} />
        <Route path="/tags" element={<TagsPage />} />
        <Route path="/collections" element={<CollectionsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
