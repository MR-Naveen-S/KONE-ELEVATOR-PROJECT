import React, { useState } from 'react';
import { SavingsData } from '../types';
import { DollarSign, TrendingUp, Leaf, Calculator, BarChart3 } from 'lucide-react';

interface SavingsPaybackProps {
  data: SavingsData;
  onUpdateSystemCost?: (newCost: number) => void;
}

export const SavingsPayback: React.FC<SavingsPaybackProps> = ({ data, onUpdateSystemCost }) => {
  const [costInput, setCostInput] = useState<number>(data.system_cost_INR || 250000);

  const handleCostChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value) || 0;
    setCostInput(val);
    if (onUpdateSystemCost) {
      onUpdateSystemCost(val);
    }
  };

  return (
    <div className="glass-card" style={{ padding: '24px', margin: '18px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={18} color="var(--color-regen)" /> Counterfactual Savings & Capital Payback
          </h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Strict comparison of Stage 2 (Supercapacitor) vs Baseline B0 (Conventional brake resistor) on identical flight sequences.
          </p>
        </div>
        <span className="badge badge-green">Indian Tariff ToU Enabled</span>
      </div>

      {/* 4 Hero Comparison Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '24px' }}>
        
        {/* Energy Saved */}
        <div style={{ padding: '16px', background: 'rgba(16, 185, 129, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>GRID ENERGY SAVED</div>
          <div className="font-mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--color-regen)', margin: '4px 0' }}>
            {data.saved_kWh.toFixed(2)} <span style={{ fontSize: '0.85rem' }}>kWh</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Baseline: {data.grid_baseline_kWh.toFixed(2)} kWh → Actual: {data.grid_actual_kWh.toFixed(2)} kWh
          </div>
        </div>

        {/* Cost Saved */}
        <div style={{ padding: '16px', background: 'rgba(59, 130, 246, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(59, 130, 246, 0.25)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>ELECTRICITY BILL SAVED</div>
          <div className="font-mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--color-grid)', margin: '4px 0' }}>
            ₹ {data.saved_INR.toFixed(2)}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Bill: ₹ {data.cost_baseline_INR.toFixed(2)} → ₹ {data.cost_actual_INR.toFixed(2)}
          </div>
        </div>

        {/* Peak Demand Shaving */}
        <div style={{ padding: '16px', background: 'rgba(168, 85, 247, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(168, 85, 247, 0.25)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>PEAK DEMAND SHAVED</div>
          <div className="font-mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--color-purple)', margin: '4px 0' }}>
            −{data.peak_reduction_pct.toFixed(1)} <span style={{ fontSize: '0.85rem' }}>%</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Peak Ratchet: {data.peak_baseline_kW.toFixed(1)} kW → {data.peak_actual_kW.toFixed(1)} kW
          </div>
        </div>

        {/* Avoided CO2 */}
        <div style={{ padding: '16px', background: 'rgba(34, 197, 94, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(34, 197, 94, 0.25)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Leaf size={14} color="#22c55e" /> AVOIDED CO2
          </div>
          <div className="font-mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: '#22c55e', margin: '4px 0' }}>
            {data.co2_avoided_kg.toFixed(1)} <span style={{ fontSize: '0.85rem' }}>kg</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Grid Emission Factor: 0.82 kg/kWh
          </div>
        </div>
      </div>

      {/* Payback Calculator & 5-Year Projection */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '20px',
        padding: '18px',
        background: 'var(--bg-secondary)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-color)'
      }}>
        {/* Left: Interactive Input */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <Calculator size={18} color="var(--color-grid)" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Interactive Payback Estimator</h3>
          </div>
          <div style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              Supercapacitor & Converter System Capital Cost (₹):
            </label>
            <input 
              type="number"
              value={costInput}
              onChange={handleCostChange}
              step="10000"
              style={{
                width: '100%',
                padding: '8px 12px',
                background: 'var(--bg-card)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '1rem',
                fontWeight: 700,
                fontFamily: 'var(--font-mono)'
              }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Estimated Simple Payback:</span>
            <span className="font-mono" style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--color-regen)' }}>
              {data.payback_years} Years
            </span>
          </div>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '6px' }}>
            Based on current daily traffic pattern and peak demand reduction charges.
          </p>
        </div>

        {/* Right: 5-Year Cumulative Savings Trajectory */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <BarChart3 size={18} color="var(--color-purple)" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>5-Year Cumulative Cash Trajectory</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {data.payback_curve?.map((point) => (
              <div key={point.year} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Year {point.year}:</span>
                <span className="font-mono" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                  Savings: ₹ {point.savings_INR.toLocaleString()}
                </span>
                <span className="font-mono" style={{
                  fontWeight: 700,
                  color: point.net_benefit_INR >= 0 ? 'var(--color-regen)' : 'var(--color-brake)'
                }}>
                  Net: {point.net_benefit_INR >= 0 ? '+' : ''}₹ {point.net_benefit_INR.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
