import { motion } from "motion/react";
import { Outlet, useLocation, useNavigate, Link } from "react-router-dom";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useAuth } from "../contexts/AuthContext";
import { quickSpring } from "../styles/springs";
import ErrorBoundary from "./ErrorBoundary";
import LiquidCapsule, { type CapsuleItem } from "./LiquidCapsule";
import ThemeSwitcher from "./ThemeSwitcher";
import UserMenu from "./UserMenu";
import s from "./Layout.module.css";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  authOnly?: boolean;
}

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: "📊" },
  { to: "/leaderboard", label: "Leaderboard", icon: "🏆" },
  { to: "/analytics", label: "Analytics", icon: "📈" },
  { to: "/me", label: "My Dashboard", icon: "🔐", authOnly: true },
  { to: "/revision", label: "Revision Bank", icon: "🧠", authOnly: true },
];

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className={s.pageHeader}>
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {actions && <div className={s.actions}>{actions}</div>}
    </header>
  );
}
/** True at ≤900px — matches the sidebar breakpoint in Layout.module.css.
 *  Only one UserMenu instance is mounted at a time thanks to this hook. */
function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia("(max-width: 900px)").matches
  );
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 900px)");
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return isMobile;
}


export default function Layout() {
  const { authenticated } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const isMobile = useIsMobile();

  const items = useMemo(
    () =>
      NAV.filter((n) => !n.authOnly || authenticated).map<CapsuleItem<string>>((n) => ({
        key: n.to,
        label: n.label,
        icon: <span>{n.icon}</span>,
      })),
    [authenticated]
  );

  // Resolve the active nav key from the current path.
  // Profile (/u/*, /users/*) and admin (/admin) don't have dedicated nav slots,
  // so we fall back to "/" (Dashboard) to keep the pill visible rather than
  // letting it vanish and making the sidebar feel broken.
  const activeKey = useMemo(() => {
    const match = NAV.find((n) => (n.to === "/" ? pathname === "/" : pathname.startsWith(n.to)));
    if (match) return match.to;
    if (pathname.startsWith("/u/") || pathname.startsWith("/users/") || pathname === "/admin") {
      return "/";
    }
    return "";
  }, [pathname]);

  return (
    <div className={s.shell}>
      {/* Skip-to-content: first focusable on the page — WCAG 2.4.1 */}
      <a href="#main" className={s.skipLink}>Skip to main content</a>
      <aside className={s.sidebar}>
        <Link to="/" className={`${s.brand} ${s.brandLink}`}>
          <img src="/Dsalogo.png" alt="DSA Tracker" width="52" height="52" />
          <div>
            <h1>DSA Tracker</h1>
            <p>Accountability</p>
          </div>
        </Link>

        <nav className={s.nav}>
          <div className={s.navScroll}>
            <LiquidCapsule
              items={items}
              value={activeKey}
              onChange={(to) => navigate(to)}
              variant="nav"
              orientation="vertical"
              aria-label="Primary"
            />
          </div>
        </nav>

        <div className={s.theme}>
          <ThemeSwitcher />
        </div>

        {/* Desktop-only auth — not rendered on mobile so only one UserMenu
            instance exists in the React tree at a time (see useIsMobile). */}
        {!isMobile && (
          <div className={s.auth}>
            <UserMenu />
          </div>
        )}

        <div className={s.footer}>
          <div className={s.footerText}>
            DSA Accountability Bot V3.0
            <br />
            Discord + API + Dashboard
          </div>
          <div className={s.signature}>crafted by @harinyathani</div>
        </div>
      </aside>

      <main id="main" className={s.main}>
        <div className={s.page}>
          <ErrorBoundary>
            <RouteTransitions />
          </ErrorBoundary>
        </div>
      </main>

      {/* Mobile floating glass nav */}
      <div className={s.bottomNav}>
        <div className={s.inner}>
          <LiquidCapsule
            items={items}
            value={activeKey}
            onChange={(to) => navigate(to)}
            variant="nav"
            aria-label="Primary (mobile)"
          />
        </div>
      </div>

      {/* Mobile auth strip — only mounted when sidebar is hidden (≤900px).
          Combined with the !isMobile guard above, exactly one UserMenu
          instance is in the React tree at any given time. */}
      {isMobile && (
        <div className={s.mobileAuth}>
          <ThemeSwitcher compact />
          <UserMenu />
        </div>
      )}
    </div>
  );
}

/** Route transition wrapper — fade + 8% slide-in on mount.
 *  Mirrors all_problems_view.dart:118-144 (200ms easeOutCubic). Exit animation
 *  is intentionally omitted: a keyed <Outlet> cannot persist old content during
 *  exit, so exit flashes. Mount-in animation is robust and still premium. */
function RouteTransitions() {
  const { pathname } = useLocation();
  return (
    <motion.div
      key={pathname}
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ ...quickSpring, duration: 0.2 }}
    >
      <Outlet />
    </motion.div>
  );
}