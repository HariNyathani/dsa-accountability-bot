import React, { useMemo } from 'react';

interface HeatmapProps {
  data: Record<string, number>;
  restDates?: Set<string>;
  activeDays: number;
  currentStreak: number;
  maxStreak: number;
  loading?: boolean;
}

const REST_COLOR = '#6D8AB0';

const Heatmap: React.FC<HeatmapProps> = ({ data, restDates, activeDays, currentStreak, maxStreak, loading }) => {
  const { months, weekdays } = useMemo(() => {
    const today = new Date();
    const startDate = new Date();
    startDate.setDate(today.getDate() - 364); // Last 365 days

    const dates: Date[] = [];
    const curr = new Date(startDate);
    while (curr <= today) {
      dates.push(new Date(curr));
      curr.setDate(curr.getDate() + 1);
    }

    const monthGroups: { month: string; dates: (Date | null)[]; year: number; monthNum: number }[] = [];

    dates.forEach(date => {
      const monthStr = date.toLocaleString('default', { month: 'short' });
      const year = date.getFullYear();
      const monthNum = date.getMonth();

      let group = monthGroups.find(g => g.month === monthStr && g.year === year);
      if (!group) {
        group = { month: monthStr, dates: [], year, monthNum };

        // Pad the start to align with correct day of week
        const firstDayOfWeek = date.getDay();
        for (let i = 0; i < firstDayOfWeek; i++) {
          group.dates.push(null);
        }

        monthGroups.push(group);
      }
      group.dates.push(date);
    });

    return { months: monthGroups, weekdays: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] };
  }, []);

  const getColor = (count: number) => {
    if (count === 0) return "#1e293b"; // Dark Gray
    if (count === 1) return "#065f46"; // Muted Emerald
    if (count >= 2 && count <= 3) return "#10b981"; // Neon Green
    return "#047857"; // Deep Intense Green
  };

  const formatDate = (d: Date) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  if (loading) {
    return (
      <div className="card" style={{ marginTop: 20, marginBottom: 24 }}>
        <div className="chart-title">🔥 Annual Contribution Heatmap</div>
        <div style={{ height: "130px", background: "rgba(255,255,255,0.02)", borderRadius: "8px", animation: "pulse 2s infinite" }}></div>
      </div>
    );
  }

  return (
    <div className="card" style={{ marginTop: 20, marginBottom: 24 }}>
      {/* Header/Stats */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 16 }}>
        <div className="chart-title" style={{ marginBottom: 0 }}>🔥 Annual Contribution Heatmap</div>
        <div style={{ display: 'flex', gap: 24, fontSize: '0.9rem' }}>
          <div><span style={{ color: '#94a3b8' }}>Active Days:</span> <strong style={{ color: '#F8FAFC' }}>{activeDays}</strong></div>
          <div><span style={{ color: '#94a3b8' }}>Current Streak:</span> <strong style={{ color: '#F8FAFC' }}>{currentStreak}</strong></div>
          <div><span style={{ color: '#94a3b8' }}>Max Streak:</span> <strong style={{ color: '#F8FAFC' }}>{maxStreak}</strong></div>
        </div>
      </div>

      <div className="w-full overflow-x-auto custom-scrollbar" style={{ paddingBottom: '12px' }}>
        <div style={{ display: 'flex', gap: '8px', width: 'max-content', margin: '0 auto' }}>
          {/* Weekday labels */}
          <div style={{ display: 'grid', gridTemplateRows: 'repeat(7, 14px)', gap: '4px', marginTop: '16px', paddingRight: '8px' }}>
            {weekdays.map((day, i) => (
              <div key={i} style={{ fontSize: '10px', color: '#64748b', lineHeight: '14px', height: '14px' }}>
                {i % 2 === 0 ? day : ''}
              </div>
            ))}
          </div>

          {/* Month grids */}
          {months.map((month, mIdx) => (
            <div key={mIdx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', height: '12px', lineHeight: '12px', paddingLeft: '2px' }}>
                {month.month}
              </div>
              <div style={{ display: 'grid', gridTemplateRows: 'repeat(7, 14px)', gridAutoFlow: 'column', gap: '4px' }}>
                {month.dates.map((date, dIdx) => {
                  if (!date) return <div key={`empty-${dIdx}`} style={{ width: '14px', height: '14px' }} />;

                  const dateStr = formatDate(date);
                  const isRest = restDates?.has(dateStr) ?? false;
                  const count = data[dateStr] || 0;
                  const formattedDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

                  // Rest day: slate-blue override, distinct tooltip
                  const tileColor = isRest ? REST_COLOR : getColor(count);
                  const tooltip = isRest
                    ? `😴 Rest Day : ${formattedDate}`
                    : `${count} question${count === 1 ? '' : 's'} on ${formattedDate}`;

                  return (
                    <div
                      key={dateStr}
                      title={tooltip}
                      style={{
                        width: '14px',
                        height: '14px',
                        backgroundColor: tileColor,
                        borderRadius: '3px',
                        cursor: 'pointer',
                        transition: 'transform 0.1s',
                        boxShadow: (count > 0 || isRest) ? 'inset 0 0 0 1px rgba(0,0,0,0.1)' : 'none'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.2)'}
                      onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px', marginTop: '12px', fontSize: '11px', color: '#64748b' }}>
        <span>Less</span>
        {["#1e293b", "#065f46", "#10b981", "#047857"].map((c, i) => (
          <div key={i} style={{ width: '12px', height: '12px', backgroundColor: c, borderRadius: '2px' }} />
        ))}
        <span>More</span>
        <span style={{ marginLeft: '12px', borderLeft: '1px solid #334155', paddingLeft: '12px' }}>😴</span>
        <div style={{ width: '12px', height: '12px', backgroundColor: REST_COLOR, borderRadius: '2px' }} />
        <span>Rest</span>
      </div>
    </div>
  );
};

export default Heatmap;
