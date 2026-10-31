# Physical Formulas, Schemas, and Accounting Rules
**Regenerative Supercapacitor Elevator Energy Manager**
*Reference Documentation for Engineering and Maintenance Teams*

---

## 1. Sign Conventions & Signal Definitions (Section 3)

| Signal | Units | Sign Convention / Meaning |
| :--- | :--- | :--- |
| $P_{\text{inv\_dc}}$ | W | **DC Inverter Power**: $+ \text{ motoring}$ (power leaves DC link into motor), $- \text{ regenerating}$ (power feeds from motor back to DC link). |
| $P_{\text{sc\_bus}}$ | W | **DC-DC Bus Power**: $+ \text{ discharge}$ (power injected into DC bus from supercapacitor), $- \text{ charge}$ (power absorbed from DC bus into supercapacitor). |
| $P_{\text{sc\_term}}$ | W | **Supercapacitor Terminal Power**: $+ \text{ discharge}$, $- \text{ charge}$. Includes converter losses. |
| $P_{\text{grid}}$ | W | **Rectifier Output Power**: strictly $\ge 0$ (diode rectifier prohibits reverse grid feed-in / export). |
| $P_{\text{brake}}$ | W | **Dynamic Braking Chopper Power**: strictly $\ge 0$ (energy dissipated across $R_{\text{brake}}$ as heat). |
| $P_{\text{aux}}$ | W | **Elevator Auxiliary Load**: strictly $\ge 0$ (cabin ventilation, lighting, door actuators, safety controller). |
| $v$ | m/s | **Cabin Velocity**: $+ \text{ upward movement}$, $- \text{ downward movement}$. |
| $x$ | m | **Cabin Position**: $+ \text{ upward}$, relative to ground landing floor ($0 \text{ m}$). |
| $F$ | N | **Mechanical Rope Traction Force**: positive in the direction of cabin acceleration / lift. |

---

## 2. Mechanical Kinematics and Motor Power (Section 4)

### Traction Elevator Dynamics
For a car mass $m_{\text{car}}$, counterweight mass $m_{\text{cw}} = m_{\text{car}} + 0.5 \cdot m_{\text{rated}}$, and passenger car load $m_{\text{load}}$:

$$F = (m_{\text{car}} + m_{\text{load}} - m_{\text{cw}}) \cdot g + (m_{\text{car}} + m_{\text{load}} + m_{\text{cw}}) \cdot a + F_{\text{friction}} \cdot \text{sign}(v)$$

$$P_{\text{mech}} = F \cdot v$$

- When $P_{\text{mech}} > 0$: **Motoring**
- When $P_{\text{mech}} < 0$: **Regeneration**
- Balanced Load Check: At $m_{\text{load}} = 0.5 \cdot m_{\text{rated}}$, $m_{\text{car}} + m_{\text{load}} - m_{\text{cw}} = 0$. In steady-state cruising ($a = 0$), $F \approx F_{\text{fric}}$, meaning net mechanical regeneration is near zero.

### Electrical DC Bus Drive Coupling
$$P_{\text{inv\_dc}} = \begin{cases} \dfrac{P_{\text{mech}}}{\eta_{\text{motor}} \cdot \eta_{\text{inv}}}, & \text{if } P_{\text{mech}} \ge 0 \quad (\text{Motoring}) \\[10pt] P_{\text{mech}} \cdot \eta_{\text{motor}} \cdot \eta_{\text{inv}}, & \text{if } P_{\text{mech}} < 0 \quad (\text{Regeneration}) \end{cases}$$

---

## 3. DC Link Instantaneous Balance & Resistor Chopper

### Kirchhoff DC Bus Power Balance:
$$P_{\text{grid}} + P_{\text{sc\_bus}} = P_{\text{inv\_dc}} + P_{\text{aux}} + P_{\text{brake}} + \frac{d}{dt}\left(\frac{1}{2} C_{\text{dc}} V_{\text{dc}}^2\right)$$

### Chopper Dissipation:
When supercapacitor charging is limited or saturated, and $V_{\text{dc}} \ge V_{\text{chop\_on}} = 600\text{ V}$:
$$P_{\text{brake}} = \frac{V_{\text{dc}}^2}{R_{\text{brake}}} \quad \left(R_{\text{brake}} = 20\,\Omega\right)$$

---

## 4. Supercapacitor Bank Physics (Section 4)

### Energy & State of Charge (SoC):
$$E_{\text{total}} = \frac{1}{2} C_{\text{sc}} V_{\text{sc}}^2$$

$$E_{\text{usable}} = \frac{1}{2} C_{\text{sc}} \left(V_{\text{max}}^2 - V_{\text{min}}^2\right)$$

$$\text{SoC} = \frac{V_{\text{sc}}^2 - V_{\text{min}}^2}{V_{\text{max}}^2 - V_{\text{min}}^2} \times 100\%$$

