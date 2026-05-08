import { NavLink, Outlet } from "react-router-dom";
import UserMenu from "./UserMenu";
import { useAuth } from "../contexts/AuthContext";

const NAV = [
  { to: "/",            icon: "📊", label: "Dashboard" },
  { to: "/leaderboard", icon: "🏆", label: "Leaderboard" },
  { to: "/analytics",   icon: "📈", label: "Analytics" },
  { to: "/users",       icon: "👥", label: "Users" },
  { to: "/status",      icon: "🟢", label: "System Status" },
];

export default function Layout() {
  const { authenticated } = useAuth();

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>DSA Tracker</h1>
          <p>Accountability Platform</p>
        </div>

        <nav className="sidebar-nav">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              <span className="nav-icon">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}

          {/* Personal dashboard link — only visible when authenticated */}
          {authenticated && (
            <NavLink
              to="/me"
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              <span className="nav-icon">🔐</span>
              My Dashboard
            </NavLink>
          )}
        </nav>

        {/* Auth section in sidebar footer */}
        <UserMenu />

        <div className="sidebar-footer">
          <div className="footer-text">
            DSA Accountability Bot v1.0<br />
            Discord + API + Dashboard
          </div>
          <div className="creator-signature">
            crafted by @harinyathani
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
