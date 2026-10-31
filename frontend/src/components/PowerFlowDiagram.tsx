import React from 'react';
import { TelemetryState } from '../types';

interface PowerFlowDiagramProps {
  state: TelemetryState;
}

export const PowerFlowDiagram: React.FC<PowerFlowDiagramProps> = ({ state }) => {
  const P_grid_kW = Math.max(0, state.P_grid) / 1000.0;
  const P_inv_kW = state.P_inv_dc / 1000.0;
  const P_sc_bus_kW = state.P_sc_bus / 1000.0;
  const P_brake_kW = Math.max(0, state.P_brake) / 1000.0;

  const isGridFlowing = P_grid_kW > 0.05;
  const isMotoring = P_inv_kW > 0.05;
  const isRegen = P_inv_kW < -0.05;
  const isScDischarging = P_sc_bus_kW > 0.05;
  const isScCharging = P_sc_bus_kW < -0.05;
  const isBraking = P_brake_kW > 0.05;

  // Normalize car position in 30m shaft to SVG y-coordinates [80, 260]
  const shaftHeight = 180;
  const carY = 260 - (Math.max(0, Math.min(30, state.position)) / 30.0) * shaftHeight;
  const cwY = 80 + (Math.max(0, Math.min(30, state.position)) / 30.0) * shaftHeight;

  return (
    <div className="glass-card" style={{ padding: '20px', margin: '18px 0', overflowX: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Physical Drive System & Real-Time Power Flow
          </h2>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Blue: Motoring toward motor | Green: Regenerative energy captured in supercap | Red: Excess energy burnt in resistor
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className="badge badge-blue">Diode 400V</span>
          <span className="badge badge-green">Droop 560V</span>
          <span className="badge badge-rose">Chopper 600V</span>
        </div>
      </div>

      <svg 
        viewBox="0 0 1150 420" 
        style={{ width: '100%', minWidth: '950px', height: 'auto', display: 'block' }}
      >
        <defs>
          {/* Subtle Glow Filters */}
          <filter id="glow-blue" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="glow-green" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          <marker id="arrow-blue" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#38bdf8" />
          </marker>
          <marker id="arrow-green" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#10b981" />
          </marker>
          <marker id="arrow-red" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#f43f5e" />
          </marker>
        </defs>

        {/* ---------------- 1. GRID & RECTIFIER ---------------- */}
        <g id="block-grid">
          <rect x="20" y="160" width="110" height="90" rx="8" fill="var(--bg-secondary)" stroke="var(--border-color)" strokeWidth="2" />
          <text x="75" y="195" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="700">3φ AC GRID</text>
          <text x="75" y="215" textAnchor="middle" fill="var(--color-grid)" fontSize="11" fontWeight="600">400 V · 50 Hz</text>
          <text x="75" y="235" textAnchor="middle" fill="var(--text-muted)" fontSize="9">Utility Source</text>
        </g>

        {/* Wire: Grid -> Rectifier */}
        <line 
          x1="130" y1="205" x2="180" y2="205" 
          stroke={isGridFlowing ? "var(--color-grid)" : "var(--border-color)"} 
          strokeWidth={isGridFlowing ? 3 : 2} 
          className={isGridFlowing ? "animate-flow-blue" : ""}
          markerEnd={isGridFlowing ? "url(#arrow-blue)" : ""}
        />

        <g id="block-rectifier">
          <rect x="180" y="160" width="115" height="90" rx="8" fill="var(--bg-secondary)" stroke="var(--border-color)" strokeWidth="2" />
          <text x="237" y="195" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="700">DIODE RECTIFIER</text>
          <text x="237" y="215" textAnchor="middle" fill="var(--color-grid)" fontSize="11" fontWeight="600">{P_grid_kW.toFixed(1)} kW</text>
          <text x="237" y="235" textAnchor="middle" fill="var(--text-muted)" fontSize="9">I_rect: {state.Idc_rect.toFixed(1)} A</text>
        </g>

        {/* Wire: Rectifier -> DC Link */}
        <line 
          x1="295" y1="205" x2="360" y2="205" 
          stroke={isGridFlowing ? "var(--color-grid)" : "var(--border-color)"} 
          strokeWidth={isGridFlowing ? 3 : 2} 
          className={isGridFlowing ? "animate-flow-blue" : ""}
          markerEnd={isGridFlowing ? "url(#arrow-blue)" : ""}
        />

        {/* ---------------- 2. DC LINK (CENTRAL BUS) ---------------- */}
        <g id="block-dclink">
          <rect x="360" y="130" width="120" height="150" rx="10" fill="var(--bg-secondary)" stroke="var(--color-grid)" strokeWidth="2.5" />
          <text x="420" y="165" textAnchor="middle" fill="var(--color-grid)" fontSize="13" fontWeight="800">DC LINK BUS</text>
          <text x="420" y="195" textAnchor="middle" fill="var(--text-primary)" fontSize="18" fontWeight="800" fontFamily="var(--font-mono)">
            {state.Vdc.toFixed(1)} V
          </text>
          <text x="420" y="225" textAnchor="middle" fill="var(--text-muted)" fontSize="10">C_dc = 4.7 mF</text>
          <text x="420" y="250" textAnchor="middle" fill="var(--text-secondary)" fontSize="9">Set-point: 560 V</text>
        </g>

        {/* ---------------- 3. BRAKE CHOPPER (TOP PATH) ---------------- */}
        {/* Wire: DC Link -> Brake Chopper */}
        <line 
          x1="420" y1="130" x2="420" y2="75" 
          stroke={isBraking ? "var(--color-brake)" : "var(--border-color)"} 
          strokeWidth={isBraking ? 4 : 2} 
          className={isBraking ? "animate-flow-red" : ""}
          markerEnd={isBraking ? "url(#arrow-red)" : ""}
        />

        <g id="block-chopper">
          <rect x="350" y="15" width="140" height="60" rx="8" fill="var(--bg-secondary)" stroke={isBraking ? "var(--color-brake)" : "var(--border-color)"} strokeWidth="2" />
          <text x="420" y="38" textAnchor="middle" fill={isBraking ? "var(--color-brake)" : "var(--text-primary)"} fontSize="11" fontWeight="700">BRAKE CHOPPER</text>
          <text x="420" y="55" textAnchor="middle" fill="var(--text-muted)" fontSize="10">
            {isBraking ? `${P_brake_kW.toFixed(1)} kW (20 Ω ON)` : 'Chopper Off (ON ≥ 600V)'}
          </text>
        </g>

        {/* ---------------- 4. SUPERCAPACITOR & DC-DC (BOTTOM PATH) ---------------- */}
        {/* Wire: DC Link <-> DC-DC Converter */}
        <line 
          x1="420" y1="280" x2="420" y2="330" 
          stroke={isScCharging ? "var(--color-regen)" : (isScDischarging ? "var(--color-sc)" : "var(--border-color)")} 
          strokeWidth={Math.abs(P_sc_bus_kW) > 0.05 ? 3.5 : 2} 
          className={isScCharging ? "animate-flow-green" : (isScDischarging ? "animate-flow-blue" : "")}
        />

        <g id="block-dcdc">
          <rect x="350" y="330" width="140" height="75" rx="8" fill="var(--bg-secondary)" stroke="var(--border-color)" strokeWidth="2" />
          <text x="420" y="352" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="700">BIDIR DC-DC</text>
          <text x="420" y="372" textAnchor="middle" fill="var(--color-sc)" fontSize="11" fontWeight="600">
            {state.dcdc_mode.toUpperCase()} (D≈{state.duty.toFixed(2)})
          </text>
          <text x="420" y="392" textAnchor="middle" fill="var(--text-muted)" fontSize="9">
            I_lim = 100 A · η = 97%
          </text>
        </g>

        {/* Wire: DC-DC <-> Supercapacitor Bank */}
        <line 
          x1="350" y1="367" x2="280" y2="367" 
          stroke={isScCharging ? "var(--color-regen)" : (isScDischarging ? "var(--color-sc)" : "var(--border-color)")} 
          strokeWidth={Math.abs(P_sc_bus_kW) > 0.05 ? 3.5 : 2} 
          className={isScCharging ? "animate-flow-green" : (isScDischarging ? "animate-flow-blue" : "")}
        />

        <g id="block-supercap">
          <rect x="150" y="325" width="130" height="85" rx="8" fill="var(--bg-secondary)" stroke="var(--color-sc)" strokeWidth="2" />
          <text x="215" y="348" textAnchor="middle" fill="var(--color-sc)" fontSize="12" fontWeight="800">SUPERCAP BANK</text>
          <text x="215" y="372" textAnchor="middle" fill="var(--text-primary)" fontSize="15" fontWeight="800" fontFamily="var(--font-mono)">
            {state.Vsc.toFixed(1)} V ({(state.soc * 100).toFixed(0)}%)
          </text>
          <text x="215" y="392" textAnchor="middle" fill="var(--text-muted)" fontSize="9">
            15 F · 200 V max · {state.SC_temp.toFixed(1)} °C
          </text>
        </g>

        {/* ---------------- 5. THREE-PHASE INVERTER ---------------- */}
        {/* Wire: DC Link <-> Inverter */}
        <line 
          x1="480" y1="205" x2="560" y2="205" 
          stroke={isRegen ? "var(--color-regen)" : (isMotoring ? "var(--color-motoring)" : "var(--border-color)")} 
          strokeWidth={Math.abs(P_inv_kW) > 0.05 ? 4 : 2} 
          className={isRegen ? "animate-flow-green" : (isMotoring ? "animate-flow-blue" : "")}
          markerEnd={isRegen ? "" : (isMotoring ? "url(#arrow-blue)" : "")}
        />

        <g id="block-inverter">
          <rect x="560" y="160" width="115" height="90" rx="8" fill="var(--bg-secondary)" stroke="var(--border-color)" strokeWidth="2" />
          <text x="617" y="195" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="700">3φ INVERTER</text>
          <text x="617" y="215" textAnchor="middle" fill={isRegen ? "var(--color-regen)" : "var(--color-motoring)"} fontSize="12" fontWeight="700">
            {P_inv_kW.toFixed(1)} kW
          </text>
          <text x="617" y="235" textAnchor="middle" fill="var(--text-muted)" fontSize="9">
            I_inv: {(state.P_inv_dc / Math.max(state.Vdc, 1.0)).toFixed(1)} A
          </text>
        </g>

        {/* Wire: Inverter <-> PMSM */}
        <line 
          x1="675" y1="205" x2="745" y2="205" 
          stroke={isRegen ? "var(--color-regen)" : (isMotoring ? "var(--color-motoring)" : "var(--border-color)")} 
          strokeWidth={Math.abs(P_inv_kW) > 0.05 ? 3 : 2} 
          className={isRegen ? "animate-flow-green" : (isMotoring ? "animate-flow-blue" : "")}
        />

        {/* ---------------- 6. PMSM TRACTION MOTOR ---------------- */}
        <g id="block-pmsm">
          <circle cx="795" cy="205" r="50" fill="var(--bg-secondary)" stroke="var(--color-motoring)" strokeWidth="2.5" />
          <text x="795" y="198" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="800">PMSM</text>
          <text x="795" y="216" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">Gearless</text>
          <text x="795" y="232" textAnchor="middle" fill="var(--text-muted)" fontSize="9">
            {Math.abs(state.motor_speed_rpm).toFixed(0)} rpm
          </text>
        </g>

        {/* ---------------- 7. TRACTION SHEAVE & HOIST SHAFT ---------------- */}
        <g id="block-sheave">
          {/* Main Traction Pulley */}
          <circle cx="940" cy="80" r="30" fill="none" stroke="var(--text-secondary)" strokeWidth="3" />
          <circle cx="940" cy="80" r="6" fill="var(--text-muted)" />
          <text x="940" y="42" textAnchor="middle" fill="var(--text-secondary)" fontSize="10" fontWeight="600">Sheave r=0.3m</text>

          {/* Ropes */}
          {/* Left Rope down to Counterweight */}
          <line x1="910" y1="80" x2="910" y2={cwY} stroke="var(--text-muted)" strokeWidth="2.5" />
          {/* Right Rope down to Cabin */}
          <line x1="970" y1="80" x2="970" y2={carY} stroke="var(--text-muted)" strokeWidth="2.5" />

          {/* Counterweight Block (CW = car + 50% rated = 1400 kg) */}
          <g transform={`translate(890, ${cwY})`}>
            <rect x="0" y="0" width="40" height="55" rx="4" fill="#334155" stroke="var(--border-color)" strokeWidth="1.5" />
            <text x="20" y="25" textAnchor="middle" fill="#f8fafc" fontSize="10" fontWeight="700">CW</text>
            <text x="20" y="42" textAnchor="middle" fill="#94a3b8" fontSize="8">1400kg</text>
          </g>

          {/* Elevator Cabin Block (Car 1000kg + Load kg) */}
          <g transform={`translate(945, ${carY})`}>
            <rect x="0" y="0" width="50" height="65" rx="5" fill="#1e293b" stroke={isRegen ? "var(--color-regen)" : "var(--color-motoring)"} strokeWidth="2" />
            <text x="25" y="24" textAnchor="middle" fill="#f8fafc" fontSize="11" fontWeight="800">CAR</text>
            <text x="25" y="42" textAnchor="middle" fill="var(--color-grid)" fontSize="9" fontWeight="700">
              {state.car_load_kg.toFixed(0)} kg
            </text>
            <text x="25" y="56" textAnchor="middle" fill="var(--text-muted)" fontSize="8">
              Floor {state.floor}
            </text>
          </g>

          {/* Shaft guide rulers */}
          <line x1="1025" y1="75" x2="1025" y2="335" stroke="var(--border-color)" strokeWidth="1" strokeDasharray="3 3" />
          <text x="1035" y="85" fill="var(--text-muted)" fontSize="9">Top (30m)</text>
          <text x="1035" y="205" fill="var(--text-muted)" fontSize="9">15m</text>
          <text x="1035" y="335" fill="var(--text-muted)" fontSize="9">Bottom (0m)</text>
        </g>
      </svg>
    </div>
  );
};
