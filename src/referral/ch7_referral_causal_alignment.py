"""Chapter 7 - VALEX Level III deep-dive on the referral-related specialty-divergence exposure.

Design (replaces damir_referral_pathway_ate.py, whose diagnostics were invalid):
  * unit = aggregated Open DAMIR cell (one row aggregates many acts); outcome = EUR reimbursed
    per act, Y = PRS_REM_MNT / PRS_ACT_QTE; an act-weighted ATT is also reported
  * exposure D = 1 if prescriber specialty != executor specialty (both physicians)
  * exact stratification on act nature (PRS_NAT) x sector (PRS_PPU_SEC), strata with
    >= 10 units per arm; k-NN matching with replacement on logit(PS) inside strata,
    caliper = c * SD(logit PS)
  * all nominal covariates one-hot (sparse); PRS_ACT_NBR / PRS_ACT_COG excluded (outcome components)
  * balance = SMD per dummy with the actual matching weights; ATT-targeted IPW as triangulation
  * sensitivity grid (k, caliper), within-stratum placebo permutation (re-matching included),
    placebo-calibrated interval, E-value
  * Level III alignment: model-implied ATT (do(D=1) - do(D=0) on the treated) and mean TreeSHAP
    of D on the treated, compared with the causal ATT

Scales to the full monthly flow (~39M rows, .csv.gz): chunked reading, sparse design matrices,
KD-tree matching in one dimension.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import OneHotEncoder

NOMINAL = ["AGE_BEN_SNDS", "BEN_RES_REG", "BEN_SEX_COD", "BEN_QLT_COD", "BEN_CMU_TOP", "ASU_NAT",
           "EXO_MTF", "ETE_CAT_SNDS", "ETE_TYP_SNDS", "ETE_IND_TAA", "PSE_STJ_SNDS",
           "PSE_ACT_CAT", "PSP_ACT_CAT", "SOI_ANN", "SOI_MOI", "PRS_PDS_QCP"]
STRATA = ["PRS_NAT", "PRS_PPU_SEC"]
MIN_PER_ARM = 10


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load(csv):
    cols = ["PSP_SPE_SNDS", "PSE_SPE_SNDS", "PRS_REM_TYP", "PRS_REM_MNT", "PRS_ACT_QTE", *NOMINAL, *STRATA]
    flow = {"rows_in_file": 0, "reference_reimbursement_type": 0, "both_roles_physicians": 0}
    parts = []
    for ch in pd.read_csv(csv, sep=";", usecols=cols, chunksize=2_000_000, low_memory=False, encoding="latin-1"):
        flow["rows_in_file"] += len(ch)
        ch = ch.apply(pd.to_numeric, errors="coerce")
        ch = ch[ch.PRS_REM_TYP.eq(0)]
        flow["reference_reimbursement_type"] += len(ch)
        ch = ch[ch.PSP_SPE_SNDS.ne(0) & ch.PSE_SPE_SNDS.ne(0)].dropna(subset=["PSP_SPE_SNDS", "PSE_SPE_SNDS"])
        flow["both_roles_physicians"] += len(ch)
        parts.append(ch[ch.PRS_ACT_QTE.gt(0) & ch.PRS_REM_MNT.ge(0)].dropna(subset=STRATA))
        log(f"  read {flow['rows_in_file']:,} rows")
    d = pd.concat(parts, ignore_index=True)
    flow["positive_act_quantity"] = int(len(d))
    d["T"] = d.PSP_SPE_SNDS.ne(d.PSE_SPE_SNDS).astype(np.int8)
    d["Y"] = d.PRS_REM_MNT / d.PRS_ACT_QTE
    d["SOI_ANN"] = d.SOI_ANN.clip(lower=2022)
    d["stratum"] = d.PRS_NAT.astype(int).astype(str) + "_" + d.PRS_PPU_SEC.astype(int).astype(str)
    c = d.groupby("stratum")["T"].agg(["sum", "size"])
    keep = c.index[(c["sum"] >= MIN_PER_ARM) & (c["size"] - c["sum"] >= MIN_PER_ARM)]
    flow["treated_before_strata"] = int(d["T"].sum())
    d = d[d.stratum.isin(keep)].reset_index(drop=True)
    flow["after_exact_strata"] = int(len(d))
    flow["n_strata"] = int(len(keep))
    return d, flow


def design(d):
    enc = OneHotEncoder(handle_unknown="ignore", min_frequency=20, sparse_output=True, dtype=np.float32)
    Z = enc.fit_transform(d[NOMINAL].fillna(-1).astype(int))
    names = list(enc.get_feature_names_out(NOMINAL))
    S = OneHotEncoder(sparse_output=True, dtype=np.float32).fit_transform(d[["stratum"]])
    return Z.tocsr(), names, S.tocsr()


def propensity(Z, S, t):
    XS = sp.hstack([Z, S], format="csr")
    ps = LogisticRegression(C=1.0, max_iter=3000).fit(XS, t).predict_proba(XS)[:, 1]
    ps = np.clip(ps, 1e-4, 1 - 1e-4)
    return ps, float(roc_auc_score(t, ps))


def match(strata_idx, t, Y, lps, k, caliper):
    """Within-stratum k-NN matching with replacement on logit(PS) (KD-tree, 1-D).
    Returns matched treated ids, per-treated effects and unit weights."""
    w = np.zeros(len(t))
    t_all, eff_all = [], []
    for idx in strata_idx:
        ti, ci = idx[t[idx] == 1], idx[t[idx] == 0]
        kk = min(k, len(ci))
        nn = NearestNeighbors(n_neighbors=kk).fit(lps[ci, None])
        dist, pos = nn.kneighbors(lps[ti, None])
        ok = dist <= caliper
        n_ok = ok.sum(axis=1)
        has = n_ok > 0
        ti, pos, ok, n_ok = ti[has], pos[has], ok[has], n_ok[has]
        ctrl = ci[pos]
        ctrl_mean = np.where(ok, Y[ctrl], 0).sum(axis=1) / n_ok
        np.add.at(w, ti, 1.0)
        np.add.at(w, ctrl[ok], np.repeat(1.0 / n_ok, ok.sum(axis=1)))
        t_all.append(ti)
        eff_all.append(Y[ti] - ctrl_mean)
    return np.concatenate(t_all), np.concatenate(eff_all), w


def smd_table(Z, names, t, w):
    """SMD for every one-hot column: weighted means, unweighted pooled SD (Austin convention)."""
    m1 = np.asarray(Z[t == 1].T @ w[t == 1]).ravel() / w[t == 1].sum()
    m0 = np.asarray(Z[t == 0].T @ w[t == 0]).ravel() / w[t == 0].sum()
    p1 = np.asarray(Z[t == 1].mean(axis=0)).ravel()
    p0 = np.asarray(Z[t == 0].mean(axis=0)).ravel()
    sd = np.sqrt((p1 * (1 - p1) + p0 * (1 - p0)) / 2)
    keep = sd > 0
    return pd.Series((m1 - m0)[keep] / sd[keep], index=np.array(names)[keep])


def boot_ci(values, B, rng, weights=None):
    n = len(values)
    s = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        s.append(values[i].mean() if weights is None else np.average(values[i], weights=weights[i]))
    return np.quantile(s, [0.025, 0.975]).tolist(), float(np.std(s, ddof=1))


def e_value(att, sd_y):
    rr = np.exp(0.91 * abs(att) / sd_y)
    return float(rr + np.sqrt(rr * (rr - 1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--caliper", type=float, default=0.2)
    ap.add_argument("--boot", type=int, default=500)
    ap.add_argument("--placebo", type=int, default=100)
    ap.add_argument("--shap-sample", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)

    d, flow = load(a.csv)
    log(f"flow: {flow}")
    t = d["T"].to_numpy().astype(int)
    Y = d.Y.to_numpy()
    acts = d.PRS_ACT_QTE.to_numpy()
    strata_idx = [np.asarray(g) for g in d.groupby("stratum").indices.values()]
    Z, names, S = design(d)
    ps, auc = propensity(Z, S, t)
    lps = np.log(ps / (1 - ps))
    cal = a.caliper * lps.std()
    log(f"PS AUC {auc:.3f}")

    t_ids, eff, w = match(strata_idx, t, Y, lps, a.k, cal)
    ci, se = boot_ci(eff, a.boot, rng)
    ci_w, _ = boot_ci(eff, a.boot, rng, weights=acts[t_ids])
    m = w > 0
    smd_b = smd_table(Z, names, t, np.ones(len(t)))
    smd_m = smd_table(Z[m], names, t[m], w[m])
    log(f"ATT matching {eff.mean():.3f} CI {ci}; max SMD {smd_b.abs().max():.3f} -> {smd_m.abs().max():.3f}")

    w_ipw = np.where(t == 1, 1.0, ps / (1 - ps))

    def att_ipw(idx):
        tt, yy, ww = t[idx], Y[idx], w_ipw[idx]
        return np.average(yy[tt == 1], weights=ww[tt == 1]) - np.average(yy[tt == 0], weights=ww[tt == 0])

    n = len(t)
    ipw_point = att_ipw(np.arange(n))
    ipw_boot = [att_ipw(rng.integers(0, n, n)) for _ in range(a.boot)]
    smd_i = smd_table(Z, names, t, w_ipw)
    ess = w_ipw[t == 0].sum() ** 2 / (w_ipw[t == 0] ** 2).sum()
    w99 = np.minimum(w_ipw, np.quantile(w_ipw[t == 0], 0.99))
    att_ipw_trunc = np.average(Y[t == 1]) - np.average(Y[t == 0], weights=w99[t == 0])
    log("IPW done")

    grid = []
    for k in (1, 3, 5, 10):
        for c in (0.1, 0.2, 0.5):
            ti, e, ww = match(strata_idx, t, Y, lps, k, c * lps.std())
            mm = ww > 0
            grid.append({"k": k, "caliper_sd": c, "n_matched": int(len(e)), "att": float(e.mean()),
                         "max_abs_smd": float(smd_table(Z[mm], names, t[mm], ww[mm]).abs().max())})
    log("sensitivity grid done")

    plac = []
    for _ in range(a.placebo):
        tp = t.copy()
        for idx in strata_idx:
            tp[idx] = rng.permutation(tp[idx])
        _, e, _ = match(strata_idx, tp, Y, lps, a.k, cal)
        plac.append(e.mean())
    plac_c = np.asarray(plac) - np.mean(plac)
    ci_cal = [float(eff.mean() - np.quantile(plac_c, 0.975)), float(eff.mean() - np.quantile(plac_c, 0.025))]
    p_plac = float((np.abs(plac_c) >= abs(eff.mean())).mean())
    log("placebo done")

    # Level III alignment: predictive model vs causal reference
    F = sp.hstack([Z, S, sp.csr_matrix(t.reshape(-1, 1).astype(np.float32))], format="csr")
    jT = F.shape[1] - 1
    model = xgb.XGBRegressor(n_estimators=400, max_depth=8, learning_rate=0.08, subsample=0.8,
                             colsample_bytree=0.8, tree_method="hist", random_state=a.seed, n_jobs=-1)
    model.fit(F, np.log1p(Y))
    base = sp.hstack([Z[t_ids], S[t_ids]], format="csr")
    ones = sp.csr_matrix(np.ones((len(t_ids), 1), dtype=np.float32))
    f1 = sp.hstack([base, ones], format="csr")
    f0 = sp.hstack([base, sp.csr_matrix((len(t_ids), 1), dtype=np.float32)], format="csr")
    diff = np.expm1(model.predict(f1)) - np.expm1(model.predict(f0))
    model_att = float(diff.mean())
    model_ci, _ = boot_ci(diff, a.boot, rng)
    sub = rng.choice(len(t_ids), min(a.shap_sample, len(t_ids)), replace=False)
    contrib = model.get_booster().predict(xgb.DMatrix(F[t_ids[sub]]), pred_contribs=True)[:, :-1]
    shap_T = contrib[:, jT]
    mean_abs = np.abs(contrib).mean(axis=0)
    shap_rank = int((np.argsort(-mean_abs) == jT).nonzero()[0][0]) + 1
    log("alignment model done")

    align = {
        "causal_att": float(eff.mean()), "causal_ci95": ci, "causal_ci95_placebo_calibrated": ci_cal,
        "model_implied_att": model_att, "model_implied_ci95": model_ci,
        "mean_treeshap_D_on_treated_log_scale": float(shap_T.mean()),
        "share_treated_with_positive_shap_D": float((shap_T > 0).mean()),
        "rank_of_D_in_mean_abs_shap": shap_rank, "n_model_features": int(F.shape[1]),
        "sign_agreement_model": bool(np.sign(model_att) == np.sign(eff.mean())),
        "sign_agreement_shap": bool(np.sign(shap_T.mean()) == np.sign(eff.mean())),
        "model_att_inside_causal_ci": bool(ci[0] <= model_att <= ci[1]),
        "model_att_inside_calibrated_ci": bool(ci_cal[0] <= model_att <= ci_cal[1]),
        "relative_gap": float(abs(model_att - eff.mean()) / max(abs(eff.mean()), 1e-12)),
    }
    causal_null = ci_cal[0] <= 0 <= ci_cal[1]
    model_null = model_ci[0] <= 0 <= model_ci[1]
    if causal_null and model_null:
        align["verdict"] = "aligned (both indistinguishable from zero)"
    elif align["model_att_inside_calibrated_ci"] and (causal_null or align["sign_agreement_model"]):
        align["verdict"] = "aligned"
    elif align["sign_agreement_model"]:
        align["verdict"] = "partially aligned (same sign, different magnitude)"
    else:
        align["verdict"] = "not aligned"

    sd_y = Y.std()
    report = {
        "design": {"unit": "aggregated Open DAMIR cell", "outcome": "EUR reimbursed per act",
                   "exposure": "prescriber specialty != executor specialty (both physicians)",
                   "exact_strata": STRATA, "k": a.k, "caliper_logit": float(cal),
                   "caliper_rule": f"{a.caliper} x SD(logit PS)", "bootstrap": a.boot},
        "flow": flow, "n_treated": int(t.sum()), "n_control": int((1 - t).sum()),
        "ps_auc": auc, "n_treated_matched": int(len(eff)), "n_unique_controls_used": int(((w > 0) & (t == 0)).sum()),
        "outcome_means": {"treated": float(Y[t == 1].mean()), "control": float(Y[t == 0].mean()), "sd_all": float(sd_y)},
        "att_matching": {"estimate": float(eff.mean()), "se": se, "ci95": ci,
                         "act_weighted_estimate": float(np.average(eff, weights=acts[t_ids])),
                         "act_weighted_ci95": ci_w, "median_cell_effect": float(np.median(eff))},
        "att_ipw": {"estimate": float(ipw_point), "ci95": np.quantile(ipw_boot, [0.025, 0.975]).tolist(),
                    "ess_control": float(ess), "estimate_weights_truncated_p99": float(att_ipw_trunc)},
        "balance": {"max_abs_smd_before": float(smd_b.abs().max()),
                    "max_abs_smd_matched": float(smd_m.abs().max()),
                    "share_lt_0_1_matched": float((smd_m.abs() < 0.1).mean()),
                    "max_abs_smd_ipw": float(smd_i.abs().max()),
                    "share_lt_0_1_ipw": float((smd_i.abs() < 0.1).mean()),
                    "worst10_matched": smd_m.abs().sort_values(ascending=False).head(10).round(3).to_dict()},
        "sensitivity_grid": grid,
        "placebo": {"n": a.placebo, "mean": float(np.mean(plac)), "q025_q975": np.quantile(plac, [0.025, 0.975]).tolist(),
                    "att_ci95_placebo_calibrated": ci_cal, "two_sided_placebo_p": p_plac},
        "e_value_point": e_value(eff.mean(), sd_y),
        "e_value_ci_bound": e_value(min(abs(ci_cal[0]), abs(ci_cal[1])) if np.sign(ci_cal[0]) == np.sign(ci_cal[1]) else 0.0, sd_y),
        "level3_alignment": align,
    }
    pd.DataFrame({"smd_before": smd_b, "smd_matched": smd_m, "smd_ipw": smd_i}).to_csv(a.out / "balance_table.csv")
    pd.DataFrame(grid).to_csv(a.out / "sensitivity_grid.csv", index=False)
    (a.out / "ch7_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
