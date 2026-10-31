import React from 'react';
import { FileText, Download, Calendar, Flame } from 'lucide-react';

interface MonthlyDailyStatsProps {
  onExportPdf: () => void;
  onExportCsv: () => void;
}

export const MonthlyDailyStats: React.FC<MonthlyDailyStatsProps> = ({ onExportPdf, onExportCsv }) => {
  // Generate 24x7 traffic & regen heatmap data
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const hours = Array.from({ length: 24 }, (_, i) => i);

  // Helper to determine traffic heat intensity
  const getHeatColor = (dayIdx: number, hour: number) => {
    const isWeekend = dayIdx >= 5;
    if (isWeekend) {
      if (hour >= 11 && hour <= 19) return 'rgba(59, 130, 246, 0.4)';
      return 'rgba(255, 255, 255, 0.04)';
    }
    // Up-peak: 8-10, Lunch: 12-14, Down-peak: 17-19
    if (hour >= 8 && hour <= 9) return 'rgba(16, 185, 129, 0.85)'; // Heavy regen
    if (hour >= 12 && hour <= 13) return 'rgba(59, 130, 246, 0.65)';
    if (hour >= 17 && hour <= 19) return 'rgba(16, 185, 129, 0.75)'; // Heavy down-peak regen
    if (hour >= 6 && hour <= 22) return 'rgba(59, 130, 246, 0.25)';
    return 'rgba(255, 255, 255, 0.04)';
  };

  return (
    <div className="glass-card" style={{ padding: '24px', margin: '18px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Calendar size={18} color="var(--color-grid)" /> Monthly & Daily Performance Analytics
          </h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Aggregated traffic statistics, busiest hours heatmap, and executive report exports.
          </p>
        </div>

        {/* Export Buttons */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={onExportCsv}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 12px',
              background: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <Download size={14} /> Export CSV
          </button>
          <button
            onClick={onExportPdf}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 14px',
              background: 'linear-gradient(135deg, #2563eb, #10b981)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            <FileText size={14} /> Download PDF Report
          </button>
        </div>
      </div>

      {/* Month-over-Month KPI Matrix */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '12px',
        marginBottom: '24px'
      }}>
        <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>TOTAL TRIPS RECORDED</div>
          <div className="font-mono" style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', margin: '4px 0' }}>
            1,482
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--color-regen)' }}>+12.4% vs last month</div>
        </div>

        <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>ENERGY / TRIP</div>
          <div className="font-mono" style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--color-grid)', margin: '4px 0' }}>
            26.4 <span style={{ fontSize: '0.75rem' }}>Wh/trip</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--color-regen)' }}>−23.1% vs conventional</div>
        </div>

        <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>REGEN CAPTURE RATIO</div>
          <div className="font-mono" style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--color-regen)', margin: '4px 0' }}>
            88.5%
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>11.5% brake chopped</div>
        </div>

        <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>SELF-SUFFICIENCY RATIO</div>
          <div className="font-mono" style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--color-sc)', margin: '4px 0' }}>
            44.2%
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Discharged into lift</div>
        </div>
      </div>

      {/* 24-Hour x 7-Day Busiest Hours & Regen Heatmap */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Flame size={15} color="var(--color-regen)" /> Busiest Hours & Regeneration Capture Heatmap (Hour × Weekday)
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            <span>Low Traffic</span>
            <div style={{ width: '40px', height: '8px', background: 'linear-gradient(to right, rgba(255,255,255,0.05), rgba(16, 185, 129, 0.85))', borderRadius: '4px' }} />
            <span>Peak Regen</span>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '50px repeat(24, 1fr)', gap: '4px', minWidth: '700px' }}>
            {/* Header row: hours 0 to 23 */}
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>Day</div>
            {hours.map(h => (
              <div key={h} style={{ fontSize: '0.65rem', textAlign: 'center', color: 'var(--text-muted)', fontWeight: 600 }}>
                {h}h
              </div>
            ))}

            {/* Days rows */}
            {days.map((d, dIdx) => (
              <React.Fragment key={d}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'flex', alignItems: 'center' }}>
                  {d}
                </div>
                {hours.map(h => (
                  <div
                    key={`${d}-${h}`}
                    title={`${d} at ${h}:00 - Traffic pattern`}
                    style={{
                      height: '24px',
                      borderRadius: '3px',
                      background: getHeatColor(dIdx, h),
                      border: '1px solid rgba(255,255,255,0.03)',
                      transition: 'transform 0.15s ease',
                      cursor: 'pointer'
                    }}
                  />
                ))}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
