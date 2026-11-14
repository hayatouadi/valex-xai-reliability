# VALEX 1.0: reliability audit of post-hoc explanations on French health-insurance claims

Code and results for:

- **H. Ouadi, I. El Farissi.** *Auditing the reliability of post-hoc explanations for health-insurance decision support: Leakage, faithfulness, stability and cost on 228 million claims.* Submitted to *Decision Support Systems* (Elsevier).
- **H. Ouadi.** *VALEX 1.0: A Multi-Level Evaluation Framework for Trustworthy AI in Decision Support Systems. Explanatory Faithfulness, Perturbation Robustness and Observational Causal Alignment.* PhD thesis, Mohammed First University, Oujda, Morocco, 2026.

VALEX evaluates explanation methods (tree gain importance, permutation importance, TreeSHAP, LIME, PermSHAP) at three levels:

| Level | Question | Score |
|---|---|---|
| I. Faithfulness | Do the top-ranked variables matter more to the model than random variables? | F (random baseline, fixed-model intervention; remove-and-retrain reported separately) |
| II. Robustness and feasibility | Is the ranking stable under a realistic perturbation operator, and what does it cost? | S (top-5 Jaccard, Spearman), latency (median, p95), peak memory |
| III. Observational causal alignment | Are the emphasised variables compatible with balance-checked causal estimates? | C (raw and tie-aware Spearman) |

Explainers that a protocol cannot validly test are reported as **Not Evaluable**. The scores feed a registry and a resource-aware routing engine (real-time, interactive, asynchronous, batch tiers).

## Repository layout

```
src/pipeline/   valex_unified_pipeline.py        data loading, leakage exclusion, model, explanations,
                                                 Levels I-III, score registry, routing
                leakage_controlled_experiment.py same pipeline with the 12 leaking columns restored (E1)
src/referral/   ch7_referral_causal_alignment.py stratified kNN propensity-score matching study of the
                                                 referral-related exposure + model-implied effect (thesis ch. 4)
                reviewer_sensitivity.py          alternative exposure definitions (sensitivity)
src/analysis/   reliability_paper_tables.py      every number of the DSS paper -> results/valex/reliability_paper_tables.*
                compare_runs.py                  comparison across months, seeds and model families
src/figures/    make_figures.py, make_diagrams.py, paper_figures.py, make_thesis_figures.py,
                ch7_figures.py, reviewer_figures.py
results/valex/     one folder per run: valex_report.json (all scores) + score_registry.json
results/referral/  one folder per month: ch7_report.json, balance_table.csv, sensitivity_grid.csv;
                   reviewer_*: sensitivity analyses; _truncated_extract: the spreadsheet-truncated copy
data/           instructions to download the Open DAMIR files (not redistributed here) + SHA-256 checksums
```

The `results/` folder contains the outputs used in the paper and the thesis, so every table and figure can be rebuilt **without** re-running the pipeline.

## Installation

Python 3.14 (tested on Windows 11, 14 logical cores, 31 GB RAM).

```bash
pip install -r requirements.txt
```

## Reproducing the tables and figures from the stored results (minutes)

```bash
python src/analysis/reliability_paper_tables.py results/valex
python src/analysis/compare_runs.py results/valex results/referral
python src/figures/make_figures.py        # -> figures/report
python src/figures/make_diagrams.py       # -> figures/thesis
python src/figures/paper_figures.py       # -> figures/paper (DSS paper figures)
python src/figures/make_thesis_figures.py # -> figures/thesis
python src/figures/ch7_figures.py results/referral/ch7_full
python src/figures/reviewer_figures.py
```

Run them in this order: `paper_figures.py` and `make_thesis_figures.py` reuse figures written by the previous scripts.

## Re-running the experiments from the raw data (hours)

Download the monthly flows described in [data/README.md](data/README.md) into `data/`, then:

```bash
# reference audit, January 2024 (E2), seed 42
python src/pipeline/valex_unified_pipeline.py --csv data/A202401.csv.gz --out results/valex/valex_unified_full
# controlled leakage experiment (E1)
python src/pipeline/leakage_controlled_experiment.py --csv data/A202401.csv.gz --out results/valex/valex_leaky_2024_01 --seed 42 --n-l3 20000
# seeds 1-4 (E3)
python src/pipeline/valex_unified_pipeline.py --csv data/A202401.csv.gz --out results/valex/valex_xgb_2024_01_seed1 --seed 1
# months (E4): A202301, A202404, A202407, A202410, A202501
python src/pipeline/valex_unified_pipeline.py --csv data/A202404.csv.gz --out results/valex/valex_unified_2024_04
# model families (E5)
python src/pipeline/valex_unified_pipeline.py --csv data/A202401.csv.gz --out results/valex/valex_mlp_2024_01 --model mlp --max-cells 500000
python src/pipeline/valex_unified_pipeline.py --csv data/A202401.csv.gz --out results/valex/valex_ridge_2024_01 --model ridge --max-cells 500000
# referral-exposure study (thesis chapter 4 and 6), one run per month
python src/referral/ch7_referral_causal_alignment.py --csv data/A202401.csv.gz --out results/referral/ch7_full
python src/referral/reviewer_sensitivity.py --csv data/A202401.csv.gz --out results/referral/reviewer_2024_01
```

`scripts/reproduce_all.sh` chains every command. One pipeline run takes 10 to 75 minutes on the hardware above; the matching study about 15 minutes per month. Latency and memory values depend on the hardware and on the load of the machine.

Main settings (defaults of the scripts): 2.5 million cells sampled uniformly per month, 80/20 split, XGBoost (400 trees, depth 8, learning rate 0.08, subsampling 0.8, hist); Level I on 20,000 test cells with k in {1, 3, 5, 10} and 20 random draws, modal replacement value; Level II with alpha = 0.05, p = 0.05, R = 20 (5 for LIME), top-5 Jaccard; Level III on 60,000 cells, PS trimming [0.05, 0.95], |SMD| < 0.1, triangulation of IPW and regression adjustment; matching study with exact strata act nature x sector, 5 nearest neighbours with replacement, caliper 0.2 SD of logit(PS), 100 within-stratum placebos.

## Data

The study uses only **Open DAMIR**, the open-data release of French inter-regime health-insurance expenditure published by the Caisse nationale de l'Assurance Maladie under the *Licence Ouverte / Open Licence* (Etalab). Each record is an aggregated cell of acts; the files contain no personal data and no patient identifier.

- **Monthly files of 2024** (January 2024, `A202401.csv.gz`, is the reference month of the study): https://open-data-assurance-maladie.ameli.fr/depenses/download.php?Dir_Rep=Open_DAMIR&Annee=2024
- **All years and documentation**: https://www.data.gouv.fr/datasets/open-damir-base-complete-sur-les-depenses-dassurance-maladie-interregimes
- **Extract included in this repository**: `data/A202401_extract_200k.csv.gz` (5.6 MB), a uniform random sample of 199,565 records of January 2024, in the original format. It lets you run every script in a few minutes; the published values require the complete monthly files.

The complete files (about 1 GB each, compressed) are not redistributed here; see [data/README.md](data/README.md) for the list of files and their SHA-256 checksums.

### Quick test on the extract (a few minutes)

```bash
python src/pipeline/valex_unified_pipeline.py --csv data/A202401_extract_200k.csv.gz --out results_test/valex \
    --max-cells 50000 --n-eval 2000 --n-l3 5000 --R 3 --boot 5 --no-retrain
python src/referral/ch7_referral_causal_alignment.py --csv data/A202401_extract_200k.csv.gz --out results_test/referral \
    --boot 20 --placebo 5 --shap-sample 5000
```

Results on the extract differ from the published ones: the sample is 190 times smaller and the settings are reduced.

## Intellectual property and licence

The multi-level evaluation and tiered orchestration method is the subject of Moroccan patent application No. 76638 (OMPIC, filed 13 October 2026). The code is released for research and for the verification of the published results under the terms of [LICENSE](LICENSE).

## How to cite

See [CITATION.cff](CITATION.cff).
