import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { t, useLocale } from "../../shared/text";
import { SidebarIcon, type NavigationIconName } from "../../shared/ui/icons";
import { useUIStore } from "../providers/uiStore";

type NavSubItem = {
  to: string;
  labelKey: Parameters<typeof t>[0];
};

type NavItem = {
  to?: string;
  labelKey: Parameters<typeof t>[0];
  icon: NavigationIconName;
  children?: NavSubItem[];
  defaultExpanded?: boolean;
};

const navGroups: Array<{
  labelKey: Parameters<typeof t>[0];
  items: NavItem[];
}> = [
  {
    labelKey: "shell.sidebar.groups.main",
    items: [
      { to: "/home", labelKey: "navigation.items.home", icon: "home" },
    ],
  },
  {
    labelKey: "shell.sidebar.groups.fileLibrary",
    items: [
      { to: "/browse-v2", labelKey: "navigation.items.browseAll", icon: "media" },
      {
        labelKey: "navigation.items.browseMedia",
        icon: "media",
        defaultExpanded: false,
        children: [
          { to: "/browse-v2?domain=media", labelKey: "features.browseV2.categories.all" },
          { to: "/browse-v2?domain=media&category=movie", labelKey: "features.browseV2.categories.movie" },
          { to: "/browse-v2?domain=media&category=series_anime", labelKey: "features.browseV2.categories.series_anime" },
          { to: "/browse-v2?domain=media&category=course", labelKey: "features.browseV2.categories.course" },
          { to: "/browse-v2?domain=media&category=video_collection", labelKey: "features.browseV2.categories.video_collection" },
          { to: "/browse-v2?domain=media&category=video_clip", labelKey: "features.browseV2.categories.video_clip" },
          { to: "/browse-v2?domain=media&category=image_album", labelKey: "features.browseV2.categories.image_album" },
          { to: "/browse-v2?domain=media&category=comic", labelKey: "features.browseV2.categories.comic" },
          { to: "/browse-v2?domain=media&category=audio", labelKey: "features.browseV2.categories.audio" },
        ],
      },
      { to: "/browse-v2?domain=documents", labelKey: "navigation.items.browseDocuments", icon: "books" },
      { to: "/browse-v2?domain=apps", labelKey: "navigation.items.browseApps", icon: "software" },
      { to: "/browse-v2?domain=assets", labelKey: "navigation.items.browseAssets", icon: "collections" },
    ],
  },
  {
    labelKey: "shell.sidebar.groups.manage",
    items: [
      { to: "/library?tab=overview", labelKey: "navigation.items.fileLibOverview", icon: "home" },
      { to: "/library?tab=sources", labelKey: "navigation.items.scanFolders", icon: "search" },
      { to: "/library?tab=roots", labelKey: "navigation.items.managedRoots", icon: "settings" },
      { to: "/library?tab=inbox", labelKey: "navigation.items.inbox", icon: "recent" },
      { to: "/library?tab=plans", labelKey: "navigation.items.plans", icon: "collections" },
    ],
  },
  {
    labelKey: "shell.sidebar.groups.refind",
    items: [
      { to: "/search", labelKey: "navigation.items.search", icon: "search" },
      { to: "/recent", labelKey: "navigation.items.recent", icon: "recent" },
      { to: "/tags", labelKey: "navigation.items.tags", icon: "tags" },
      { to: "/collections", labelKey: "navigation.items.collections", icon: "collections" },
    ],
  },
  {
    labelKey: "shell.sidebar.groups.system",
    items: [
      { to: "/tools", labelKey: "navigation.items.tools", icon: "tools" },
      { to: "/settings", labelKey: "navigation.items.settings", icon: "settings" },
    ],
  },
];

type RouterLocation = ReturnType<typeof useLocation>;

function splitNavTarget(to: string) {
  const [pathname, search = ""] = to.split("?");
  return { pathname, params: new URLSearchParams(search) };
}

function isNavTargetActive(to: string, location: RouterLocation): boolean {
  const target = splitNavTarget(to);

  if (location.pathname !== target.pathname) {
    return false;
  }

  const currentParams = new URLSearchParams(location.search);

  if (target.pathname === "/library") {
    const targetTab = target.params.get("tab") ?? "overview";
    const currentTab = currentParams.get("tab") ?? "overview";
    return targetTab === currentTab;
  }

  if (target.pathname === "/browse-v2") {
    const targetDomain = target.params.get("domain");
    const targetCategory = target.params.get("category") ?? "";
    const currentDomain = currentParams.get("domain");
    const currentCategory = currentParams.get("category") ?? "";

    if (!targetDomain) {
      return !currentDomain && !currentCategory;
    }

    return targetDomain === currentDomain && targetCategory === currentCategory;
  }

  return true;
}

