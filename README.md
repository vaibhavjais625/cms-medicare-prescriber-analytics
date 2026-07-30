# RxMarketIQ

**Real-World Medicare Part D Prescriber and Pharmaceutical Market Analytics**

RxMarketIQ answers one commercial analytics question: **Which therapeutic markets, geographic areas, and prescriber segments represent the most meaningful observable pharmaceutical market opportunities based on real Medicare Part D utilization and drug-cost data?**

The project uses exact CMS provider–drug records for 2022–2024, reproducibly filtered to a documented diabetes ingredient map. It is descriptive market analytics—not medical guidance, a quality assessment, causal evidence, or a patient-level analysis.

## Headline findings

- The 2024 observed market contains **205.8M standardized 30-day fills**, **104.2M claims**, and **$50.71B in aggregate drug cost** across **316,486 prescribers**.
- Standardized fills changed **10.1% year over year** in 2024; the selected GLP-1-based class represented **12.8%** of observed fills.
- **Metformin Hcl** led product volume in 2024, while **CA** and **Family Practice** led the state and specialty views.
- Prescribing is concentrated: the top 1% of observed prescribers accounted for **10.6%** of 2024 standardized fills (Gini **0.634**).
- Under the documented primary opportunity weights, **FL** ranks first. This is a descriptive combination of scale, growth, selected-class gap, and beneficiary-count completeness—not a causal promotional estimate.

## Source and reproducibility

Official source: [CMS Medicare Part D Prescribers — by Provider and Drug](https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug). Latest complete year verified on 2026-07-30: **2024**.

| Reporting year | Official CMS file | Source rows scanned | In-scope rows retained | Columns | Download date |
|---:|---|---:|---:|---:|---|
| 2022 | `MUP_DPR_RY24_P04_V10_DY22_NPIBN.csv` | 25,869,521 | 1,944,541 | 22 | 2026-07-30 |
| 2023 | `MUP_DPR_RY25_P04_V10_DY23_NPIBN.csv` | 26,794,878 | 2,116,541 | 22 | 2026-07-30 |
| 2024 | `MUP_DPR_RY26_P04_V10_DY24_NPIBN.csv` | 28,023,892 | 2,254,990 | 22 | 2026-07-30 |

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
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts\run_pipeline.py
pnpm install
pnpm run dev
```

Open the local URL printed by the dashboard process. The executed repository already includes the processed data, database, and dashboard payload used for the findings above.

### Deploy on Netlify from GitHub

The repository includes `netlify.toml` and a dedicated static build target. In Netlify, choose **Add new project → Import an existing project → GitHub**, select this repository, and deploy. Netlify reads the settings automatically:

- Build command: `pnpm run build:netlify`
- Publish directory: `dist/netlify`
- Node.js: 22

To verify the exact production artifact locally, run `pnpm run build:netlify` and serve `dist/netlify/` with any static file server.

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

- Built an end-to-end Medicare Part D pharmaceutical market pipeline across 2022–2024, streaming and validating **6.3M exact provider–drug records** from multi-gigabyte CMS source files into Parquet and DuckDB.
- Developed reusable SQL/Python metrics for **205.8M 2024 standardized fills** and **$50.71B aggregate drug cost**, including YoY growth, class share, Pareto/HHI/Gini concentration, geographic and specialty segmentation, and reconciliation tests.
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
