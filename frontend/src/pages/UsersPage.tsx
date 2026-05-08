import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { SkeletonRows } from "../components/Loader";
import { EmptyState, ErrorState } from "../components/EmptyState";

export default function UsersPage() {
  const nav = useNavigate();
  const { data, loading, error, refetch } = useApi(() => api.users(1, 100), []);

  if (error) return <ErrorState message={error} onRetry={refetch} />;

  return (
    <>
      <div className="page-header">
        <h2>Users</h2>
        <p>All registered users — click any row to view profile</p>
      </div>

      <div className="card">
        {loading ? <SkeletonRows count={8} /> : !data || data.length === 0 ? (
          <EmptyState icon="👥" title="No users registered" message="Use !register in Discord to join." />
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>ID</th>
                  <th>Timezone</th>
                  <th>Status</th>
                  <th>Joined</th>
                </tr>
              </thead>
              <tbody>
                {data.map((u) => (
                  <tr key={u.user_id} style={{ cursor: "pointer" }} onClick={() => nav(`/users/${u.user_id}`)}>
                    <td className="username-cell">{u.discord_username || `User ${u.user_id}`}</td>
                    <td style={{ fontFamily: "monospace", fontSize: ".82rem", color: "#94A3B8" }}>{u.user_id}</td>
                    <td>{u.timezone}</td>
                    <td>
                      <span className={`status-badge ${u.is_active ? "up" : "down"}`}>
                        <span className="dot" />
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td style={{ fontSize: ".82rem", color: "#94A3B8" }}>{u.created_at?.slice(0, 10) ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
