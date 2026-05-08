import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import StatCard from "../components/StatCard";
import { SkeletonCards } from "../components/Loader";
import { ErrorState } from "../components/EmptyState";

function fmt(secs: number): string {
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export default function StatusPage() {
  const health = useApi(() => api.health(), []);
  const status = useApi(() => api.status(), []);

  if (health.error) return <ErrorState message={health.error} onRetry={health.refetch} />;

  const h = health.data;
  const s = status.data;

  return (
    <>
      <div className="page-header">
        <h2>System Status</h2>
        <p>Real-time health monitoring for the DSA Accountability Platform</p>
      </div>

      {/* Quick stats */}
      {health.loading ? <SkeletonCards count={4} /> : h && s && (
        <div className="stats-grid">
          <StatCard icon="🟢" value={h.status === "healthy" ? "Healthy" : "Degraded"} label="API Health" accent="emerald" />
          <StatCard icon="⏱️" value={fmt(h.uptime_seconds)} label="Uptime" accent="sky" />
          <StatCard icon="🗄️" value={s.database === "up" ? "Connected" : "Down"} label="Database" accent="indigo" />
          <StatCard icon="👥" value={s.registered_users} label="Registered Users" accent="purple" />
        </div>
      )}

      {/* Detailed services */}
      {s && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="chart-title">🔧 Service Status</div>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Status</th>
                  <th>Latency</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {/* Core services */}
                <tr>
                  <td className="username-cell">FastAPI Server</td>
                  <td><span className={`status-badge ${s.api === "running" ? "up" : "down"}`}><span className="dot" />{s.api}</span></td>
                  <td>—</td>
                  <td style={{ color: "#94A3B8" }}>REST API + OpenAPI docs</td>
                </tr>
                <tr>
                  <td className="username-cell">Discord Bot</td>
                  <td><span className={`status-badge ${s.bot !== "down" ? "up" : "down"}`}><span className="dot" />{s.bot}</span></td>
                  <td>—</td>
                  <td style={{ color: "#94A3B8" }}>discord.py event loop</td>
                </tr>
                <tr>
                  <td className="username-cell">Scheduler</td>
                  <td><span className={`status-badge ${s.scheduler === "active" ? "up" : "down"}`}><span className="dot" />{s.scheduler}</span></td>
                  <td>—</td>
                  <td style={{ color: "#94A3B8" }}>APScheduler — reminders + weekly summary</td>
                </tr>
                {/* DB services */}
                {s.services.map((svc, i) => (
                  <tr key={i}>
                    <td className="username-cell" style={{ textTransform: "capitalize" }}>{svc.name}</td>
                    <td><span className={`status-badge ${svc.status === "up" ? "up" : "down"}`}><span className="dot" />{svc.status}</span></td>
                    <td>{svc.latency_ms != null ? `${svc.latency_ms}ms` : "—"}</td>
                    <td style={{ color: "#94A3B8" }}>{svc.detail ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Metadata */}
      {h && (
        <div className="card">
          <div className="chart-title">ℹ️ System Info</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, fontSize: ".88rem" }}>
            <div><span style={{ color: "#94A3B8" }}>API Version:</span> <strong>{h.api_version}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Uptime:</span> <strong>{fmt(h.uptime_seconds)}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Last Check:</span> <strong>{new Date(h.timestamp).toLocaleString()}</strong></div>
          </div>
        </div>
      )}
    </>
  );
}
