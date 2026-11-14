#!/usr/bin/env bash
# Re-runs every experiment from the raw Open DAMIR files (several hours), then rebuilds tables and figures.
# Usage: bash scripts/reproduce_all.sh          (files expected in data/, see data/README.md)
#        bash scripts/reproduce_all.sh --tables  (only tables and figures, from the stored results)
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" != "--tables" ]]; then
  P=src/pipeline/valex_unified_pipeline.py
  python $P --csv data/A202401.csv.gz --out results/valex/valex_unified_full --seed 42
  python src/pipeline/leakage_controlled_experiment.py --csv data/A202401.csv.gz \
      --out results/valex/valex_leaky_2024_01 --seed 42 --n-l3 20000
  for s in 1 2 3 4; do
    python $P --csv data/A202401.csv.gz --out results/valex/valex_xgb_2024_01_seed$s --seed $s
  done
  for m in 2023_01 2024_04 2024_07 2024_10 2025_01; do
    python $P --csv data/A${m/_/}.csv.gz --out results/valex/valex_unified_$m
  done
  python $P --csv data/A202401.csv.gz --out results/valex/valex_mlp_2024_01 --model mlp --max-cells 500000
  python $P --csv data/A202401.csv.gz --out results/valex/valex_ridge_2024_01 --model ridge --max-cells 500000

  R=src/referral/ch7_referral_causal_alignment.py
  python $R --csv data/A202401.csv.gz --out results/referral/ch7_full
  for m in 2023_01 2024_04 2024_07 2024_10 2025_01; do
    python $R --csv data/A${m/_/}.csv.gz --out results/referral/ch7_$m
  done
  for m in 2024_01 2024_04 2024_07 2024_10; do
    python src/referral/reviewer_sensitivity.py --csv data/A${m/_/}.csv.gz --out results/referral/reviewer_$m
  done
fi

python src/analysis/reliability_paper_tables.py results/valex
python src/analysis/compare_runs.py results/valex results/referral
python src/figures/make_figures.py
python src/figures/make_diagrams.py
python src/figures/paper_figures.py
python src/figures/make_thesis_figures.py
python src/figures/ch7_figures.py results/referral/ch7_full
python src/figures/reviewer_figures.py
echo "done: tables in results/valex, figures in figures/"
