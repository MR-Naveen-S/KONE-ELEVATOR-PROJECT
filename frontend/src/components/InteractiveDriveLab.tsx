import React, { useEffect, useRef, useState } from 'react';

interface InteractiveDriveLabProps {
  onTelemetryUpdate?: (telemetry: any) => void;
}

export const InteractiveDriveLab: React.FC<InteractiveDriveLabProps> = ({ onTelemetryUpdate }) => {
  // Simulator configuration parameters matching simulator defaults
  const [stage, setStage] = useState<number>(2);
  const [mode, setMode] = useState<string>('alt');
  const [paused, setPaused] = useState<boolean>(false);

  // Sliders state
  const [load, setLoad] = useState<number>(800);
  const [H, setH] = useState<number>(30);
  const [vmax, setVmax] = useState<number>(2.0);
  const [acc, setAcc] = useState<number>(1.0);
  const [rbr, setRbr] = useState<number>(20);
  const [vbr, setVbr] = useState<number>(600);
  const [csc, setCsc] = useState<number>(15);
  const [vscm, setVscm] = useState<number>(200);
  const [ilim, setIlim] = useState<number>(100);
  const [vref, setVref] = useState<number>(560);
  const [simSpeed, setSimSpeed] = useState<number>(1.0);

  // Ref holders for DOM elements
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const canvasRefs = useRef<(HTMLCanvasElement | null)[]>([]);

  // Simulation physics state stored in ref for high-fps requestAnimationFrame loop
  const simState = useRef({
    fr: 0,
    v: 0,
    s: 0,
    af: 0,
    dir: 1,
    ph: 'dwell',
    tm: 1,
    th: 0,
    ang: 0,
    Vdc: 540,
    Vsc: 0.65 * 200,
    brk: 0,
    a1: 0,
    a2: 0,
    E: { g: 0, m: 0, rg: 0, br: 0, si: 0, so: 0 },
    o: {
      vup: 0,
      F: 0,
      Pm: 0,
      Pe: 0,
      Pi: 0,
      Ir: 0,
      Ii: 0,
      Ib: 0,
      Isd: 0,
      Is: 0,
      Ps: 0,
      iq: 0,
      fe: 0,
      m: 0,
      V: 540,
      vph: 0,
    },
    buffers: {} as Record<string, number[]>,
    flowOffsets: [0, 0, 0, 0, 0, 0, 0, 0],
    lastTs: 0,
    lastTelemetryTs: 0,
  });

  const paramsRef = useRef({
    stage: 2,
    mode: 'alt',
    load: 800,
    H: 30,
    vmax: 2.0,
    acc: 1.0,
    rbr: 20,
    vbr: 600,
    csc: 15,
    vscm: 200,
    ilim: 100,
    vref: 560,
    speed: 1.0,
    paused: false,
  });

  // Keep paramsRef in sync with state
  useEffect(() => {
    paramsRef.current = {
      stage,
      mode,
      load,
      H,
      vmax,
      acc,
      rbr,
      vbr,
      csc,
      vscm,
      ilim,
      vref,
      speed: simSpeed,
      paused,
    };
  }, [stage, mode, load, H, vmax, acc, rbr, vbr, csc, vscm, ilim, vref, simSpeed, paused]);

  // Waveform Scope definitions
  const SCOPES = [
    { title: 'Speed m/s (+up) · rope force kN', series: [{ k: 'v', c: '#60a5fa', l: 'speed' }, { k: 'F', c: '#fbbf24', l: 'force' }], zero: true },
    { title: 'Power kW (+ = toward load / charging)', series: [{ k: 'pm', c: '#60a5fa', l: 'shaft' }, { k: 'pg', c: '#fbbf24', l: 'grid' }, { k: 'pb', c: '#f87171', l: 'brake' }, { k: 'ps', c: '#4ade80', l: 'SC' }], zero: true },
    { title: 'DC-link voltage V', series: [{ k: 'vdc', c: '#60a5fa', l: 'Vdc' }], zero: false },
    { title: 'Supercap: V and I (A, + charging)', series: [{ k: 'vsc', c: '#4ade80', l: 'Vsc' }, { k: 'isc', c: '#fbbf24', l: 'Isc' }], zero: false },
    { title: 'DC-side currents A', series: [{ k: 'ir', c: '#fbbf24', l: 'rectifier' }, { k: 'ii', c: '#60a5fa', l: 'inverter' }, { k: 'ibr', c: '#f87171', l: 'brake' }, { k: 'isd', c: '#4ade80', l: 'to DC-DC' }], zero: true },
    { title: 'Phase currents A (last 0.8 s)', series: [{ k: 'ca', c: '#60a5fa', l: 'ia' }, { k: 'cb', c: '#4ade80', l: 'ib' }, { k: 'cc', c: '#a78bfa', l: 'ic' }], zero: true },
    { title: 'Phase voltages V (last 0.8 s)', series: [{ k: 'wa', c: '#60a5fa', l: 'va' }, { k: 'wb', c: '#4ade80', l: 'vb' }, { k: 'wc', c: '#a78bfa', l: 'vc' }], zero: true },
  ];

  const resetSim = () => {
    const P = paramsRef.current;
    const S = simState.current;
    S.fr = P.mode === 'down' ? 1 : 0;
    S.v = 0;
    S.s = 0;
    S.af = 0;
    S.dir = P.mode === 'down' ? -1 : 1;
    S.ph = 'dwell';
    S.tm = 1;
    S.th = 0;
    S.ang = 0;
    S.Vdc = 540;
    S.Vsc = 0.65 * P.vscm;
    S.brk = 0;
    S.a1 = 0;
    S.a2 = 0;
    S.E = { g: 0, m: 0, rg: 0, br: 0, si: 0, so: 0 };
    S.o = { vup: 0, F: 0, Pm: 0, Pe: 0, Pi: 0, Ir: 0, Ii: 0, Ib: 0, Isd: 0, Is: 0, Ps: 0, iq: 0, fe: 0, m: 0, V: 540, vph: 0 };

    // Clear buffers
    const b: Record<string, number[]> = {};
    ['v', 'F', 'pm', 'pg', 'pb', 'ps', 'vdc', 'vsc', 'isc', 'ir', 'ii', 'ibr', 'isd', 'ca', 'cb', 'cc', 'wa', 'wb', 'wc'].forEach((k) => {
      b[k] = [];
    });
    S.buffers = b;
  };

  useEffect(() => {
    resetSim();
  }, [mode, stage]);

  useEffect(() => {
    let animId: number;
    const DT = 2.5e-4; // 250 microsecond discrete physics step
    const push = (k: string, v: number) => {
      const a = simState.current.buffers[k];
      if (a) {
        a.push(v);
        if (a.length > 800) a.shift();
      }
    };

    const step = (dt: number) => {
      const S = simState.current;
      const P = paramsRef.current;
      const g = 9.81,
        r = 0.3,
        pp = 12,
        lam = 2.5,
        R = 0.5,
        Ld = 0.02,
        mcw = 1400;
      let aup = 0,
        vup = 0,
        F = 0;

      if (S.ph === 'dwell') {
        S.tm -= dt;
        if (S.tm <= 0) {
          S.ph = 'move';
          S.s = 0;
          S.fr = S.dir > 0 ? 0 : 1;
        }
      } else {
        const d = P.H - S.s;
        const vt = Math.max(0.03, Math.min(P.vmax, Math.sqrt(1.6 * P.acc * Math.max(d, 0))));
        const ar = Math.max(-P.acc, Math.min(P.acc, (vt - S.v) / 0.15));
        S.af += ((ar - S.af) * dt) / 0.25;
        S.v = Math.max(0, S.v + S.af * dt);
        S.s += S.v * dt;
        if (S.s >= P.H - 0.005) {
          S.ph = 'dwell';
          S.tm = 3;
          S.v = 0;
          S.af = 0;
          S.fr = S.dir > 0 ? 1 : 0;
          if (P.mode === 'alt') S.dir *= -1;
        } else {
          S.fr = S.dir > 0 ? S.s / P.H : 1 - S.s / P.H;
        }
      }

      if (S.ph === 'move') {
        aup = S.dir * S.af;
        vup = S.dir * S.v;
        const m = 1000 + P.load;
        F = (m - mcw) * g + (m + mcw + 300) * aup + 300 * Math.tanh(vup / 0.05);
      }

      const T = F * r,
        wm = vup / r,
        we = pp * wm;
      const iq = T / (1.5 * pp * lam);
      const vq = R * iq + we * lam;
      const vd = -we * Ld * iq;
      S.th += we * dt;
      S.ang += wm * dt;

      const Pm = F * vup;
      const Pe = 1.5 * vq * iq;
      const Pi = Pe >= 0 ? Pe / 0.97 : Pe * 0.97;
      const V = Math.max(S.Vdc, 50);
      const Ii = Pi / V;
      const Ir = Math.max(0, (540 - S.Vdc) / 0.4);

      if (S.Vdc > P.vbr) S.brk = 1;
      else if (S.Vdc < P.vbr - 15) S.brk = 0;
      const Ib = S.brk ? S.Vdc / P.rbr : 0;

      let Ps = 0,
        Pc = 0,
        Is = 0;
      S.Vsc = Math.min(S.Vsc, P.vscm);

      if (P.stage === 2) {
        const vm = P.vscm,
          Pl = P.ilim * S.Vsc;
        const cl = (x: number) => Math.max(0, Math.min(1, x));
        let p = 2000 * (S.Vdc - P.vref);
        p *= p > 0 ? cl((vm - S.Vsc) / (0.03 * vm)) : cl((S.Vsc - 0.5 * vm) / (0.03 * vm));
        Pc = p > 0 ? p * 0.97 : p / 0.97;
        Pc = Math.max(-Pl, Math.min(Pl, Pc));
        Ps = Pc > 0 ? Pc / 0.97 : Pc * 0.97;
        S.Vsc = Math.sqrt(Math.max(1, S.Vsc * S.Vsc + (2 * Pc * dt) / P.csc));
        Is = Pc / S.Vsc;
      }

      const Isd = Ps / V;
      S.Vdc += (dt * (Ir - Ii - Ib - Isd)) / 4.7e-3;

      const E = S.E;
      E.g += Ir * V * dt;
      E.m += Math.max(Pi, 0) * dt;
      E.rg += Math.max(-Pi, 0) * dt;
      E.br += Ib * V * dt;
      E.si += Math.max(Ps, 0) * dt;
      E.so += Math.max(-Ps, 0) * dt;

      const q = 2.0944,
        th = S.th,
        pv = (a: number) => vq * Math.sin(a) + vd * Math.cos(a);
      S.o = {
        vup,
        F,
        Pm,
        Pe,
        Pi,
        Ir,
        Ii,
        Ib,
        Isd,
        Is,
        Ps,
        iq,
        fe: we / 6.2832,
        m: Math.hypot(vq, vd) / (V / 1.732),
        V,
        vph: Math.hypot(vq, vd),
      };

      // Scope buffer sampling
      S.a1 += dt;
      if (S.a1 >= 0.001) {
        S.a1 -= 0.001;
        push('ca', iq * Math.sin(th));
        push('cb', iq * Math.sin(th - q));
        push('cc', iq * Math.sin(th + q));
        push('wa', pv(th));
        push('wb', pv(th - q));
        push('wc', pv(th + q));
      }

      S.a2 += dt;
      if (S.a2 >= 0.05) {
        S.a2 -= 0.05;
        push('v', vup);
        push('F', F / 1000);
        push('pm', Pm / 1000);
        push('pg', (Ir * V) / 1000);
        push('pb', (Ib * V) / 1000);
        push('ps', Ps / 1000);
        push('vdc', S.Vdc);
        push('vsc', S.Vsc);
        push('isc', Is);
        push('ir', Ir);
        push('ii', Ii);
        push('ibr', Ib);
        push('isd', Isd);
      }
    };

    // Canvas Oscilloscope Renderer
    const renderScope = (
      cv: HTMLCanvasElement,
      series: { k: string; c: string; l: string }[],
      title: string,
      zero: boolean,
      lines: { y: number; c: string }[] = []
    ) => {
      const x = cv.getContext('2d');
      if (!x) return;
      const W = cv.width,
        H = cv.height;
      x.clearRect(0, 0, W, H);

      let lo = 1e9,
        hi = -1e9;
      series.forEach((s) => {
        const buf = simState.current.buffers[s.k] || [];
        buf.forEach((v) => {
          if (v < lo) lo = v;
          if (v > hi) hi = v;
        });
      });

      if (zero) {
        lo = Math.min(lo, 0);
        hi = Math.max(hi, 0);
      }
      lines.forEach((l) => {
        lo = Math.min(lo, l.y);
        hi = Math.max(hi, l.y);
      });

      if (!isFinite(lo)) {
        lo = 0;
        hi = 1;
      }
      if (hi - lo < 1e-6) {
        hi += 1;
        lo -= 1;
      }
      const pd = (hi - lo) * 0.08;
      lo -= pd;
      hi += pd;

      const ml = 46,
        mt = 34,
        mb = 6,
        pw = W - ml - 8,
        ph = H - mt - mb;
      const Y = (v: number) => mt + ph * (1 - (v - lo) / (hi - lo));

      x.font = '11px -apple-system, system-ui, sans-serif';
      x.lineWidth = 1;

      // Grid lines
      for (let i = 0; i <= 4; i++) {
        const v = lo + ((hi - lo) * i) / 4;
        const y = Y(v);
        x.strokeStyle = '#272b35';
        x.beginPath();
        x.moveTo(ml, y);
        x.lineTo(W - 8, y);
        x.stroke();
        x.fillStyle = '#6b7280';
        x.fillText(v.toFixed(hi - lo < 10 ? 1 : 0), 4, y + 4);
      }

      // Zero axis line
      if (lo < 0 && hi > 0) {
        x.strokeStyle = '#4b5563';
        x.beginPath();
        x.moveTo(ml, Y(0));
        x.lineTo(W - 8, Y(0));
        x.stroke();
      }

      // Threshold lines
      lines.forEach((l) => {
        x.strokeStyle = l.c;
        x.setLineDash([5, 4]);
        x.beginPath();
        x.moveTo(ml, Y(l.y));
        x.lineTo(W - 8, Y(l.y));
        x.stroke();
        x.setLineDash([]);
      });

      // Scope Title
      x.fillStyle = '#f3f4f6';
      x.font = 'bold 12px -apple-system, system-ui, sans-serif';
      x.fillText(title, 8, 15);

      // Data series
      x.font = '11px -apple-system, system-ui, sans-serif';
      let lx = 8;
      series.forEach((s) => {
        const d = simState.current.buffers[s.k] || [];
        x.strokeStyle = s.c;
        x.lineWidth = 1.6;
        x.beginPath();
        d.forEach((v, i) => {
          const px = ml + (pw * (i + 800 - d.length)) / 799;
          i ? x.lineTo(px, Y(v)) : x.moveTo(px, Y(v));
        });
        x.stroke();

        const latestVal = d.length ? d[d.length - 1].toFixed(1) : '0.0';
        const legendText = `${s.l} ${latestVal}`;
        x.fillStyle = s.c;
        x.fillText(legendText, lx, 28);
        lx += x.measureText(legendText).width + 14;
      });
    };

    // Helper for fast text updating
    const f1 = (v: number, n: number = 1) => (typeof v === 'number' && isFinite(v) ? v.toFixed(n) : '0.0');
    const setTxt = (id: string, text: string) => {
      const el = containerRef.current?.querySelector<HTMLElement | SVGElement>(`#${id}`);
      if (el) el.textContent = text;
    };

    // Master Render Loop
    const render = () => {
      const S = simState.current;
      const P = paramsRef.current;
      const o = S.o;
      const V = S.Vdc;
      const E = S.E;
      const w = (j: number) => f1(j / 3600, 1) + ' Wh';
      const vm = P.vscm;

      // 1. Animate Power Flow Paths
      const flows = [
        { v: o.Ir, fwdColor: '#3b82f6', revColor: '#10b981' },
        { v: o.Ir, fwdColor: '#3b82f6', revColor: '#10b981' },
        { v: o.Ii, fwdColor: '#3b82f6', revColor: '#10b981' },
        { v: o.Ib, fwdColor: '#ef4444', revColor: '#ef4444' },
        { v: o.Isd, fwdColor: '#10b981', revColor: '#3b82f6' },
        { v: o.Is, fwdColor: '#10b981', revColor: '#3b82f6' },
        { v: o.Pe / Math.max(o.V, 1), fwdColor: '#3b82f6', revColor: '#10b981' },
        { v: o.Pm / 200, fwdColor: '#3b82f6', revColor: '#10b981' },
      ];

      const svg = svgRef.current;
      if (svg) {
        const flowPaths = svg.querySelectorAll<SVGPathElement>('.fl-path');
        flows.forEach((fl, idx) => {
          const el = flowPaths[idx];
          if (!el) return;
          const a = Math.abs(fl.v);
          el.style.stroke = fl.v >= 0 ? fl.fwdColor : fl.revColor;
          el.style.strokeWidth = `${2 + Math.min(5, a / 12)}px`;
          el.style.opacity = a < 0.3 ? '0.1' : '1';
          S.flowOffsets[idx] -= Math.sign(fl.v) * (1 + Math.min(a, 60) / 8);
          el.setAttribute('stroke-dashoffset', S.flowOffsets[idx].toString());
        });

        // 2. Animate Elevator Cabin, Counterweight & Spinning Sheave
        const ct = 70 + (1 - S.fr) * 190;
        const cab = svg.querySelector('#cab');
        const cabm = svg.querySelector('#cabm');
        const cw = svg.querySelector('#cw');
        const r1 = svg.querySelector('#r1');
        const r2 = svg.querySelector('#r2');
        const tcw = svg.querySelector('#tcw');
        const sh = svg.querySelector('#sh');

        if (cab) cab.setAttribute('y', ct.toString());
        if (cw) cw.setAttribute('y', (70 + S.fr * 190).toString());
        if (r1) r1.setAttribute('y2', ct.toString());
        if (r2) r2.setAttribute('y2', (70 + S.fr * 190).toString());
        if (tcw) tcw.setAttribute('y', (96 + S.fr * 190).toString());

        const mh = (38 * P.load) / 1000;
        if (cabm) {
          cabm.setAttribute('y', (ct + 37 - mh).toString());
          cabm.setAttribute('height', mh.toString());
        }

        if (sh) {
          sh.setAttribute('transform', `rotate(${(S.ang * 57.3).toFixed(1)} 735 40)`);
        }

        // Brake chopper highlight
        const bk = svg.querySelector('#bk') as SVGElement;
        if (bk) {
          bk.style.stroke = S.brk ? '#ef4444' : '#334155';
          bk.style.strokeWidth = S.brk ? '3px' : '1.5px';
        }

        // Opacity for stage 2 supercapacitor components
        const op = P.stage === 2 ? '1' : '0.25';
        const scg = svg.querySelector('#scg') as SVGElement;
        const scl = svg.querySelector('#scl') as SVGElement;
        const scx = svg.querySelector('#scx') as SVGElement;
        if (scg) scg.style.opacity = op;
        if (scl) scl.style.opacity = op;
        if (scx) scx.style.opacity = op;
      }

      // 3. Update SVG Engineering Text Measurements in Real-Time
      setTxt('tIr', `Irect ${f1(o.Ir)} A`);
      setTxt('tPg', `Pgrid ${f1((o.Ir * o.V) / 1000)} kW`);
      setTxt('tVdc', `Vdc ${f1(V)} V`);
      setTxt('tIi', `Iinv ${f1(o.Ii)} A`);
      setTxt('tPi', `Pinv ${f1(o.Pi / 1000)} kW`);
      setTxt('tIb', `Ibr ${f1(o.Ib)} A · ${f1((o.Ib * o.V) / 1000)} kW`);
      setTxt('tBs', S.brk ? 'CHOPPER ON' : 'chopper off');
      const tBsEl = containerRef.current?.querySelector<SVGElement>('#tBs');
      if (tBsEl) {
        tBsEl.style.fill = S.brk ? '#f87171' : '#6b7280';
        tBsEl.style.fontWeight = S.brk ? '700' : '400';
      }

      setTxt('tIs', `Idc ${f1(o.Isd)} A`);
      setTxt('tD', `duty D≈${f1(S.Vsc / V, 2)}  ${o.Ps > 50 ? 'BUCK: charging' : o.Ps < -50 ? 'BOOST: discharging' : 'idle'}`);
      setTxt('tVs', `Vsc ${f1(S.Vsc)} V`);
      setTxt('tIc', `Isc ${f1(o.Is)} A (${f1((o.Is * S.Vsc) / 1000)} kW)`);

      setTxt('tIq', `iq ${f1(o.iq)} A pk`);
      setTxt('tFe', `fe ${f1(Math.abs(o.fe))} Hz · Vph ${f1(o.vph, 0)} V`);
      setTxt('tM', `mod. index ${f1(o.m, 2)}${o.m > 1 ? ' >1 !' : ''}`);
      const tMEl = containerRef.current?.querySelector<SVGElement>('#tM');
      if (tMEl) tMEl.style.fill = o.m > 1 ? '#ef4444' : '#94a3b8';

      setTxt('tV', `v ${f1(o.vup, 2)} m/s`);
      setTxt('tF', `F ${f1(o.F / 1000, 2)} kN`);
      setTxt('tPm', `Pshaft ${f1(o.Pm / 1000)} kW`);
      const statusText = o.Pm > 50 ? 'MOTORING' : o.Pm < -50 ? 'REGENERATING' : S.ph === 'dwell' ? 'standstill' : 'coasting';
      setTxt('tL', statusText);
      const tLEl = containerRef.current?.querySelector<SVGElement>('#tL');
      if (tLEl) tLEl.style.fill = o.Pm > 50 ? '#60a5fa' : o.Pm < -50 ? '#4ade80' : '#94a3b8';

      // 4. Update Real-Time Energy Counters (Wh)
      setTxt('kg', w(E.g));
      setTxt('km', w(E.m));
      setTxt('kr', w(E.rg));
      setTxt('kb', w(E.br));
      setTxt('ks', w(E.si));
      setTxt('ko', w(E.so));
      setTxt('kw', E.rg > 1 ? f1((E.br / E.rg) * 100, 0) + ' %' : '0 %');
      const socVal =
        P.stage === 2
          ? f1(Math.max(0, Math.min(100, ((S.Vsc ** 2 - (0.5 * vm) ** 2) / (vm ** 2 - (0.5 * vm) ** 2)) * 100)), 0) + ' %'
          : '-';
      setTxt('kq', socVal);

      // 5. Render 7 Canvas Oscilloscopes
      const thresholdLines = [
        [],
        [],
        [{ y: P.vbr, c: '#ef4444' }, { y: P.vref, c: '#10b981' }, { y: 540, c: '#6b7280' }],
        [{ y: P.vscm, c: '#ef4444' }, { y: 0.5 * P.vscm, c: '#ef4444' }],
        [],
        [],
        [],
      ];

      SCOPES.forEach((sc, i) => {
        const cv = canvasRefs.current[i];
        if (cv) {
          renderScope(cv, sc.series, sc.title, sc.zero, thresholdLines[i]);
        }
      });

      // 6. Throttled Callback to Parent (150ms) to sync top header / KPI cards
      const now = performance.now();
      if (onTelemetryUpdate && now - simState.current.lastTelemetryTs > 150) {
        simState.current.lastTelemetryTs = now;
        onTelemetryUpdate({
          time: Date.now(),
          trip_id: 1,
          lift_state: S.ph,
          direction: S.dir,
          floor: Math.round(1 + S.s / 3.5),
          position: S.s,
          velocity: o.vup,
          accel: S.af,
          car_load_kg: P.load,
          Vgrid: 400.0,
          Igrid: o.Ir,
          P_grid: (o.Ir * o.V) / 1000,
          Vdc: S.Vdc,
          Idc_rect: o.Ir,
          P_inv_dc: o.Pi / 1000,
          P_aux: 250.0,
          P_brake: (o.Ib * o.V) / 1000,
          brake_chopper_on: Boolean(S.brk),
          Vsc: S.Vsc,
          Isc: o.Is,
          P_sc_term: o.Ps / 1000,
          P_sc_bus: o.Ps / 1000,
          soc: Math.max(0, Math.min(1, (S.Vsc - 0.5 * P.vscm) / (0.5 * P.vscm))),
          dcdc_mode: o.Ps > 50 ? 'buck_charging' : o.Ps < -50 ? 'boost_discharging' : 'idle',
          duty: S.Vsc / o.V,
          SC_temp: 28.5,
          Te: (o.F * 0.3) / 12,
          motor_speed_rpm: (o.vup / 0.3) * (60 / (2 * Math.PI)),
          controller_mode: P.stage === 2 ? 'SUPERCAP_OPTIMIZED' : 'CONVENTIONAL_BRAKE_R',
          raw_action_W: o.Ps,
          approved_action_W: o.Ps,
          safety_clipped: false,
          data_quality_warning: false,
          bus_residual_pct: 0.15,
        });
      }
    };

    const frame = (ts: number) => {
      const fd = Math.min(0.033, (ts - simState.current.lastTs) / 1000 || 0.016);
      simState.current.lastTs = ts;

      if (!paramsRef.current.paused) {
        const n = Math.round((fd * paramsRef.current.speed) / DT);
        for (let i = 0; i < n; i++) {
          step(DT);
        }
      }

      render();
      animId = requestAnimationFrame(frame);
    };

    animId = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(animId);
  }, []);

  return (
    <div ref={containerRef} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Top Simulator Control Bar */}
      <div
        className="glass-card"
        style={{
          padding: '12px 18px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '10px',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={() => setStage(1)}
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              border: stage === 1 ? '1px solid #3b82f6' : '1px solid var(--border-color)',
              backgroundColor: stage === 1 ? '#2563eb' : 'var(--bg-secondary)',
              color: '#fff',
              fontSize: '0.78rem',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Stage 1 · Conventional (brake resistor)
          </button>
          <button
            onClick={() => setStage(2)}
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              border: stage === 2 ? '1px solid #10b981' : '1px solid var(--border-color)',
              backgroundColor: stage === 2 ? '#059669' : 'var(--bg-secondary)',
              color: '#fff',
              fontSize: '0.78rem',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Stage 2 · + Supercap via bidirectional DC-DC
          </button>

          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            style={{
              padding: '6px 10px',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              fontSize: '0.78rem',
              cursor: 'pointer',
            }}
          >
            <option value="alt">Trips: up / down alternate</option>
            <option value="up">Up only</option>
            <option value="down">Down only</option>
          </select>

          <button
            onClick={() => setPaused(!paused)}
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {paused ? 'Resume' : 'Pause'}
          </button>

          <button
            onClick={resetSim}
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Reset
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <span>Arrow direction = real current direction |</span>
          <span style={{ color: '#60a5fa', fontWeight: 600 }}>Blue: motoring</span>
          <span style={{ color: '#4ade80', fontWeight: 600 }}>Green: supercap charge/regen</span>
          <span style={{ color: '#f87171', fontWeight: 600 }}>Red: brake chopper</span>
        </div>
      </div>

      {/* Interactive Sliders Bar (Exact responsive layout) */}
      <div className="glass-card sliders-grid" style={{ padding: '12px 16px' }}>
        {[
          { key: 'load', label: 'Car load', min: 0, max: 1000, step: 50, val: load, set: setLoad, unit: 'kg' },
          { key: 'H', label: 'Travel height', min: 10, max: 60, step: 5, val: H, set: setH, unit: 'm' },
          { key: 'vmax', label: 'Max speed', min: 0.5, max: 4, step: 0.1, val: vmax, set: setVmax, unit: 'm/s' },
          { key: 'acc', label: 'Accel limit', min: 0.3, max: 1.5, step: 0.1, val: acc, set: setAcc, unit: 'm/s²' },
          { key: 'rbr', label: 'Brake resistor', min: 8, max: 80, step: 2, val: rbr, set: setRbr, unit: 'Ω' },
          { key: 'vbr', label: 'Chopper ON level', min: 580, max: 680, step: 5, val: vbr, set: setVbr, unit: 'V' },
          { key: 'csc', label: 'Supercap C', min: 2, max: 40, step: 1, val: csc, set: setCsc, unit: 'F' },
          { key: 'vscm', label: 'Supercap max V', min: 100, max: 300, step: 10, val: vscm, set: setVscm, unit: 'V' },
          { key: 'ilim', label: 'DC-DC current limit', min: 10, max: 200, step: 5, val: ilim, set: setIlim, unit: 'A' },
          { key: 'vref', label: 'DC-link set-point', min: 545, max: 590, step: 1, val: vref, set: setVref, unit: 'V' },
          { key: 'speed', label: 'Sim speed', min: 0.5, max: 10, step: 0.5, val: simSpeed, set: setSimSpeed, unit: '×' },
        ].map((s) => (
          <label key={s.key} style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
              <span>{s.label}:</span>
              <strong style={{ color: 'var(--text-primary)' }}>
                {s.val} {s.unit}
              </strong>
            </div>
            <input
              type="range"
              min={s.min}
              max={s.max}
              step={s.step}
              value={s.val}
              onChange={(e) => s.set(parseFloat(e.target.value))}
              style={{ width: '100%', cursor: 'pointer', height: '4px' }}
            />
          </label>
        ))}
      </div>

      {/* Interactive Animated SVG Schematic */}
      <div className="schematic-wrapper glass-card" style={{ padding: '12px' }}>
        <svg ref={svgRef} id="sch" viewBox="0 0 900 340" className="schematic-svg">
          {/* Static Wires */}
          <g>
            <path className="wire" d="M100,135 H130" stroke="#334155" strokeWidth="3" fill="none" />
            <path className="wire" d="M210,135 H240" stroke="#334155" strokeWidth="3" fill="none" />
            <path className="wire" d="M300,135 H350" stroke="#334155" strokeWidth="3" fill="none" />
            <path className="wire" d="M270,70 V50" stroke="#334155" strokeWidth="3" fill="none" />
            <path className="wire" d="M270,210 V232" stroke="#334155" strokeWidth="3" fill="none" />
            <path className="wire" d="M270,272 V294" stroke="#334155" strokeWidth="3" fill="none" />
            <path className="wire" d="M440,135 H482" stroke="#334155" strokeWidth="3" fill="none" />
            <path className="wire" d="M558,135 H640 V40 H711" stroke="#334155" strokeWidth="3" fill="none" />
          </g>

          {/* Animated Power Flow Dashed Lines */}
          <g>
            <path className="fl-path" d="M100,135 H130" stroke="#60a5fa" strokeWidth="3" strokeDasharray="9 7" fill="none" />
            <path className="fl-path" d="M210,135 H240" stroke="#60a5fa" strokeWidth="3" strokeDasharray="9 7" fill="none" />
            <path className="fl-path" d="M300,135 H350" stroke="#60a5fa" strokeWidth="3" strokeDasharray="9 7" fill="none" />
            <path className="fl-path" d="M270,70 V50" stroke="#f87171" strokeWidth="3" strokeDasharray="9 7" fill="none" />
            <path className="fl-path" d="M270,210 V232" stroke="#4ade80" strokeWidth="3" strokeDasharray="9 7" fill="none" />
            <path className="fl-path" d="M270,272 V294" stroke="#4ade80" strokeWidth="3" strokeDasharray="9 7" fill="none" />
            <path className="fl-path" d="M440,135 H482" stroke="#60a5fa" strokeWidth="3" strokeDasharray="9 7" fill="none" />
            <path className="fl-path" d="M558,135 H640 V40 H711" stroke="#60a5fa" strokeWidth="3" strokeDasharray="9 7" fill="none" />
          </g>

          {/* Component Blocks */}
          <g>
            <rect x="10" y="110" width="90" height="50" rx="6" fill="#131722" stroke="#334155" strokeWidth="1.5" />
            <rect x="130" y="110" width="80" height="50" rx="6" fill="#131722" stroke="#334155" strokeWidth="1.5" />
            <rect x="240" y="70" width="60" height="140" rx="6" fill="#131722" stroke="#334155" strokeWidth="1.5" />
            <rect id="bk" x="215" y="10" width="110" height="40" rx="6" fill="#131722" stroke="#334155" strokeWidth="1.5" />
            <rect x="350" y="105" width="90" height="60" rx="6" fill="#131722" stroke="#334155" strokeWidth="1.5" />
            <circle cx="520" cy="135" r="38" fill="#131722" stroke="#334155" strokeWidth="1.5" />

            <g id="scg">
              <rect x="215" y="232" width="110" height="40" rx="6" fill="#131722" stroke="#334155" strokeWidth="1.5" />
              <rect x="215" y="294" width="110" height="38" rx="6" fill="#131722" stroke="#334155" strokeWidth="1.5" />
            </g>
          </g>

          {/* Block Labels */}
          <g textAnchor="middle" fill="#f3f4f6" style={{ font: '12px -apple-system, system-ui, sans-serif' }}>
            <text x="55" y="131" fontWeight="600">3φ GRID</text>
            <text x="55" y="148" fill="#94a3b8" fontSize="11px">400 V</text>
            <text x="170" y="131" fontWeight="600">DIODE</text>
            <text x="170" y="148" fontSize="11px">RECTIFIER</text>

            <text x="270" y="118" fontWeight="600">DC LINK</text>
            <text x="270" y="136">C_dc</text>
            <text x="270" y="152" fill="#94a3b8" fontSize="11px">4.7 mF</text>

            <text x="270" y="27" fontWeight="600">BRAKE CHOPPER</text>
            <text x="270" y="43" fill="#94a3b8" fontSize="11px">+ R_brake</text>

            <text x="395" y="131" fontWeight="600">INVERTER</text>
            <text x="395" y="148" fill="#94a3b8" fontSize="11px">3φ VSI</text>

            <text x="520" y="131" fontWeight="600">PMSM</text>
            <text x="520" y="148" fill="#94a3b8" fontSize="11px">gearless</text>

            <g id="scl">
              <text x="270" y="248" fontWeight="600">BIDIR DC-DC</text>
              <text x="270" y="264" fill="#94a3b8" fontSize="11px">buck / boost</text>
              <text x="270" y="311" fontWeight="600">SUPERCAP</text>
              <text x="270" y="326" fill="#94a3b8" fontSize="11px">bank</text>
            </g>
          </g>

          {/* Real-Time Live Measurement Annotations (Dynamically updated via IDs) */}
          <g fill="#f3f4f6" style={{ font: '11px -apple-system, system-ui, sans-serif' }}>
            <text id="tIr" x="100" y="190" fill="#94a3b8">Irect 0.0 A</text>
            <text id="tPg" x="100" y="206" fill="#94a3b8">Pgrid 0.0 kW</text>

            <text id="tVdc" x="306" y="96" fontWeight="700" fill="#60a5fa" fontSize="13px">Vdc 560.0 V</text>
            <text id="tIi" x="355" y="190" fill="#94a3b8">Iinv 0.0 A</text>
            <text id="tPi" x="355" y="206" fill="#94a3b8">Pinv 0.0 kW</text>

            <text id="tIb" x="332" y="24" fill="#94a3b8">Ibr 0.0 A · 0.0 kW</text>
            <text id="tBs" x="332" y="40" fill="#6b7280" fontWeight="400">
              chopper off
            </text>

            <g id="scx">
              <text id="tIs" x="332" y="248" fill="#94a3b8">Idc 0.0 A</text>
              <text id="tD" x="332" y="264" fill="#94a3b8">duty D≈0.23 idle</text>
              <text id="tVs" x="332" y="308" fill="#4ade80" fontWeight="600">Vsc 130.0 V</text>
              <text id="tIc" x="332" y="324" fill="#94a3b8">Isc 0.0 A (0.0 kW)</text>
            </g>

            <text id="tIq" x="468" y="190" fill="#94a3b8">iq 0.0 A pk</text>
            <text id="tFe" x="468" y="206" fill="#94a3b8">fe 0.0 Hz · Vph 0 V</text>
            <text id="tM" x="468" y="222" fill="#94a3b8">mod. index 0.00</text>

            {/* Shaft motion readouts */}
            <text id="tV" x="800" y="110" fontWeight="600" fill="#60a5fa">v 0.00 m/s</text>
            <text id="tF" x="800" y="128" fill="#fbbf24">F 0.00 kN</text>
            <text id="tPm" x="800" y="146" fill="#94a3b8">Pshaft 0.0 kW</text>
            <text id="tL" x="800" y="164" fontWeight="700" fill="#94a3b8">
              standstill
            </text>
          </g>

          {/* Elevator Shaft Guide Lines */}
          <line x1="670" y1="70" x2="795" y2="70" stroke="#334155" strokeDasharray="3 3" />
          <line x1="670" y1="300" x2="795" y2="300" stroke="#334155" strokeDasharray="3 3" />
          <text x="640" y="74" fill="#6b7280" fontSize="11px">top</text>
          <text x="620" y="304" fill="#6b7280" fontSize="11px">bottom</text>

          {/* Elevator Cabin & Counterweight */}
          <line id="r1" x1="711" y1="40" x2="711" y2="70" stroke="#94a3b8" strokeWidth="2" />
          <line id="r2" x1="759" y1="40" x2="759" y2="70" stroke="#94a3b8" strokeWidth="2" />

          {/* Moving Elevator Cabin with passenger load box inside */}
          <rect id="cab" x="690" y="70" width="44" height="40" rx="4" fill="#131722" stroke="#3b82f6" strokeWidth="2" />
          <rect id="cabm" x="693" y="100" width="38" height="0" fill="#d97706" opacity="0.65" />

          {/* Moving Counterweight */}
          <rect id="cw" x="737" y="70" width="44" height="52" rx="4" fill="#131722" stroke="#64748b" strokeWidth="2" />
          <text id="tcw" x="745" y="96" fill="#94a3b8" fontSize="11px" fontWeight="600">CW</text>

          {/* Rotating Sheave */}
          <g id="sh">
            <circle cx="735" cy="40" r="24" fill="#131722" stroke="#f3f4f6" strokeWidth="2" />
            <line x1="735" y1="18" x2="735" y2="62" stroke="#f3f4f6" strokeWidth="1.5" />
            <line x1="713" y1="40" x2="757" y2="40" stroke="#f3f4f6" strokeWidth="1.5" />
          </g>
        </svg>
      </div>

      {/* Real-time Energy Counters Row (Exact Wh metrics with IDs) */}
      <div className="kpi-counters-grid">
        {[
          { id: 'kg', label: 'Grid energy drawn', color: '#60a5fa' },
          { id: 'km', label: 'Motoring (DC side)', color: '#3b82f6' },
          { id: 'kr', label: 'Regen into DC link', color: '#10b981' },
          { id: 'kb', label: 'Burnt in brake R', color: '#ef4444' },
          { id: 'ks', label: 'Into supercap', color: '#4ade80' },
          { id: 'ko', label: 'Out of supercap', color: '#38bdf8' },
          { id: 'kw', label: 'Regen wasted', color: '#f59e0b' },
          { id: 'kq', label: 'Supercap usable SOC', color: '#a855f7' },
        ].map((kp) => (
          <div
            key={kp.id}
            className="glass-card"
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--bg-secondary)',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{kp.label}</div>
            <strong
              id={kp.id}
              style={{
                display: 'block',
                fontSize: '1.05rem',
                color: kp.color,
                marginTop: '2px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              0.0 Wh
            </strong>
          </div>
        ))}
      </div>

      {/* 7 Real-Time Rolling Waveform Oscilloscopes (Responsive Grid) */}
      <div className="oscilloscope-grid">
        {SCOPES.map((sc, i) => (
          <div
            key={i}
            className="glass-card"
            style={{
              backgroundColor: '#0f141d',
              borderRadius: '8px',
              border: '1px solid #1f293d',
              overflow: 'hidden',
            }}
          >
            <canvas
              ref={(el) => {
                canvasRefs.current[i] = el;
              }}
              width={600}
              height={190}
              style={{ width: '100%', height: 'auto', display: 'block' }}
            />
          </div>
        ))}
      </div>
    </div>
  );
};
