import { Suspense, lazy } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../shell/AppShell";
import { getSources } from "../../services/api/sourcesApi";
import { queryKeys } from "../../services/query/queryKeys";

const HomePage = lazy(() => import("../../pages/home/HomePage").then(m => ({ default: m.HomePage })));
const OnboardingPage = lazy(() => import("../../pages/onboarding/OnboardingPage").then(m => ({ default: m.OnboardingPage })));
const ToolsPage = lazy(() => import("../../pages/tools/ToolsPage").then(m => ({ default: m.ToolsPage })));
const RecentImportsPage = lazy(() => import("../../pages/recent/RecentImportsPage").then(m => ({ default: m.RecentImportsPage })));
const TagsPage = lazy(() => import("../../pages/tags/TagsPage").then(m => ({ default: m.TagsPage })));
const CollectionsPage = lazy(() => import("../../pages/collections/CollectionsPage").then(m => ({ default: m.CollectionsPage })));
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
        <Route path="/home" element={<LazyPage><HomePage /></LazyPage>} />
        <Route path="/onboarding" element={<LazyPage><OnboardingPage /></LazyPage>} />
        <Route path="/search" element={<LazyPage><SearchPage /></LazyPage>} />
        <Route path="/library" element={<LazyPage><LibraryPage /></LazyPage>} />
        <Route path="/browse-v2" element={<LazyPage><BrowseV2Page /></LazyPage>} />
        <Route path="/tools" element={<LazyPage><ToolsPage /></LazyPage>} />
        <Route path="/recent" element={<LazyPage><RecentImportsPage /></LazyPage>} />
        <Route path="/tags" element={<LazyPage><TagsPage /></LazyPage>} />
        <Route path="/collections" element={<LazyPage><CollectionsPage /></LazyPage>} />
        <Route path="/settings" element={<LazyPage><SettingsPage /></LazyPage>} />
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Route>
    </Routes>
  );
}
