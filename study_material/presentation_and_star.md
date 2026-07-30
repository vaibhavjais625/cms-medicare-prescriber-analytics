# Presentation scripts and STAR answer

## 30-second introduction

“RxMarketIQ is a real-world pharmaceutical market analytics project using 2022–2024 CMS Medicare Part D provider-by-drug data. I built a streaming pipeline for multi-gigabyte official files, created an auditable diabetes drug-class map, standardized the data in Parquet and DuckDB, and analyzed market size, growth, product mix, geography, specialties, cost, and prescriber concentration. I also built a transparent opportunity score with sensitivity analysis and a responsive dashboard. The project explicitly handles CMS suppression and separates descriptive evidence from commercial hypotheses.”

## Two-minute project presentation

“The business question was: where do Medicare Part D utilization patterns suggest meaningful pharmaceutical market-development hypotheses? I chose diabetes because CMS has strong coverage across GLP-1, SGLT2, DPP-4, insulin, and established oral therapies.

The source files are several gigabytes each, so I avoided both an undocumented sample and unnecessary raw storage. My Python downloader streams every official CMS row and retains exact records that match a version-controlled ingredient map, while excluding weight-management brands outside scope. I profiled schema, missingness, suppression, duplicates, and numeric ranges before converting to typed Parquet.

DuckDB powers reusable SQL views for standardized fills, claims, aggregate cost, cost per fill, class share, growth, geography, specialty, and provider deciles. I measured concentration using top 1/5/10/20% contribution, HHI, Gini, and a Lorenz curve. For opportunity ranking, I combined scale, multi-year growth, a gap below national GLP-1-based share, and beneficiary-count completeness. The weights are explicit, and growth-led and gap-led alternatives show rank sensitivity.

The dashboard turns those results into an executive workflow: size the market, identify mix and growth, locate geographic and specialty differences, understand concentration, and review descriptive opportunity scenarios. I never interpret claims as patients, cost as CMS payment, or volume as quality. The next step would be to validate access, indication, formulary, competitor, and field-context data before making a business decision.”

## STAR-format explanation

**Situation:** Public Medicare Part D data can answer valuable market questions, but the annual provider-by-drug files are multi-gigabyte, suppressed, and easy to misinterpret.

**Task:** Build a reproducible portfolio project that converts those files into decision-ready pharmaceutical market evidence without inventing records or overstating causality.

**Action:** I streamed three official annual files; version-controlled the therapeutic scope; profiled and standardized the data; built Parquet, DuckDB, and denominator-safe SQL; added concentration and sensitivity methods; reconciled dashboard totals; and automated integrity tests. I masked provider display IDs and emphasized aggregated views.

**Result:** I delivered a runnable repository, validated analytical database, transparent opportunity framework, interactive dashboard, executive report, and interview study package. The output makes commercial hypotheses easy to explore while keeping suppression, Part D population limits, and causal boundaries visible.

## Difficult follow-ups

- **Why is this not patient-level market size?** Provider–drug claims and fills are aggregated events. Beneficiary counts are partially suppressed and cannot be summed across providers/drugs without duplication.
- **Why include insulin in a T2D market?** It is commercially relevant to diabetes, but CMS has no indication. I label the scope as diabetes-drug utilization and state that insulin can include other diabetes types.
- **Why use standardized fills?** Claims have different days supplied. Standardized fills improve comparability, while claims remain separately reported.
- **Can the opportunity score predict sales lift?** No. It prioritizes descriptive hypotheses; it has no exposure/outcome design and no causal claim.
- **Why use national class share as a benchmark?** It is transparent and reproducible. A production version would test access-adjusted peer groups and external formulary/context variables.
- **What is the largest bias?** Suppression removes low-volume provider–drug cells, disproportionately affecting small segments and making the observed market a lower-bound view.

## Questions to ask the interviewer

1. How does your team separate descriptive opportunity identification from causal impact measurement?
2. Which access, formulary, or claims enrichments are most important after a public-data screen?
3. How are metric definitions governed across analytics, field, and client teams?
4. What level of score explainability is expected in client-facing segmentation work?
5. How does the team validate that an opportunity framework remains stable over time?
6. What are common analytical failure modes you see in life-sciences market assessments?
7. How are privacy and responsible-use reviews integrated into provider analytics?
8. What distinguishes a strong analyst’s technical output from a strong consulting deliverable here?

