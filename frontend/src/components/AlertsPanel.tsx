import React, { useState, useEffect } from 'react';
import { AlertTriangle, ShieldAlert, Activity, CheckCircle, RefreshCw, Info } from 'lucide-react';
import { AlertItem } from '../types';

interface ClipEvent {
  time: number;
  raw_action_W: number;
  approved_action_W: number;
  reason: string;
}

interface AlertsPanelProps {
  telemetryWarning?: boolean;
  busResidualPct?: number;
}

export const AlertsPanel: React.FC<AlertsPanelProps> = ({ telemetryWarning, busResidualPct }) => {
  const [filter, setFilter] = useState<'all' | 'safety' | 'health' | 'data'>('all');
  const [healthAlerts, setHealthAlerts] = useState<AlertItem[]>([]);
  const [safetyClips, setSafetyClips] = useState<ClipEvent[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchAlerts = async () => {
    setIsLoading(true);
    try {
      const resp = await fetch('/api/alerts');
      if (resp.ok) {
        const data = await resp.json();
        setHealthAlerts(data.health_alerts || []);
        setSafetyClips(data.safety_clips || []);
      }
    } catch {
      // Offline fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, []);

  const unifiedEvents = [
    ...(telemetryWarning
      ? [
          {
            id: 'live-dq',
            timestamp: Date.now(),
            category: 'data' as const,
            severity: 'WARNING' as const,
            title: 'DATA_QUALITY_WARNING Active',
            message: `DC Bus balance residual is ${busResidualPct?.toFixed(2)}%, exceeding Section 9 limit of 1.5%. Inspection recommended.`,
            metric: `${busResidualPct?.toFixed(2)}%`,
            threshold: '1.5%',
          },
        ]
      : []),
    ...healthAlerts.map((ha, idx) => ({
      id: `health-${idx}-${ha.time}`,
      timestamp: ha.time * 1000,
      category: 'health' as const,
      severity: ha.level as 'INFO' | 'WARNING' | 'CRITICAL',
      title: `${ha.alert_type} Alert`,
      message: ha.message,
      metric: `${ha.metric_value.toFixed(1)}`,
      threshold: `${ha.threshold.toFixed(1)}`,
    })),
    ...safetyClips.map((sc, idx) => ({
      id: `clip-${idx}-${sc.time}`,
      timestamp: sc.time * 1000,
      category: 'safety' as const,
      severity: 'WARNING' as const,
      title: 'Safety Supervisor Clip Event',
      message: `Enforced constraint: ${sc.reason}. Output clamped from ${(sc.raw_action_W / 1000).toFixed(1)} kW to ${(sc.approved_action_W / 1000).toFixed(1)} kW.`,
      metric: `${(sc.approved_action_W / 1000).toFixed(1)} kW`,
      threshold: `${(sc.raw_action_W / 1000).toFixed(1)} kW`,
    })),
  ];

  const filteredEvents = unifiedEvents.filter((ev) => {
    if (filter === 'all') return true;
    return ev.category === filter;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Controls */}
      <div className="glass-card" style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertTriangle size={20} color="var(--color-warning)" />
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>System Alerts & Safety Clip History</h2>
            <span className="badge badge-amber">{unifiedEvents.length} EVENTS</span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Section 8 & 9: Real-time audit of Safety Supervisor constraint clipping, energy balance residuals (&gt; 1.5%), and supercapacitor health.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ display: 'flex', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', padding: '2px' }}>
            {(['all', 'safety', 'health', 'data'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setFilter(tab)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '4px',
                  border: 'none',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  backgroundColor: filter === tab ? 'var(--color-motoring)' : 'transparent',
                  color: filter === tab ? '#fff' : 'var(--text-secondary)'
                }}
              >
                {tab.toUpperCase()}
              </button>
            ))}
          </div>

          <button
            onClick={fetchAlerts}
            disabled={isLoading}
            style={{ display: 'flex', alignItems: 'center', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', cursor: 'pointer' }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px' }}>
        <div className="glass-card" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-warning)', fontWeight: 600 }}>SAFETY SUPERVISOR CLIPS</span>
            <ShieldAlert size={16} color="var(--color-warning)" />
          </div>
          <div className="font-mono" style={{ fontSize: '1.8rem', fontWeight: 800, margin: '8px 0', color: 'var(--text-primary)' }}>
            {safetyClips.length}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Non-learned hard projections clipping P_sc_ref</div>
        </div>

        <div className="glass-card" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-brake)', fontWeight: 600 }}>SUPERCAP HEALTH ALARMS</span>
            <Activity size={16} color="var(--color-brake)" />
          </div>
          <div className="font-mono" style={{ fontSize: '1.8rem', fontWeight: 800, margin: '8px 0', color: 'var(--text-primary)' }}>
            {healthAlerts.length}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Over-temperature, SOH fade & ESR anomalies</div>
        </div>

        <div className="glass-card" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-grid)', fontWeight: 600 }}>DATA QUALITY WARNINGS</span>
            <AlertTriangle size={16} color="var(--color-grid)" />
          </div>
          <div className="font-mono" style={{ fontSize: '1.8rem', fontWeight: 800, margin: '8px 0', color: telemetryWarning ? 'var(--color-brake)' : 'var(--text-primary)' }}>
            {telemetryWarning ? '1 ACTIVE' : '0 NORMAL'}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Residual &gt; 1.5% flags indicating sensor drift</div>
        </div>
      </div>

      {/* Event Stream */}
      <div className="glass-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', marginBottom: '14px' }}>
          <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>Audit & Safety Event Stream</h3>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{filteredEvents.length} events recorded</span>
        </div>

        {filteredEvents.length === 0 ? (
          <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <CheckCircle size={36} color="var(--color-regen)" style={{ margin: '0 auto 8px auto', opacity: 0.6 }} />
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>All Systems Nominal</div>
            <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>Zero active safety clips, health violations, or energy balance anomalies detected.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {filteredEvents.map((ev) => (
              <div key={ev.id} style={{ padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '14px' }}>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <div style={{ padding: '8px', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)', marginTop: '2px' }}>
                    {ev.category === 'safety' ? <ShieldAlert size={16} color="var(--color-warning)" /> : ev.category === 'health' ? <Activity size={16} color="var(--color-brake)" /> : <AlertTriangle size={16} color="var(--color-grid)" />}
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>{ev.title}</span>
                      <span className={`badge ${ev.severity === 'CRITICAL' ? 'badge-rose' : ev.severity === 'WARNING' ? 'badge-amber' : 'badge-blue'}`}>{ev.severity}</span>
                    </div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: 1.4 }}>{ev.message}</p>
                    <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      <span>Observed: <strong style={{ color: 'var(--text-primary)' }}>{ev.metric}</strong></span>
                      <span>Limit: <strong style={{ color: 'var(--text-primary)' }}>{ev.threshold}</strong></span>
                    </div>
                  </div>
                </div>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
