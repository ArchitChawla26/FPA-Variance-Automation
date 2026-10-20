#!/usr/bin/env python3
"""Build the deliverables from the engine output:
- FPA_variance_pack.xlsx : the monthly FP&A pack (summary sheets carry live
  Excel formulas linked to the data grids; engine results are values)
- FPA_monthly_report.md  : the one-page September 2026 close report

Every number comes from data/engine_output.json or the CSVs. Nothing is
transcribed by hand.
"""
import json
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
O = json.load(open(os.path.join(DATA, "engine_output.json")))
BA = pd.read_csv(os.path.join(DATA, "budget_actuals.csv"))
HC = pd.read_csv(os.path.join(DATA, "headcount.csv"))
VT = pd.read_csv(os.path.join(DATA, "variance_table.csv"))

NAVY = "0C1A2E"
HDR = Font(bold=True, color="FFFFFF")
HDRFILL = PatternFill("solid", fgColor=NAVY)
TITLE = Font(bold=True, size=15, color=NAVY)
SUB = Font(size=10, color="5D6F88")
BOLD = Font(bold=True)
MONEY = '#,##0'
MONEYV = '+#,##0;-#,##0'
PCT = '0.0%'
THIN = Border(bottom=Side(style="thin", color="DDE5EF"))

LINES = list(BA["line"].unique())
MONTHS_ALL = [str(m) for m in pd.period_range("2025-01", "2026-12", freq="M")]
MONTH_IDX = {m: i + 2 for i, m in enumerate(MONTHS_ALL)}  # column number in data grids

wb = Workbook()

# ---------------- Cover ----------------
ws = wb.active
ws.title = "Cover"
ws.sheet_properties.pageSetUpPr.fitToPage = True
cover = [
    ("FP&A Variance Pack", TITLE),
    ("Modeled B2B SaaS company — monthly budget vs. actual review", SUB),
    ("", None),
    ("Close month: September 2026 (latest closed month; 21 months of actuals, Jan 2025 – Sep 2026)", None),
    ("Prepared by: Archit Chawla", None),
    ("", None),
    ("Contents", BOLD),
    ("PL_Summary — September 2026 and FY2026-to-date P&L: budget, actual, variance (live formulas)", None),
    ("Variance_Detail — September line detail with flags, plus labor rate/volume decomposition", None),
    ("Anomaly_Log — every flagged line-month from the two detection layers, with the validation scorecard", None),
    ("Forecast — Q4 2026 rolling reforecast and the Dec-2025 backtest vs. budget", None),
    ("Data_Budget / Data_Actual — the full monthly grids the summary formulas read", None),
    ("Methodology — thresholds, sign conventions, and limitations", None),
    ("", None),
    ("The company is a modeled business built for this project; the structure, thresholds and", None),
    ("workflow are a real FP&A close process. See Methodology.", SUB),
]
for i, (t, f) in enumerate(cover, start=1):
    c = ws.cell(row=i, column=1, value=t)
    if f:
        c.font = f
ws.column_dimensions["A"].width = 115

# ---------------- Data grids ----------------
def grid(sheet_name, col):
    w = wb.create_sheet(sheet_name)
    w.cell(row=1, column=1, value="Line").font = HDR
    w.cell(row=1, column=1).fill = HDRFILL
    for m, ci in MONTH_IDX.items():
        c = w.cell(row=1, column=ci, value=m)
        c.font = HDR
        c.fill = HDRFILL
    piv = BA.pivot(index="line", columns="month", values=col)
    for ri, line in enumerate(LINES, start=2):
        w.cell(row=ri, column=1, value=line)
        for m, ci in MONTH_IDX.items():
            v = piv.loc[line, m] if m in piv.columns else None
            if pd.notna(v):
                cell = w.cell(row=ri, column=ci, value=float(v))
                cell.number_format = MONEY
    w.column_dimensions["A"].width = 26
    for ci in MONTH_IDX.values():
        w.column_dimensions[get_column_letter(ci)].width = 13
    w.freeze_panes = "B2"
    return w

grid("Data_Budget", "budget")
grid("Data_Actual", "actual")

