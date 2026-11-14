"""Supplementary sensitivity analyses requested by the ICIDSMAI'26 reviewers (paper 45).

Reuses the design of ch7_referral_causal_alignment.py (same unit, outcome, strata, PS, matching).
  A. Exposure misclassification: alternative definitions of the referral proxy
       main         prescriber specialty != executor specialty (both coded, != 0)
       known_spec   main, excluding unknown specialty (99) on either side
       no_technical main, excluding technical executors (radiology 6, pathology 37, lab director 38)
       gp_referral  prescriber is a general practitioner (1); exposed = executor is not a GP
       no_pathway_cov  main exposure, care-pathway qualifier PRS_PDS_QCP removed from the PS model
     + concordance of the proxy with the coordinated-care qualifier (PRS_PDS_QCP = 3, oriented by the GP)
  B. Matching vs weighting (main exposure only)
       ATT-IPW untruncated / control weights truncated at p95, p99, p99.9
       stratum-normalized ATT-IPW (weights rescaled inside each exact stratum)
       ATT-IPW restricted to the matched support (logit-PS range of matched exposed cells, per stratum)
       overlap weights (ATO; different estimand, reported for context)
Usage: python reviewer_sensitivity.py --csv A202401.csv.gz --out outputs/reviewer_2024_01
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ch7_referral_causal_alignment as ch7  # noqa: E402
from ch7_referral_causal_alignment import (NOMINAL, STRATA, MIN_PER_ARM, boot_ci, e_value,  # noqa: E402
                                           match, propensity, smd_table)


def design(d, cols=NOMINAL):
    saved = ch7.NOMINAL
    ch7.NOMINAL = list(cols)
    try:
        return ch7.design(d)
    finally:
        ch7.NOMINAL = saved

TECHNICAL = {6, 37, 38}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_raw(csv):
    cols = ["PSP_SPE_SNDS", "PSE_SPE_SNDS", "PRS_REM_TYP", "PRS_REM_MNT", "PRS_ACT_QTE", *NOMINAL, *STRATA]
    parts = []
    for ch in pd.read_csv(csv, sep=";", usecols=cols, chunksize=2_000_000, low_memory=False, encoding="latin-1"):
        ch = ch.apply(pd.to_numeric, errors="coerce")
        ch = ch[ch.PRS_REM_TYP.eq(0)]
        ch = ch[ch.PSP_SPE_SNDS.ne(0) & ch.PSE_SPE_SNDS.ne(0)].dropna(subset=["PSP_SPE_SNDS", "PSE_SPE_SNDS"])
        parts.append(ch[ch.PRS_ACT_QTE.gt(0) & ch.PRS_REM_MNT.ge(0)].dropna(subset=STRATA))
    d = pd.concat(parts, ignore_index=True)
    d["Y"] = d.PRS_REM_MNT / d.PRS_ACT_QTE
    d["SOI_ANN"] = d.SOI_ANN.clip(lower=2022)
    d["stratum"] = d.PRS_NAT.astype(int).astype(str) + "_" + d.PRS_PPU_SEC.astype(int).astype(str)
    return d


def subset(d, name):
    sp_, se_ = d.PSP_SPE_SNDS, d.PSE_SPE_SNDS
    if name in ("main", "no_pathway_cov"):
        m = pd.Series(True, index=d.index)
    elif name == "known_spec":
        m = sp_.ne(99) & se_.ne(99)
    elif name == "no_technical":
        m = ~se_.isin(TECHNICAL)
    elif name == "gp_referral":
        m = sp_.eq(1)
    else:
        raise ValueError(name)
    s = d[m].copy()
    s["T"] = s.PSP_SPE_SNDS.ne(s.PSE_SPE_SNDS).astype(np.int8)
    c = s.groupby("stratum")["T"].agg(["sum", "size"])
    keep = c.index[(c["sum"] >= MIN_PER_ARM) & (c["size"] - c["sum"] >= MIN_PER_ARM)]
    return s[s.stratum.isin(keep)].reset_index(drop=True), int(len(keep))


def run_exposure(d, name, args, rng):
    s, n_strata = subset(d, name)
    t = s["T"].to_numpy().astype(int)
    Y = s.Y.to_numpy()
    strata_idx = [np.asarray(g) for g in s.groupby("stratum").indices.values()]
    Z, names, S = design(s, [c for c in NOMINAL if not (name == "no_pathway_cov" and c == "PRS_PDS_QCP")])
    ps, auc = propensity(Z, S, t)
    lps = np.log(ps / (1 - ps))
    cal = args.caliper * lps.std()
    t_ids, eff, w = match(strata_idx, t, Y, lps, args.k, cal)
    ci, _ = boot_ci(eff, args.boot, rng)
    m = w > 0
    smd_b = smd_table(Z, names, t, np.ones(len(t))).abs().max()
    smd_m = smd_table(Z[m], names, t[m], w[m]).abs().max()
    plac = []
    for _ in range(args.placebo):
        tp = t.copy()
        for idx in strata_idx:
            tp[idx] = rng.permutation(tp[idx])
        plac.append(match(strata_idx, tp, Y, lps, args.k, cal)[1].mean())
    plac = np.asarray(plac)
    pc = plac - plac.mean()
    att = float(eff.mean())
    out = {"exposure": name, "n_cells": int(len(t)), "n_treated": int(t.sum()), "n_strata": n_strata,
           "ps_auc": auc, "n_treated_matched": int(len(eff)), "att": att, "ci95_boot": ci,
           "placebo_mean": float(plac.mean()), "att_bias_corrected": float(att - plac.mean()),
           "ci95_placebo_calibrated": [float(att - np.quantile(pc, 0.975)), float(att - np.quantile(pc, 0.025))],
           "placebo_p": float((np.abs(pc) >= abs(att)).mean()),
           "max_abs_smd_before": float(smd_b), "max_abs_smd_matched": float(smd_m),
           "mean_outcome_treated": float(Y[t == 1].mean()), "e_value": e_value(att, Y.std())}
    log(f"{name}: {out}")
    return out, (s, t, Y, ps, lps, strata_idx, Z, names, t_ids, cal)


def weighting(ctx, args, rng):
    s, t, Y, ps, lps, strata_idx, Z, names, t_ids, cal = ctx
    n = len(t)
    odds = ps / (1 - ps)
    stratum = s.stratum.to_numpy()

    def att_w(w, idx=None):
        idx = np.arange(n) if idx is None else idx
        tt, yy, ww = t[idx], Y[idx], w[idx]
        return np.average(yy[tt == 1], weights=ww[tt == 1]) - np.average(yy[tt == 0], weights=ww[tt == 0])

    def ess(w):
        w0 = w[t == 0]
        return float(w0.sum() ** 2 / (w0 ** 2).sum())

    def summarize(label, w, keep=None, estimand="ATT"):
        idx = np.arange(n) if keep is None else np.flatnonzero(keep)
        point = att_w(w, idx)
        bs = [att_w(w, idx[rng.integers(0, len(idx), len(idx))]) for _ in range(args.boot_ipw)]
        smd = smd_table(Z[idx], names, t[idx], w[idx]).abs()
        ww = np.zeros(n)
        ww[idx] = w[idx]
        r = {"estimator": label, "estimand": estimand, "estimate": float(point),
             "ci95": np.quantile(bs, [0.025, 0.975]).tolist(), "max_abs_smd": float(smd.max()),
             "share_smd_lt_0_1": float((smd < 0.1).mean()), "ess_control": ess(ww),
             "n_treated": int(t[idx].sum())}
        log(f"  {r}")
        return r

    res = []
    w_ipw = np.where(t == 1, 1.0, odds)
    res.append(summarize("ATT-IPW, untruncated", w_ipw))
    for q in (0.95, 0.99, 0.999):
        res.append(summarize(f"ATT-IPW, control weights truncated at p{100 * q:g}",
                             np.where(t == 1, 1.0, np.minimum(odds, np.quantile(odds[t == 0], q)))))
    # stratum-normalized: inside each stratum controls carry the treated count of that stratum
    w_s = w_ipw.copy()
    for idx in strata_idx:
        c = idx[t[idx] == 0]
        w_s[c] = odds[c] / odds[c].sum() * t[idx].sum()
    res.append(summarize("ATT-IPW, stratum-normalized", w_s))
    # matched support: logit-PS range of matched exposed cells (+ caliper) inside each stratum
    keep = np.zeros(n, bool)
    matched = np.zeros(n, bool)
    matched[t_ids] = True
    for idx in strata_idx:
        mt = idx[matched[idx]]
        if len(mt) == 0:
            continue
        lo, hi = lps[mt].min() - cal, lps[mt].max() + cal
        keep[idx[(t[idx] == 0) & (lps[idx] >= lo) & (lps[idx] <= hi)]] = True
        keep[mt] = True
    w_ms = w_s.copy()
    for idx in strata_idx:
        c = idx[(t[idx] == 0) & keep[idx]]
        if len(c):
            w_ms[c] = odds[c] / odds[c].sum() * (matched[idx] & (t[idx] == 1)).sum()
    res.append(summarize("ATT-IPW, stratum-normalized, matched support", w_ms, keep=keep))
    res.append(summarize("Overlap weights (ATO)", np.where(t == 1, 1 - ps, ps), estimand="ATO"))
    return res


def concordance(s):
    q = s.PRS_PDS_QCP.fillna(-1).astype(int)
    grp = np.select([q.eq(3), q.eq(1), q.isin([0, 99, -1])], ["oriented_by_gp", "executor_is_gp", "not_applicable"],
                    "other_pathway_code")
    out = {}
    for lab, w in (("cells", np.ones(len(s))), ("acts", s.PRS_ACT_QTE.to_numpy())):
        tab = pd.crosstab(grp, s["T"].to_numpy(), values=w, aggfunc="sum").fillna(0)
        out[lab] = {str(k): {str(c): float(v) for c, v in row.items()} for k, row in tab.iterrows()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--caliper", type=float, default=0.2)
    ap.add_argument("--boot", type=int, default=500)
    ap.add_argument("--boot-ipw", type=int, default=200)
    ap.add_argument("--placebo", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--exposures", default="main,known_spec,no_technical,gp_referral,no_pathway_cov")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    d = load_raw(a.csv)
    log(f"loaded {len(d):,} cells")
    report = {"exposures": [], "weighting": []}
    for name in a.exposures.split(","):
        r, ctx = run_exposure(d, name, a, rng)
        report["exposures"].append(r)
        if name == "main":
            report["concordance"] = concordance(ctx[0])
            log(f"concordance {report['concordance']}")
            report["weighting"] = weighting(ctx, a, rng)
        (a.out / "reviewer_sensitivity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()
