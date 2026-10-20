# FP&A Variance Automation with Anomaly Detection

**By Archit Chawla — October 2026**

A working FP&A close process, built end to end: a Python variance engine that reviews every budget line every month, flags what matters, decomposes the drivers, and re-forecasts the year — feeding an Excel variance pack and a written monthly report.

The company is a modeled B2B SaaS business (~$30M FY2025 revenue plan; 12 P&L lines; Jan 2025 – Sep 2026 actuals). It is modeled rather than real so the detection layer can be scored honestly: six operating events were planted in the actuals as ground truth (a Q1 bookings miss, a Q2 engineering hiring freeze, a cloud usage overrun, a campaign overrun, a one-off legal cost, an above-plan exec hire). The workflow, thresholds, and pack structure are a real FP&A process.

## What it does

- **Variance engine** (`variance_engine.py`) — budget vs. actual for all 252 closed line-months, with correct favorable/unfavorable sign conventions (revenue and cost flip), by line and department.
- **Two-layer anomaly detection**, thresholds fixed before seeing results:
  - *Alert (materiality):* |variance| ≥ $25,000 **and** ≥ 5% of budget
  - *Watch (statistical):* |z| ≥ 2 on variance % vs. the line's own trailing 6 months, with a 3% actionability floor
- **Driver decomposition** — labor variances split exactly into volume (headcount vs. plan) and rate (cost per head); the two sum to the total.
- **Rolling reforecast** — trailing-6-month median variance run-rate applied to remaining budget, clipped at ±15%.
- **Deliverables** (`build_pack.py`) — `FPA_variance_pack.xlsx` (summary sheets run on live Excel formulas linked to the data grids; verified cell-for-cell against the engine) and `FPA_monthly_report.md`, the September 2026 close report.

## Results (all measured, none assumed)

- **Detection:** 10 of 11 planted event line-months caught (91% recall); 20 of 252 line-months flagged for review (8%); 10 false positives, all from the statistical layer — the materiality layer alone caught 9 with zero false alarms. The one miss (February 2026 subscription revenue, −4.7%) sat just under the materiality bar, inside a three-month event caught in its other two months.
- **Decomposition:** the Q2 freeze shows up as $284.8K of volume saving vs. $81.7K of rate in engineering labor YTD — a headcount decision, not cheaper engineers.
- **Forecast:** the reforecast backtests at 3.2% MAPE for Jan–Sep 2026 vs. 3.2% for holding budget — a tie overall. It beats budget on the stable run-rate lines and structurally cannot anticipate one-offs, which is what the anomaly layer is for.
- **September 2026 close:** revenue $3.329M vs. $3.332M plan; operating result −$270K vs. −$293K planned; no Alert-threshold breaches.

## Rerun

```bash
python3 generate_data.py     # rebuilds the modeled dataset (fixed seed, deterministic)
python3 variance_engine.py   # variances, flags, decomposition, reforecast, scorecard
python3 build_pack.py        # Excel pack + monthly report
```

## Limitations

- Modeled data: magnitudes are realistic for a growth-stage SaaS P&L but are not a real company's financials.
- The statistical layer trades precision for recall by design; an FP&A analyst still reviews every flag.
- Decomposition is exact for labor (headcount data exists) and directional for non-labor lines.
