# Reliability paper — extracted numbers

## Jan 2023 (test R2 = 0.9193; random d1/d10 = 0.032/1.208)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 0.786 | 2.620 | 0.129 | 4.548 | 0.654 | NE | — | — | 5.4 | 7.0 | 9.6 | 0.35 | PSE_ACT_CAT, PRS_NAT, PRS_PPU_SEC |
| PFI | 0.968 | 3.227 | 2.604 | 4.318 | 0.643 | 1.000 | 0.000 | 0.976 | 2457.9 | 2480.5 | 943.5 | 0.73 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| TreeSHAP | 0.988 | 3.295 | 2.604 | 4.419 | 0.662 | 1.000 | 0.000 | 0.996 | 43.5 | 44.4 | 28.3 | 0.53 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 1.000 | 3.334 | 2.604 | 4.367 | 0.603 | 0.733 | 0.133 | 0.953 | 45.7 | 47.9 | 683.8 | 0.18 | PRS_NAT, EXO_MTF, PSE_ACT_CAT |

Agreement: TFI-PFI rho=0.87 J5=0.43; TFI-TreeSHAP rho=0.80 J5=0.67; TFI-LIME rho=0.64 J5=0.43; PFI-TreeSHAP rho=0.91 J5=0.67; PFI-LIME rho=0.60 J5=0.43; TreeSHAP-LIME rho=0.53 J5=0.43

## Jan 2024 (test R2 = 0.9219; random d1/d10 = 0.030/1.148)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 0.740 | 2.411 | 0.142 | 3.844 | 0.646 | NE | — | — | 3.1 | 5.7 | 9.6 | 0.37 | PSE_ACT_CAT, PRS_NAT, PRS_PPU_SEC |
| PFI | 1.000 | 3.258 | 2.406 | 4.329 | 0.715 | 0.833 | 0.167 | 0.978 | 1745.1 | 1772.2 | 941.8 | 0.75 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| TreeSHAP | 0.945 | 3.079 | 2.406 | 3.957 | 0.734 | 1.000 | 0.000 | 0.999 | 33.8 | 36.4 | 28.3 | 0.54 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 0.973 | 3.172 | 2.406 | 4.161 | 0.607 | 0.819 | 0.234 | 0.909 | 32.7 | 34.0 | 683.7 | 0.15 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |

Agreement: TFI-PFI rho=0.81 J5=0.43; TFI-TreeSHAP rho=0.75 J5=0.67; TFI-LIME rho=0.51 J5=0.43; PFI-TreeSHAP rho=0.89 J5=0.43; PFI-LIME rho=0.59 J5=0.67; TreeSHAP-LIME rho=0.42 J5=0.43

## Apr 2024 (test R2 = 0.9150; random d1/d10 = 0.023/0.712)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 1.000 | 1.544 | 1.678 | 1.891 | 0.690 | NE | — | — | 2.4 | 3.9 | 9.6 | 0.32 | PRS_NAT, PSE_ACT_CAT, PRS_PPU_SEC |
| PFI | 0.986 | 1.522 | 1.678 | 1.930 | 0.693 | 1.000 | 0.000 | 0.970 | 1291.8 | 1388.0 | 940.5 | 0.84 | PRS_NAT, EXO_MTF, ETE_CAT_SNDS |
| TreeSHAP | 0.995 | 1.537 | 1.678 | 1.877 | 0.702 | 0.917 | 0.144 | 0.998 | 19.8 | 21.0 | 28.3 | 0.61 | PRS_NAT, EXO_MTF, PSE_ACT_CAT |
| LIME | 0.904 | 1.396 | 1.678 | 1.684 | 0.550 | 0.867 | 0.163 | 0.908 | 23.7 | 31.6 | 683.7 | 0.17 | PRS_NAT, ETE_CAT_SNDS, EXO_MTF |

Agreement: TFI-PFI rho=0.90 J5=0.43; TFI-TreeSHAP rho=0.77 J5=0.67; TFI-LIME rho=0.49 J5=0.25; PFI-TreeSHAP rho=0.89 J5=0.43; PFI-LIME rho=0.43 J5=0.43; TreeSHAP-LIME rho=0.31 J5=0.25

