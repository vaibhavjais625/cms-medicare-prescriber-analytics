# Interview preparation: 55 questions with sample answers

## Business framing

### 1. What business problem does RxMarketIQ solve?

It identifies where Medicare Part D diabetes-drug utilization is large, growing, concentrated, or under-indexed to a selected class. The result is a prioritized set of market-development hypotheses, not a causal sales forecast or provider-targeting instruction.

### 2. Who is the intended user?

A pharmaceutical commercial analytics or life-sciences consulting team doing early market assessment. The dashboard lets an analyst or engagement lead move from national size to class, product, geography, specialty, and concentration evidence.

### 3. Why did you choose diabetes?

CMS has broad, commercially relevant coverage across established oral therapies, insulin, SGLT2, DPP-4, and incretin products. That creates enough volume and class diversity for market-share, trend, cost, segmentation, and concentration analysis.

### 4. Is this truly a Type 2 diabetes cohort?

No. CMS provider-by-drug data have no diagnosis or indication field. I call it a diabetes-drug market scope and explicitly state that insulin and some products can reflect uses beyond confirmed T2D.

### 5. What decision should not be made from this project?

It should not determine clinical appropriateness, care quality, compliance risk, or individual provider action. It also cannot prove that promotional activity caused any observed geographic or product difference.

### 6. How would you explain the project to a nontechnical executive?

I converted three years of public Part D prescription activity into a market map: how big the observed market is, which products and classes drive it, where it is concentrated, and which regions warrant deeper research. Every recommendation is paired with the data limitation that could change interpretation.

### 7. What makes the project consulting-ready?

It starts with a decision question, uses governed definitions, reconciles evidence, converts analysis into an explainable opportunity scenario, and ends with recommendations, caveats, and a measurement plan. The dashboard supports a client conversation rather than only presenting code.

### 8. What is the key commercial insight structure?

I use evidence → interpretation → opportunity → next validation. That prevents a descriptive difference from being presented as a causal or immediately actionable recommendation.

## Data source and grain

### 9. What is the source grain?

One row represents a calendar year, prescriber NPI, brand-name label, and generic-name label after CMS privacy suppression. That grain must remain unique; provider or product joins are tested so they do not multiply rows.

### 10. What do `Tot_Clms` and `Tot_30day_Fills` mean?

`Tot_Clms` counts original prescriptions plus refills. `Tot_30day_Fills` standardizes days supplied to 30-day equivalents, so it is usually a better cross-product utilization measure; neither is a patient count.

### 11. What does total drug cost represent?

It includes ingredient cost, dispensing fee, sales tax, applicable administration fees, and amounts across plans, beneficiaries, subsidies, and other third parties. It is not the amount CMS alone paid and does not reflect rebates.

### 12. Why not sum beneficiaries across drugs?

The same beneficiary can receive multiple drugs and see multiple prescribers. Summing provider–drug beneficiary counts would double-count people, and low counts are suppressed, so I do not present a market patient total.

### 13. How did you verify the latest years?

I checked the official CMS product page and captured `data.cms.gov/data.json`. The catalog identifies 2024 as the latest complete year and provides version-specific official files and API UUIDs for 2022–2024.

### 14. Why not use Kaggle?

The official CMS files and metadata were available, so a secondary copy added unnecessary lineage and licensing risk. The repository records official URLs, filenames, year, modified date, scanned rows, retained rows, columns, download timestamp, and checksum.

### 15. Why use a filtered download?

Each annual provider-by-drug file is several gigabytes. The script still scans every official source row and retains every row matching the documented scope, so the extract is deterministic and auditable rather than an undocumented sample.

### 16. How do you know the filter did not fabricate data?

The raw output writes the original row values and header without mutation. Classification, masking, and calculated fields only appear in the processed layer; manifests store counts and SHA-256 checksums.

### 17. What are the major suppression rules?

CMS omits provider–drug cells with fewer than 11 claims. Beneficiary counts below 11 are blank, and related age fields can also be suppressed; I preserve those blanks and never impute hidden values.

