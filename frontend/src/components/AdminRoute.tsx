/* ──────────────────────────────────────────────────────────────────────────
   AdminRoute — React Router wrapper that blocks non-admin navigation.

   • While auth is loading:   renders a loading spinner (no redirect flash)
   • Not authenticated:       renders a hidden 403 status panel
   • Authenticated non-admin: renders a hard 403 status panel
   • Verified admin:          renders the child <Outlet />

   Security note: we never redirect to login — a 403 wall reveals nothing
   about whether the resource exists to non-admin users.
   ────────────────────────────────────────────────────────────────────────── */

import { Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function AdminRoute() {
  const { authenticated, loading, isAdmin } = useAuth();

  // Wait for auth state to resolve — prevents redirect flash
  if (loading) {
    return (
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "60vh",
      }}>
        <div className="auth-loading">
          <div className="auth-loading-dot" />
          <div className="auth-loading-dot" />
          <div className="auth-loading-dot" />
        </div>
      </div>
    );
  }

  // Not authenticated or not admin → hard 403 wall (no redirect, no URL hint)
  if (!authenticated || !isAdmin) {
    return (
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        textAlign: "center",
        gap: "12px",
      }}>
        <div style={{ fontSize: "4rem", lineHeight: 1 }}>🔒</div>
        <h2 style={{
          fontSize: "1.5rem",
          fontWeight: 700,
          background: "linear-gradient(135deg, #f43f5e, #e11d48)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}>
          403 — Access Denied
        </h2>
        <p style={{ color: "#94A3B8", fontSize: "0.9rem", maxWidth: "360px" }}>
          This area is restricted to the platform administrator.
          If you believe this is an error, contact the bot owner.
        </p>
      </div>
    );
  }

  // Verified admin — render the protected content
  return <Outlet />;
}
