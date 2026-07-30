"""Clean and standardize CMS extracts into typed, partitioned Parquet files."""

from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from common import PROCESSED_DIR, RAW_DIR, REPORTS_DIR, YEARS, classify_drug, load_excluded_generic_patterns, load_mapping, write_json

RENAME = {
    "Prscrbr_NPI": "provider_npi", "Prscrbr_Last_Org_Name": "provider_last_org_name",
    "Prscrbr_First_Name": "provider_first_name", "Prscrbr_City": "provider_city",
    "Prscrbr_State_Abrvtn": "provider_state", "Prscrbr_State_FIPS": "provider_state_fips",
    "Prscrbr_Type": "provider_specialty", "Prscrbr_Type_Src": "provider_type_source",
    "Brnd_Name": "brand_name", "Gnrc_Name": "generic_name", "Tot_Clms": "total_claims",
    "Tot_30day_Fills": "total_30day_fills", "Tot_Day_Suply": "total_day_supply",
    "Tot_Drug_Cst": "total_drug_cost", "Tot_Benes": "total_beneficiaries",
    "GE65_Sprsn_Flag": "age65_suppression_flag", "GE65_Tot_Clms": "age65_total_claims",
    "GE65_Tot_30day_Fills": "age65_total_30day_fills", "GE65_Tot_Drug_Cst": "age65_total_drug_cost",
    "GE65_Tot_Day_Suply": "age65_total_day_supply", "GE65_Bene_Sprsn_Flag": "age65_bene_suppression_flag",
    "GE65_Tot_Benes": "age65_total_beneficiaries",
}

INTEGER_COLUMNS = ["total_claims", "total_day_supply", "total_beneficiaries", "age65_total_claims", "age65_total_day_supply", "age65_total_beneficiaries"]
FLOAT_COLUMNS = ["total_30day_fills", "total_drug_cost", "age65_total_30day_fills", "age65_total_drug_cost"]


def transform_chunk(chunk: pd.DataFrame, year: int, mapping: list[dict[str, object]], excluded_patterns: set[str]) -> pd.DataFrame:
    frame = chunk.rename(columns=RENAME)
    frame["provider_npi"] = frame["provider_npi"].astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(10)
    frame["provider_masked_id"] = "NPI-******" + frame["provider_npi"].str[-4:]
    text_columns = [column for column in RENAME.values() if column not in INTEGER_COLUMNS + FLOAT_COLUMNS]
    for column in text_columns:
        frame[column] = frame[column].astype("string").fillna("").str.strip()
    for column in INTEGER_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
    for column in FLOAT_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Float64")
    decisions = [classify_drug(brand, generic, mapping, excluded_patterns) for brand, generic in zip(frame["brand_name"], frame["generic_name"])]
    frame["drug_class"] = [item["drug_class"] for item in decisions]
    frame["matched_terms"] = [item["matched_terms"] for item in decisions]
    frame["is_selected_class"] = [item["is_selected_class"] for item in decisions]
    frame["marketed_name_type"] = [item["marketed_name_type"] for item in decisions]
    frame["scope_status"] = [item["scope_status"] for item in decisions]
    frame["year"] = year
    frame["cost_per_claim"] = frame["total_drug_cost"] / frame["total_claims"].replace({0: pd.NA})
    frame["cost_per_30day_fill"] = frame["total_drug_cost"] / frame["total_30day_fills"].replace({0: pd.NA})
    frame["beneficiary_count_suppressed"] = frame["total_beneficiaries"].isna()
    return frame


def transform_year(year: int) -> dict[str, object]:
    source = RAW_DIR / "cms_filtered" / f"cms_partd_provider_drug_diabetes_{year}.csv"
    destination = PROCESSED_DIR / f"year={year}" / "provider_drug.parquet"
    destination.parent.mkdir(parents=True, exist_ok=True)
    mapping = load_mapping()
    excluded_patterns = load_excluded_generic_patterns()
    writer = None
    input_row_count = row_count = unmapped = excluded_non_drug_rows = 0
    class_counts: dict[str, int] = {}
    try:
        for chunk in pd.read_csv(source, dtype=str, chunksize=150_000, keep_default_na=False, na_values=[""]):
            transformed = transform_chunk(chunk, year, mapping, excluded_patterns)
            input_row_count += len(transformed)
            excluded_non_drug_rows += int(transformed["scope_status"].eq("excluded_non_drug").sum())
            transformed = transformed[transformed["scope_status"].eq("included")].copy()
            unmapped += int(transformed["drug_class"].eq("Unmapped").sum())
            row_count += len(transformed)
            for key, value in transformed["drug_class"].value_counts().items():
                class_counts[str(key)] = class_counts.get(str(key), 0) + int(value)
            table = pa.Table.from_pandas(transformed, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(destination, table.schema, compression="zstd")
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()
    if unmapped:
        raise AssertionError(f"{year}: {unmapped} source rows could not be mapped")
    return {"year": year, "input_candidate_rows": input_row_count, "excluded_non_drug_rows": excluded_non_drug_rows, "row_count": row_count, "unmapped_rows": unmapped, "class_row_counts": class_counts, "file": str(destination)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, default=list(YEARS))
    args = parser.parse_args()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    results = [transform_year(year) for year in args.years]
    write_json(REPORTS_DIR / "transform_summary.json", results)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