function NavItemWithChildren({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  const location = useLocation();
  const hasChildren = item.children && item.children.length > 0;

  const activeChildUrl = hasChildren
    ? item.children!.find((child) => isNavTargetActive(child.to, location))
    : null;
  const isChildActive = activeChildUrl != null;

  const [expanded, setExpanded] = useState(
    item.defaultExpanded ?? false
  );
  const isOpen = expanded || isChildActive;

  if (!hasChildren) {
    const isActive = isNavTargetActive(item.to!, location);

    return (
      <Link
        to={item.to!}
        aria-label={t(item.labelKey)}
        aria-current={isActive ? "page" : undefined}
        title={collapsed ? t(item.labelKey) : undefined}
        className={isActive ? "app-sidebar__link app-sidebar__link--active" : "app-sidebar__link"}
      >
        <span className="app-sidebar__link-icon" aria-hidden="true">
          <SidebarIcon name={item.icon} />
        </span>
        <span className="app-sidebar__link-label">{t(item.labelKey)}</span>
      </Link>
    );
  }

  return (
    <div className="app-sidebar__expandable">
      <button
        className={`app-sidebar__link app-sidebar__link--expandable${
          isChildActive ? " app-sidebar__link--active-parent" : ""
        }`}
        type="button"
        aria-expanded={isOpen}
        onClick={() => setExpanded(!isOpen)}
        title={collapsed ? t(item.labelKey) : undefined}
      >
        <span className="app-sidebar__link-icon" aria-hidden="true">
          <SidebarIcon name={item.icon} />
        </span>
        <span className="app-sidebar__link-label">{t(item.labelKey)}</span>
        <span
          className={`app-sidebar__chevron${
            isOpen ? " app-sidebar__chevron--open" : ""
          }`}
          aria-hidden="true"
        >
          ▸
        </span>
      </button>
      {isOpen && !collapsed && (
        <div className="app-sidebar__children">
          {item.children!.map((child) => {
            const isActive = isNavTargetActive(child.to, location);

            return (
              <Link
                key={child.to}
                to={child.to}
                aria-current={isActive ? "page" : undefined}
                className={
                  isActive
                    ? "app-sidebar__link app-sidebar__link--child app-sidebar__link--active"
                    : "app-sidebar__link app-sidebar__link--child"
                }
              >
                <span className="app-sidebar__link-label">
                  {t(child.labelKey)}
                </span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AppSidebar() {
  useLocale();
  const isSidebarCollapsed = useUIStore((state) => state.isSidebarCollapsed);
  const toggleSidebarCollapsed = useUIStore(
    (state) => state.toggleSidebarCollapsed
  );

  return (
    <aside
      className={`app-sidebar${
        isSidebarCollapsed ? " app-sidebar--collapsed" : ""
      }`}
    >
      <div className="app-sidebar__brand">
        <div className="app-sidebar__brand-mark" aria-hidden="true">
          W
        </div>
        <div className="app-sidebar__brand-copy">
          <span className="app-sidebar__eyebrow">
            {t("shell.sidebar.eyebrow")}
          </span>
          <h1>{t("shell.sidebar.title")}</h1>
        </div>
        <button
          className="ghost-button app-sidebar__toggle"
          type="button"
          onClick={toggleSidebarCollapsed}
          aria-label={
            isSidebarCollapsed
              ? t("shell.sidebar.expand")
              : t("shell.sidebar.collapse")
          }
          title={
            isSidebarCollapsed
              ? t("shell.sidebar.expand")
              : t("shell.sidebar.collapse")
          }
        >
          <span className="app-sidebar__toggle-icon" aria-hidden="true">
            <SidebarIcon
              name={isSidebarCollapsed ? "sidebar2" : "sidebar1"}
            />
          </span>
        </button>
      </div>
      <nav
        className="app-sidebar__nav"
        aria-label={t("shell.sidebar.navigationLabel")}
      >
        {navGroups.map((group) => (
          <div className="app-sidebar__nav-group" key={group.labelKey}>
            <span className="app-sidebar__nav-heading">
              {t(group.labelKey)}
            </span>
            {group.items.map((item) => (
              <NavItemWithChildren
                key={item.to ?? item.labelKey}
                item={item}
                collapsed={isSidebarCollapsed}
              />
            ))}
          </div>
        ))}
      </nav>
      <div
        className="app-sidebar__footer"
        aria-hidden={isSidebarCollapsed ? "true" : "false"}
      >
        <span className="app-sidebar__footer-kicker">
          {t("shell.sidebar.footerKicker")}
        </span>
        <span className="app-sidebar__footer-copy">
          {t("shell.sidebar.footerCopy")}
        </span>
      </div>
    </aside>
  );
}
