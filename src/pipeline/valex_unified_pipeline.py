"""VALEX 1.0 unified pipeline: one dataset, one model, three levels, score registry, orchestration.

Implements the embodiment described in the OMPIC patent application
("Procédé et système d'évaluation multi-niveaux de méthodes d'explication ..."):

  Level I   [0023]-[0028]  fidelity F_m = mean_k (Delta_m(k) - Delta_rand(k)), P = -MSE,
                           reference value = modal code; optional remove-and-retrain variant
  Level II  [0029]-[0032]  Gaussian noise alpha*sigma_j on ordinal variables, marginal
                           re-draw with probability p on nominal codes, R repetitions,
                           Jaccard top-k (+ Spearman); latency median/p95 and peak memory
  Level III [0033]-[0039]  per-variable binary treatment T_j, propensity score, trimming
                           [0.05, 0.95], IPW effect, SMD < 0.1 balance check (richer model
                           retry, else non-identifiable), regression adjustment on the
                           back-door set, triangulation, C_m = Spearman / Jaccard on V
  Registry  [0044]         JSON registry of F, S, C, L, M
  Routing   [0045]-[0052]  usage profiles P1-P4, eligibility on p95 latency and memory,
                           weighted score, fallback, routing overhead

Data unit: one Open DAMIR row is an aggregated cell, not a single prestation. The target is
the reimbursed amount per act, log1p(PRS_REM_MNT / PRS_ACT_QTE). Amount, base, rate,
payment, overrun, quantity and FLT_* flux columns are excluded because they are components
or copies of the target (target leakage in the earlier campaign).
"""
from __future__ import annotations

import argparse
import json
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from lime.lime_tabular import LimeTabularExplainer
from scipy.stats import spearmanr
import shap
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

NOMINAL = [
    "ORG_CLE_REG", "BEN_RES_REG", "BEN_CMU_TOP", "BEN_QLT_COD", "BEN_SEX_COD", "ETE_CAT_SNDS",
    "ETE_TYP_SNDS", "ETE_IND_TAA", "MDT_TYP_COD", "PRS_FJH_TYP", "ASU_NAT", "ATT_NAT", "CPL_COD",
    "CPT_ENV_TYP", "DRG_AFF_NAT", "EXO_MTF", "MTM_NAT", "PRS_NAT", "PRS_PPU_SEC", "PRS_PDS_QCP",
    "PSE_ACT_CAT", "PSE_SPE_SNDS", "PSE_STJ_SNDS", "PSP_ACT_CAT", "PSP_SPE_SNDS", "ETB_DCS_MCO",
]
ORDINAL = ["AGE_BEN_SNDS", "SOI_ANN", "SOI_MOI"]
LEAKAGE_EXCLUDED = [
    "PRS_REM_MNT", "PRS_REM_BSE", "PRS_REM_TAU", "PRS_PAI_MNT", "PRS_DEP_MNT", "PRS_ACT_QTE",
    "PRS_ACT_NBR", "PRS_ACT_COG", "FLT_ACT_COG", "FLT_ACT_NBR", "FLT_ACT_QTE", "FLT_PAI_MNT",
    "FLT_DEP_MNT", "FLT_REM_MNT",
]
TREE_METHODS = ["TFI", "PFI", "TreeSHAP", "LIME"]
NON_TREE_METHODS = ["PFI", "PermSHAP", "LIME"]
TREE_ONLY = ["TFI", "TreeSHAP"]  # Not Evaluable when the model is not tree-based (eligibility-first)
METHODS = TREE_METHODS  # reset in main() according to --model
# Columns that define a derived treatment cannot be used to adjust for it (deterministic positivity violation)
DEFINITION_PARENTS = {"REFERRAL_DIV": ["PSP_SPE_SNDS", "PSE_SPE_SNDS"]}
LOCAL_METHODS = {"TreeSHAP", "LIME"}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ----------------------------------------------------------------------------- data
def load(csv: Path, max_cells: int | None, seed: int) -> tuple[pd.DataFrame, pd.Series, dict]:
    """Chunked read (works on the full ~39M-row .csv.gz), cohort filter, then uniform random sample."""
    usecols = [*NOMINAL, *ORDINAL, "PRS_REM_MNT", "PRS_ACT_QTE", "PRS_REM_TYP"]
    parts, n_rows = [], 0
    for chunk in pd.read_csv(csv, sep=";", usecols=usecols, chunksize=2_000_000, low_memory=False,
                             encoding="latin-1"):
        n_rows += len(chunk)
        chunk = chunk.apply(pd.to_numeric, errors="coerce")
        chunk = chunk[chunk.PRS_REM_TYP.eq(0) & chunk.PRS_ACT_QTE.gt(0) & chunk.PRS_REM_MNT.gt(0)]
        parts.append(chunk.astype(np.float64))
        log(f"  read {n_rows:,} rows")
    d = pd.concat(parts, ignore_index=True)
    flow = {"rows_in_file": int(n_rows), "cells_in_cohort": int(len(d))}
    if max_cells is not None and len(d) > max_cells:
        d = d.sample(max_cells, random_state=seed).reset_index(drop=True)
    flow["cells_sampled"] = int(len(d))
    y = np.log1p(d.PRS_REM_MNT / d.PRS_ACT_QTE)
    X = d[[*NOMINAL, *ORDINAL]].fillna(-1)
    X["SOI_ANN"] = X["SOI_ANN"].clip(lower=2022)
    # referral-related specialty divergence (Chapter 6 exposure), kept as an explicit feature
    X["REFERRAL_DIV"] = ((X.PSP_SPE_SNDS != X.PSE_SPE_SNDS) & X.PSP_SPE_SNDS.ne(0) & X.PSE_SPE_SNDS.ne(0)).astype(int)
    return X.astype(np.float32), y.astype(np.float32), flow


