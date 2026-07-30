-- Reusable, denominator-safe analytical views.

CREATE OR REPLACE VIEW v_market_year AS
SELECT
    year,
    SUM(total_claims) AS total_claims,
    SUM(total_30day_fills) AS total_30day_fills,
    SUM(total_drug_cost) AS total_drug_cost,
    COUNT(DISTINCT provider_npi) AS prescribers,
    COUNT(DISTINCT brand_name || '|' || generic_name) AS products,
    SUM(total_drug_cost) / NULLIF(SUM(total_claims), 0) AS avg_cost_per_claim,
    SUM(total_drug_cost) / NULLIF(SUM(total_30day_fills), 0) AS avg_cost_per_30day_fill,
    SUM(CASE WHEN is_selected_class THEN total_30day_fills ELSE 0 END) / NULLIF(SUM(total_30day_fills), 0) AS selected_class_share
FROM fact_provider_drug
GROUP BY year;

CREATE OR REPLACE VIEW v_class_year AS
SELECT
    year, drug_class,
    SUM(total_claims) AS total_claims,
    SUM(total_30day_fills) AS total_30day_fills,
    SUM(total_drug_cost) AS total_drug_cost,
    COUNT(DISTINCT provider_npi) AS prescribers,
    SUM(total_30day_fills) / NULLIF(SUM(SUM(total_30day_fills)) OVER (PARTITION BY year), 0) AS fill_share
FROM fact_provider_drug
GROUP BY year, drug_class;

CREATE OR REPLACE VIEW v_product_year AS
SELECT
    year, drug_class, brand_name, generic_name, marketed_name_type,
    SUM(total_claims) AS total_claims,
    SUM(total_30day_fills) AS total_30day_fills,
    SUM(total_drug_cost) AS total_drug_cost,
    COUNT(DISTINCT provider_npi) AS prescribers,
    SUM(total_drug_cost) / NULLIF(SUM(total_claims), 0) AS avg_cost_per_claim,
    SUM(total_drug_cost) / NULLIF(SUM(total_30day_fills), 0) AS avg_cost_per_30day_fill
FROM fact_provider_drug
GROUP BY year, drug_class, brand_name, generic_name, marketed_name_type;

CREATE OR REPLACE VIEW v_state_year AS
SELECT
    year,
    COALESCE(NULLIF(provider_state, ''), 'Unknown') AS provider_state,
    SUM(total_claims) AS total_claims,
    SUM(total_30day_fills) AS total_30day_fills,
    SUM(total_drug_cost) AS total_drug_cost,
    COUNT(DISTINCT provider_npi) AS prescribers,
    SUM(CASE WHEN is_selected_class THEN total_30day_fills ELSE 0 END) AS selected_class_fills,
    SUM(CASE WHEN total_beneficiaries IS NOT NULL THEN total_claims ELSE 0 END) / NULLIF(SUM(total_claims), 0) AS beneficiary_completeness
FROM fact_provider_drug
GROUP BY year, COALESCE(NULLIF(provider_state, ''), 'Unknown');

CREATE OR REPLACE VIEW v_specialty_year AS
SELECT
    year,
    COALESCE(NULLIF(provider_specialty, ''), 'Unknown') AS provider_specialty,
    SUM(total_claims) AS total_claims,
    SUM(total_30day_fills) AS total_30day_fills,
    SUM(total_drug_cost) AS total_drug_cost,
    COUNT(DISTINCT provider_npi) AS prescribers,
    SUM(CASE WHEN is_selected_class THEN total_30day_fills ELSE 0 END) AS selected_class_fills,
    SUM(CASE WHEN total_beneficiaries IS NOT NULL THEN total_claims ELSE 0 END) / NULLIF(SUM(total_claims), 0) AS beneficiary_completeness
FROM fact_provider_drug
GROUP BY year, COALESCE(NULLIF(provider_specialty, ''), 'Unknown');

CREATE OR REPLACE VIEW v_provider_year AS
WITH provider_totals AS (
    SELECT
        year, provider_npi, provider_masked_id,
        ANY_VALUE(provider_state) AS provider_state,
        ANY_VALUE(provider_city) AS provider_city,
        ANY_VALUE(provider_specialty) AS provider_specialty,
        SUM(total_claims) AS total_claims,
        SUM(total_30day_fills) AS total_30day_fills,
        SUM(total_drug_cost) AS total_drug_cost,
        SUM(CASE WHEN is_selected_class THEN total_30day_fills ELSE 0 END) AS selected_class_fills
    FROM fact_provider_drug
    GROUP BY year, provider_npi, provider_masked_id
)
SELECT *,
    NTILE(10) OVER (PARTITION BY year ORDER BY total_30day_fills DESC, provider_npi) AS volume_decile,
    CUME_DIST() OVER (PARTITION BY year ORDER BY total_30day_fills) AS volume_percentile
FROM provider_totals;

CREATE OR REPLACE VIEW v_dashboard_cube AS
SELECT
    f.year,
    COALESCE(NULLIF(f.provider_state, ''), 'Unknown') AS provider_state,
    COALESCE(NULLIF(f.provider_specialty, ''), 'Unknown') AS provider_specialty,
    f.drug_class,
    f.marketed_name_type,
    p.volume_decile,
    SUM(f.total_claims) AS total_claims,
    SUM(f.total_30day_fills) AS total_30day_fills,
    SUM(f.total_drug_cost) AS total_drug_cost,
    COUNT(DISTINCT f.provider_npi) AS prescribers,
    SUM(CASE WHEN f.is_selected_class THEN f.total_30day_fills ELSE 0 END) AS selected_class_fills
FROM fact_provider_drug f
JOIN v_provider_year p ON p.year = f.year AND p.provider_npi = f.provider_npi
GROUP BY ALL;

CREATE OR REPLACE VIEW v_city_year AS
SELECT
    year,
    COALESCE(NULLIF(provider_state, ''), 'Unknown') AS provider_state,
    COALESCE(NULLIF(provider_city, ''), 'Unknown') AS provider_city,
    SUM(total_claims) AS total_claims,
    SUM(total_30day_fills) AS total_30day_fills,
    SUM(total_drug_cost) AS total_drug_cost,
    COUNT(DISTINCT provider_npi) AS prescribers
FROM fact_provider_drug
GROUP BY ALL;

