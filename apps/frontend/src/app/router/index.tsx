import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../shell/AppShell";
import { BooksPage } from "../../pages/books/BooksPage";
import { CollectionsPage } from "../../pages/collections/CollectionsPage";
import { FilesPage } from "../../pages/files/FilesPage";
import { GamesPage } from "../../pages/games/GamesPage";
import { HomePage } from "../../pages/home/HomePage";
import { MediaLibraryPage } from "../../pages/media-library/MediaLibraryPage";
import { OnboardingPage } from "../../pages/onboarding/OnboardingPage";
import { RecentImportsPage } from "../../pages/recent/RecentImportsPage";
import { SearchPage } from "../../pages/search/SearchPage";
import { SettingsPage } from "../../pages/settings/SettingsPage";
import { SoftwarePage } from "../../pages/software/SoftwarePage";
import { TagsPage } from "../../pages/tags/TagsPage";
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
        <Route path="/files" element={<FilesPage />} />
        <Route path="/books" element={<BooksPage />} />
        <Route path="/software" element={<SoftwarePage />} />
        <Route path="/library/games" element={<GamesPage />} />
        <Route path="/library/media" element={<MediaLibraryPage />} />
        <Route path="/recent" element={<RecentImportsPage />} />
        <Route path="/tags" element={<TagsPage />} />
        <Route path="/collections" element={<CollectionsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