# ----------------------------------------------------------------------------- explainers
class Library:
    """Candidate explanation methods (patent ref. 130). Each returns a global importance vector."""

    def __init__(self, model, X_train, X_eval, y_eval, seed):
        self.model, self.X_train, self.X_eval, self.y_eval, self.seed = model, X_train, X_eval, y_eval, seed
        self.cols = list(X_eval.columns)
        self.booster = model.get_booster() if hasattr(model, "get_booster") else None
        if self.booster is None:
            # model-agnostic Shapley values on the 30 raw features (replaces TreeSHAP for non-tree models)
            background = X_train.sample(50, random_state=seed)
            self.perm_shap = shap.PermutationExplainer(model.predict, shap.maskers.Independent(background),
                                                       seed=seed)
        self.lime = LimeTabularExplainer(
            X_train.sample(5000, random_state=seed).to_numpy(), feature_names=self.cols,
            categorical_features=list(range(len(NOMINAL))), mode="regression", random_state=seed,
            discretize_continuous=False,
        )

    def tfi(self, X):
        gain = self.booster.get_score(importance_type="gain")
        return np.array([gain.get(c, 0.0) for c in self.cols])

    def pfi(self, X, y=None, n=3000):
        idx = np.random.default_rng(self.seed).choice(len(X), min(n, len(X)), replace=False)
        yy = (self.y_eval if y is None else y).to_numpy()[idx]
        r = permutation_importance(self.model, X.iloc[idx], yy, n_repeats=3, random_state=self.seed,
                                   scoring="neg_mean_squared_error", n_jobs=1)
        return r.importances_mean

    def treeshap(self, X):
        contrib = self.booster.predict(xgb.DMatrix(X), pred_contribs=True)[:, :-1]
        return np.abs(contrib).mean(axis=0)

    def lime_global(self, X, n=30):
        rows = X.sample(min(n, len(X)), random_state=self.seed).to_numpy()
        imp = np.zeros(len(self.cols))
        for r in rows:
            exp = self.lime.explain_instance(r, self.model.predict, num_features=len(self.cols), num_samples=500)
            for j, w in exp.as_map()[0]:
                imp[j] += abs(w)
        return imp / len(rows)

    def permshap_global(self, X, n=100):
        rows = X.sample(min(n, len(X)), random_state=self.seed)
        return np.abs(self.perm_shap(rows, silent=True).values).mean(axis=0)

    def importance(self, method, X, y=None):
        if method == "PermSHAP":
            return self.permshap_global(X)
        if method == "TFI":
            return self.tfi(X)
        if method == "PFI":
            return self.pfi(X, y)
        if method == "TreeSHAP":
            return self.treeshap(X)
        if method == "LIME":
            return self.lime_global(X)
        raise KeyError(method)

    def single_call(self, method, x_row):
        """One explanation request, used for latency / memory profiling (ref. 144)."""
        if method == "PermSHAP":
            return self.perm_shap(x_row, silent=True)
        if method == "TFI":
            return self.tfi(x_row)
        if method == "TreeSHAP":
            return self.booster.predict(xgb.DMatrix(x_row), pred_contribs=True)
        if method == "LIME":
            return self.lime.explain_instance(x_row.to_numpy()[0], self.model.predict, num_features=10, num_samples=500)
        if method == "PFI":  # PFI is inherently a batch method: one call = one global audit on 1000 rows
            return self.pfi(self.X_eval, n=1000)


