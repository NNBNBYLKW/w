import { NavLink } from "react-router-dom";


const navItems = [
  { to: "/onboarding", label: "Onboarding" },
  { to: "/search", label: "Search" },
  { to: "/files", label: "Files" },
  { to: "/library/media", label: "Media" },
  { to: "/recent", label: "Recent" },
  { to: "/tags", label: "Tags" },
  { to: "/settings", label: "Settings" },
];


export function AppSidebar() {
  return (
    <aside className="app-sidebar">
      <div className="app-sidebar__brand">
        <span className="app-sidebar__eyebrow">Phase 0</span>
        <h1>Workbench</h1>
      </div>
      <nav className="app-sidebar__nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              isActive ? "app-sidebar__link app-sidebar__link--active" : "app-sidebar__link"
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
