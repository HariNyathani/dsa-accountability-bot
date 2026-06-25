import { motion } from "motion/react";
import { Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { enterSpring } from "../styles/springs";

/**
 * AdminRoute — guards the admin area.
 * Loading → pulsing dots; not-admin → glass 403 wall; admin → <Outlet/>.
 * No redirect (security: reveals nothing about resource existence).
 */
export default function AdminRoute() {
  const { authenticated, loading, isAdmin } = useAuth();

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)" }}
              animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (!authenticated || !isAdmin) {
    return (
      <motion.div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "60vh",
          textAlign: "center",
          gap: 14,
        }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={enterSpring}
      >
        <div style={{ fontSize: "4rem", lineHeight: 1 }}>🔒</div>
        <h2
          style={{
            fontSize: "1.5rem",
            fontWeight: 800,
            background: "linear-gradient(135deg, var(--diff-hard), color-mix(in srgb, var(--diff-hard) 55%, black))",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          403 — Access Denied
        </h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.92rem", maxWidth: 360 }}>
          This area is restricted to the platform administrator.
          If you believe this is an error, contact the bot owner.
        </p>
      </motion.div>
    );
  }

  return <Outlet />;
}