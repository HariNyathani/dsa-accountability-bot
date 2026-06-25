import type { ReactNode } from "react";
import GlassCard from "./GlassCard";
import { SkeletonRows } from "./Loader";
import { EmptyState } from "./EmptyState";
import type { ActivityLog } from "../types";
import s from "./RecentActivity.module.css";

function timeAgo(dateStr: string) {
  if (!dateStr) return "Just now";
  let dateObj = new Date(dateStr);
  if (isNaN(dateObj.getTime())) {
    let safeStr = dateStr.replace(" ", "T");
    const hasTimezone = safeStr.endsWith("Z") || safeStr.includes("+") || safeStr.substring(10).includes("-");
    if (!hasTimezone) safeStr += "Z";
    dateObj = new Date(safeStr);
  }
  if (isNaN(dateObj.getTime())) return "Just now";
  const now = new Date();
  const seconds = Math.floor((now.getTime() - dateObj.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min${minutes !== 1 ? "s" : ""} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr${hours !== 1 ? "s" : ""} ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  return `${days} days ago`;
}

interface Props {
  logs: ActivityLog[] | undefined;
  loading: boolean;
}

function renderTitle(log: ActivityLog): string {
  let titleText = "Logged progress";
  if (log.parsed_fields) {
    try {
      const parsed = JSON.parse(log.parsed_fields);
      if (parsed.log && parsed.log.length > 0) {
        const parts: string[] = parsed.log.map((l: any) =>
          l.question_count > 1 ? `${l.question_count} ${l.canonical_topic} questions` : `${l.canonical_topic}`
        );
        titleText = `${log.message_type === "plan" ? "Planned" : "Logged"} ${parts.join(", ")}`;
      }
    } catch {
      /* ignore */
    }
  } else if (log.topics) {
    titleText = `${log.message_type === "plan" ? "Planned" : "Logged"} ${log.topics}`;
  }
  return titleText;
}

function renderNote(log: ActivityLog): ReactNode {
  let note = "";
  if (log.message_content) {
    const lines = log.message_content.split("\\n");
    if (lines.length > 1) note = lines.slice(1).join(" ").trim();
    else if (!log.message_content.startsWith("!")) note = log.message_content.trim();
  }
  return note ? <div className={s.note}>{note}</div> : null;
}

export default function RecentActivity({ logs, loading }: Props) {
  if (loading) {
    return (
      <GlassCard padded glow className={s.wrap}>
        <div className={s.title}>⏳ Recent Activity</div>
        <SkeletonRows count={3} />
      </GlassCard>
    );
  }
  if (!logs || logs.length === 0) {
    return (
      <GlassCard padded glow className={s.wrap}>
        <div className={s.title}>⏳ Recent Activity</div>
        <EmptyState icon="📝" title="No recent activity" message="Log your progress to see it here." />
      </GlassCard>
    );
  }
  const displayLogs = logs.slice(0, 4);
  return (
    <GlassCard padded glow className={s.wrap}>
      <div className={s.title}>⏳ Recent Activity</div>
      <div className={s.feed}>
        {displayLogs.map((log) => (
          <div key={log.id} className={s.item}>
            <div className={s.itemHead}>
              <span className={s.itemTitle}>{renderTitle(log)}</span>
              <span className={s.itemTime}>{timeAgo(log.posted_at)}</span>
            </div>
            {renderNote(log)}
          </div>
        ))}
      </div>
    </GlassCard>
  );
}