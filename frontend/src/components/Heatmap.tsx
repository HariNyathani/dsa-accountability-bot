import { useMemo, useState } from "react";
import GlassCard from "./GlassCard";
import s from "./Heatmap.module.css";

interface HeatmapProps {
  data: Record<string, number>;
  restDates?: Set<string>;
  activeDays: number;
  currentStreak: number;
  maxStreak: number;
  loading?: boolean;
}

const levelClass = (count: number) => {
  if (count <= 0) return s.tileL0;
  if (count === 1) return s.tileL1;
  if (count <= 3) return s.tileL2;
  return s.tileL3;
};

/** Module-scoped so it's never re-created on component re-renders. */
const formatDate = (d: Date): string => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
};

const Heatmap: React.FC<HeatmapProps> = ({ data, restDates, activeDays, currentStreak, maxStreak, loading }) => {
  // Recomputes if the component re-renders past midnight (todayKey changes).
  const todayKey = new Date().toDateString();
  const { months, weekdays } = useMemo(() => {
    const today = new Date();
    const startDate = new Date();
    startDate.setDate(today.getDate() - 364);

    const dates: Date[] = [];
    const curr = new Date(startDate);
    while (curr <= today) {
      dates.push(new Date(curr));
      curr.setDate(curr.getDate() + 1);
    }

    const monthGroups: { month: string; dates: (Date | null)[]; year: number; monthNum: number }[] = [];
    dates.forEach((date) => {
      const monthStr = date.toLocaleString("default", { month: "short" });
      const year = date.getFullYear();
      const monthNum = date.getMonth();
      let group = monthGroups.find((g) => g.month === monthStr && g.year === year);
      if (!group) {
        group = { month: monthStr, dates: [], year, monthNum };
        const firstDayOfWeek = date.getDay();
        for (let i = 0; i < firstDayOfWeek; i++) group.dates.push(null);
        monthGroups.push(group);
      }
      group.dates.push(date);
    });
    return { months: monthGroups, weekdays: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] };
  }, [todayKey]);



  // Floating tooltip state — event-delegated from the scroll container so we
  // never create 365 individual event listeners.
  const [hoverTip, setHoverTip] = useState<{ text: string; x: number; y: number } | null>(null);

  if (loading) {
    return (
      <div className={s.wrap}>
        <GlassCard padded glow>
          <div className={s.title}>🔥 Annual Contribution Heatmap</div>
          <div className={s.skeleton} />
        </GlassCard>
      </div>
    );
  }

  return (
    <div className={s.wrap}>
      <GlassCard padded glow>
        <div className={s.head}>
          <div className={s.title}>🔥 Annual Contribution Heatmap</div>
          <div className={s.stats}>
            <span><span className={s.statK}>Active Days:</span> <strong className={s.statV}>{activeDays}</strong></span>
            <span><span className={s.statK}>Current Streak:</span> <strong className={s.statV}>{currentStreak}</strong></span>
            <span><span className={s.statK}>Max Streak:</span> <strong className={s.statV}>{maxStreak}</strong></span>
          </div>
        </div>

        {/* Single onMouseMove on the scroll wrapper — reads data-tip from each
            tile via event delegation so we never create 365+ closures. */}
        <div
          className={s.scroll}
          onMouseMove={(e) => {
            const el = e.target as HTMLElement;
            const tip = el.dataset.tip;
            if (tip) setHoverTip({ text: tip, x: e.clientX, y: e.clientY });
            else setHoverTip(null);
          }}
          onMouseLeave={() => setHoverTip(null)}
        >
          <div className={s.grid} role="grid" aria-label={`Activity heatmap, ${activeDays} active days in the last year`}>
            <div className={s.weekdays}>
              {weekdays.map((day, i) => (
                <div key={i} className={s.weekday}>{i % 2 === 1 ? day : ""}</div>
              ))}
            </div>
            {months.map((month, mIdx) => (
              <div key={mIdx} className={s.month}>
                <div className={s.monthLabel}>{month.month}</div>
                <div className={s.cells}>
                  {month.dates.map((date, dIdx) => {
                    if (!date) return <div key={`empty-${dIdx}`} className={s.tile} style={{ background: "transparent", cursor: "default" }} />;
                    const dateStr = formatDate(date);
                    const isRest = restDates?.has(dateStr) ?? false;
                    const count = data[dateStr] || 0;
                    const formattedDate = date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
                    const tipText = isRest ? `😴 Rest Day · ${formattedDate}` : `${count} question${count === 1 ? "" : "s"} on ${formattedDate}`;
                    const tier = isRest ? s.tileRest : levelClass(count);
                    return (
                      <div
                        key={dateStr}
                        data-tip={tipText}
                        role="gridcell"
                        aria-label={tipText}
                        className={`${s.tile} ${tier}${(count > 0 || isRest) ? ` ${s.tileActive}` : ""}`}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>


        <div className={s.legend}>
          <span>Less</span>
          <div className={`${s.swatch} ${s.tileL0}`} />
          <div className={`${s.swatch} ${s.tileL1}`} />
          <div className={`${s.swatch} ${s.tileL2}`} />
          <div className={`${s.swatch} ${s.tileL3}`} />
          <span>More</span>
          <span className={s.legendDivider}>😴</span>
          <div className={`${s.swatch} ${s.tileRest}`} />
          <span>Rest</span>
        </div>
      </GlassCard>

      {/* Styled floating tooltip — rendered outside the card so it's never
          clipped by overflow:hidden on the scroll container. position:fixed
          keeps it anchored to the viewport regardless of page scroll. */}
      {hoverTip && (
        <div
          className={s.floatTip}
          style={{ left: hoverTip.x + 14, top: hoverTip.y - 44 }}
          aria-hidden="true"
        >
          {hoverTip.text}
        </div>
      )}
    </div>
  );
};

export default Heatmap;