### 18. How can suppression bias the analysis?

The observed market is left-censored. Smaller providers, rarer products, and lower-volume geographies lose relatively more cells, so their activity may be understated and concentration can appear higher than it truly is.

## Scope and mapping

### 19. How did you build the drug-class mapping?

I profiled observed brand and generic labels, then used a version-controlled ingredient-first map. Combination products follow transparent priority rules, and every processed row retains the matched ingredient terms for auditability.

### 20. Why exclude Wegovy, Saxenda, and Zepbound?

The business scope is diabetes treatment, while those marketed brands are weight-management products. Their generic ingredients overlap diabetes brands, so an ingredient-only filter would otherwise contaminate the commercial scope.

### 21. How do you handle combination products?

Fixed insulin/GLP-1 and SGLT2/DPP-4 combinations receive distinct classes. Other combinations inherit the higher-priority differentiating component; the rule is documented so stakeholders can challenge or change it.

### 22. How did you perform brand-versus-generic analysis?

The source lacks a definitive FDA approval-category flag at provider–drug grain. I therefore label a row “brand-identifiable” when the marketed name differs from the generic label and “generic-name listed” when they match, and I present this as a heuristic rather than a legal classification.

### 23. What mapping validation did you perform?

I require zero unmapped retained rows, export observed brand/generic pairs, exclude the three out-of-scope brands, and reconcile class totals to the whole market. Mapping terms and exclusions are configuration files, not hidden code.

### 24. What would you add in production?

I would use an NDC-level product master with FDA approval category, indication, dosage form, route, launch date, manufacturer, and lifecycle status. That would replace the marketed-name heuristic and support more precise franchise definitions.

## Engineering and quality

### 25. Why use streaming and chunks?

The full files are too large to load safely into memory. Streaming limits disk use during retrieval, and pandas chunks cap memory during profiling and transformation while preserving all in-scope rows.

### 26. Why Parquet?

Parquet is typed, compressed, and columnar. It reduces storage and lets DuckDB scan only the columns needed for a query, which is much faster than repeatedly parsing CSV.

### 27. Why DuckDB instead of SQLite?

The workload is analytical: large scans, group-bys, windows, percentiles, and Parquet ingestion. DuckDB is columnar and optimized for that pattern, while SQLite is stronger for row-oriented transactional access.

### 28. What is schema standardization?

It means every year has the same canonical snake-case fields and nullable numeric types. NPI remains a string, suppression blanks remain null, year is explicit, and the cross-year test prevents silent drift.

### 29. How do you validate the grain?

The uniqueness key is year + NPI + brand name + generic name. Both the profiler and a SQL/pytest check look for duplicates; the executed provider-grain query must return zero rows.

### 30. How do you protect against join multiplication?

I aggregate providers to exactly one row per year + NPI before joining to fact rows for deciles. A test compares claims, fills, and cost before and after the dashboard join at tight numerical tolerance.

### 31. What required-field tests exist?

NPI, product labels, class, claims, standardized fills, and cost must be present. NPI must be ten digits after zero-padding, and every retained row must have a mapped class.

### 32. What range tests exist?

Published rows must have at least 11 claims; fills, days, and cost cannot be negative; nonmissing beneficiary counts must be at least 11. Cost ratios use safe denominators.

### 33. How do you reconcile raw and processed data?

Each year’s manifest retained-row count must equal the DuckDB fact count for that year. Class views and dashboard totals are independently summed and compared with the fact table.

### 34. What happens if a download is interrupted?

The script writes a `.part` file and promotes it only after a complete scan. An interrupted partial file is not a valid artifact; rerunning restarts that year and regenerates its checksum and manifest.

### 35. How is reproducibility handled?

Version-specific CMS URLs and UUIDs, configuration, dependency ranges, scripts, SQL, manifests, checksums, database, tests, and exact commands are all inside the project folder. Headline findings are generated from executed metric JSON.

## Metrics and SQL

### 36. Why use weighted aggregation for cost per claim?