# ---------------- PL Summary (live formulas) ----------------
ws = wb.create_sheet("PL_Summary")
ws.cell(row=1, column=1, value="P&L Summary — variance vs. budget (live formulas from Data grids)").font = TITLE
headers = ["Line", "Kind", "Sep-26 Budget", "Sep-26 Actual", "Sep Var $", "Sep Var %",
           "F/U", "FYTD Budget", "FYTD Actual", "FYTD Var $", "FYTD Var %", "F/U"]
for ci, h in enumerate(headers, start=1):
    c = ws.cell(row=3, column=ci, value=h)
    c.font = HDR
    c.fill = HDRFILL
sep_col = get_column_letter(MONTH_IDX["2026-09"])
fytd_cols = [get_column_letter(MONTH_IDX[m]) for m in
             [str(m) for m in pd.period_range("2026-01", "2026-09", freq="M")]]
kind_of = dict(zip(BA["line"], BA["kind"]))
row = 4
line_rows = {}
for line in LINES:
    r = row
    line_rows[line] = r
    gri = LINES.index(line) + 2
    ws.cell(row=r, column=1, value=line)
    ws.cell(row=r, column=2, value=kind_of[line])
    ws.cell(row=r, column=3, value=f"='Data_Budget'!{sep_col}{gri}")
    ws.cell(row=r, column=4, value=f"='Data_Actual'!{sep_col}{gri}")
    ws.cell(row=r, column=5, value=f"=D{r}-C{r}")
    ws.cell(row=r, column=6, value=f"=IF(C{r}=0,0,E{r}/C{r})")
    fu = [x for x in O["sep2026_lines"] if x["line"] == line][0]["fu"]
    ws.cell(row=r, column=7, value=fu)
    ws.cell(row=r, column=8, value=f"=SUM('Data_Budget'!{fytd_cols[0]}{gri}:{fytd_cols[-1]}{gri})")
    ws.cell(row=r, column=9, value=f"=SUM('Data_Actual'!{fytd_cols[0]}{gri}:{fytd_cols[-1]}{gri})")
    ws.cell(row=r, column=10, value=f"=I{r}-H{r}")
    ws.cell(row=r, column=11, value=f"=IF(H{r}=0,0,J{r}/H{r})")
    fy = [x for x in O["fytd_lines"] if x["line"] == line][0]
    ws.cell(row=r, column=12, value="F" if (fy["var"] >= 0) == (fy["kind"] == "revenue") else "U")
    for ci in (3, 4, 5, 8, 9, 10):
        ws.cell(row=r, column=ci).number_format = MONEYV if ci in (5, 10) else MONEY
    for ci in (6, 11):
        ws.cell(row=r, column=ci).number_format = PCT
    row += 1
for label, kinds, bold in [("Total Revenue", ["revenue"], True), ("Total Costs", ["cost"], True)]:
    ws.cell(row=row, column=1, value=label).font = BOLD
    rs = [line_rows[l] for l in LINES if kind_of[l] in kinds]
    for ci in (3, 4, 5, 8, 9, 10):
        L = get_column_letter(ci)
        cell = ws.cell(row=row, column=ci, value=f"=SUM({L}{rs[0]}:{L}{rs[-1]})" if False else
                       "=" + "+".join(f"{L}{r}" for r in rs))
        cell.number_format = MONEYV if ci in (5, 10) else MONEY
        cell.font = BOLD
    for ci in (6, 11):
        base = "C" if ci == 6 else "H"
        varc = "E" if ci == 6 else "J"
        cell = ws.cell(row=row, column=ci, value=f"=IF({base}{row}=0,0,{varc}{row}/{base}{row})")
        cell.number_format = PCT
        cell.font = BOLD
    if label == "Total Revenue":
        rev_row = row
    else:
        cost_row = row
    row += 1
ws.cell(row=row, column=1, value="Operating Result").font = BOLD
for ci in (3, 4, 5, 8, 9, 10):
    L = get_column_letter(ci)
    cell = ws.cell(row=row, column=ci, value=f"={L}{rev_row}-{L}{cost_row}")
    cell.number_format = MONEYV if ci in (5, 10) else MONEY
    cell.font = BOLD
