# Validation report

**Independent artifact reconciliation: PASS**

The validation reads each Parquet file with PyArrow, recomputes row counts and core sums, and compares them with the DuckDB fact table and dashboard JSON. It also reconciles source-candidate counts to documented processed exclusions and verifies that every named SQL query executed, including a zero-row duplicate-grain query.

| Year | CMS rows scanned | Raw candidates | Non-drug exclusions | Processed rows | Claims | Standardized fills | Aggregate drug cost |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 25,869,521 | 1,944,541 | 28,970 | 1,915,571 | 83,702,377 | 171,623,487.8 | $35,665,409,118.36 |
| 2023 | 26,794,878 | 2,116,541 | 26,872 | 2,089,669 | 92,799,490 | 187,002,433.4 | $48,150,586,219.14 |
| 2024 | 28,023,892 | 2,254,990 | 23,743 | 2,231,247 | 104,160,253 | 205,841,944.7 | $50,712,600,298.58 |

Automated structural, domain, missingness, suppression, grain, join-multiplication, and dashboard checks are defined in `tests/test_pipeline.py`. Front-end build/output assertions are defined in `tests/rendered-html.test.mjs`. The exact executed command results are reported in the final project handoff; a passing result is never inferred from the presence of this file.
