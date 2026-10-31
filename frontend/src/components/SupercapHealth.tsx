import React, { useState } from 'react';
import { HealthStatus } from '../types';
import { HeartPulse, Thermometer, RefreshCw, AlertTriangle, CheckCircle, Sliders, Shield } from 'lucide-react';

interface SupercapHealthProps {
  health?: HealthStatus;
  onInjectDegradation: (cMult: number, esrMult: number) => void;
  onResetDegradation: () => void;
}

export const SupercapHealth: React.FC<SupercapHealthProps> = ({
  health,
  onInjectDegradation,
  onResetDegradation
}) => {
  const [cSlider, setCSlider] = useState<number>(0.85);
  const [esrSlider, setEsrSlider] = useState<number>(1.6);

  const h = health || {
    C_est_F: 15.0,
    ESR_est_mOhm: 35.0,
    SOH_C_pct: 100.0,
    SOH_ESR_pct: 100.0,
    SOH_pct: 100.0,
    is_eol: false,
    SC_temp_degC: 25.0,
    aging_acceleration: 1.0,
    RUL_years_nominal: 10.0,
    RUL_years_low: 8.5,
    RUL_years_high: 11.5,
    confidence_note: 'Rule of thumb 2^((T-25)/10) model.'
  };

  const getSohColor = (soh: number) => {
    if (soh > 90) return 'var(--color-regen)';
    if (soh > 80) return 'var(--color-warning)';
    return 'var(--color-brake)';
  };

  return (
    <div className="glass-card" style={{ padding: '24px', margin: '18px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <HeartPulse size={18} color="var(--color-regen)" /> Supercapacitor Diagnostics & State of Health (SOH)
          </h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Online estimation of capacitance C = ∫i dt / ΔV and ESR = ΔV / ΔI with first-order thermal modeling.
          </p>
        </div>

        {/* EOL Status Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '5px 12px',
          background: h.is_eol ? 'rgba(244, 63, 94, 0.15)' : 'rgba(16, 185, 129, 0.12)',
          border: `1px solid ${h.is_eol ? 'rgba(244, 63, 94, 0.4)' : 'rgba(16, 185, 129, 0.35)'}`,
          borderRadius: 'var(--radius-sm)'
        }}>
          {h.is_eol ? <AlertTriangle size={15} color="var(--color-brake)" /> : <CheckCircle size={15} color="var(--color-regen)" />}
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: h.is_eol ? 'var(--color-brake)' : 'var(--color-regen)' }}>
            {h.is_eol ? 'END-OF-LIFE REACHED (EOL)' : 'HEALTH: NOMINAL COMMISSIONED'}
          </span>
        </div>
      </div>

      {/* Primary Health Meters Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '24px' }}>
        
        {/* Overall SOH */}
        <div style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>OVERALL SOH (MIN C, ESR)</div>
          <div className="font-mono" style={{ fontSize: '2rem', fontWeight: 800, color: getSohColor(h.SOH_pct), margin: '4px 0' }}>
            {h.SOH_pct.toFixed(1)} <span style={{ fontSize: '1rem' }}>%</span>
          </div>
          <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
            <div style={{ width: `${Math.min(100, h.SOH_pct)}%`, height: '100%', background: getSohColor(h.SOH_pct) }} />
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '6px' }}>EOL Criteria: SOH ≤ 80%</div>
        </div>

        {/* Capacitance C */}
        <div style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>ESTIMATED CAPACITANCE</div>
          <div className="font-mono" style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--color-sc)', margin: '4px 0' }}>
            {h.C_est_F.toFixed(2)} <span style={{ fontSize: '1rem' }}>F</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            SOH_C: {h.SOH_C_pct.toFixed(1)}% (Nominal: 15.0 F)
          </div>
        </div>

        {/* ESR */}
        <div style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>ESTIMATED ESR</div>
          <div className="font-mono" style={{ fontSize: '2rem', fontWeight: 800, color: h.ESR_est_mOhm > 55 ? 'var(--color-warning)' : 'var(--color-grid)', margin: '4px 0' }}>
            {h.ESR_est_mOhm.toFixed(1)} <span style={{ fontSize: '1rem' }}>mΩ</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            SOH_ESR: {h.SOH_ESR_pct.toFixed(1)}% (Nominal: 35.0 mΩ)
          </div>
        </div>

        {/* Temperature & Thermal Stress */}
        <div style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Thermometer size={14} color={h.SC_temp_degC > 55 ? 'var(--color-brake)' : 'var(--color-warning)'} /> TEMPERATURE
          </div>
          <div className="font-mono" style={{ fontSize: '2rem', fontWeight: 800, color: h.SC_temp_degC > 55 ? 'var(--color-brake)' : 'var(--text-primary)', margin: '4px 0' }}>
            {h.SC_temp_degC.toFixed(1)} <span style={{ fontSize: '1rem' }}>°C</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Aging Acceleration: {h.aging_acceleration.toFixed(2)}× nominal
          </div>
        </div>
      </div>

      {/* Remaining Useful Life Box */}
      <div style={{
        padding: '16px 20px',
        background: 'rgba(15, 23, 42, 0.5)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-color)',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Projected Remaining Useful Life (RUL): <span className="font-mono" style={{ color: 'var(--color-regen)' }}>{h.RUL_years_nominal} Years</span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Confidence Range: [{h.RUL_years_low} - {h.RUL_years_high} Years] · {h.confidence_note}
          </div>
        </div>
        <span className="badge badge-blue">Arrhenius-Eyring Model</span>
      </div>

      {/* Degradation Injector (Section 10 Mandate for Pipeline Validation) */}
      <div style={{
        padding: '18px',
        background: 'rgba(30, 41, 59, 0.4)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid rgba(245, 158, 11, 0.3)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={16} color="var(--color-warning)" />
            <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--color-warning)' }}>
              Hardware Degradation Injector (Test Pipeline Validation)
            </h3>
          </div>
          <button
            onClick={onResetDegradation}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              background: 'transparent',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <RefreshCw size={12} /> Reset to Nominal
          </button>
        </div>

        <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
          Inject synthetic capacitance fade and ESR growth to verify health diagnostics, EOL indicators, and automatic alert dispatching.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600, marginBottom: '4px' }}>
              <span>Capacitance Multiplier: {(cSlider * 100).toFixed(0)}%</span>
              <span className="font-mono">{(15.0 * cSlider).toFixed(1)} F</span>
            </div>
            <input 
              type="range"
              min="0.70"
              max="1.0"
              step="0.01"
              value={cSlider}
              onChange={(e) => setCSlider(parseFloat(e.target.value))}
              style={{ width: '100%', cursor: 'pointer' }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600, marginBottom: '4px' }}>
              <span>ESR Multiplier: {(esrSlider * 100).toFixed(0)}%</span>
              <span className="font-mono">{(35.0 * esrSlider).toFixed(1)} mΩ</span>
            </div>
            <input 
              type="range"
              min="1.0"
              max="2.5"
              step="0.05"
              value={esrSlider}
              onChange={(e) => setEsrSlider(parseFloat(e.target.value))}
              style={{ width: '100%', cursor: 'pointer' }}
            />
          </div>

          <button
            onClick={() => onInjectDegradation(cSlider, esrSlider)}
            style={{
              padding: '8px 16px',
              background: 'var(--color-warning)',
              color: '#000',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.82rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            Apply Degradation Stress
          </button>
        </div>
      </div>
    </div>
  );
};