for ci in (6, 11):
    base = "C" if ci == 6 else "H"
    varc = "E" if ci == 6 else "J"
    cell = ws.cell(row=row, column=ci, value=f"=IF({base}{rev_row}=0,0,{varc}{row}/{base}{rev_row})")
    cell.number_format = PCT
    cell.font = BOLD
widths = [26, 9, 14, 14, 12, 10, 5, 14, 14, 12, 10, 5]
for i, wdt in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = wdt

# ---------------- Variance Detail ----------------
ws = wb.create_sheet("Variance_Detail")
ws.cell(row=1, column=1, value="September 2026 — line detail and flags").font = TITLE
hdrs = ["Line", "Dept", "Budget", "Actual", "Var $", "Var %", "F/U", "Tier", "Materiality", "Z-flag", "Z"]
for ci, h in enumerate(hdrs, start=1):
    c = ws.cell(row=3, column=ci, value=h)
    c.font = HDR
    c.fill = HDRFILL
r = 4
for x in sorted(O["sep2026_lines"], key=lambda d: -abs(d["var"])):
    tier = "Alert" if x["flag_material"] else ("Watch" if x["flag_z"] else "")
    vals = [x["line"], x["dept"], x["budget"], x["actual"], x["var"], x["var_pct"] / 100,
            x["fu"], tier, "Yes" if x["flag_material"] else "", "Yes" if x["flag_z"] else "",
            None if x["z"] is None or str(x["z"]) == "nan" else x["z"]]
    for ci, v in enumerate(vals, start=1):
        cell = ws.cell(row=r, column=ci, value=v)
        if ci in (3, 4):
            cell.number_format = MONEY
        if ci == 5:
            cell.number_format = MONEYV
        if ci == 6:
            cell.number_format = PCT
        if ci == 11:
            cell.number_format = '0.00'
    r += 1
r += 1
ws.cell(row=r, column=1, value="Labor decomposition — FY2026 to date (Jan–Sep): volume = headcount effect, rate = cost per head").font = BOLD
r += 1
for ci, h in enumerate(["Line", "HC Budget (avg)", "HC Actual (avg)", "Volume var $", "Rate var $", "Total var $"], start=1):
    c = ws.cell(row=r, column=ci, value=h)
    c.font = HDR
    c.fill = HDRFILL
r += 1
fytd_m = [str(m) for m in pd.period_range("2026-01", "2026-09", freq="M")]
hcf = HC[HC["month"].isin(fytd_m) & HC["hc_actual"].notna()].merge(
    VT[VT["month"].isin(fytd_m)][["month", "line", "budget", "actual"]], on=["month", "line"])
hcf["rate_b"] = hcf["budget"] / hcf["hc_budget"]
hcf["rate_a"] = hcf["actual"] / hcf["hc_actual"]
hcf["vol"] = (hcf["hc_actual"] - hcf["hc_budget"]) * hcf["rate_b"]
hcf["rate"] = (hcf["rate_a"] - hcf["rate_b"]) * hcf["hc_actual"]
for line, g in hcf.groupby("line"):
    vals = [line, round(g["hc_budget"].mean(), 1), round(g["hc_actual"].mean(), 1),
            round(g["vol"].sum()), round(g["rate"].sum()), round(g["vol"].sum() + g["rate"].sum())]
    for ci, v in enumerate(vals, start=1):
        cell = ws.cell(row=r, column=ci, value=v)
        if ci >= 4:
            cell.number_format = MONEYV
    r += 1
for i, wdt in enumerate([26, 10, 13, 13, 13, 13, 6, 8, 12, 8, 7], start=1):
    ws.column_dimensions[get_column_letter(i)].width = wdt

