interface Props {
  icon: string;
  value: string | number;
  label: string;
  accent?: string;
}

export default function StatCard({ icon, value, label, accent = "indigo" }: Props) {
  return (
    <div className="card stat-card" data-accent={accent}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
