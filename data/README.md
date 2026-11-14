# Data: Open DAMIR monthly flows

The experiments use six complete monthly flows of **Open DAMIR** (*base complète sur les dépenses d'assurance maladie inter-régimes*), published as open data by the Caisse nationale de l'Assurance Maladie:

- Monthly files of 2024: https://open-data-assurance-maladie.ameli.fr/depenses/download.php?Dir_Rep=Open_DAMIR&Annee=2024
- Monthly files of 2025: https://open-data-assurance-maladie.ameli.fr/depenses/download.php?Dir_Rep=Open_DAMIR&Annee=2025
- All years and documentation: https://www.data.gouv.fr/datasets/open-damir-base-complete-sur-les-depenses-dassurance-maladie-interregimes

Licence: *Licence Ouverte / Open Licence* (Etalab). Source: Caisse nationale de l'Assurance Maladie, Open DAMIR.

## Extract included in this repository

`A202401_extract_200k.csv.gz` (5.6 MB) is a uniform random sample of 199,565 records of `A202401.csv.gz` (each record kept with probability 200,000 / 38,758,176, random seed 42), with the original header and format. It is redistributed under the Licence Ouverte, with the source above. It is meant to test the scripts quickly; the published values require the complete files.

## Complete files used in the study

| File | Month | Records | Role |
|---|---|---|---|
| `A202301.csv.gz` | January 2023 | 37,658,818 | temporal replication |
| `A202401.csv.gz` | January 2024 | 38,758,176 | reference month, seeds, model families, leakage experiment |
| `A202404.csv.gz` | April 2024 | 36,248,691 | temporal replication |
| `A202407.csv.gz` | July 2024 | 39,730,422 | temporal replication |
| `A202410.csv.gz` | October 2024 | 39,075,646 | temporal replication |
| `A202501.csv.gz` | January 2025 | 36,640,259 | temporal replication |

Download the files from the page above (one archive per month), and place them in this folder under the names shown. The files are not redistributed in this repository because of their size (about 1 GB each, compressed); check the licence terms on the dataset page before any reuse.

Each record is an aggregated cell (all acts sharing the same combination of about fifty administrative attributes). The files contain no personal data and no patient identifier.

## Checksums

`SHA256SUMS.txt` gives the SHA-256 of the files used in the study, so that you can check that you have the same release:

```bash
sha256sum -c SHA256SUMS.txt
```

The October 2024 file is not listed: it was deleted after the run, before checksums were recorded. Its record count (39,075,646) is stored in `results/valex/valex_unified_2024_10/valex_report.json`.

## The spreadsheet-truncated copy

An earlier analysis used a copy of January 2024 truncated at 1,048,575 rows (the row limit of a spreadsheet). Its results are kept in `results/referral/_truncated_extract/` to document how the conclusions changed with the complete file (thesis, section 4.7).