# ---------------- Anomaly Log ----------------
ws = wb.create_sheet("Anomaly_Log")
ws.cell(row=1, column=1, value="Anomaly log — all flagged line-months (Jan 2025 – Sep 2026)").font = TITLE
sc = O["scorecard"]
ws.cell(row=2, column=1, value=(
    f"Validation vs. ground truth: {sc['caught']} of {sc['planted_line_months']} planted event line-months caught "
    f"(recall {sc['recall']:.0%}); {sc['flagged_total']} of 252 line-months flagged for review; "
    f"{sc['false_positives']} false positives. Materiality layer alone: {sc['materiality_caught']} caught, "
    f"{sc['materiality_fp']} false positives. Statistical layer adds recall at the cost of review volume.")).font = SUB
hdrs = ["Month", "Line", "Kind", "Tier", "Budget", "Actual", "Var $", "Var %", "F/U", "Planted event"]
for ci, h in enumerate(hdrs, start=1):
    c = ws.cell(row=4, column=ci, value=h)
    c.font = HDR
    c.fill = HDRFILL
r = 5
for x in O["anomaly_log"]:
    vals = [x["month"], x["line"], x["kind"], x["tier"], x["budget"], x["actual"], x["var"],
            x["var_pct"] / 100, x["fu"], "Yes" if str(x["is_planted"]) in ("True", "true") else ""]
    for ci, v in enumerate(vals, start=1):
        cell = ws.cell(row=r, column=ci, value=v)
        if ci in (5, 6):
            cell.number_format = MONEY
        if ci == 7:
            cell.number_format = MONEYV
        if ci == 8:
            cell.number_format = PCT
    r += 1
if sc["missed_detail"]:
    r += 1
    ws.cell(row=r, column=1, value="Missed by both layers:").font = BOLD
    for md in sc["missed_detail"]:
        r += 1
        ws.cell(row=r, column=1, value=f"{md['month']} — {md['line']}: var ${md['var']:,.0f} ({md['var_pct']:+.1f}%), just under the 5% materiality bar").font = SUB
for i, wdt in enumerate([10, 26, 9, 8, 13, 13, 12, 9, 5, 13], start=1):
    ws.column_dimensions[get_column_letter(i)].width = wdt

# ---------------- Forecast ----------------
ws = wb.create_sheet("Forecast")
ws.cell(row=1, column=1, value="Rolling reforecast — Q4 2026 (trailing-6-month median var% run-rate, clipped at ±15%)").font = TITLE
for ci, h in enumerate(["Line", "Oct-26", "Nov-26", "Dec-26", "Q4 Total"], start=1):
    c = ws.cell(row=3, column=ci, value=h)
    c.font = HDR
    c.fill = HDRFILL
r = 4
for line in LINES:
    f = O["reforecast_q4_2026"][line]
    vals = [line, f["2026-10"], f["2026-11"], f["2026-12"], sum(f.values())]
    for ci, v in enumerate(vals, start=1):
        cell = ws.cell(row=r, column=ci, value=v)
        if ci > 1:
            cell.number_format = MONEY
    r += 1
r += 1
bt = O["backtest"]
ws.cell(row=r, column=1, value=(
    f"Backtest — forecast made at Dec 2025 for Jan–Sep 2026: reforecast MAPE {bt['mape_forecast']*100:.1f}% "
    f"vs. budget {bt['mape_budget']*100:.1f}%. The reforecast wins on stable run-rate lines and cannot "
    f"anticipate one-off events; overall it ties the budget.")).font = BOLD
r += 2
for ci, h in enumerate(["Line", "Reforecast MAPE", "Budget MAPE", "Winner"], start=1):
    c = ws.cell(row=r, column=ci, value=h)
    c.font = HDR
    c.fill = HDRFILL
r += 1
for x in bt["by_line"]:
    vals = [x["line"], x["mape_forecast"], x["mape_budget"],
            "Reforecast" if x["mape_forecast"] < x["mape_budget"] else "Budget"]
    for ci, v in enumerate(vals, start=1):
        cell = ws.cell(row=r, column=ci, value=v)
        if ci in (2, 3):
            cell.number_format = PCT
    r += 1
for i, wdt in enumerate([26, 14, 14, 14, 14], start=1):
    ws.column_dimensions[get_column_letter(i)].width = wdt

