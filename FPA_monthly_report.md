# FP&A Monthly Report — September 2026 Close

**By Archit Chawla — October 2026**

*Modeled B2B SaaS company · Actuals through September 2026 · Budget: FY2025–FY2026 plan*

---

## Headline

September was a clean close. Revenue landed at $3,329,003 against a $3,332,216 plan (-$3,213), costs ran $26,484 favorable, and the operating result of $-269,915 beat the planned $-293,187. No line breached the Alert threshold in September. The year's story is not in this month — it is in the year-to-date variances, where three operating events from earlier in the year are still sitting in the run-rate.

Year to date (Jan–Sep 2026): revenue $27,265,476 vs. $27,718,176 planned (-$452,700); costs $30,818,456 vs. $30,825,360 (-$6,904); operating result $-3,552,980 vs. $-3,107,184 planned.

## What drove the year

- **Subscription Revenue -$460,064 YTD.** The Q1 bookings miss — enterprise deals slipping a quarter — accounts for nearly all of it. Volumes recovered from April; the variance is a timing/slippage story, not churn, but it permanently lowers the FY base unless Q4 bookings over-deliver.
- **Engineering Labor -$366,534 YTD.** The Q2 hiring freeze. Decomposition is unambiguous: $284,800 of the saving is volume (fewer heads than plan) and $81,735 is rate — this was a headcount decision, not cheaper engineers. The saving is real but it is borrowed capacity; the roadmap cost lands in 2027 planning, not this P&L.
- **Cloud Hosting +$166,023 YTD.** Mostly one month: the March usage overrun, caught by the materiality layer at +35% in-month. Run-rate since is back near plan; the residual YTD variance is the March event annualizing, not a new trend.
- **Marketing Programs -$1,182 YTD.** The autumn-2025 campaign extension sits in the FY2025 base; 2026 spend is tracking plan. No action.
- **Legal & Professional +$162,724 YTD.** A one-off $160,000 outside-counsel cost in May. Excluded from the run-rate view; it should not be forecast forward.

## Detection & forecast validation

The two-layer flagging system (materiality: ≥$25K and ≥5%; statistical: |z| ≥ 2 vs. each line's own trailing six months, 3% floor) flagged 20 of 252 line-months for review across the 21 closed months. Scored against the six operating events planted in this dataset as ground truth, it caught 10 of 11 event line-months (recall 91%) with 10 false positives — the statistical layer's cost. The one miss, February subscription revenue at −4.7%, sat just under the materiality bar inside a three-month event the layer caught in the other two months. I would rather review 8% of lines than miss a bookings miss.

The rolling reforecast (trailing-6-month median variance run-rate) backtests at 3.2% MAPE against 3.2% for simply holding budget — a tie overall. It wins on the stable lines (support, customer success, hosting) and structurally cannot see one-offs coming. Conclusion: use it for the run-rate, and keep the anomaly layer for the breaks.

## Q4 2026 outlook

The reforecast puts Q4 revenue at $10,397,968 and costs at $10,995,721, an operating result of $-597,752 for the quarter. Two judgment notes on top of the mechanical forecast: engineering's run-rate still carries the freeze, so any Q4 rehiring lands as an unfavorable rate/volume mix the model will flag before it surprises anyone; and the legal one-off is excluded from the run-rate by the median method, correctly. The swing factor for the full year is Q4 bookings — the Q1 slippage is recoverable only there.

*Modeled company built for this project; structure, thresholds and workflow are a real FP&A close process. Method and limitations are documented in the pack's Methodology sheet.*
