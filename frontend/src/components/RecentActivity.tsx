import { ActivityLog } from "../types";
import { SkeletonRows } from "./Loader";
import { EmptyState } from "./EmptyState";

function timeAgo(dateStr: string) {
  if (!dateStr) return "Just now";

  // 1. Try parsing the raw string directly
  let dateObj = new Date(dateStr);

  // 2. Fallback for plain SQLite strings or invalid formats
  if (isNaN(dateObj.getTime())) {
    let safeStr = dateStr.replace(' ', 'T');
    // Don't append 'Z' if timezone info already exists
    const hasTimezone = safeStr.endsWith('Z') || safeStr.includes('+') || safeStr.substring(10).includes('-');
    if (!hasTimezone) {
      safeStr += 'Z';
    }
    dateObj = new Date(safeStr);
  }

  // 3. Safety check to avoid "NaN days ago"
  if (isNaN(dateObj.getTime())) {
    return "Just now";
  }

  const now = new Date();
  const seconds = Math.floor((now.getTime() - dateObj.getTime()) / 1000);
  
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min${minutes !== 1 ? 's' : ''} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr${hours !== 1 ? 's' : ''} ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  return `${days} days ago`;
}

interface Props {
  logs: ActivityLog[] | undefined;
  loading: boolean;
}

export default function RecentActivity({ logs, loading }: Props) {
  if (loading) {
    return (
      <div className="card">
        <div className="chart-title">⏳ Recent Activity</div>
        <SkeletonRows count={3} />
      </div>
    );
  }

  if (!logs || logs.length === 0) {
    return (
      <div className="card">
        <div className="chart-title">⏳ Recent Activity</div>
        <EmptyState icon="📝" title="No recent activity" message="Log your progress to see it here." />
      </div>
    );
  }

  const displayLogs = logs.slice(0, 4);

  return (
    <div className="card" style={{ marginBottom: 0, flexGrow: 1, display: "flex", flexDirection: "column" }}>
      <div className="chart-title">⏳ Recent Activity</div>
      <div className="activity-feed" style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "12px", flexGrow: 1 }}>
        {displayLogs.map(log => {
          let titleText = "Logged progress";
          let note = "";
          
          if (log.parsed_fields) {
            try {
              const parsed = JSON.parse(log.parsed_fields);
              if (parsed.log && parsed.log.length > 0) {
                const parts = parsed.log.map((l: any) => {
                  if (l.question_count > 1) return `${l.question_count} ${l.canonical_topic} questions`;
                  return `${l.canonical_topic}`;
                });
                titleText = `${log.message_type === 'plan' ? 'Planned' : 'Logged'} ${parts.join(', ')}`;
              }
            } catch (e) {}
          } else if (log.topics) {
            titleText = `${log.message_type === 'plan' ? 'Planned' : 'Logged'} ${log.topics}`;
          }
          
          // Extract note from message_content
          if (log.message_content) {
            const lines = log.message_content.split('\\n');
            if (lines.length > 1) {
              note = lines.slice(1).join(' ').trim();
            } else if (!log.message_content.startsWith('!')) {
              note = log.message_content.trim();
            }
          }

          return (
            <div key={log.id} style={{ display: "flex", flexDirection: "column", borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: "12px", gap: "4px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "#F8FAFC" }}>{titleText}</span>
                <span style={{ fontSize: "0.8rem", color: "#64748b", whiteSpace: "nowrap", marginLeft: "12px" }}>{timeAgo(log.posted_at)}</span>
              </div>
              {note && (
                <div style={{ fontSize: "0.85rem", color: "#94A3B8", fontStyle: "italic", lineHeight: 1.4 }}>
                  {note}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
