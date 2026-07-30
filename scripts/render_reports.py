"""Render metric-backed README and analytical reports after the pipeline finishes."""

from __future__ import annotations

import json
from pathlib import Path

from common import PROJECT_ROOT, REPORTS_DIR


def money(value: float) -> str:
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return f"${value:,.0f}"


def compact(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    return f"{value:,.0f}"


def main() -> None:
    h = json.loads((REPORTS_DIR / "headline_metrics.json").read_text(encoding="utf-8"))
    manifests = json.loads((PROJECT_ROOT / "data" / "raw" / "cms_filtered" / "download_manifest.json").read_text(encoding="utf-8"))
    latest = h["latest"]
    opp = h["top_opportunities"][0]
    concentration = h["concentration_2024"]
    manifest_rows = "\n".join(
        f"| {item['reporting_year']} | `{item['source_file_name']}` | {item['source_rows_scanned']:,} | {item['filtered_row_count']:,} | {item['column_count']} | {item['download_completed_utc'][:10]} |"
        for item in manifests
    )
    readme = f"""# RxMarketIQ

**Real-World Medicare Part D Prescriber and Pharmaceutical Market Analytics**

RxMarketIQ answers one commercial analytics question: **Which therapeutic markets, geographic areas, and prescriber segments represent the most meaningful observable pharmaceutical market opportunities based on real Medicare Part D utilization and drug-cost data?**

The project uses exact CMS provider–drug records for 2022–2024, reproducibly filtered to a documented diabetes ingredient map. It is descriptive market analytics—not medical guidance, a quality assessment, causal evidence, or a patient-level analysis.

## Headline findings

- The 2024 observed market contains **{compact(latest['total_30day_fills'])} standardized 30-day fills**, **{compact(latest['total_claims'])} claims**, and **{money(latest['total_drug_cost'])} in aggregate drug cost** across **{compact(latest['prescribers'])} prescribers**.
- Standardized fills changed **{h['yoy_fill_growth']:.1%} year over year** in 2024; the selected GLP-1-based class represented **{latest['selected_class_share']:.1%}** of observed fills.
- **{h['top_product']['brand_name']}** led product volume in 2024, while **{h['top_state']['provider_state']}** and **{h['top_specialty']['provider_specialty']}** led the state and specialty views.
- Prescribing is concentrated: the top 1% of observed prescribers accounted for **{concentration['top_1_share']:.1%}** of 2024 standardized fills (Gini **{concentration['gini']:.3f}**).
- Under the documented primary opportunity weights, **{opp['provider_state']}** ranks first. This is a descriptive combination of scale, growth, selected-class gap, and beneficiary-count completeness—not a causal promotional estimate.

## Source and reproducibility

Official source: [CMS Medicare Part D Prescribers — by Provider and Drug](https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug). Latest complete year verified on 2026-07-30: **2024**.

| Reporting year | Official CMS file | Source rows scanned | In-scope rows retained | Columns | Download date |
|---:|---|---:|---:|---:|---|
{manifest_rows}

Full annual CSVs are multi-gigabyte. `scripts/download_data.py` streams each official CMS file and preserves every source row matching `config/drug_mapping.csv`, minus only the explicit weight-management brands in `config/excluded_brands.txt`. This is a deterministic candidate download, not a sample. The processed pharmaceutical layer then removes pumps, reusable pens, insulin-delivery devices, and syringes using `config/excluded_generic_patterns.txt`; excluded rows remain preserved in raw. Raw exact extracts remain in `data/raw/cms_filtered/`; typed Parquet lives in `data/processed/`.

## Architecture

`CMS bulk CSV → exact filtered raw CSV → profiled/typed Parquet → DuckDB + SQL views → validated dashboard JSON → interactive dashboard`

- **Python:** streaming retrieval, profiling, cleaning, class mapping, metrics, opportunity scoring, report generation.
- **DuckDB:** chosen over SQLite for fast columnar Parquet ingestion, analytical windows, and large group-bys.
- **SQL:** reusable views and commented business queries with `NULLIF` denominator protection.
- **React/Vinext:** responsive static dashboard with client-side filters and downloadable tables.
- **Pytest:** grain, schema, domain, suppression, reconciliation, and join-multiplication tests.

## Setup

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python -m pip install -r requirements.txt
.\\.venv\\Scripts\\python scripts\\run_pipeline.py
pnpm install
pnpm run dev
```

Open the local URL printed by the dashboard process. The executed repository already includes the processed data, database, and dashboard payload used for the findings above.

## Analytical methods

The project applies chunked profiling, schema standardization, duplicate/grain checks, missingness and suppression analysis, typed conversion, weighted aggregation, year-over-year growth, class/product share, claims, 30-day standardized fills, drug cost, average cost per claim/fill, geography and specialty segmentation, marketed-name heuristics, Pareto shares, HHI, Lorenz/Gini, deciles, outlier review, opportunity scoring, and weight sensitivity.

The opportunity score uses 2024 scale (35%), 2022–2024 growth (25%), gap below national GLP-1-based fill share (25%), and beneficiary-count completeness (15%). Two alternative weight sets test rank sensitivity. It uses only descriptive CMS fields, excludes protected attributes, and is not machine learning or “next best action.”

## Key limitations

- CMS removes provider–drug cells with fewer than 11 claims; low-volume activity is omitted.
- Beneficiary counts below 11 are blank. They are not imputed.
- Claims include original fills and refills; they are not patient counts.
- Total drug cost combines plan, beneficiary, subsidy, and other payer amounts; it is not CMS payment and excludes rebates.
- Part D is not a provider’s complete practice. Volume does not measure care quality.
- Provider-by-drug files have no rural/urban field; this project does not infer one from city or ZIP.
- Diabetes drugs—especially insulin—can be used outside Type 2 diabetes. The data have no diagnosis/indication field.

## Dashboard

The dashboard includes market KPIs, class trend, product rankings, state and specialty views, concentration/Lorenz analysis, cost–volume scatter, opportunity ranking, filters, table search, CSV export, methodology dialog, source date, and visible limitations. See `dashboard/README.md` for controls.

## Resume bullets

- Built an end-to-end Medicare Part D pharmaceutical market pipeline across 2022–2024, streaming and validating **{compact(sum(item['filtered_row_count'] for item in manifests))} exact provider–drug records** from multi-gigabyte CMS source files into Parquet and DuckDB.
- Developed reusable SQL/Python metrics for **{compact(latest['total_30day_fills'])} 2024 standardized fills** and **{money(latest['total_drug_cost'])} aggregate drug cost**, including YoY growth, class share, Pareto/HHI/Gini concentration, geographic and specialty segmentation, and reconciliation tests.
- Designed a transparent four-factor opportunity framework with sensitivity analysis and delivered a responsive, filterable dashboard that clearly separates observed evidence, assumptions, scenarios, and limitations.

## Interview explanation

**30 seconds:** “RxMarketIQ is a real-world Medicare Part D market analytics project. I streamed three multi-gigabyte CMS provider–drug files, retained an auditable diabetes-market subset, standardized it to Parquet and DuckDB, and built reusable measures for market size, growth, cost, geography, specialties, and prescriber concentration. I then created an explainable opportunity score and tested its sensitivity. The dashboard is honest about CMS suppression and never equates claims with patients or cost with CMS payment.”

For the two-minute narrative, STAR answer, 55 interview questions, exercises, and a seven-day plan, see `study_material/`.

## Repository map

- `config/` drug scope and opportunity weights
- `data/raw/` exact CMS-derived raw extracts and source metadata
- `data/processed/` cleaned Parquet
- `scripts/` complete pipeline
- `sql/` schema, views, and analysis queries
- `database/` DuckDB analytical database
- `tests/` validation suite
- `dashboard/` dashboard payload and usage guide
- `reports/` executive, quality, validation, methodology, and SQL results
- `study_material/` learning and interview package
"""
    (PROJECT_ROOT / "README.md").write_text(readme, encoding="utf-8")

    executive = f"""# Executive summary

## Business question

Which therapeutic markets, geographic areas, and prescriber segments represent the most meaningful observable pharmaceutical market opportunities in Medicare Part D?

## Data and definitions

The evidence is exact CMS provider–drug records from 2022–2024, reproducibly filtered to the documented diabetes ingredient map. Claims include refills; standardized 30-day fills adjust for days supplied; aggregate drug cost is broader than CMS payment. GLP-1-based share includes fixed-ratio insulin/GLP-1 products and excludes Wegovy, Saxenda, and Zepbound.

## Evidence

The 2024 scope totals {compact(latest['total_claims'])} claims, {compact(latest['total_30day_fills'])} standardized fills, and {money(latest['total_drug_cost'])}. Fill volume changed {h['yoy_fill_growth']:.1%} versus 2023. {h['top_product']['brand_name']} led product volume; {h['top_state']['provider_state']} led states; {h['top_specialty']['provider_specialty']} led specialties. The top 1% of prescribers represented {concentration['top_1_share']:.1%} of fills.

## Interpretation

The observed market combines broad chronic oral therapy volume with rapidly shifting incretin use and materially different cost intensity. Geography and specialty differences describe Part D utilization patterns, not clinical appropriateness or commercial causation.

## Opportunity scenario

{opp['provider_state']} ranks first under the primary score because of its combined observed scale, growth, below-benchmark selected-class share, and data completeness. Rank range across the three documented weighting scenarios is {opp['rank_range']} positions.

## Recommendation

Use the ranking as a hypothesis-generation layer. Prioritize aggregated market research in high-scale, high-growth segments with stable sensitivity ranks, then validate formulary, access, indication, competitor, and local-context information before any decision.

## Limitations

Suppressed low-volume cells, absent diagnosis/indication, Part D-only coverage, no rebates, and no rural/urban field constrain inference. Prescription volume is neither patient count nor care quality.

## Measurement plan

Refresh annually; track standardized fills, selected-class share, cost per fill, rank stability, suppression/completeness, and pre-specified segment trends. Any commercial program should define independent exposure and outcome data before causal evaluation.
"""
    (REPORTS_DIR / "executive_summary.md").write_text(executive, encoding="utf-8")

    methodology = """# Methodology

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
"""
    (REPORTS_DIR / "methodology.md").write_text(methodology, encoding="utf-8")

    data_readme = """# Data directory

- `raw/metadata/cms_data_catalog.json`: official CMS DCAT catalog captured on 2026-07-30.
- `raw/cms_filtered/*.csv`: exact source rows retained by the documented ingredient filter.
- `raw/cms_filtered/*.manifest.json`: source URL, endpoint UUID, reporting year, file, download time, scanned/retained rows, columns, suppression rule, and SHA-256.
- `processed/year=YYYY/provider_drug.parquet`: typed analytical layer.

To retrieve from scratch, activate the project environment and run `python scripts/download_data.py`. The process scans approximately 11–12 GB across three official annual files and may take substantial time depending on the connection. Interrupted `.part` files are never treated as complete; the downloader records validated byte/row checkpoints and resumes the unfinished year. No source records are synthesized or imputed.
"""
    (PROJECT_ROOT / "data" / "README.md").write_text(data_readme, encoding="utf-8")


if __name__ == "__main__":
    main()
