-- name: market_size_and_growth
-- Business question: How large is the observed Part D diabetes market, and how is it changing?
SELECT
    year, total_claims, total_30day_fills, total_drug_cost, prescribers,
    (total_30day_fills / NULLIF(LAG(total_30day_fills) OVER (ORDER BY year), 0)) - 1 AS yoy_fill_growth,
    selected_class_share
FROM v_market_year
ORDER BY year;

-- name: class_leaders
-- Business question: Which classes lead on standardized fills and cost?
SELECT * FROM v_class_year
QUALIFY ROW_NUMBER() OVER (PARTITION BY year ORDER BY total_30day_fills DESC) <= 10
ORDER BY year, total_30day_fills DESC;

-- name: product_leaders_2024
-- Business question: Which 2024 products have the most standardized fills?
SELECT brand_name, generic_name, drug_class, total_claims, total_30day_fills, total_drug_cost, avg_cost_per_claim
FROM v_product_year
WHERE year = 2024
ORDER BY total_30day_fills DESC
LIMIT 20;

-- name: state_leaders_2024
-- Business question: Which geographies have the greatest observed 2024 volume?
SELECT provider_state, total_claims, total_30day_fills, total_drug_cost, prescribers,
       selected_class_fills / NULLIF(total_30day_fills, 0) AS selected_class_share
FROM v_state_year
WHERE year = 2024
ORDER BY total_30day_fills DESC
LIMIT 20;

-- name: specialty_leaders_2024
-- Business question: Which prescriber specialties account for the most volume?
SELECT provider_specialty, total_claims, total_30day_fills, total_drug_cost, prescribers,
       selected_class_fills / NULLIF(total_30day_fills, 0) AS selected_class_share
FROM v_specialty_year
WHERE year = 2024
ORDER BY total_30day_fills DESC
LIMIT 20;

-- name: provider_grain_validation
-- Validation: provider-drug rows must be unique within each year.
SELECT year, provider_npi, brand_name, generic_name, COUNT(*) AS duplicate_count
FROM fact_provider_drug
GROUP BY year, provider_npi, brand_name, generic_name
HAVING COUNT(*) > 1;

-- name: outlier_review_2024
-- Descriptive data-quality review only; high cost is not a quality or compliance judgment.
WITH scored AS (
    SELECT provider_masked_id, brand_name, generic_name, total_30day_fills, cost_per_30day_fill,
           PERCENT_RANK() OVER (ORDER BY cost_per_30day_fill) AS cost_percentile
    FROM fact_provider_drug
    WHERE year = 2024 AND total_30day_fills >= 50 AND cost_per_30day_fill IS NOT NULL
)
SELECT * FROM scored WHERE cost_percentile >= 0.999 ORDER BY cost_per_30day_fill DESC LIMIT 25;