*Hand-calculated benchmark check:*
For $C_{\text{sc}} = 15\text{ F}$, $V_{\text{min}} = 100\text{ V}$, $V_{\text{max}} = 200\text{ V}$:
$$E_{\text{usable}} = \frac{1}{2} \times 15 \times (200^2 - 100^2) = 7.5 \times 30{,}000 = 225{,}000\text{ Joules}$$
$$\frac{225{,}000\text{ J}}{3{,}600\text{ s/h}} = 62.50\text{ Watt-hours (Wh)}$$

### Converter Power & Losses:
$$I_{\text{sc}} = \frac{P_{\text{sc\_term}}}{V_{\text{sc}}}$$
$$P_{\text{loss\_ESR}} = I_{\text{sc}}^2 \cdot \text{ESR}$$
$$P_{\text{loss\_dcdc}} = |P_{\text{sc\_term}}| - |P_{\text{sc\_bus}}|$$

### Ideal Boost Converter Duty Cycle & Current Ripple:
$$D_{\text{boost}} = 1 - \frac{V_{\text{sc}}}{V_{\text{dc}}}$$
$$\Delta I = \frac{V_{\text{sc}} \cdot D_{\text{boost}}}{L \cdot f_{\text{sw}}}$$

### Maximum Theoretical Power at Efficiency $\eta$:
$$P_{\text{max}} = \eta(1 - \eta) \cdot \frac{V_{\text{sc}}^2}{\text{ESR}}$$

---

## 5. Energy Accounting & Validation Balance Checks (Section 9)

Energies are computed by integrating 1-second trapezoidal powers:
- **Grid Drawn**: $E_{\text{grid}} = \int P_{\text{grid}} \, dt$
- **Motoring DC Demand**: $E_{\text{motoring\_dc}} = \int \max(P_{\text{inv\_dc}}, 0) \, dt$
- **Gross Regeneration**: $E_{\text{regen\_gross}} = \int \max(-P_{\text{inv\_dc}}, 0) \, dt$
- **Captured into Supercap Path**: $E_{\text{captured\_bus}} = \int \max(-P_{\text{sc\_bus}}, 0) \, dt$
- **Burned in Dynamic Brake**: $E_{\text{brake}} = \int P_{\text{brake}} \, dt$
- **Discharged from Supercap**: $E_{\text{sc\_out}} = \int \max(P_{\text{sc\_bus}}, 0) \, dt$
- **Counterfactual Energy Saved**: $E_{\text{saved}} = E_{\text{grid\_baseline}} - E_{\text{grid\_actual}}$

### Automated Audit Check Gate:
Residual check computed per trip and per day:
$$\text{Residual}_{\text{regen}} = \frac{|E_{\text{regen\_gross}} - (E_{\text{captured\_bus}} + E_{\text{brake}} + \Delta E_{C_{\text{dc}}})|}{\max(E_{\text{regen\_gross}}, E_{\text{captured\_bus}} + E_{\text{brake}})}$$

> **Section 9 Mandatory Gate:** If $\text{Residual} > 1.5\%$, the record is flagged with `DATA_QUALITY_WARNING` and immediately exposed on the UI alerts log.

---

## 6. Supercapacitor Health & Diagnostics (Section 10)

### Online Capacitance Estimation:
Filtered over stable current segments where $|\Delta V| \ge 1.0\text{ V}$:
$$C_{\text{est}} = \frac{\int I_{\text{sc}} \, dt}{\Delta V_{\text{sc}}}$$

### Online ESR Estimation:
Computed at current step transients:
$$\text{ESR}_{\text{est}} = \frac{\Delta V_{\text{instant}}}{\Delta I_{\text{sc}}}$$

### State of Health (SOH):
$$\text{SOH}_C = \frac{C_{\text{est}}}{C_0} \times 100\% \qquad \text{SOH}_{\text{ESR}} = \frac{\text{ESR}_0}{\text{ESR}_{\text{est}}} \times 100\%$$
$$\text{SOH}_{\text{overall}} = \min(\text{SOH}_C, \text{SOH}_{\text{ESR}})$$
- **End-of-Life (EOL) Threshold**: $\text{SOH}_C \le 80\%$ or $\text{ESR}_{\text{est}} \ge 200\% \times \text{ESR}_0$.

### Thermal Model & Arrhenius Aging Acceleration:
$$T_{\text{sc}} = T_{\text{amb}} + R_{\text{th}} \cdot I_{\text{rms}}^2 \cdot \text{ESR}$$
$$\text{Aging Acceleration Factor } A_T = 2^{\frac{T_{\text{sc}} - T_{\text{ref}}}{10}}$$
RUL confidence interval is computed based on nominal vs high thermal stress envelopes.