The correct market metric is total cost divided by total claims. Averaging row ratios gives a tiny provider–drug cell the same weight as a large cell and can materially bias the answer.

### 37. How is year-over-year growth calculated?

For a like-for-like scope, current standardized fills are divided by prior-year fills and one is subtracted. SQL uses `LAG`, and zero denominators are protected with `NULLIF`.

### 38. Why report both claims and standardized fills?

Claims are intuitive event counts, while standardized fills adjust for days supplied. Differences between them can reveal refill-duration or product-mix effects and prevent one utilization definition from dominating the narrative.

### 39. How do you calculate market share?

I divide a class’s summed standardized fills by all in-scope standardized fills for the same year and filter context. I do not average provider-level shares.

### 40. What does HHI add beyond top-10 share?

Top shares focus on a threshold, while HHI incorporates every provider’s share and is especially sensitive to the largest providers. Together with Gini and Lorenz, it gives a fuller concentration picture.

### 41. How is the Gini coefficient interpreted here?

Zero would mean every observed prescriber has equal volume; values closer to one indicate greater inequality. It describes distribution, not unfairness or quality.

### 42. What is the Lorenz curve?

It plots cumulative provider share against cumulative fill share after sorting providers from lowest to highest volume. The farther it bows below the equality line, the more concentrated the observed prescribing distribution.

### 43. Why use provider deciles?

Deciles make skew operationally understandable and support filters without exposing names. Decile 1 is the highest-volume tenth in this project, defined explicitly to avoid ambiguity.

### 44. How do you review outliers responsibly?

I require at least 50 standardized fills, calculate cost-per-fill percentiles, and label the result as a data-quality/market-structure review. I never infer fraud, noncompliance, or poor care from an extreme value.

## Opportunity framework

### 45. What are the opportunity-score components?

The primary score uses log market scale, winsorized 2022–2024 growth, the positive gap below national GLP-1-based share, and beneficiary-count completeness. Each component is converted to a percentile before weighting.

### 46. Why use percentiles?

The raw components have different units and skew. Percentiles put them on a common, explainable 0–1 scale and reduce domination by very large states.

### 47. Why log-transform scale?

State volume is highly skewed. `log1p` preserves ordering while compressing the gap between the largest and typical states so other components remain meaningful.

### 48. Why winsorize growth?

Small bases can create extreme growth rates. Capping at the 5th and 95th percentiles reduces that instability without deleting geographies, and the rule is documented.

### 49. Why is the selected-class gap not automatically an opportunity?

A low share can reflect formulary, indication, affordability, competitor, population, or clinical factors. It is only a screening signal; deeper access and context validation must precede action.

### 50. How did you choose weights?

I favored scale at 35% because a gap in a tiny market has limited commercial relevance, then balanced growth and class gap at 25% each and completeness at 15%. The weights are assumptions, so two alternative scenarios test rank robustness.

### 51. What does sensitivity analysis show?

It recomputes scores with growth-led and gap-led weights, then reports each geography’s rank range. Stable high ranks are stronger hypotheses; volatile ranks signal dependence on stakeholder preferences.

### 52. Is this machine learning?

No. There is no learned model, labeled outcome, train/test split, or predictive validation. It is a transparent weighted prioritization framework.

### 53. Why is it not “next best action”?

The data do not contain customer eligibility, channel, access, engagement history, response outcomes, or constraints. The score identifies areas for further investigation, not a provider-level action.

## Communication and next steps

### 54. What would you do next with additional data?

I would add formulary/access, diagnosis-linked claims, NDC product master, manufacturer, rebates/net price where lawful, epidemiology, and contextual geography. I would redefine peer groups, retest scope, and separate opportunity discovery from causal program measurement.

### 55. How would you measure whether a commercial program worked?

First define exposure, eligible population, pre-period, outcomes, and confounders outside this public dataset. Then use an appropriate design—such as matched controls or difference-in-differences—while monitoring access and market changes; the RxMarketIQ score alone cannot estimate impact.