def ranking(imp):
    return np.argsort(-np.asarray(imp), kind="stable")


# ----------------------------------------------------------------------------- level I
def level1(lib, model, X_tr, y_tr, X_ev, y_ev, imps, K, n_rand, retrain, seed):
    rng = np.random.default_rng(seed)
    ref = X_tr.mode().iloc[0]
    P = lambda Xm: -mean_squared_error(y_ev, model.predict(Xm))
    base = P(X_ev)

    def intervene(cols):
        Xm = X_ev.copy()
        for c in cols:
            Xm[c] = ref[c]
        return Xm

    d_rand = {}
    for k in K:
        d_rand[k] = float(np.mean([base - P(intervene(rng.choice(X_ev.columns, k, replace=False))) for _ in range(n_rand)]))
    out = {}
    for m, imp in imps.items():
        top = [X_ev.columns[i] for i in ranking(imp)]
        deltas = {k: float(base - P(intervene(top[:k]))) for k in K}
        rec = {"delta_method": deltas, "delta_random": d_rand,
               "F_raw": float(np.mean([deltas[k] - d_rand[k] for k in K]))}
        if retrain:
            rr = {}
            for k in K:
                keep = [c for c in X_tr.columns if c not in top[:k]]
                m2 = clone(model).fit(X_tr[keep], y_tr)
                rr[k] = float(r2_score(y_ev, model.predict(X_ev)) - r2_score(y_ev, m2.predict(X_ev[keep])))
            rec["remove_and_retrain_r2_drop"] = rr
        out[m] = rec
    mx = max(max(r["F_raw"] for r in out.values()), 1e-12)
    for r in out.values():
        r["F"] = max(r["F_raw"], 0.0) / mx
    return {"baseline_neg_mse": base, "methods": out}


# ----------------------------------------------------------------------------- level II
def perturb(X, X_ref, alpha, p, rng):
    Xp = X.copy()
    for c in ORDINAL:
        sd = X_ref[c].std()
        lo, hi = X_ref[c].min(), X_ref[c].max()
        Xp[c] = np.clip(np.round(X[c] + rng.normal(0, alpha * sd, len(X))), lo, hi)
    pool = {c: X_ref[c].to_numpy() for c in NOMINAL + ["REFERRAL_DIV"]}
    for c, vals in pool.items():
        swap = rng.random(len(X)) < p
        Xp.loc[swap, c] = rng.choice(vals, swap.sum())
    return Xp