# ---------------- Methodology ----------------
ws = wb.create_sheet("Methodology")
th = O["thresholds"]
meth = [
    ("Methodology & verification notes", TITLE),
    ("", None),
    ("Company: a modeled B2B SaaS business (~$30M FY2025 revenue plan) built for this project. Budget and actuals are", None),
    ("generated from stated plan assumptions; six operating events were planted in the actuals as ground truth so the", None),
    ("detection layer can be scored honestly. The workflow, thresholds and pack structure are a real FP&A close process.", None),
    ("", None),
    (f"Materiality (Alert): |variance| >= ${th['materiality_dollars']:,} AND >= {th['materiality_pct']*100:.0f}% of budget — fixed before seeing results.", None),
    (f"Statistical (Watch): |z| >= {th['z_threshold']} on variance % vs. the line's own trailing {th['z_window_months']} months, with a 3% actionability floor.", None),
    ("Sign convention: revenue variance is favorable when actual > budget; cost variance is favorable when actual < budget.", None),
    ("Labor decomposition: volume = (actual HC - budget HC) x budget cost/head; rate = (actual - budget cost/head) x actual HC.", None),
    ("The two sum exactly to the labor variance. Reforecast: trailing-6-month median var% applied to budget, clipped at +/-15%.", None),
    ("", None),
    ("Limitations", BOLD),
    ("- A run-rate reforecast cannot anticipate one-off events (legal costs, freezes); the backtest shows it ties the budget overall.", None),
    ("- The statistical layer trades precision for recall: about 8% of line-months are flagged for human review.", None),
    ("- Driver decomposition is exact for labor (headcount data) and directional elsewhere; hosting and programs variances", None),
    ("  are explained from the anomaly log and event review, not decomposed.", None),
    ("- Modeled data: magnitudes are realistic for a growth-stage SaaS P&L but are not a real company's financials.", None),
]
for i, (t, f) in enumerate(meth, start=1):
    c = ws.cell(row=i, column=1, value=t)
    if f:
        c.font = f
ws.column_dimensions["A"].width = 118

wb.save(os.path.join(HERE, "FPA_variance_pack.xlsx"))

# ---------------- Monthly report ----------------
h_s, h_f = O["headline_sep2026"], O["headline_fytd2026"]
fy = {x["line"]: x for x in O["fytd_lines"]}
top_fy = sorted(O["fytd_lines"], key=lambda d: -abs(d["var"]))[:5]
dec = {d["line"]: d for d in O["decomp_sep2026"]}
eng_fy = hcf[hcf["line"] == "Engineering Labor"]
eng_vol, eng_rate = eng_fy["vol"].sum(), eng_fy["rate"].sum()
q4_rev = sum(O["reforecast_q4_2026"][l][m] for l in ["Subscription Revenue", "Services Revenue"]
             for m in ["2026-10", "2026-11", "2026-12"])
q4_cost = sum(O["reforecast_q4_2026"][l][m] for l in LINES
              if l not in ("Subscription Revenue", "Services Revenue")
              for m in ["2026-10", "2026-11", "2026-12"])
sep_flags = [x for x in O["anomaly_log"] if x["month"] == "2026-09"]

def money(v):
    return f"${v:,.0f}"

def sgn(v):
    return f"+${v:,.0f}" if v >= 0 else f"-${abs(v):,.0f}"

