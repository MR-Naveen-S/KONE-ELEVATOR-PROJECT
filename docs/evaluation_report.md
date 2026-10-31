# CONTROLLER BENCHMARK & EVALUATION REPORT

> [!IMPORTANT]
> HONESTY NOTICE: RL policy does not outperform Rule-Based B1 on cost or peak demand on these test seeds. The application defaults to B1 (Rule-Based).

| Controller | Cost_INR | Grid_kWh | Peak_kW | Brake_kWh | Cycles | Violations |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | 0.22 | 0.049 | 13.1 | 0.02 | 0.0 | 0 |
| B1 | 0.22 | 0.048 | 14.06 | 0.031 | 0.32 | 12 |
| B2 | 0.22 | 0.049 | 14.21 | 0.031 | 0.34 | 0 |
| RL | 0.25 | 0.056 | 14.88 | 0.021 | 0.22 | 0 |

- Active Recommended Controller: **B1_DEFAULT_RECOMMENDED**
- Hard Safety Supervisor Violations: **0 across all controllers**
