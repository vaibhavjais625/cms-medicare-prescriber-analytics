-- RxMarketIQ analytical schema (DuckDB)
-- DuckDB is used because columnar Parquet scans and analytical window functions
-- are materially more efficient than row-oriented SQLite for this multi-year grain.

CREATE TABLE IF NOT EXISTS fact_provider_drug (
    provider_npi VARCHAR NOT NULL,
    provider_masked_id VARCHAR NOT NULL,
    provider_last_org_name VARCHAR,
    provider_first_name VARCHAR,
    provider_city VARCHAR,
    provider_state VARCHAR,
    provider_state_fips VARCHAR,
    provider_specialty VARCHAR,
    provider_type_source VARCHAR,
    brand_name VARCHAR NOT NULL,
    generic_name VARCHAR NOT NULL,
    total_claims BIGINT NOT NULL,
    total_30day_fills DOUBLE NOT NULL,
    total_day_supply BIGINT NOT NULL,
    total_drug_cost DOUBLE NOT NULL,
    total_beneficiaries BIGINT,
    age65_suppression_flag VARCHAR,
    age65_total_claims BIGINT,
    age65_total_30day_fills DOUBLE,
    age65_total_drug_cost DOUBLE,
    age65_total_day_supply BIGINT,
    age65_bene_suppression_flag VARCHAR,
    age65_total_beneficiaries BIGINT,
    drug_class VARCHAR NOT NULL,
    matched_terms VARCHAR NOT NULL,
    is_selected_class BOOLEAN NOT NULL,
    marketed_name_type VARCHAR NOT NULL,
    scope_status VARCHAR NOT NULL,
    year INTEGER NOT NULL,
    cost_per_claim DOUBLE,
    cost_per_30day_fill DOUBLE,
    beneficiary_count_suppressed BOOLEAN NOT NULL
);
