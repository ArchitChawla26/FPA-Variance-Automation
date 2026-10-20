#!/usr/bin/env python3
"""FP&A variance engine.

Reads data/budget_actuals.csv + data/headcount.csv and produces:
- a full variance table (all closed line-months) with F/U direction logic
- anomaly flags from two independent layers, fixed ex ante:
    1) materiality: |var$| >= $25,000 AND |var%| >= 5%
    2) statistics: |z| >= 2 on var% vs. the line's own trailing 6 months
- labor driver decomposition (volume = headcount effect, rate = cost/head)
- a rolling reforecast for Oct-Dec 2026 (trailing-3-month var% run-rate)
- a backtest: reforecast made at Dec 2025 for Jan-Sep 2026 vs. actual,
  benchmarked against simply using the budget
- a detection scorecard against the planted events (ground truth)

Writes data/engine_output.json with every number the pack/report builders use,
so no figure in any deliverable is transcribed by hand.
"""
import json
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

MAT_DOLLARS = 25_000
MAT_PCT = 0.05
Z_MIN_HIST = 4
Z_WINDOW = 6
Z_THRESH = 2.0
Z_FLOOR = 0.03  # a statistically unusual but <3% variance is not actionable

df = pd.read_csv(os.path.join(DATA, "budget_actuals.csv"))
hc = pd.read_csv(os.path.join(DATA, "headcount.csv"))
events = json.load(open(os.path.join(DATA, "planted_events.json")))

closed = df[df["actual"].notna()].copy()
closed["var"] = closed["actual"] - closed["budget"]
closed["var_pct"] = closed["var"] / closed["budget"]
closed["fu"] = np.where(
    closed["kind"] == "revenue",
    np.where(closed["var"] >= 0, "F", "U"),
    np.where(closed["var"] <= 0, "F", "U"),
)

# ---- anomaly flags ----
def zscore_flags(g):
    g = g.sort_values("month").copy()
    z = [np.nan] * len(g)
    vp = g["var_pct"].to_numpy()
    for i in range(len(g)):
        hist = vp[max(0, i - Z_WINDOW):i]
        if len(hist) >= Z_MIN_HIST and np.std(hist, ddof=1) > 0:
            z[i] = (vp[i] - np.mean(hist)) / np.std(hist, ddof=1)
    g["z"] = z
    return g

closed = closed.groupby("line", group_keys=False).apply(zscore_flags)
closed["flag_material"] = (closed["var"].abs() >= MAT_DOLLARS) & (closed["var_pct"].abs() >= MAT_PCT)
closed["flag_z"] = (closed["z"].abs() >= Z_THRESH) & (closed["var_pct"].abs() >= Z_FLOOR)
closed["flagged"] = closed["flag_material"] | closed["flag_z"]
closed["tier"] = np.where(closed["flag_material"], "Alert",
                  np.where(closed["flag_z"], "Watch", ""))

# ---- detection scorecard vs planted ground truth ----
planted = set()
for e in events:
    for m in pd.period_range(e["start"], e["end"], freq="M"):
        planted.add((e["line"], str(m)))
closed["is_planted"] = [(l, m) in planted for l, m in zip(closed["line"], closed["month"])]
tp = closed[closed["is_planted"] & closed["flagged"]]
fp = closed[~closed["is_planted"] & closed["flagged"]]
fn = closed[closed["is_planted"] & ~closed["flagged"]]
score = {
    "planted_line_months": int(len(planted)),
    "caught": int(len(tp)),
    "missed": int(len(fn)),
    "false_positives": int(len(fp)),
    "flagged_total": int(closed["flagged"].sum()),
    "recall": round(len(tp) / len(planted), 3) if planted else None,
    "materiality_caught": int((closed["is_planted"] & closed["flag_material"]).sum()),
    "materiality_fp": int((~closed["is_planted"] & closed["flag_material"]).sum()),
    "z_caught": int((closed["is_planted"] & closed["flag_z"]).sum()),
    "z_fp": int((~closed["is_planted"] & closed["flag_z"]).sum()),
    "precision": round(len(tp) / closed["flagged"].sum(), 3) if closed["flagged"].sum() else None,
    "missed_detail": fn[["line", "month", "var", "var_pct"]].assign(
        var=lambda d: d["var"].round(0), var_pct=lambda d: (d["var_pct"] * 100).round(1)
    ).to_dict("records"),
    "false_positive_detail": fp[["line", "month", "var", "var_pct"]].assign(
        var=lambda d: d["var"].round(0), var_pct=lambda d: (d["var_pct"] * 100).round(1)
    ).to_dict("records"),
}

# ---- labor decomposition (exact: rates derived from $ and HC) ----
hc_closed = hc[hc["hc_actual"].notna()].merge(
    closed[["month", "line", "budget", "actual", "var"]], on=["month", "line"], how="inner")
hc_closed["rate_b"] = hc_closed["budget"] / hc_closed["hc_budget"]
hc_closed["rate_a"] = hc_closed["actual"] / hc_closed["hc_actual"]
hc_closed["vol_var"] = (hc_closed["hc_actual"] - hc_closed["hc_budget"]) * hc_closed["rate_b"]
hc_closed["rate_var"] = (hc_closed["rate_a"] - hc_closed["rate_b"]) * hc_closed["hc_actual"]
decomp_latest = hc_closed[hc_closed["month"] == "2026-09"][
    ["line", "hc_budget", "hc_actual", "rate_b", "rate_a", "vol_var", "rate_var", "var"]
].round(2).to_dict("records")

