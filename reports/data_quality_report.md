# Data quality profile

Generated from the exact filtered CMS source extracts.

## 2022

- Rows: 1,944,541; columns: 22.
- Distinct brand/generic pairs: 197.
- Duplicate provider–brand–generic keys: 0.
- Suppressed/blank beneficiary counts: 1,328,157 (68.3% of rows).
- Total claims range: 11 to 3,718.

## 2023

- Rows: 2,116,541; columns: 22.
- Distinct brand/generic pairs: 199.
- Duplicate provider–brand–generic keys: 0.
- Suppressed/blank beneficiary counts: 1,413,504 (66.8% of rows).
- Total claims range: 11 to 5,956.

## 2024

- Rows: 2,254,990; columns: 22.
- Distinct brand/generic pairs: 188.
- Duplicate provider–brand–generic keys: 0.
- Suppressed/blank beneficiary counts: 1,456,920 (64.6% of rows).
- Total claims range: 11 to 6,531.

## Drug-scope audit

The version-controlled map classified 400 observed year/product combinations as included and 184 as non-drug devices or supplies. See `reports/drug_scope_audit.csv` for every observed brand/generic/year decision.

## Interpretation

CMS omits provider–drug cells with fewer than 11 claims and blanks beneficiary counts below 11. Accordingly, the extract is left-censored and beneficiary-based rates are incomplete. No suppressed value is imputed.