def level2(lib, X_ev, y_ev, X_ref, imps, R, alpha, p, k, seed, n_eval):
    rng = np.random.default_rng(seed)
    out = {}
    Xs = X_ev.sample(min(n_eval, len(X_ev)), random_state=seed)
    ys = y_ev.loc[Xs.index]
    for m in METHODS:
        if m == "TFI":
            out[m] = {"status": "Not Evaluable",
                      "reason": "TFI is computed from the fitted trees and is invariant to input perturbation "
                                "by construction; S would be trivially 1 under the input-noise operator."}
            continue
        base = lib.importance(m, Xs, ys)
        top0 = set(ranking(base)[:k])
        jac, spr = [], []
        reps = R if m not in ("LIME", "PermSHAP") else max(5, R // 4)  # costly sampling-based explainers
        for _ in range(reps):
            Xp = perturb(Xs, X_ref, alpha, p, rng)
            imp_p = lib.importance(m, Xp, ys)
            top1 = set(ranking(imp_p)[:k])
            jac.append(len(top0 & top1) / len(top0 | top1))
            spr.append(spearmanr(base, imp_p).statistic)
        out[m] = {"S_jaccard": float(np.mean(jac)), "S_jaccard_sd": float(np.std(jac)),
                  "spearman": float(np.nanmean(spr)), "R": reps}
    return out


def profile(lib, X_ev, n_calls, seed):
    rng = np.random.default_rng(seed)
    out = {}
    for m in METHODS:
        n = n_calls if m in ("TFI", "TreeSHAP") else (10 if m == "LIME" else 5)
        lat, mem = [], []
        for _ in range(n):
            row = X_ev.iloc[[int(rng.integers(len(X_ev)))]]
            tracemalloc.start()
            before = tracemalloc.get_traced_memory()[0]
            t0 = time.perf_counter()
            lib.single_call(m, row)
            lat.append((time.perf_counter() - t0) * 1000)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            mem.append((peak - before) / 1024)
        out[m] = {"latency_ms_median": float(np.median(lat)), "latency_ms_p95": float(np.percentile(lat, 95)),
                  "memory_kb_peak_median": float(np.median(mem)), "n_calls": n}
    return out


# ----------------------------------------------------------------------------- level III
def wsmd(Z, t, w):
    res = []
    for c in Z.columns:
        z = Z[c].to_numpy()
        m1, m0 = np.average(z[t == 1], weights=w[t == 1]), np.average(z[t == 0], weights=w[t == 0])
        sd = np.sqrt((z[t == 1].var() + z[t == 0].var()) / 2)
        res.append(0.0 if sd == 0 else abs(m1 - m0) / sd)
    return float(max(res)) if res else 0.0


def treatment(X, j):
    x = X[j]
    if set(np.unique(x)) <= {0.0, 1.0}:
        return x.astype(int), "binary"
    if j in ORDINAL:
        return (x > x.median()).astype(int), "above median"
    mode = x.mode().iloc[0]
    return (x == mode).astype(int), f"modal code == {int(mode)}"


def causal_effect(X, y, j, seed, n_boot, smd_thr):
    t, rule = treatment(X, j)
    t = t.to_numpy()
    if t.mean() < 0.02 or t.mean() > 0.98:
        return {"variable": j, "rule": rule, "status": "non-identifiable", "reason": "treatment prevalence < 2%"}
    excluded = {j, *DEFINITION_PARENTS.get(j, [])}
    excluded |= {d for d, parents in DEFINITION_PARENTS.items() if j in parents}
    others = [c for c in X.columns if c not in excluded]
    Z = pd.get_dummies(X[others].astype(int).astype(str), sparse=False).astype(np.float32)
    Z = Z.loc[:, Z.mean().between(0.005, 0.995)]
    fits = [("logistic", LogisticRegression(C=1.0, max_iter=1000)),
            ("gradient boosting", HistGradientBoostingClassifier(max_iter=200, random_state=seed))]
    smd = float("nan")
    for name, clf in fits:
        Xin = Z.to_numpy() if name == "logistic" else X[others].to_numpy()
        e = clf.fit(Xin, t).predict_proba(Xin)[:, 1]
        keep = (e >= 0.05) & (e <= 0.95)
        tk, ek, yk = t[keep], e[keep], y.to_numpy()[keep]
        if tk.sum() < 50 or (1 - tk).sum() < 50:
            smd = float("nan")  # positivity failure: too few units left in one arm after trimming
            continue
        w = np.where(tk == 1, tk.mean() / ek, (1 - tk.mean()) / (1 - ek))
        smd = wsmd(Z[keep], tk, w)
        if smd < smd_thr:
            break
    else:
        return {"variable": j, "rule": rule, "status": "non-identifiable",
                "reason": (f"max |SMD| after weighting = {smd:.3f} >= {smd_thr} with both PS models" if smd == smd
                           else "positivity: < 50 units in one arm after [0.05, 0.95] trimming")}

    def ipw(idx):
        tt, yy, ww = tk[idx], yk[idx], w[idx]
        return np.average(yy[tt == 1], weights=ww[tt == 1]) - np.average(yy[tt == 0], weights=ww[tt == 0])

    def reg(idx):
        A = np.column_stack([tk[idx], Z[keep].to_numpy()[idx]])
        return Ridge(alpha=1e-3).fit(A, yk[idx]).coef_[0]

    rng = np.random.default_rng(seed)
    n = len(tk)
    tau_ipw, tau_reg = ipw(np.arange(n)), reg(np.arange(n))
    b_ipw, b_reg = [], []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        b_ipw.append(ipw(i)); b_reg.append(reg(i))
    ci_ipw, ci_reg = np.quantile(b_ipw, [0.025, 0.975]), np.quantile(b_reg, [0.025, 0.975])
    same_sign = np.sign(tau_ipw) == np.sign(tau_reg)
    rel_gap = abs(tau_ipw - tau_reg) / max(abs(tau_ipw), abs(tau_reg), 1e-12)
    overlap = ci_ipw[0] <= ci_reg[1] and ci_reg[0] <= ci_ipw[1]
    validated = bool(same_sign and (rel_gap < 0.5 or overlap))
    return {"variable": j, "rule": rule, "ps_model": name, "n_after_trim": int(n),
            "max_smd_weighted": smd, "tau_ipw": float(tau_ipw), "ci_ipw": ci_ipw.tolist(),
            "tau_regression": float(tau_reg), "ci_regression": ci_reg.tolist(),
            "same_sign": bool(same_sign), "relative_gap": float(rel_gap), "ci_overlap": bool(overlap),
            "status": "validated" if validated else "not validated (triangulation failed)",
            "c_j": float(abs((tau_ipw + tau_reg) / 2)) if validated else None,
            "c_j_interval": abs_interval(min(ci_ipw[0], ci_reg[0]), max(ci_ipw[1], ci_reg[1])) if validated else None}


def abs_interval(lo, hi):
    """Interval of |effect| implied by a signed interval [lo, hi]."""
    if lo <= 0 <= hi:
        return [0.0, float(max(abs(lo), abs(hi)))]
    return [float(min(abs(lo), abs(hi))), float(max(abs(lo), abs(hi)))]


def tied_causal_ranks(V, c, intervals):
    """Causal ranks where variables with overlapping |effect| intervals share a rank.

    Variables are sorted by decreasing c_j and chained into groups while each interval overlaps
    the previous one; every member of a group receives the group's mean position. This prevents
    C from rewarding or penalising an ordering that the causal estimates cannot resolve."""
    order = sorted(V, key=lambda v: -c[v])
    groups, current = [], [order[0]]
    for v in order[1:]:
        prev = current[-1]
        if intervals[v][1] >= intervals[prev][0]:  # overlap with the previous (larger) effect
            current.append(v)
        else:
            groups.append(current)
            current = [v]
    groups.append(current)
    ranks, pos = {}, 1
    for g in groups:
        mean_pos = pos + (len(g) - 1) / 2
        for v in g:
            ranks[v] = mean_pos
        pos += len(g)
    return ranks, groups


def level3(X, y, imps, studied, seed, n_boot, smd_thr, k):
    effects = [causal_effect(X, y, j, seed, n_boot, smd_thr) for j in studied]
    for e in effects:
        log(f"    L3 {e['variable']}: {e['status']}")
    V = [e["variable"] for e in effects if e["status"] == "validated"]
    c = {e["variable"]: e["c_j"] for e in effects if e["status"] == "validated"}
    iv = {e["variable"]: e["c_j_interval"] for e in effects if e["status"] == "validated"}
    tie_ranks, tie_groups = tied_causal_ranks(V, c, iv) if V else ({}, [])
    cols = list(X.columns)
    scores = {}
    for m, imp in imps.items():
        if len(V) < 3:
            scores[m] = {"status": "Not Evaluable", "reason": f"only {len(V)} causally validated variables (< 3)"}
            continue
        im = np.array([imp[cols.index(v)] for v in V])
        cv = np.array([c[v] for v in V])
        kk = min(k, len(V))
        top_m = set(np.array(V)[np.argsort(-im)[:kk]])
        top_c = set(np.array(V)[np.argsort(-cv)[:kk]])
        tie_r = np.array([tie_ranks[v] for v in V])
        scores[m] = {"C_spearman": float(spearmanr(im, cv).statistic),
                     "C_spearman_tie_aware": float(spearmanr(im, -tie_r).statistic),
                     "C_jaccard_top_k": len(top_m & top_c) / len(top_m | top_c), "k": kk,
                     "method_rank_within_V": [V[i] for i in np.argsort(-im)]}
    return {"effects": effects, "validated_set": V, "causal_tie_groups": tie_groups, "scores": scores}


# ----------------------------------------------------------------------------- routing
PROFILES = {
    "P1_real_time":   {"latency_ms": 30,   "memory_kb": 2048,   "w": (0.2, 0.6, 0.2), "tier": "181 synchronous real time"},
    "P2_interactive": {"latency_ms": 50,   "memory_kb": 8192,   "w": (0.5, 0.3, 0.2), "tier": "182 synchronous interactive"},
    "P3_causal":      {"latency_ms": None, "memory_kb": 262144, "w": (0.2, 0.2, 0.6), "tier": "183 asynchronous queue"},
    "P4_audit":       {"latency_ms": None, "memory_kb": None,   "w": (1/3, 1/3, 1/3), "tier": "184 batch audit"},
}


def route(registry, profile, available_kb, safety_kb=0.0):
    wF, wS, wC = profile["w"]
    best, best_score = None, -np.inf
    eligible = []
    for m, r in registry.items():
        if r.get("model_eligible") is False:  # method not applicable to this model family
            continue
        if profile["latency_ms"] is not None and r["L_p95_ms"] > profile["latency_ms"]:
            continue
        mem_cap = min(x for x in (profile["memory_kb"], available_kb - safety_kb) if x is not None)
        if r["M_kb"] > mem_cap:
            continue
        eligible.append(m)
        # Not Evaluable scores contribute 0 and are reported, never imputed as evidence
        score = wF * (r["F"] or 0) + wS * (r["S"] or 0) + wC * (r["C"] or 0)
        if score > best_score or (score == best_score and r["L_p95_ms"] < registry[best]["L_p95_ms"]):
            best, best_score = m, score
    return {"eligible": eligible, "selected": best, "score": None if best is None else float(best_score),
            "fallback": "S90: degrade to lowest-latency method and/or enqueue in 185" if best is None else None}


# ----------------------------------------------------------------------------- models
def make_model(kind: str, seed: int):
    """Predictive model on the 30 raw administrative codes. Non-tree models one-hot encode them
    internally, so every explanation method still works on the same 30 input variables."""
    if kind == "xgb":
        return xgb.XGBRegressor(n_estimators=400, max_depth=8, learning_rate=0.08, subsample=0.8,
                                colsample_bytree=0.8, tree_method="hist", random_state=seed, n_jobs=-1)
    enc = OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=50, sparse_output=True)
    if kind == "ridge":
        return make_pipeline(enc, Ridge(alpha=1.0))
    if kind == "mlp":
        return make_pipeline(enc, MLPRegressor(hidden_layer_sizes=(64, 32), batch_size=1024, max_iter=30,
                                               early_stopping=True, n_iter_no_change=3, random_state=seed))
    raise ValueError(kind)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-eval", type=int, default=20000)
    ap.add_argument("--n-l3", type=int, default=60000)
    ap.add_argument("--R", type=int, default=20)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--p-swap", type=float, default=0.05)
    ap.add_argument("--k-top", type=int, default=5)
    ap.add_argument("--boot", type=int, default=50)
    ap.add_argument("--no-retrain", action="store_true")
    ap.add_argument("--max-cells", type=int, default=2_500_000,
                    help="uniform random sample of cohort cells used for modelling (None = all)")
    ap.add_argument("--model", choices=["xgb", "ridge", "mlp"], default="xgb")
    a = ap.parse_args()
    global METHODS
    METHODS = TREE_METHODS if a.model == "xgb" else NON_TREE_METHODS
    a.out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    X, y, flow = load(a.csv, a.max_cells, a.seed)
    log(f"flow: {flow}, features: {X.shape[1]}")
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=a.seed)
    model = make_model(a.model, a.seed)
    t0 = time.time()
    model.fit(X_tr, y_tr)
    fit_s = time.time() - t0
    pred_tr, pred_te = model.predict(X_tr), model.predict(X_te)
    perf = {"train_r2": float(r2_score(y_tr, pred_tr)), "test_r2": float(r2_score(y_te, pred_te)),
            "test_rmse_log": float(np.sqrt(mean_squared_error(y_te, pred_te))),
            "test_mae_log": float(np.mean(np.abs(y_te - pred_te))),
            "family": a.model, "fit_seconds": fit_s}
    log(f"model: {perf}")

    X_ev = X_te.sample(min(a.n_eval, len(X_te)), random_state=a.seed)
    y_ev = y_te.loc[X_ev.index]
    lib = Library(model, X_tr, X_ev, y_ev, a.seed)
    imps = {}
    for m in METHODS:
        t0 = time.time()
        imps[m] = lib.importance(m, X_ev)
        log(f"importance {m} computed in {time.time() - t0:.1f}s")
    top_by_method = {m: [X.columns[i] for i in ranking(v)[:10]] for m, v in imps.items()}

    log("Level I")
    L1 = level1(lib, model, X_tr, y_tr, X_ev, y_ev, imps, [1, 3, 5, 10], 20, not a.no_retrain, a.seed)
    log("Level II")
    L2 = level2(lib, X_ev, y_ev, X_tr, imps, a.R, a.alpha, a.p_swap, a.k_top, a.seed, n_eval=3000)
    PR = profile(lib, X_ev, 50, a.seed)

    log("Level III")
    studied = list(dict.fromkeys(c for m in METHODS for c in top_by_method[m][:8]))
    if "REFERRAL_DIV" not in studied:
        studied.append("REFERRAL_DIV")
    X3 = X.sample(min(a.n_l3, len(X)), random_state=a.seed)
    L3 = level3(X3, y.loc[X3.index], imps, studied, a.seed, a.boot, 0.1, a.k_top)

    registry = {}
    for m in METHODS:
        s2, s3 = L2[m], L3["scores"][m]
        registry[m] = {"F": L1["methods"][m]["F"],
                       "S": s2.get("S_jaccard"), "S_status": s2.get("status", "evaluated"),
                       "C": s3.get("C_spearman"), "C_status": s3.get("status", "evaluated"),
                       "C_tie_aware": s3.get("C_spearman_tie_aware"),
                       "L_median_ms": PR[m]["latency_ms_median"], "L_p95_ms": PR[m]["latency_ms_p95"],
                       "M_kb": PR[m]["memory_kb_peak_median"],
                       "model_version": f"{a.model}-seed{a.seed}",
                       "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if a.model != "xgb":
        for m in TREE_ONLY:
            registry[m] = {"model_eligible": False, "F": None, "S": None, "C": None, "C_tie_aware": None,
                           "status": f"Not Evaluable: {m} requires a tree-based model ({a.model} given)",
                           "model_version": f"{a.model}-seed{a.seed}"}
    cascade = {"F_min": 0.5, "S_min": 0.6}
    cascade["passed_to_level3"] = [m for m, r in registry.items() if r.get("model_eligible", True)
                                   and r["F"] >= cascade["F_min"] and (r["S"] or 0) >= cascade["S_min"]]

    available_kb = 4 * 1024 * 1024
    routing = {}
    for name, prof in PROFILES.items():
        t0 = time.perf_counter()
        for _ in range(1000):
            res = route(registry, prof, available_kb)
        res["routing_overhead_us"] = (time.perf_counter() - t0) / 1000 * 1e6
        res["tier"] = prof["tier"]
        routing[name] = res
    routing["overload_example"] = {"cpu_or_ram_above_80pct": True, **route(registry, PROFILES["P2_interactive"], 4096, 4096)}
    # Same routing with the tie-aware causal-alignment score (C differences that the causal
    # estimates cannot resolve no longer drive the selection)
    registry_tie = {m: {**r, "C": r["C_tie_aware"]} for m, r in registry.items()}
    routing_tie = {name: {**route(registry_tie, prof, available_kb), "tier": prof["tier"]}
                   for name, prof in PROFILES.items()}

    report = {"data": {"source": str(a.csv), "unit": "aggregated Open DAMIR cell",
                       "target": "log1p(PRS_REM_MNT / PRS_ACT_QTE), EUR reimbursed per act",
                       "n_cells": int(len(X)), "flow": flow, "features": list(X.columns),
                       "excluded_for_leakage": LEAKAGE_EXCLUDED},
              "model": perf, "top10_by_method": top_by_method, "level1": L1, "level2": L2,
              "profiling": PR, "level3": L3, "registry": registry, "cascade": cascade,
              "routing": routing, "routing_tie_aware_C": routing_tie,
              "global_importances": {m: dict(zip(X.columns, map(float, v))) for m, v in imps.items()},
              "runtime_s": time.time() - t_start}
    (a.out / "valex_report.json").write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")
    (a.out / "score_registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    log(f"done in {report['runtime_s']:.0f}s -> {a.out}")


if __name__ == "__main__":
    main()
