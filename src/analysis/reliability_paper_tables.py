"""Collect every number used in the reliability paper (Levels I and II) from the pipeline outputs.

Usage:  python code/reliability_paper_tables.py [outputs_dir]
Writes outputs/reliability_paper_tables.md and .json.
"""
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "results" / "valex"
RUNS = {
    "Jan 2023": "valex_unified_2023_01", "Jan 2024": "valex_unified_full", "Apr 2024": "valex_unified_2024_04",
    "Jul 2024": "valex_unified_2024_07", "Oct 2024": "valex_unified_2024_10", "Jan 2025": "valex_unified_2025_01",
    "Jan 2024 s1": "valex_xgb_2024_01_seed1", "Jan 2024 s2": "valex_xgb_2024_01_seed2",
    "Jan 2024 s3": "valex_xgb_2024_01_seed3", "Jan 2024 s4": "valex_xgb_2024_01_seed4",
    "MLP Jan 2024": "valex_mlp_2024_01", "Ridge Jan 2024": "valex_ridge_2024_01",
    "LEAKY Jan 2024": "valex_leaky_2024_01",
}


def load(folder):
    f = OUT / folder / "valex_report.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def summarise(r):
    l1, l2, pr = r["level1"]["methods"], r["level2"], r["profiling"]
    gi = r["global_importances"]
    feats = list(next(iter(gi.values())).keys())
    rows = {}
    for m in l1:
        s = l2.get(m, {})
        v = gi.get(m)
        tot = sum(abs(x) for x in v.values()) if v else 0
        top = sorted(v, key=lambda f: -abs(v[f]))[:3] if v else []
        rows[m] = {
            "F": l1[m].get("F"), "F_raw": l1[m].get("F_raw"),
            "d1": l1[m]["delta_method"]["1"], "d10": l1[m]["delta_method"]["10"],
            "rr10": (l1[m].get("remove_and_retrain_r2_drop") or {}).get("10"),
            "S": s.get("S_jaccard"), "S_sd": s.get("S_jaccard_sd"), "rho": s.get("spearman"),
            "S_status": s.get("status", "evaluated"),
            "L_med": pr.get(m, {}).get("latency_ms_median"), "L_p95": pr.get(m, {}).get("latency_ms_p95"),
            "M_kb": pr.get(m, {}).get("memory_kb_peak_median"),
            "top1_share": abs(v[top[0]]) / tot if tot else None, "top3": top,
        }
    agree = {}
    ms = [m for m in gi if gi[m]]
    for a, b in combinations(ms, 2):
        va = [gi[a][f] for f in feats]
        vb = [gi[b][f] for f in feats]
        ta = set(sorted(feats, key=lambda f: -abs(gi[a][f]))[:5])
        tb = set(sorted(feats, key=lambda f: -abs(gi[b][f]))[:5])
        agree[f"{a}-{b}"] = {"rho": float(spearmanr(va, vb).correlation), "J5": len(ta & tb) / len(ta | tb)}
    return {"r2": r["model"]["test_r2"], "rand": r["level1"]["methods"][next(iter(l1))]["delta_random"],
            "methods": rows, "agreement": agree}


res = {k: summarise(r) for k, v in RUNS.items() if (r := load(v))}
(OUT / "reliability_paper_tables.json").write_text(json.dumps(res, indent=1), encoding="utf-8")

lines = ["# Reliability paper — extracted numbers", ""]
for run, s in res.items():
    lines += [f"## {run} (test R2 = {s['r2']:.4f}; random d1/d10 = {s['rand']['1']:.3f}/{s['rand']['10']:.3f})", "",
              "| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, x in s["methods"].items():
        f = lambda v, d=3: "—" if v is None else f"{v:.{d}f}"
        lines.append(f"| {m} | {f(x['F'])} | {f(x['F_raw'])} | {f(x['d1'])} | {f(x['d10'])} | {f(x['rr10'])} | "
                     f"{f(x['S']) if x['S_status'] == 'evaluated' else 'NE'} | {f(x['S_sd'])} | {f(x['rho'])} | "
                     f"{f(x['L_med'], 1)} | {f(x['L_p95'], 1)} | {f(x['M_kb'], 1)} | {f(x['top1_share'], 2)} | "
                     f"{', '.join(x['top3'])} |")
    lines += ["", "Agreement: " + "; ".join(f"{k} rho={v['rho']:.2f} J5={v['J5']:.2f}" for k, v in s["agreement"].items()), ""]

# cross-run summaries over the 10 XGBoost runs (6 months + 4 extra seeds)
xgb = [k for k in res if not k.startswith(("MLP", "Ridge", "LEAKY"))]
lines += ["## Across the 10 XGBoost runs (6 months + 4 extra seeds)", ""]
for m in ["PFI", "TreeSHAP", "LIME", "TFI"]:
    F = np.array([res[k]["methods"][m]["F"] for k in xgb])
    S = [res[k]["methods"][m]["S"] for k in xgb if res[k]["methods"][m]["S"] is not None]
    L = np.array([res[k]["methods"][m]["L_p95"] for k in xgb])
    lines.append(f"- {m}: F mean {F.mean():.3f} sd {F.std(ddof=1):.3f} min {F.min():.3f}; "
                 f"S mean {np.mean(S) if S else float('nan'):.3f} min {np.min(S) if S else float('nan'):.3f}; "
                 f"L p95 median {np.median(L):.1f} ms [{L.min():.1f}, {L.max():.1f}]")
lowest_F = [min(["PFI", "TreeSHAP", "LIME", "TFI"], key=lambda m: res[k]["methods"][m]["F"]) for k in xgb]
lowest_S = [min(["PFI", "TreeSHAP", "LIME"], key=lambda m: res[k]["methods"][m]["S"]) for k in xgb]
lines += [f"- lowest F per run: {lowest_F}", f"- lowest S per run: {lowest_S}"]
(OUT / "reliability_paper_tables.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
