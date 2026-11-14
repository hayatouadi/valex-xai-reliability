"""Compare VALEX runs across months, model families and seeds.

Usage: python compare_runs.py <outputs_dir> [<study3_outputs_dir>]
Reads every */valex_report.json under <outputs_dir> (and ch7_*/ch7_report.json under the
optional study-3 outputs dir) and writes runs_comparison.csv, ch7_comparison.csv and
runs_comparison.md in <outputs_dir>. With several seeds of the same month and model, it also
reports mean ± SD of F, S and C (score uncertainty).
"""
import json
import sys
from pathlib import Path

import pandas as pd

out = Path(sys.argv[1])
rows = []
for rep in sorted(out.glob("*/valex_report.json")):
    r = json.loads(rep.read_text(encoding="utf-8"))
    src = Path(r["data"]["source"]).name
    month = src.replace("A", "").split(".")[0]
    for m, reg in r["registry"].items():
        rows.append({
            "run": rep.parent.name, "month": f"{month[:4]}-{month[4:6]}", "model": r["model"].get("family", "xgb"),
            "seed": reg.get("model_version", "").split("seed")[-1], "test_r2": r["model"]["test_r2"],
            "method": m, "F": reg.get("F"), "S": reg.get("S"), "C_raw": reg.get("C"), "C_tie": reg.get("C_tie_aware"),
            "L_p95_ms": reg.get("L_p95_ms"), "M_kb": reg.get("M_kb"),
            "status": reg.get("status") or ("S Not Evaluable" if reg.get("S_status") == "Not Evaluable" else "evaluated"),
            "n_validated_V": len(r["level3"]["validated_set"]),
            "selected_P2_tie": r.get("routing_tie_aware_C", {}).get("P2_interactive", {}).get("selected"),
        })
df = pd.DataFrame(rows)
df.to_csv(out / "runs_comparison.csv", index=False)

md = ["# VALEX runs comparison", ""]
if not df.empty:
    piv = df.pivot_table(index=["month", "model", "seed"], columns="method", values=["F", "S", "C_tie"], aggfunc="first")
    md += ["## Scores by run", "", piv.round(3).to_markdown(), ""]
    multi = df.groupby(["month", "model", "method"]).filter(lambda g: g["seed"].nunique() > 1)
    if not multi.empty:
        agg = multi.groupby(["month", "model", "method"])[["F", "S", "C_tie", "L_p95_ms"]].agg(["mean", "std"])
        md += ["## Uncertainty across seeds (mean, SD)", "", agg.round(3).to_markdown(), ""]

if len(sys.argv) > 2:
    crow = []
    for rep in sorted(Path(sys.argv[2]).glob("ch7_*/ch7_report.json")):
        r = json.loads(rep.read_text(encoding="utf-8"))
        a = r["level3_alignment"]
        crow.append({"run": rep.parent.name, "cells": r["flow"]["after_exact_strata"], "strata": r["flow"]["n_strata"],
                     "ATT": r["att_matching"]["estimate"], "CI_cal_lo": r["placebo"]["att_ci95_placebo_calibrated"][0],
                     "CI_cal_hi": r["placebo"]["att_ci95_placebo_calibrated"][1], "placebo_p": r["placebo"]["two_sided_placebo_p"],
                     "max_SMD": r["balance"]["max_abs_smd_matched"], "E_value": r["e_value_point"],
                     "model_ATT": a["model_implied_att"], "verdict": a["verdict"]})
    cdf = pd.DataFrame(crow)
    cdf.to_csv(out / "ch7_comparison.csv", index=False)
    md += ["## Referral exposure (Chapter 7B) by run", "", cdf.round(3).to_markdown(index=False), ""]

(out / "runs_comparison.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
