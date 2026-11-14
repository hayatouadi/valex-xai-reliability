"""Controlled leakage experiment for the reliability paper.

Runs valex_unified_pipeline.py unchanged, on the same complete monthly flow and the same random
sample (same seed), but with the target-leaking columns put back among the inputs, exactly as in
the earlier campaign. Comparing its report with the leakage-free run isolates the effect of
leakage on Levels I and II (all other factors are held fixed).

Usage (same arguments as the pipeline):
    python code/leakage_controlled_experiment.py --csv ../../THESIS_SKELETON/A202401.csv.gz \
        --out outputs/valex_leaky_2024_01 --seed 42 --n-l3 20000
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import valex_unified_pipeline as vp  # noqa: E402

# Leaking columns (components or copies of the reimbursed amount, or act counts). PRS_REM_MNT is the
# target numerator and PRS_ACT_QTE its denominator; both are already read by the pipeline, so the
# remaining leaking columns are added here as continuous inputs.
LEAKY = ["PRS_REM_BSE", "PRS_REM_TAU", "PRS_PAI_MNT", "PRS_DEP_MNT", "PRS_ACT_NBR", "PRS_ACT_COG",
         "FLT_ACT_COG", "FLT_ACT_NBR", "FLT_ACT_QTE", "FLT_PAI_MNT", "FLT_DEP_MNT", "FLT_REM_MNT"]
ORDINAL_CODES = list(vp.ORDINAL)
vp.ORDINAL = ORDINAL_CODES + LEAKY  # read, kept as inputs, perturbed with alpha * sigma noise


def perturb(X, X_ref, alpha, p, rng):
    """Same operator as the pipeline; continuous leaking columns are not rounded."""
    Xp = X.copy()
    for c in vp.ORDINAL:
        sd = X_ref[c].std()
        lo, hi = X_ref[c].min(), X_ref[c].max()
        noisy = X[c] + rng.normal(0, alpha * sd, len(X))
        Xp[c] = np.clip(noisy if c in LEAKY else np.round(noisy), lo, hi)
    pool = {c: X_ref[c].to_numpy() for c in vp.NOMINAL + ["REFERRAL_DIV"]}
    for c, vals in pool.items():
        swap = rng.random(len(X)) < p
        Xp.loc[swap, c] = rng.choice(vals, swap.sum())
    return Xp


vp.perturb = perturb

if __name__ == "__main__":
    vp.main()
