import { NavLink } from "react-router-dom";

import { SidebarIcon, type NavigationIconName } from "../../shared/ui/icons";
import { useUIStore } from "../providers/uiStore";

const navItems: Array<{ to: string; label: string; icon: NavigationIconName }> = [
  { to: "/onboarding", label: "Onboarding", icon: "onboarding" },
  { to: "/search", label: "Search", icon: "search" },
  { to: "/files", label: "Files", icon: "files" },
  { to: "/books", label: "Books", icon: "books" },
  { to: "/software", label: "Software", icon: "software" },
  { to: "/library/media", label: "Media", icon: "media" },
  { to: "/library/games", label: "Games", icon: "games" },
  { to: "/recent", label: "Recent", icon: "recent" },
  { to: "/tags", label: "Tags", icon: "tags" },
  { to: "/collections", label: "Collections", icon: "collections" },
  { to: "/settings", label: "Settings", icon: "settings" },
];

export function AppSidebar() {
  const isSidebarCollapsed = useUIStore((state) => state.isSidebarCollapsed);
  const toggleSidebarCollapsed = useUIStore((state) => state.toggleSidebarCollapsed);

  return (
    <aside className={`app-sidebar${isSidebarCollapsed ? " app-sidebar--collapsed" : ""}`}>
      <div className="app-sidebar__brand">
        <div className="app-sidebar__brand-copy">
          <span className="app-sidebar__eyebrow">Local-first asset workbench</span>
          <h1>Asset Workbench</h1>
        </div>
        <button
          className="ghost-button app-sidebar__toggle"
          type="button"
          onClick={toggleSidebarCollapsed}
          aria-label={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
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
            aria-label={item.label}
            title={item.label}
            className={({ isActive }) =>
              isActive ? "app-sidebar__link app-sidebar__link--active" : "app-sidebar__link"
            }
          >
            <span className="app-sidebar__link-icon">
              <SidebarIcon name={item.icon} />
            </span>
            <span className="app-sidebar__link-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