## Jul 2024 (test R2 = 0.9175; random d1/d10 = 0.034/0.747)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 0.730 | 1.164 | 0.186 | 2.028 | 0.648 | NE | — | — | 6.2 | 7.2 | 9.6 | 0.36 | PSE_ACT_CAT, PRS_NAT, PSP_ACT_CAT |
| PFI | 1.000 | 1.596 | 1.625 | 2.074 | 0.652 | 0.767 | 0.153 | 0.972 | 2425.2 | 2456.8 | 941.0 | 0.76 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| TreeSHAP | 0.992 | 1.583 | 1.625 | 2.053 | 0.641 | 1.000 | 0.000 | 0.997 | 40.8 | 42.9 | 28.3 | 0.53 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 0.965 | 1.540 | 1.625 | 1.943 | 0.608 | 0.733 | 0.133 | 0.932 | 44.1 | 47.0 | 684.0 | 0.18 | PRS_NAT, ETE_CAT_SNDS, PSE_ACT_CAT |

Agreement: TFI-PFI rho=0.83 J5=0.43; TFI-TreeSHAP rho=0.80 J5=0.67; TFI-LIME rho=0.55 J5=0.43; PFI-TreeSHAP rho=0.93 J5=0.67; PFI-LIME rho=0.60 J5=0.67; TreeSHAP-LIME rho=0.53 J5=0.67

## Oct 2024 (test R2 = 0.9166; random d1/d10 = 0.033/0.745)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 0.746 | 1.175 | 0.149 | 2.054 | 0.645 | NE | — | — | 2.3 | 3.7 | 9.6 | 0.38 | PSE_ACT_CAT, PRS_NAT, PSP_ACT_CAT |
| PFI | 1.000 | 1.577 | 1.630 | 2.026 | 0.665 | 1.000 | 0.000 | 0.942 | 1147.3 | 1202.5 | 942.2 | 0.75 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| TreeSHAP | 0.999 | 1.576 | 1.630 | 1.992 | 0.731 | 1.000 | 0.000 | 0.998 | 22.5 | 24.7 | 28.3 | 0.53 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 0.922 | 1.454 | 1.630 | 1.931 | 0.619 | 0.800 | 0.163 | 0.918 | 22.0 | 24.3 | 683.9 | 0.18 | PRS_NAT, ETE_CAT_SNDS, EXO_MTF |

Agreement: TFI-PFI rho=0.82 J5=0.43; TFI-TreeSHAP rho=0.82 J5=0.67; TFI-LIME rho=0.63 J5=0.43; PFI-TreeSHAP rho=0.88 J5=0.67; PFI-LIME rho=0.65 J5=0.67; TreeSHAP-LIME rho=0.54 J5=0.67

## Jan 2025 (test R2 = 0.9164; random d1/d10 = 0.033/1.183)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 0.810 | 2.807 | 0.155 | 4.425 | 0.626 | NE | — | — | 8.7 | 143.1 | 9.6 | 0.40 | PSE_ACT_CAT, PRS_NAT, PRS_PPU_SEC |
| PFI | 0.980 | 3.396 | 2.250 | 4.289 | 0.626 | 0.817 | 0.166 | 0.984 | 1609.0 | 2749.0 | 943.0 | 0.72 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| TreeSHAP | 1.000 | 3.467 | 2.250 | 4.320 | 0.631 | 1.000 | 0.000 | 0.987 | 26.3 | 47.0 | 28.3 | 0.51 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 0.999 | 3.462 | 2.250 | 4.439 | 0.576 | 0.733 | 0.133 | 0.928 | 26.2 | 29.3 | 683.8 | 0.14 | PRS_NAT, EXO_MTF, PSE_ACT_CAT |

Agreement: TFI-PFI rho=0.86 J5=0.43; TFI-TreeSHAP rho=0.85 J5=0.67; TFI-LIME rho=0.63 J5=0.67; PFI-TreeSHAP rho=0.96 J5=0.67; PFI-LIME rho=0.54 J5=0.67; TreeSHAP-LIME rho=0.49 J5=0.67

## Jan 2024 s1 (test R2 = 0.9224; random d1/d10 = 0.013/1.501)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 0.817 | 2.700 | 0.176 | 4.446 | — | NE | — | — | 2.0 | 2.7 | 9.6 | 0.42 | PSE_ACT_CAT, PRS_NAT, PRS_PPU_SEC |
| PFI | 0.994 | 3.286 | 2.516 | 4.273 | — | 0.917 | 0.144 | 0.984 | 1256.4 | 1304.6 | 937.3 | 0.72 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| TreeSHAP | 0.999 | 3.302 | 2.516 | 4.291 | — | 1.000 | 0.000 | 0.997 | 25.7 | 26.9 | 28.3 | 0.53 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 1.000 | 3.306 | 2.516 | 4.366 | — | 0.619 | 0.095 | 0.878 | 21.5 | 22.5 | 684.0 | 0.15 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |

Agreement: TFI-PFI rho=0.84 J5=0.43; TFI-TreeSHAP rho=0.72 J5=0.67; TFI-LIME rho=0.61 J5=0.43; PFI-TreeSHAP rho=0.88 J5=0.43; PFI-LIME rho=0.55 J5=0.43; TreeSHAP-LIME rho=0.47 J5=0.43

## Jan 2024 s2 (test R2 = 0.9217; random d1/d10 = 0.011/1.118)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 0.787 | 2.486 | 0.203 | 4.278 | — | NE | — | — | 2.7 | 3.1 | 9.6 | 0.41 | PSE_ACT_CAT, PRS_NAT, PRS_PPU_SEC |
| PFI | 1.000 | 3.160 | 2.517 | 4.315 | — | 0.933 | 0.133 | 0.976 | 1294.3 | 1310.0 | 935.2 | 0.68 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| TreeSHAP | 0.994 | 3.141 | 2.517 | 4.315 | — | 1.000 | 0.000 | 0.997 | 19.4 | 20.4 | 28.2 | 0.52 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 0.951 | 3.007 | 2.517 | 4.128 | — | 0.867 | 0.163 | 0.906 | 20.7 | 25.0 | 683.7 | 0.15 | PRS_NAT, PSE_ACT_CAT, MDT_TYP_COD |

Agreement: TFI-PFI rho=0.78 J5=0.43; TFI-TreeSHAP rho=0.71 J5=0.67; TFI-LIME rho=0.56 J5=0.43; PFI-TreeSHAP rho=0.93 J5=0.43; PFI-LIME rho=0.34 J5=0.43; TreeSHAP-LIME rho=0.34 J5=0.43

## Jan 2024 s3 (test R2 = 0.9222; random d1/d10 = 0.150/1.184)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 0.765 | 2.368 | 0.194 | 4.108 | — | NE | — | — | 6.8 | 7.6 | 9.6 | 0.39 | PSE_ACT_CAT, PRS_NAT, PRS_PPU_SEC |
| PFI | 1.000 | 3.095 | 2.595 | 4.359 | — | 0.900 | 0.153 | 0.974 | 2501.3 | 2521.2 | 936.3 | 0.69 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| TreeSHAP | 0.980 | 3.033 | 2.595 | 4.199 | — | 1.000 | 0.000 | 0.998 | 42.9 | 45.3 | 28.3 | 0.53 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 0.949 | 2.938 | 2.595 | 3.896 | — | 0.686 | 0.182 | 0.915 | 47.6 | 49.3 | 683.7 | 0.15 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |

Agreement: TFI-PFI rho=0.87 J5=0.43; TFI-TreeSHAP rho=0.71 J5=0.67; TFI-LIME rho=0.61 J5=0.43; PFI-TreeSHAP rho=0.85 J5=0.43; PFI-LIME rho=0.54 J5=0.43; TreeSHAP-LIME rho=0.39 J5=0.43

## Jan 2024 s4 (test R2 = 0.9215; random d1/d10 = 0.149/1.134)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 0.743 | 2.413 | 0.101 | 4.232 | — | NE | — | — | 6.5 | 7.5 | 9.6 | 0.31 | PSE_ACT_CAT, PRS_NAT, PRS_PPU_SEC |
| PFI | 0.979 | 3.180 | 2.530 | 4.358 | — | 0.983 | 0.073 | 0.984 | 2412.8 | 2440.7 | 936.7 | 0.74 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| TreeSHAP | 1.000 | 3.248 | 2.530 | 4.663 | — | 1.000 | 0.000 | 0.999 | 43.2 | 45.0 | 28.3 | 0.53 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 0.952 | 3.091 | 2.530 | 4.127 | — | 0.867 | 0.163 | 0.922 | 48.4 | 49.2 | 683.5 | 0.15 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |

Agreement: TFI-PFI rho=0.83 J5=0.67; TFI-TreeSHAP rho=0.82 J5=0.67; TFI-LIME rho=0.56 J5=0.67; PFI-TreeSHAP rho=0.94 J5=0.67; PFI-LIME rho=0.54 J5=0.67; TreeSHAP-LIME rho=0.41 J5=0.67

