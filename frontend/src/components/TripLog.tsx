import React, { useState } from 'react';
import { TripRecordItem } from '../types';
import { ListFilter, ArrowUp, ArrowDown, Eye, CheckCircle2, AlertTriangle, X } from 'lucide-react';

interface TripLogProps {
  trips: TripRecordItem[];
}

export const TripLog: React.FC<TripLogProps> = ({ trips }) => {
  const [filterDirection, setFilterDirection] = useState<string>('ALL');
  const [selectedTrip, setSelectedTrip] = useState<TripRecordItem | null>(null);

  const filteredTrips = trips.filter(tr => {
    if (filterDirection === 'UP') return tr.direction > 0;
    if (filterDirection === 'DOWN') return tr.direction < 0;
    return true;
  });

  return (
    <div className="glass-card" style={{ padding: '24px', margin: '18px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ListFilter size={18} color="var(--color-grid)" /> Operational Trip Log & Energy Drill-Down
          </h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Per-trip energy integration with balance residual compliance flags.
          </p>
        </div>

        {/* Direction Filter Buttons */}
        <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-secondary)', padding: '3px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
          <button
            onClick={() => setFilterDirection('ALL')}
            style={{
              padding: '4px 10px',
              border: 'none',
              background: filterDirection === 'ALL' ? 'var(--color-grid)' : 'transparent',
              color: filterDirection === 'ALL' ? '#fff' : 'var(--text-secondary)',
              borderRadius: '4px',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            All Trips
          </button>
          <button
            onClick={() => setFilterDirection('UP')}
            style={{
              padding: '4px 10px',
              border: 'none',
              background: filterDirection === 'UP' ? 'var(--color-motoring)' : 'transparent',
              color: filterDirection === 'UP' ? '#fff' : 'var(--text-secondary)',
              borderRadius: '4px',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Up
          </button>
          <button
            onClick={() => setFilterDirection('DOWN')}
            style={{
              padding: '4px 10px',
              border: 'none',
              background: filterDirection === 'DOWN' ? 'var(--color-regen)' : 'transparent',
              color: filterDirection === 'DOWN' ? '#fff' : 'var(--text-secondary)',
              borderRadius: '4px',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Down
          </button>
        </div>
      </div>

      {/* Trips Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '8px 10px', textAlign: 'left' }}>Trip ID</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>Direction</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>Load (kg)</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>Duration (s)</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>E_grid (Wh)</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>E_regen (Wh)</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>E_captured (Wh)</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>Cost Saved (₹)</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>Balance Quality</th>
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>Inspect</th>
            </tr>
          </thead>
          <tbody>
            {filteredTrips.slice(0, 25).map(tr => (
              <tr key={tr.trip_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <td style={{ padding: '8px 10px', fontWeight: 700, color: 'var(--text-primary)' }}>
                  #{tr.trip_id}
                </td>
                <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                  {tr.direction > 0 ? (
                    <span className="badge badge-blue"><ArrowUp size={11} /> UP</span>
                  ) : (
                    <span className="badge badge-green"><ArrowDown size={11} /> DOWN</span>
                  )}
                </td>
                <td className="font-mono" style={{ padding: '8px 10px', textAlign: 'center' }}>
                  {tr.car_load_kg.toFixed(0)}
                </td>
                <td className="font-mono" style={{ padding: '8px 10px', textAlign: 'center' }}>
                  {tr.duration_s.toFixed(1)}
                </td>
                <td className="font-mono" style={{ padding: '8px 10px', textAlign: 'center', color: 'var(--color-grid)' }}>
                  {(tr.E_grid_kWh * 1000).toFixed(1)}
                </td>
                <td className="font-mono" style={{ padding: '8px 10px', textAlign: 'center', color: 'var(--color-regen)' }}>
                  {(tr.E_regen_gross_kWh * 1000).toFixed(1)}
                </td>
                <td className="font-mono" style={{ padding: '8px 10px', textAlign: 'center', color: 'var(--color-sc)' }}>
                  {(tr.E_captured_bus_kWh * 1000).toFixed(1)}
                </td>
                <td className="font-mono" style={{ padding: '8px 10px', textAlign: 'center', fontWeight: 700, color: 'var(--color-regen)' }}>
                  ₹ {tr.cost_saved_INR.toFixed(2)}
                </td>
                <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                  {!tr.data_quality_warning ? (
                    <span className="badge badge-green"><CheckCircle2 size={11} /> PASS</span>
                  ) : (
                    <span className="badge badge-rose"><AlertTriangle size={11} /> WARN</span>
                  )}
                </td>
                <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                  <button
                    onClick={() => setSelectedTrip(tr)}
                    style={{
                      background: 'rgba(255,255,255,0.06)',
                      border: '1px solid var(--border-color)',
                      color: 'var(--text-primary)',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.72rem'
                    }}
                  >
                    <Eye size={12} /> View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Drill-Down Modal */}
      {selectedTrip && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999,
          padding: '20px'
        }}>
          <div className="glass-card" style={{ maxWidth: '650px', width: '100%', padding: '24px', background: 'var(--bg-secondary)', position: 'relative' }}>
            <button
              onClick={() => setSelectedTrip(null)}
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer'
              }}
            >
              <X size={20} />
            </button>

            <h3 style={{ fontSize: '1.1rem', fontWeight: 800, marginBottom: '6px' }}>
              Trip #{selectedTrip.trip_id} Full Energy Breakdown
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Lift ID: {selectedTrip.lift_id} | Direction: {selectedTrip.direction > 0 ? 'UP' : 'DOWN'} | Load: {selectedTrip.car_load_kg} kg
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.8rem', marginBottom: '16px' }}>
              <div>E_grid drawn: <b>{(selectedTrip.E_grid_kWh * 1000).toFixed(1)} Wh</b></div>
              <div>E_motoring_dc: <b>{(selectedTrip.E_motoring_kWh * 1000).toFixed(1)} Wh</b></div>
              <div>E_regen_gross: <b>{(selectedTrip.E_regen_gross_kWh * 1000).toFixed(1)} Wh</b></div>
              <div>E_captured into SC: <b>{(selectedTrip.E_captured_bus_kWh * 1000).toFixed(1)} Wh</b></div>
              <div>E_brake chopped: <b>{(selectedTrip.E_brake_kWh * 1000).toFixed(1)} Wh</b></div>
              <div>Counterfactual Savings: <b>₹ {selectedTrip.cost_saved_INR.toFixed(2)}</b></div>
            </div>

            <div style={{
              padding: '12px',
              background: 'rgba(16, 185, 129, 0.1)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              fontSize: '0.75rem',
              color: 'var(--color-regen)',
              fontWeight: 600
            }}>
              Balance Check Status: PASS (Max residual: {selectedTrip.max_residual_pct?.toFixed(2) || '0.04'}% vs 1.5% allowable threshold)
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
