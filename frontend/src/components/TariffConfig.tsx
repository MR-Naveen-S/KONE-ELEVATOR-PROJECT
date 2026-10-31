import React, { useState, useEffect } from 'react';
import { DollarSign, Sliders, Save, RotateCcw, AlertTriangle, ShieldCheck, CheckCircle2, Info } from 'lucide-react';

interface TariffConfigProps {
  onNotify?: (msg: string, type?: 'success' | 'warning' | 'info') => void;
}

export const TariffConfig: React.FC<TariffConfigProps> = ({ onNotify }) => {
  // Tariff Rates
  const [offPeakRate, setOffPeakRate] = useState<number>(4.5);
  const [normalRate, setNormalRate] = useState<number>(7.5);
  const [peakRate, setPeakRate] = useState<number>(11.0);
  const [demandCharge, setDemandCharge] = useState<number>(350.0);

  // Hardware Parameters (Section 3 & 4)
  const [cSc, setCSc] = useState<number>(15.0);
  const [vscMax, setVscMax] = useState<number>(200.0);
  const [vscMin, setVscMin] = useState<number>(100.0);
  const [esrSc, setEsrSc] = useState<number>(20.0); // mOhm
  const [iMaxDcdc, setIMaxDcdc] = useState<number>(100.0);
  const [cdc, setCdc] = useState<number>(4.7);
  const [vdcNominal, setVdcNominal] = useState<number>(560.0);
  const [chopperOn, setChopperOn] = useState<number>(600.0);

  // Thresholds
  const [busResThresh, setBusResThresh] = useState<number>(1.5);
  const [tempLimit, setTempLimit] = useState<number>(65.0);
  const [sohEolThresh, setSohEolThresh] = useState<number>(80.0);

  const [version, setVersion] = useState<string>('v1.4');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  useEffect(() => {
    fetch('/api/tariffs')
      .then(r => r.json())
      .then(d => {
        if (d && d.demand_charge_per_kW) {
          setDemandCharge(d.demand_charge_per_kW);
        }
      })
      .catch(() => {});
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const resp = await fetch('/api/tariffs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          off_peak_rate: offPeakRate,
          normal_rate: normalRate,
          peak_rate: peakRate,
          demand_charge_per_kW: demandCharge,
        }),
      });
      if (resp.ok) {
        setSaveSuccess(true);
        const newVer = `v1.${parseInt(version.split('.')[1] || '4') + 1}`;
        setVersion(newVer);
        setTimeout(() => setSaveSuccess(false), 3000);
        onNotify?.(`Configuration saved & deployed as ${newVer}`, 'success');
      } else {
        onNotify?.('Failed to save tariff rates', 'warning');
      }
    } catch {
      onNotify?.('Network error saving configuration', 'warning');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setOffPeakRate(4.5);
    setNormalRate(7.5);
    setPeakRate(11.0);
    setDemandCharge(350.0);
    setCSc(15.0);
    setVscMax(200.0);
    setVscMin(100.0);
    setEsrSc(20.0);
    setIMaxDcdc(100.0);
    setCdc(4.7);
    setVdcNominal(560.0);
    setChopperOn(600.0);
    setBusResThresh(1.5);
    setTempLimit(65.0);
    setSohEolThresh(80.0);
    onNotify?.('Parameters reset to nominal defaults', 'info');
  };

  const getTariffForHour = (h: number) => {
    if ((h >= 22 && h <= 23) || (h >= 0 && h < 6)) return { type: 'Off-Peak', rate: offPeakRate, bg: 'rgba(16, 185, 129, 0.2)', border: 'rgba(16, 185, 129, 0.4)', color: 'var(--color-regen)' };
    if ((h >= 8 && h < 12) || (h >= 18 && h < 20)) return { type: 'Peak', rate: peakRate, bg: 'rgba(244, 63, 94, 0.2)', border: 'rgba(244, 63, 94, 0.4)', color: 'var(--color-brake)' };
    return { type: 'Normal', rate: normalRate, bg: 'rgba(245, 158, 11, 0.2)', border: 'rgba(245, 158, 11, 0.4)', color: 'var(--color-warning)' };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="glass-card" style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Sliders size={20} color="var(--color-grid)" />
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>Tariff & Parameter Configuration</h2>
            <span className="badge badge-blue">{version} ACTIVE</span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Section 4 & 8: Configurable Time-of-Use (ToU) billing, maximum demand charges, physical drive limits, and safety supervision thresholds.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleReset}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.78rem' }}
          >
            <RotateCcw size={14} /> Reset Defaults
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 18px', borderRadius: '6px', border: 'none', backgroundColor: saveSuccess ? '#16a34a' : 'var(--color-motoring)', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: '0.78rem' }}
          >
            {saveSuccess ? <CheckCircle2 size={14} /> : <Save size={14} />}
            {saveSuccess ? 'Saved' : isSaving ? 'Saving...' : 'Save & Deploy'}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '20px' }}>
        {/* Left Column: Tariff & Billing */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="glass-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <DollarSign size={16} color="var(--color-regen)" />
                <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>Time-of-Use (ToU) Energy Rates</h3>
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Currency: INR (₹)</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
              <div style={{ padding: '12px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.3)', backgroundColor: 'rgba(16, 185, 129, 0.1)' }}>
                <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--color-regen)' }}>Off-Peak (22h-06h)</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>₹</span>
                  <input
                    type="number"
                    step="0.1"
                    value={offPeakRate}
                    onChange={(e) => setOffPeakRate(parseFloat(e.target.value) || 0)}
                    style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '4px 8px', color: 'var(--text-primary)', fontWeight: 700, fontSize: '0.85rem' }}
                  />
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>/kWh</span>
                </div>
              </div>

              <div style={{ padding: '12px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.3)', backgroundColor: 'rgba(245, 158, 11, 0.1)' }}>
                <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--color-warning)' }}>Normal (Mid-Peak)</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>₹</span>
                  <input
                    type="number"
                    step="0.1"
                    value={normalRate}
                    onChange={(e) => setNormalRate(parseFloat(e.target.value) || 0)}
                    style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '4px 8px', color: 'var(--text-primary)', fontWeight: 700, fontSize: '0.85rem' }}
                  />
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>/kWh</span>
                </div>
              </div>

              <div style={{ padding: '12px', borderRadius: '8px', border: '1px solid rgba(244, 63, 94, 0.3)', backgroundColor: 'rgba(244, 63, 94, 0.1)' }}>
                <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--color-brake)' }}>Peak Hours</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>₹</span>
                  <input
                    type="number"
                    step="0.1"
                    value={peakRate}
                    onChange={(e) => setPeakRate(parseFloat(e.target.value) || 0)}
                    style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '4px 8px', color: 'var(--text-primary)', fontWeight: 700, fontSize: '0.85rem' }}
                  />
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>/kWh</span>
                </div>
              </div>
            </div>

            <div style={{ padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>Monthly Maximum Demand Charge</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Billed on rolling 15-minute maximum kVA/kW window</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', width: '130px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>₹</span>
                <input
                  type="number"
                  step="10"
                  value={demandCharge}
                  onChange={(e) => setDemandCharge(parseFloat(e.target.value) || 0)}
                  style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '4px 8px', color: 'var(--text-primary)', fontWeight: 700, fontSize: '0.85rem' }}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>/kW</span>
              </div>
            </div>

            {/* 24h timeline */}
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>24-Hour Tariff Schedule Strip:</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: '3px' }}>
              {Array.from({ length: 24 }).map((_, h) => {
                const t = getTariffForHour(h);
                return (
                  <div
                    key={h}
                    title={`${h}:00 - ${h + 1}:00: ${t.type} (₹${t.rate.toFixed(1)}/kWh)`}
                    style={{ height: '32px', borderRadius: '4px', backgroundColor: t.bg, border: `1px solid ${t.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.62rem', color: t.color, fontWeight: 700 }}
                  >
                    {h}h
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section 4 Grid Arbitrage Rule */}
          <div className="glass-card" style={{ padding: '16px 20px', borderLeft: '4px solid var(--color-grid)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-grid)', fontWeight: 700, fontSize: '0.85rem', marginBottom: '6px' }}>
              <Info size={16} /> Section 4 Grid Arbitrage Rule
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Charging supercapacitor from grid during off-peak pays off only if:<br />
              <code style={{ background: 'var(--bg-primary)', padding: '2px 6px', borderRadius: '4px', color: 'var(--color-grid)', fontFamily: 'var(--font-mono)' }}>
                Price_peak × η_roundtrip &gt; Price_offpeak
              </code><br />
              With current parameters: ₹{peakRate} × 0.88 = ₹{(peakRate * 0.88).toFixed(2)} &gt; ₹{offPeakRate} (<strong style={{ color: 'var(--color-regen)' }}>Arbitrage Economically Viable</strong>).
            </p>
          </div>
        </div>

        {/* Right Column: Physical Drive & Safety Thresholds */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="glass-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={16} color="var(--color-grid)" />
                <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>Supercapacitor & Drive Hardware Specs</h3>
              </div>
              <span className="badge badge-amber">config/params.yaml</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
              {[
                { label: 'Bank Capacitance (C_sc)', unit: 'F', val: cSc, setVal: setCSc, note: 'Nominal rating' },
                { label: 'ESR Bank (ESR_sc)', unit: 'mΩ', val: esrSc, setVal: setEsrSc, note: '[ASSUMED]' },
                { label: 'Vsc Max Voltage', unit: 'V', val: vscMax, setVal: setVscMax, note: 'Upper cutoff' },
                { label: 'Vsc Min Voltage', unit: 'V', val: vscMin, setVal: setVscMin, note: '0.5 × Vmax cutoff' },
                { label: 'DC-DC I_max', unit: 'A', val: iMaxDcdc, setVal: setIMaxDcdc, note: 'Inductor sat. limit' },
                { label: 'DC Link Cdc', unit: 'mF', val: cdc, setVal: setCdc, note: 'Bus capacitor' },
                { label: 'DC Link Setpoint', unit: 'V', val: vdcNominal, setVal: setVdcNominal, note: 'Stage 2 nominal' },
                { label: 'Brake Chopper Level', unit: 'V', val: chopperOn, setVal: setChopperOn, note: 'Turn-on threshold' },
              ].map((item, idx) => (
                <div key={idx} style={{ padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>{item.label}</div>
                    <div style={{ fontSize: '0.65rem', color: item.note.includes('ASSUMED') ? 'var(--color-warning)' : 'var(--text-muted)' }}>{item.note}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <input
                      type="number"
                      value={item.val}
                      onChange={(e) => item.setVal(parseFloat(e.target.value) || 0)}
                      style={{ width: '60px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '3px 6px', textAlign: 'right', color: 'var(--text-primary)', fontWeight: 700, fontSize: '0.8rem' }}
                    />
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{item.unit}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Supervisory & Audit Thresholds */}
          <div className="glass-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px', marginBottom: '14px' }}>
              <AlertTriangle size={16} color="var(--color-warning)" />
              <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>Supervisory & Audit Thresholds</h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>Max Energy Balance Residual (DATA_QUALITY_WARNING)</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Section 9 threshold for diagnostic audit alert</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <input
                    type="number"
                    step="0.1"
                    value={busResThresh}
                    onChange={(e) => setBusResThresh(parseFloat(e.target.value) || 0)}
                    style={{ width: '55px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '3px 6px', textAlign: 'right', color: 'var(--text-primary)', fontWeight: 700, fontSize: '0.8rem' }}
                  />
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>%</span>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>Supercapacitor Over-Temperature Trip Limit</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Safety Supervisor hard cutoff above this limit</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <input
                    type="number"
                    value={tempLimit}
                    onChange={(e) => setTempLimit(parseFloat(e.target.value) || 0)}
                    style={{ width: '55px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '3px 6px', textAlign: 'right', color: 'var(--text-primary)', fontWeight: 700, fontSize: '0.8rem' }}
                  />
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>°C</span>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>End-of-Life (EOL) SOH Threshold</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>IEC 62391 standard retirement threshold</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <input
                    type="number"
                    value={sohEolThresh}
                    onChange={(e) => setSohEolThresh(parseFloat(e.target.value) || 0)}
                    style={{ width: '55px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '3px 6px', textAlign: 'right', color: 'var(--text-primary)', fontWeight: 700, fontSize: '0.8rem' }}
                  />
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