## MLP Jan 2024 (test R2 = 0.9200; random d1/d10 = 0.032/1.369)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PFI | 1.000 | 3.421 | 2.951 | 4.441 | 0.716 | 0.933 | 0.133 | 0.926 | 6871.6 | 6981.0 | 1475.6 | 0.82 | PRS_NAT, EXO_MTF, PSE_ACT_CAT |
| PermSHAP | 1.000 | 3.420 | 2.951 | 4.440 | 0.736 | 0.800 | 0.163 | 0.961 | 701.3 | 738.3 | 2184.8 | 0.51 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 0.967 | 3.309 | 2.951 | 4.142 | 0.618 | 0.752 | 0.220 | 0.954 | 105.1 | 107.6 | 889.4 | 0.15 | PRS_NAT, CPT_ENV_TYP, PSE_ACT_CAT |

Agreement: PFI-PermSHAP rho=0.91 J5=0.67; PFI-LIME rho=0.57 J5=0.67; PermSHAP-LIME rho=0.62 J5=0.67

## Ridge Jan 2024 (test R2 = 0.8829; random d1/d10 = 0.029/1.463)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PFI | 0.882 | 3.029 | 2.694 | 4.632 | 0.677 | 0.983 | 0.073 | 0.963 | 6316.3 | 6419.7 | 1230.9 | 0.75 | PRS_NAT, ETE_CAT_SNDS, PSE_ACT_CAT |
| PermSHAP | 1.000 | 3.435 | 2.694 | 4.568 | 0.674 | 1.000 | 0.000 | 0.979 | 587.1 | 602.8 | 1912.5 | 0.42 | PRS_NAT, PSE_ACT_CAT, EXO_MTF |
| LIME | 0.563 | 1.934 | 0.135 | 4.482 | 0.660 | 1.000 | 0.000 | 0.977 | 87.8 | 94.6 | 752.3 | 0.12 | ETE_CAT_SNDS, CPT_ENV_TYP, PRS_NAT |

Agreement: PFI-PermSHAP rho=0.90 J5=0.67; PFI-LIME rho=0.73 J5=0.67; PermSHAP-LIME rho=0.75 J5=0.43

## LEAKY Jan 2024 (test R2 = 0.9996; random d1/d10 = 0.242/1.898)

| Method | F | F_raw | d(k=1) | d(k=10) | RR R2 drop k=10 | S | S sd | Spearman | L med | L p95 | M KB | top-1 share | top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TFI | 1.000 | 4.302 | 4.496 | 5.109 | 0.067 | NE | — | — | 5.9 | 7.7 | 10.3 | 0.33 | FLT_REM_MNT, PRS_REM_BSE, FLT_ACT_QTE |
| PFI | 0.985 | 4.237 | 4.496 | 5.109 | 0.067 | 0.607 | 0.103 | 0.292 | 3853.1 | 3891.5 | 1138.8 | 0.66 | FLT_REM_MNT, FLT_ACT_QTE, PRS_REM_BSE |
| TreeSHAP | 0.997 | 4.290 | 4.496 | 5.051 | 0.508 | 0.667 | 0.000 | 0.919 | 47.0 | 48.2 | 39.7 | 0.48 | FLT_REM_MNT, FLT_ACT_QTE, PRS_REM_BSE |
| LIME | 0.681 | 2.928 | 4.496 | 3.412 | 0.007 | 0.686 | 0.182 | 0.897 | 46.3 | 49.0 | 919.8 | 0.23 | FLT_REM_MNT, FLT_ACT_QTE, ASU_NAT |

Agreement: TFI-PFI rho=0.77 J5=0.67; TFI-TreeSHAP rho=0.90 J5=0.67; TFI-LIME rho=0.24 J5=0.25; PFI-TreeSHAP rho=0.86 J5=0.67; PFI-LIME rho=0.33 J5=0.43; TreeSHAP-LIME rho=0.26 J5=0.25

## Across the 10 XGBoost runs (6 months + 4 extra seeds)

- PFI: F mean 0.991 sd 0.012 min 0.968; S mean 0.915 min 0.767; L p95 median 2106.4 ms [1202.5, 2749.0]
- TreeSHAP: F mean 0.989 sd 0.017 min 0.945; S mean 0.992 min 0.917; L p95 median 39.7 ms [20.4, 47.0]
- LIME: F mean 0.962 sd 0.033 min 0.904; S mean 0.772 min 0.619; L p95 median 32.8 ms [22.5, 49.3]
- TFI: F mean 0.792 sd 0.079 min 0.730; S mean nan min nan; L p95 median 6.4 ms [2.7, 143.1]
- lowest F per run: ['TFI', 'TFI', 'LIME', 'TFI', 'TFI', 'TFI', 'TFI', 'TFI', 'TFI', 'TFI']
- lowest S per run: ['LIME', 'LIME', 'LIME', 'LIME', 'LIME', 'LIME', 'LIME', 'LIME', 'LIME', 'LIME']