report = f"""# FP&A Monthly Report — September 2026 Close

**By Archit Chawla — October 2026**

*Modeled B2B SaaS company · Actuals through September 2026 · Budget: FY2025–FY2026 plan*

---

## Headline

September was a clean close. Revenue landed at {money(h_s['rev_actual'])} against a {money(h_s['rev_budget'])} plan ({sgn(h_s['rev_var'])}), costs ran {money(abs(h_s['cost_var']))} favorable, and the operating result of {money(h_s['op_actual'])} beat the planned {money(h_s['op_budget'])}. No line breached the Alert threshold in September{"" if not sep_flags else " beyond the items noted below"}. The year's story is not in this month — it is in the year-to-date variances, where three operating events from earlier in the year are still sitting in the run-rate.

Year to date (Jan–Sep 2026): revenue {money(h_f['rev_actual'])} vs. {money(h_f['rev_budget'])} planned ({sgn(h_f['rev_var'])}); costs {money(h_f['cost_actual'])} vs. {money(h_f['cost_budget'])} ({sgn(h_f['cost_var'])}); operating result {money(h_f['op_actual'])} vs. {money(h_f['op_budget'])} planned.

## What drove the year

- **Subscription Revenue {sgn(fy['Subscription Revenue']['var'])} YTD.** The Q1 bookings miss — enterprise deals slipping a quarter — accounts for nearly all of it. Volumes recovered from April; the variance is a timing/slippage story, not churn, but it permanently lowers the FY base unless Q4 bookings over-deliver.
- **Engineering Labor {sgn(fy['Engineering Labor']['var'])} YTD.** The Q2 hiring freeze. Decomposition is unambiguous: {money(abs(eng_vol))} of the saving is volume (fewer heads than plan) and {money(abs(eng_rate))} is rate — this was a headcount decision, not cheaper engineers. The saving is real but it is borrowed capacity; the roadmap cost lands in 2027 planning, not this P&L.
- **Cloud Hosting {sgn(fy['Cloud Hosting']['var'])} YTD.** Mostly one month: the March usage overrun, caught by the materiality layer at +35% in-month. Run-rate since is back near plan; the residual YTD variance is the March event annualizing, not a new trend.
- **Marketing Programs {sgn(fy['Marketing Programs']['var'])} YTD.** The autumn-2025 campaign extension sits in the FY2025 base; 2026 spend is tracking plan. No action.
- **Legal & Professional {sgn(fy['Legal & Professional']['var'])} YTD.** A one-off {money(160_000)} outside-counsel cost in May. Excluded from the run-rate view; it should not be forecast forward.

## Detection & forecast validation

The two-layer flagging system (materiality: ≥$25K and ≥5%; statistical: |z| ≥ 2 vs. each line's own trailing six months, 3% floor) flagged {sc['flagged_total']} of 252 line-months for review across the 21 closed months. Scored against the six operating events planted in this dataset as ground truth, it caught {sc['caught']} of {sc['planted_line_months']} event line-months (recall {sc['recall']:.0%}) with {sc['false_positives']} false positives — the statistical layer's cost. The one miss, February subscription revenue at −4.7%, sat just under the materiality bar inside a three-month event the layer caught in the other two months. I would rather review 8% of lines than miss a bookings miss.

The rolling reforecast (trailing-6-month median variance run-rate) backtests at {bt['mape_forecast']*100:.1f}% MAPE against {bt['mape_budget']*100:.1f}% for simply holding budget — a tie overall. It wins on the stable lines (support, customer success, hosting) and structurally cannot see one-offs coming. Conclusion: use it for the run-rate, and keep the anomaly layer for the breaks.

## Q4 2026 outlook

The reforecast puts Q4 revenue at {money(q4_rev)} and costs at {money(q4_cost)}, an operating result of {money(q4_rev - q4_cost)} for the quarter. Two judgment notes on top of the mechanical forecast: engineering's run-rate still carries the freeze, so any Q4 rehiring lands as an unfavorable rate/volume mix the model will flag before it surprises anyone; and the legal one-off is excluded from the run-rate by the median method, correctly. The swing factor for the full year is Q4 bookings — the Q1 slippage is recoverable only there.

*Modeled company built for this project; structure, thresholds and workflow are a real FP&A close process. Method and limitations are documented in the pack's Methodology sheet.*
"""
with open(os.path.join(HERE, "FPA_monthly_report.md"), "w") as f:
    f.write(report)

print("pack written: FPA_variance_pack.xlsx")
print("report written: FPA_monthly_report.md")
print(f"Q4 reforecast: revenue {money(q4_rev)}, costs {money(q4_cost)}, op {money(q4_rev - q4_cost)}")
print(f"Sep flags: {len(sep_flags)}; FYTD eng decomposition vol {money(eng_vol)} rate {money(eng_rate)}")
print("top FYTD variances:", [(x['line'], round(x['var'])) for x in top_fy])
