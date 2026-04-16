import { Route, Routes } from "react-router-dom";

import { AppShell } from "../shell/AppShell";
import { FilesPage } from "../../pages/files/FilesPage";
import { HomePage } from "../../pages/home/HomePage";
import { MediaLibraryPage } from "../../pages/media-library/MediaLibraryPage";
import { OnboardingPage } from "../../pages/onboarding/OnboardingPage";
import { RecentImportsPage } from "../../pages/recent/RecentImportsPage";
import { SearchPage } from "../../pages/search/SearchPage";
import { SettingsPage } from "../../pages/settings/SettingsPage";
import { TagsPage } from "../../pages/tags/TagsPage";


export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/files" element={<FilesPage />} />
        <Route path="/library/media" element={<MediaLibraryPage />} />
        <Route path="/recent" element={<RecentImportsPage />} />
        <Route path="/tags" element={<TagsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
