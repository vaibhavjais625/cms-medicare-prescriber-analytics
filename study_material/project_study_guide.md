# RxMarketIQ study guide

## Project fundamentals

The unit of analysis is a CMS reporting year × prescriber NPI × brand/generic drug label. The portfolio question is commercial and descriptive: market size, growth, mix, geography, specialty, concentration, and observable opportunity gaps in Medicare Part D. It is not a patient cohort, clinical assessment, causal model, or measure of a provider’s full practice.

## Complete pipeline walkthrough

1. The download script resolves version-specific 2022–2024 CMS files and streams each official bulk CSV.
2. Ingredient terms retain the exact diabetes-market source rows; explicit weight-management brands are removed.
3. Profiling counts rows/columns, nulls, duplicate keys, numeric ranges, and observed drug labels.
4. Transformation standardizes names and types, masks provider display IDs, maps classes, and writes partitioned Parquet.
5. DuckDB ingests Parquet and creates reusable market, class, product, geography, specialty, provider, and dashboard views.
6. Python computes concentration curves and an explainable opportunity score with sensitivity scenarios.
7. Dashboard JSON is reconciled to DuckDB totals.
8. Pytest checks schema, grain, required fields, ranges, suppression, raw/processed counts, aggregations, and join protection.

## Analytical methods

- **Profiling:** understand schema, completeness, ranges, duplicates, and observed labels before analysis.
- **Weighted aggregation:** calculate ratios from summed numerators/denominators, never the average of row-level ratios.
- **Growth:** compare like-for-like standardized fills across calendar years.
- **Concentration:** use top shares, HHI, Lorenz, and Gini because each shows a different aspect of skew.
- **Segmentation:** aggregate by state, city, specialty, drug class, marketed-name type, and provider decile.
- **Opportunity sizing:** combine normalized descriptive components and explicitly test alternative weights.
- **Outlier review:** flag extreme cost per fill only after a minimum-volume threshold; do not infer misconduct or quality.

## KPI formulas

- Claims = Σ `total_claims`
- Standardized fills = Σ `total_30day_fills`
- Drug cost = Σ `total_drug_cost`
- Cost per claim = Σ cost / Σ claims
- Cost per standardized fill = Σ cost / Σ standardized fills
- Class share = class standardized fills / market standardized fills
- YoY growth = current fills / prior fills − 1
- Provider HHI = Σ(provider fills / market fills)²
- Top-p contribution = fills from highest-volume p% of providers / all fills
- Opportunity score = 100 × Σ(component percentile × documented weight)

## Python walkthrough

`download_data.py` uses streaming I/O so full multi-gigabyte files are not stored. `profile_data.py` and `clean_transform.py` use chunks to cap memory. Nullable pandas types protect suppressed beneficiary fields. PyArrow writes compressed Parquet. `build_dashboard_data.py` uses pandas for percentile components, winsorization, rank sensitivity, Gini, and dashboard serialization.

## SQL walkthrough

`v_market_year` defines topline KPIs. `v_class_year` and `v_product_year` define mix and cost. `v_provider_year` uses `NTILE` and `CUME_DIST`. `v_dashboard_cube` joins only on year + NPI after confirming one provider-year row, preventing multiplication. Business queries use `NULLIF` in denominators and named comments so execution can be audited.

## Dashboard walkthrough

Start with the KPI row, then read the class trend, product cost/volume, geographic opportunity table, specialty mix, and concentration panels. Filters apply to the dashboard cube; panels explicitly marked national use national aggregates. Search narrows the opportunity table; CSV export downloads the filtered table. The methodology dialog documents scope, scoring, and CMS caveats.

## Glossary

- **NPI:** National Provider Identifier.
- **PDE:** Prescription Drug Event submitted by a Part D plan.
- **Claim/fill:** Original prescription or refill; not a person.
- **30-day standardized fill:** Days supplied divided by 30, with CMS coding limits at the claim level.
- **Aggregate drug cost:** Ingredient cost, dispensing fee, tax, and applicable administration fee across payer sources.
- **Suppression:** Removal/blanking of small cells to protect beneficiary privacy.
- **Market share:** A product/class share of in-scope standardized fills.
- **HHI:** Sum of squared market shares; higher means more concentration.
- **Lorenz curve:** Cumulative share of volume versus cumulative share of providers.
- **Gini:** Inequality index derived from the Lorenz curve; 0 is equal, 1 is maximally unequal.
- **CAGR:** Smoothed annual growth across multiple years.
- **Winsorization:** Capping extreme values at selected percentiles.
- **Sensitivity analysis:** Recomputing ranks under alternative transparent assumptions.

## Practice exercises

1. Recompute 2024 class share directly from `fact_provider_drug` and reconcile to `v_class_year`.
2. Explain why averaging row-level cost per claim is wrong.
3. Change the selected class to SGLT2 inhibitors and rebuild the opportunity table.
4. Compare claims versus standardized fills for insulin and explain the difference.
5. Calculate top 5% contribution without using a prebuilt view.
6. Add a minimum-prescriber rule to the specialty opportunity table.
7. Explain how suppression could bias rural or low-volume segment comparisons.
8. Create a leave-one-component-out sensitivity check for the opportunity score.
9. Inspect the top cost-per-fill rows and propose nonjudgmental validation checks.
10. Write a one-slide executive recommendation that separates evidence, assumption, and next measurement.

## Seven-day study schedule

**Day 1:** Read the README, source methodology, grain, and suppression rules. Rehearse the 30-second introduction.

**Day 2:** Trace one row from raw CSV to Parquet to DuckDB. Review typing, nulls, duplicates, and mapping.

**Day 3:** Rebuild the five core KPIs in SQL. Practice explaining safe denominators and weighted averages.

**Day 4:** Study class/product/geography/specialty results. Practice insight → implication → limitation.

**Day 5:** Recompute Gini/top shares and the opportunity score. Defend each weight and sensitivity scenario.

**Day 6:** Demo every dashboard control on desktop and mobile. Practice an empty-state explanation.

**Day 7:** Answer the interview guide aloud, deliver the two-minute presentation, and run a mock follow-up round.

