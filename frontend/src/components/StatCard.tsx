import s from "./StatCard.module.css";

interface Props {
  icon: string;
  value: string | number;
  label: string;
  accent?:
    | "espresso"
    | "amber"
    | "sage"
    | "slate"
    | "clay"
    | "rose";
}

export default function StatCard({
  icon,
  value,
  label,
  accent = "espresso",
}: Props) {
  return (
    <div className={s.card} data-accent={accent}>
      <span className={s.icon}>{icon}</span>
      <div className={s.value}>{value}</div>
      <div className={s.label}>{label}</div>
    </div>
  );
}