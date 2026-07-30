# Methodology

## Scope decision

Type 2 diabetes treatments were selected because the CMS files contain broad coverage across oral therapies, insulin, GLP-1 receptor agonists, SGLT2 inhibitors, and DPP-4 inhibitors. The source has no diagnosis or indication field, so the project is more precisely a diabetes-drug market scope—not a confirmed T2D patient cohort. Insulin may reflect multiple diabetes types.

The mapping is ingredient-first and version-controlled in `config/drug_mapping.csv`. Combination products inherit the strategically differentiating component class: fixed insulin/GLP-1 and SGLT2/DPP-4 combinations are separate; other combinations follow mapping priority. Wegovy, Saxenda, and Zepbound are excluded because their marketed indications are weight management. The broad insulin candidate filter also captures pumps, reusable pens, V-Go devices, and syringes; these exact rows stay in raw but are removed from the analytical pharmaceutical layer using `config/excluded_generic_patterns.txt`. No medical recommendation is made.

## Grain and retrieval

One raw row is one reporting year × NPI × brand-name label × generic-name label after CMS suppression. The annual multi-gigabyte CMS CSV is streamed, each source row is evaluated against documented generic-name ingredient substrings, and in-scope rows are written unchanged. This avoids an opaque sample while keeping the repository practical.

## Cleaning

Names and geography are trimmed; NPI is preserved as a zero-padded string; numeric fields use nullable types; year is explicit; provider display IDs are masked. Missing beneficiary counts remain missing. Duplicate keys and cross-year schemas are tested.

## Metrics

- Market volume = sum of `Tot_Clms` or `Tot_30day_Fills`; these are fills, not people.
- Aggregate drug cost = sum of `Tot_Drug_Cst`; this is not CMS payment.
- Cost per claim/fill = aggregate cost divided by the corresponding summed denominator, protected with `NULLIF`.
- Market share = class standardized fills / all in-scope standardized fills.
- YoY growth = current standardized fills / prior standardized fills − 1.
- HHI = sum of squared provider fill shares; reported on a 0–1 scale.
- Gini and Lorenz = inequality of provider-level standardized-fill distribution.
- Top contribution = standardized fills from the top p% of providers / all standardized fills.

## Opportunity framework

The primary score is a weighted percentile composite: log scale 35%, winsorized 2022–2024 CAGR 25%, positive gap below the 2024 national GLP-1-based fill share 25%, and beneficiary-count completeness 15%. Growth-led and gap-led alternatives test sensitivity. Scores are descriptive scenarios, not predictions, causal effects, clinical guidance, or provider targeting. Protected attributes are not used.

## Outliers

Cost-per-fill percentiles are reviewed only for rows with at least 50 standardized fills. Outliers are data-quality and market-structure observations; they are not fraud, compliance, or quality judgments.

## Suppression and uncertainty

CMS omits provider–drug records below 11 claims and blanks beneficiary counts below 11. This produces left-censoring, especially for low-volume providers/products. Because suppressed records are not published, the exact amount of omitted volume cannot be recovered and is never imputed. Sensitivity analysis varies decision weights, not hidden CMS values.
