import { Suspense, lazy } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../shell/AppShell";
import { HomePage } from "../../pages/home/HomePage";
import { OnboardingPage } from "../../pages/onboarding/OnboardingPage";
import { RecentImportsPage } from "../../pages/recent/RecentImportsPage";
import { TagsPage } from "../../pages/tags/TagsPage";
import { CollectionsPage } from "../../pages/collections/CollectionsPage";
import { ToolsPage } from "../../pages/tools/ToolsPage";
import { getSources } from "../../services/api/sourcesApi";
import { queryKeys } from "../../services/query/queryKeys";

const BrowseV2Page = lazy(() => import("../../pages/browse-v2/BrowseV2Page"));
const LibraryPage = lazy(() => import("../../pages/library/LibraryPage"));
const SearchPage = lazy(() => import("../../pages/search/SearchPage"));
const SettingsPage = lazy(() => import("../../pages/settings/SettingsPage"));

function PageLoader() {
  return <div className="page-loader" aria-busy="true">Loading...</div>;
}

function LazyPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<PageLoader />}>{children}</Suspense>;
}


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
        <Route path="/search" element={<LazyPage><SearchPage /></LazyPage>} />
        <Route path="/library" element={<LazyPage><LibraryPage /></LazyPage>} />
        <Route path="/browse-v2" element={<LazyPage><BrowseV2Page /></LazyPage>} />
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/recent" element={<RecentImportsPage />} />
        <Route path="/tags" element={<TagsPage />} />
        <Route path="/collections" element={<CollectionsPage />} />
        <Route path="/settings" element={<LazyPage><SettingsPage /></LazyPage>} />
      </Route>
    </Routes>
  );
}