# ---- reforecast Oct-Dec 2026 (trailing-3-month var% run-rate, clipped) ----
def reforecast(asof_idx_months, target_months):
    out = {}
    for line, g in closed.groupby("line"):
        hist = g[g["month"].isin(asof_idx_months)].sort_values("month")
        run_rate = hist["var_pct"].median()
        run_rate = float(np.clip(run_rate, -0.15, 0.15))
        bud = df[(df["line"] == line) & (df["month"].isin(target_months))]
        out[line] = {r.month: round(r.budget * (1 + run_rate), 2) for r in bud.itertuples()}
    return out

fc = reforecast([str(m) for m in pd.period_range("2026-04", "2026-09", freq="M")], ["2026-10", "2026-11", "2026-12"])

# ---- backtest: reforecast at Dec 2025 for Jan-Sep 2026 ----
bt_fc = reforecast([str(m) for m in pd.period_range("2025-07", "2025-12", freq="M")],
                   [str(m) for m in pd.period_range("2026-01", "2026-09", freq="M")])
bt_rows = []
for line, months in bt_fc.items():
    for m, f in months.items():
        a = float(closed[(closed["line"] == line) & (closed["month"] == m)]["actual"].iloc[0])
        b = float(closed[(closed["line"] == line) & (closed["month"] == m)]["budget"].iloc[0])
        bt_rows.append({"line": line, "month": m, "forecast": f, "actual": a, "budget": b})
bt = pd.DataFrame(bt_rows)
bt["ape_fc"] = (bt["forecast"] - bt["actual"]).abs() / bt["actual"]
bt["ape_bud"] = (bt["budget"] - bt["actual"]).abs() / bt["actual"]
backtest = {
    "mape_forecast": round(float(bt["ape_fc"].mean()), 4),
    "mape_budget": round(float(bt["ape_bud"].mean()), 4),
    "by_line": bt.groupby("line").agg(
        mape_forecast=("ape_fc", "mean"), mape_budget=("ape_bud", "mean")
    ).round(4).reset_index().to_dict("records"),
}

# ---- headline numbers for Sep 2026 + FYTD ----
def block(months):
    d = closed[closed["month"].isin(months)]
    rev = d[d.kind == "revenue"][["budget", "actual"]].sum()
    cost = d[d.kind == "cost"][["budget", "actual"]].sum()
    return {
        "rev_budget": round(float(rev.budget), 2), "rev_actual": round(float(rev.actual), 2),
        "rev_var": round(float(rev.actual - rev.budget), 2),
        "cost_budget": round(float(cost.budget), 2), "cost_actual": round(float(cost.actual), 2),
        "cost_var": round(float(cost.actual - cost.budget), 2),
        "op_budget": round(float(rev.budget - cost.budget), 2),
        "op_actual": round(float(rev.actual - cost.actual), 2),
    }

sep = closed[closed["month"] == "2026-09"].sort_values("var")
sep_lines = sep[["line", "kind", "dept", "budget", "actual", "var", "var_pct", "fu",
                 "flag_material", "flag_z", "flagged", "z"]].assign(
    var_pct=lambda d: (d["var_pct"] * 100).round(2),
    z=lambda d: d["z"].round(2)).to_dict("records")
fytd_months = [str(m) for m in pd.period_range("2026-01", "2026-09", freq="M")]
fytd = closed[closed["month"].isin(fytd_months)].groupby(["line", "kind", "dept"], as_index=False)[
    ["budget", "actual"]].sum()
fytd["var"] = fytd["actual"] - fytd["budget"]

out = {
    "asof_month": "2026-09",
    "thresholds": {"materiality_dollars": MAT_DOLLARS, "materiality_pct": MAT_PCT,
                   "z_threshold": Z_THRESH, "z_window_months": Z_WINDOW, "z_floor_pct": Z_FLOOR,
                   "forecast_method": "trailing-6-month median var% run-rate, clipped at +/-15%"},
    "scorecard": score,
    "backtest": backtest,
    "headline_sep2026": block(["2026-09"]),
    "headline_fytd2026": block(fytd_months),
    "sep2026_lines": sep_lines,
    "fytd_lines": fytd.assign(var_pct=(fytd["var"] / fytd["budget"] * 100).round(2)).to_dict("records"),
    "decomp_sep2026": decomp_latest,
    "reforecast_q4_2026": fc,
    "anomaly_log": closed[closed["flagged"]].sort_values(["month", "line"])[
        ["month", "line", "kind", "tier", "budget", "actual", "var", "var_pct", "fu", "is_planted"]].assign(
        var_pct=lambda d: (d["var_pct"] * 100).round(2)).to_dict("records"),
}
with open(os.path.join(DATA, "engine_output.json"), "w") as f:
    json.dump(out, f, indent=2, default=str)
closed.to_csv(os.path.join(DATA, "variance_table.csv"), index=False)

print("detection: caught {}/{} planted line-months (recall {}), {} false positives, precision {}".format(
    score["caught"], score["planted_line_months"], score["recall"], score["false_positives"], score["precision"]))
if score["missed_detail"]:
    print("missed:", score["missed_detail"])
print("backtest MAPE: reforecast {:.1%} vs budget {:.1%}".format(backtest["mape_forecast"], backtest["mape_budget"]))
h = out["headline_sep2026"]
print("Sep-2026: revenue ${:,.0f} vs budget ${:,.0f} (var {:+,.0f}); costs ${:,.0f} vs ${:,.0f}; op result ${:,.0f} vs ${:,.0f}".format(
    h["rev_actual"], h["rev_budget"], h["rev_var"], h["cost_actual"], h["cost_budget"], h["op_actual"], h["op_budget"]))
print("flagged line-months total:", score["flagged_total"], "of", len(closed))
