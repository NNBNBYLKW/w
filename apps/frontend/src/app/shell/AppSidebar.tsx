import { NavLink } from "react-router-dom";

import { t } from "../../shared/text";
import { SidebarIcon, type NavigationIconName } from "../../shared/ui/icons";
import { useUIStore } from "../providers/uiStore";

const navItems: Array<{ to: string; labelKey: Parameters<typeof t>[0]; icon: NavigationIconName }> = [
  { to: "/home", labelKey: "navigation.items.home", icon: "home" },
  { to: "/search", labelKey: "navigation.items.search", icon: "search" },
  { to: "/files", labelKey: "navigation.items.files", icon: "files" },
  { to: "/books", labelKey: "navigation.items.books", icon: "books" },
  { to: "/software", labelKey: "navigation.items.software", icon: "software" },
  { to: "/library/media", labelKey: "navigation.items.media", icon: "media" },
  { to: "/library/games", labelKey: "navigation.items.games", icon: "games" },
  { to: "/recent", labelKey: "navigation.items.recent", icon: "recent" },
  { to: "/tags", labelKey: "navigation.items.tags", icon: "tags" },
  { to: "/collections", labelKey: "navigation.items.collections", icon: "collections" },
  { to: "/settings", labelKey: "navigation.items.settings", icon: "settings" },
];

export function AppSidebar() {
  const isSidebarCollapsed = useUIStore((state) => state.isSidebarCollapsed);
  const toggleSidebarCollapsed = useUIStore((state) => state.toggleSidebarCollapsed);

  return (
    <aside className={`app-sidebar${isSidebarCollapsed ? " app-sidebar--collapsed" : ""}`}>
      <div className="app-sidebar__brand">
        <div className="app-sidebar__brand-copy">
          <span className="app-sidebar__eyebrow">{t("shell.sidebar.eyebrow")}</span>
          <h1>{t("shell.sidebar.title")}</h1>
        </div>
        <button
          className="ghost-button app-sidebar__toggle"
          type="button"
          onClick={toggleSidebarCollapsed}
          aria-label={isSidebarCollapsed ? t("shell.sidebar.expand") : t("shell.sidebar.collapse")}
          title={isSidebarCollapsed ? t("shell.sidebar.expand") : t("shell.sidebar.collapse")}
        >
          <span className="app-sidebar__toggle-icon" aria-hidden="true">
            <SidebarIcon name={isSidebarCollapsed ? "sidebar2" : "sidebar1"} />
          </span>
        </button>
      </div>
      <nav className="app-sidebar__nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            aria-label={t(item.labelKey)}
            title={t(item.labelKey)}
            className={({ isActive }) =>
              isActive ? "app-sidebar__link app-sidebar__link--active" : "app-sidebar__link"
            }
          >
            <span className="app-sidebar__link-icon">
              <SidebarIcon name={item.icon} />
            </span>
            <span className="app-sidebar__link-label">{t(item.labelKey)}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
