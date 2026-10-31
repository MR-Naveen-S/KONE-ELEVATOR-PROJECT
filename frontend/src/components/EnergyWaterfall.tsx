import React from 'react';
import { WaterfallData } from '../types';
import { CheckCircle2, AlertTriangle, Layers, Info } from 'lucide-react';

interface EnergyWaterfallProps {
  data: WaterfallData;
}

export const EnergyWaterfall: React.FC<EnergyWaterfallProps> = ({ data }) => {
  const isCompliant = data.balance_checks.check_1_regen_balance === 'PASS';
  const residual = data.balance_checks.residual_pct;

  const items = [
    { label: '1. Net Lift Motoring Demand (E_motoring_dc)', val: data.motoring_demand_kWh, color: 'var(--color-motoring)', note: 'Gross mechanical + electrical demand' },
    { label: '2. Energy Drawn from 3φ Grid (E_grid)', val: data.grid_drawn_kWh, color: 'var(--color-grid)', note: 'Diode rectifier input (always >= 0)' },
    { label: '3. Gross Regenerated Energy (E_regen_gross)', val: data.gross_regen_kWh, color: 'var(--color-regen)', note: 'Generated during downward heavy or upward empty trips' },
    { label: '4. Captured into Supercapacitor (E_captured_bus)', val: data.captured_in_sc_kWh, color: 'var(--color-sc)', note: 'Power routed through bidirectional DC-DC converter' },
    { label: '5. Stored Energy Discharged to Lift (E_sc_out)', val: data.stored_energy_used_kWh, color: '#38bdf8', note: 'Reused on subsequent motoring trips' },
    { label: '6. Burnt in Brake Resistor (E_brake)', val: data.brake_burnt_kWh, color: 'var(--color-brake)', note: 'Excess energy dissipated when Vdc >= 600V' },
    { label: '7. Usable Energy in Supercap Bank', val: data.energy_in_sc_kWh, color: 'var(--color-purple)', note: 'Current state of charge available for next trip' },
    { label: '8. Counterfactual Energy Saved vs B0', val: data.saved_kWh, color: '#16a34a', note: 'Direct utility electricity reduction' },
  ];

  return (
    <div className="glass-card" style={{ padding: '24px', margin: '18px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} color="var(--color-grid)" /> Section 9 Energy Waterfall & Balance Accounting
          </h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Trapezoidal integration of 1-second power signals across all operational regimes.
          </p>
        </div>

        {/* Balance Checks Compliance Box */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          background: isCompliant ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.15)',
          border: `1px solid ${isCompliant ? 'rgba(16, 185, 129, 0.35)' : 'rgba(244, 63, 94, 0.4)'}`,
          borderRadius: 'var(--radius-sm)'
        }}>
          {isCompliant ? (
            <CheckCircle2 size={16} color="var(--color-regen)" />
          ) : (
            <AlertTriangle size={16} color="var(--color-brake)" />
          )}
          <span style={{ fontSize: '0.78rem', fontWeight: 700, color: isCompliant ? 'var(--color-regen)' : 'var(--color-brake)' }}>
            {isCompliant ? 'BALANCE VERIFIED: Residual < 1.5%' : 'DATA_QUALITY_WARNING: Residual > 1.5%'}
          </span>
          <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            ({residual.toFixed(2)}% vs 1.50% max)
          </span>
        </div>
      </div>

      {/* Visual Waterfall Bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {items.map((item, idx) => {
          const maxVal = Math.max(...items.map(i => i.val), 0.1);
          const widthPct = Math.min(100, Math.max(2, (item.val / maxVal) * 100));

          return (
            <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', fontWeight: 600 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
                <span className="font-mono" style={{ color: item.color, fontWeight: 700 }}>
                  {item.val.toFixed(3)} kWh
                </span>
              </div>
              <div style={{ width: '100%', height: '10px', background: 'rgba(255,255,255,0.06)', borderRadius: '5px', overflow: 'hidden' }}>
                <div style={{
                  width: `${widthPct}%`,
                  height: '100%',
                  background: item.color,
                  borderRadius: '5px',
                  transition: 'width 0.4s ease'
                }} />
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                {item.note}
              </div>
            </div>
          );
        })}
      </div>

      {/* Automated Balance Invariant Footnote */}
      <div style={{
        marginTop: '20px',
        padding: '12px 16px',
        background: 'rgba(15, 23, 42, 0.4)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-color)',
        fontSize: '0.74rem',
        color: 'var(--text-secondary)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
          <Info size={14} color="var(--color-grid)" /> Mandatory Balance Invariants (Section 9):
        </div>
        <div>(1) E_regen_gross ≈ E_captured_bus + E_brake + ΔE_Cdc + E_aux_direct_use</div>
        <div>(2) E_captured_bus ≈ E_sc_out + ΔE_sc_stored + E_losses (ESR + DC-DC)</div>
        <div>(3) P_grid + P_sc_bus = P_inv_dc + P_aux + P_brake + d(½Cdc·Vdc²)/dt at every step</div>
      </div>
    </div>
  );
};
