#!/usr/bin/env python3
"""Generate the modeled SaaS company dataset for the FP&A variance project.

Company: a fictional growth-stage B2B SaaS business ("the Company"), modeled
the way an FP&A team structures a plan: monthly budget vs. actuals by line,
Jan 2025 - Sep 2026 (21 closed months), plus budget-only Oct - Dec 2026.

Design rules (documented so nothing is presented as real company data):
- Budget is a smooth plan: revenue grows monthly, costs follow hiring plans.
- Actuals = budget x (1 + noise) with small per-line noise, EXCEPT six planted
  operating events (ground truth saved to planted_events.json) that a real
  FP&A review should catch: a cloud overrun, a hiring freeze, a campaign
  overrun, a bookings miss, a one-off legal cost, an exec hire above plan.
- Labor lines also carry budget/actual headcount so the engine can split
  labor variances into rate (cost per head) vs. volume (heads) drivers.

Deterministic: fixed seed, reruns produce identical files.
"""
import json
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

rng = np.random.default_rng(42)

MONTHS = pd.period_range("2025-01", "2026-09", freq="M")
BUDGET_MONTHS = pd.period_range("2025-01", "2026-12", freq="M")

# line -> (kind, dept, base monthly budget Jan-2025, monthly growth, noise sd)
# kind: revenue | cost. Labor lines get headcount below.
LINES = {
    "Subscription Revenue":    ("revenue", "Revenue", 2_050_000, 0.021, 0.012),
    "Services Revenue":        ("revenue", "Revenue",   185_000, 0.010, 0.030),
    "Cloud Hosting":           ("cost",    "COGS",      385_000, 0.023, 0.020),
    "Support Labor":           ("cost",    "COGS",      268_000, 0.012, 0.015),
    "Engineering Labor":       ("cost",    "R&D",       742_000, 0.014, 0.015),
    "Software & Tools":        ("cost",    "R&D",        96_000, 0.012, 0.025),
    "Sales & Marketing Labor": ("cost",    "S&M",       512_000, 0.016, 0.015),
    "Marketing Programs":      ("cost",    "S&M",       148_000, 0.008, 0.030),
    "Customer Success Labor":  ("cost",    "CS",        196_000, 0.013, 0.015),
    "G&A Labor":               ("cost",    "G&A",       238_000, 0.010, 0.015),
    "Legal & Professional":    ("cost",    "G&A",        54_000, 0.004, 0.040),
    "Facilities & Other":      ("cost",    "G&A",        88_000, 0.005, 0.020),
}

# labor line -> (starting headcount, monthly HC growth, avg fully-loaded $/head/month)
LABOR = {
    "Support Labor":           (34, 0.012, 268_000 / 34),
    "Engineering Labor":       (86, 0.014, 742_000 / 86),
    "Sales & Marketing Labor": (57, 0.016, 512_000 / 57),
    "Customer Success Labor":  (26, 0.013, 196_000 / 26),
    "G&A Labor":               (24, 0.010, 238_000 / 24),
}

# Planted events: (line, start, end, multiplicative effect, description)
EVENTS = [
    ("Cloud Hosting",           "2026-03", "2026-03", 1.35,
     "Cloud usage overrun: unplanned data-pipeline workload ran for a full month before cost alerts fired."),
    ("Engineering Labor",       "2026-04", "2026-06", 0.88,
     "Hiring freeze: engineering requisitions paused for one quarter, headcount ran below plan."),
    ("Marketing Programs",      "2025-09", "2025-10", 1.28,
     "Campaign overrun: a paid demand-gen campaign was extended two months past its approved budget."),
    ("Subscription Revenue",    "2026-01", "2026-03", 0.94,
     "Bookings miss: enterprise deals slipped a quarter, subscription revenue ran below plan."),
    ("Legal & Professional",    "2026-05", "2026-05", None,  # additive, set below
     "One-off legal cost: outside counsel for a contract dispute, not in plan."),
    ("G&A Labor",               "2026-08", "2026-08", 1.09,
     "Exec hire above plan: a VP hire closed at a higher package than budgeted."),
]
LEGAL_SPIKE = 160_000  # additive dollars for the Legal event

rows = []
for line, (kind, dept, base, growth, sd) in LINES.items():
    for i, m in enumerate(BUDGET_MONTHS):
        budget = base * (1 + growth) ** i
        rec = {"month": str(m), "line": line, "kind": kind, "dept": dept,
               "budget": round(budget, 2), "actual": np.nan}
        if m in MONTHS:
            noise = rng.normal(0, sd)
            actual = budget * (1 + noise)
            for eline, start, end, mult, _desc in EVENTS:
                if eline == line and start <= str(m) <= end:
                    actual = actual + LEGAL_SPIKE if mult is None else actual * mult
            rec["actual"] = round(actual, 2)
        rows.append(rec)

df = pd.DataFrame(rows)
df.to_csv(os.path.join(DATA, "budget_actuals.csv"), index=False)

# Headcount for labor lines: budget path smooth; actual follows budget except
# where a planted event moves hiring (freeze = fewer heads; exec hire = +1 VP
# at an above-plan package is a rate effect, so HC stays on plan for G&A).
hc_rows = []
for line, (hc0, hc_g, _avg) in LABOR.items():
    for i, m in enumerate(BUDGET_MONTHS):
        hc_budget = hc0 * (1 + hc_g) ** i
        hc_actual = np.nan
        if m in MONTHS:
            hc_actual = hc_budget + rng.normal(0, 0.6)
            if line == "Engineering Labor" and "2026-04" <= str(m) <= "2026-06":
                hc_actual = hc_budget * 0.90  # freeze: 10% fewer heads
            hc_actual = max(1.0, round(hc_actual, 1))
        hc_rows.append({"month": str(m), "line": line,
                        "hc_budget": round(hc_budget, 1), "hc_actual": hc_actual})
pd.DataFrame(hc_rows).to_csv(os.path.join(DATA, "headcount.csv"), index=False)

events_out = [
    {"line": l, "start": s, "end": e, "effect": ("+160000 USD" if mult is None else f"x{mult}"),
     "description": d}
    for (l, s, e, mult, d) in EVENTS
]
with open(os.path.join(DATA, "planted_events.json"), "w") as f:
    json.dump(events_out, f, indent=2)

closed = df[df["actual"].notna()]
print(f"lines: {df['line'].nunique()}  budget months: {len(BUDGET_MONTHS)}  closed months: {len(MONTHS)}")
print(f"closed rows: {len(closed)}  planted events: {len(events_out)}")
print(f"FY2025 budget revenue: ${df[(df.kind=='revenue') & (df.month<='2025-12')]['budget'].sum():,.0f}")
print(f"Latest month (2026-09) budget revenue: ${df[(df.kind=='revenue') & (df.month=='2026-09')]['budget'].sum():,.0f}")
print("wrote data/budget_actuals.csv, data/headcount.csv, data/planted_events.json")
