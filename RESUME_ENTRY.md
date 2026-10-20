# Resume entry — FP&A Variance Automation with Anomaly Detection

## Entry (Projects section)

FP&A Variance Automation with Anomaly Detection
Code: github.com/ArchitChawla26/FPA-Variance-Automation

- Built to demonstrate an FP&A close process end to end: a Python variance engine reviewing budget vs. actuals across 12 P&L lines and 21 months for a modeled B2B SaaS company, with favorable/unfavorable sign logic, labor rate-vs-volume driver decomposition, and a rolling reforecast
- Two-layer anomaly detection (materiality ≥$25K and ≥5%; statistical z-score vs. each line's own history) caught 10 of 11 planted operating events — a bookings miss, a hiring freeze, a cloud overrun — flagging just 8% of line-months for review; reforecast backtested at 3.2% MAPE
- Produces the artefacts an FP&A team circulates: a live-formula Excel variance pack and a written monthly close report with drivers, risks, and an updated outlook

## One-line version

FP&A variance automation: Python engine that flags material budget variances, decomposes labor drivers, and re-forecasts the year — validated against planted events (10/11 caught) with an Excel close pack and monthly report.
