"""Chunked profiling of the exact filtered CMS source records."""

from __future__ import annotations

import argparse
import json
from collections import Counter

import pandas as pd

from common import (
    EXPECTED_COLUMNS,
    RAW_DIR,
    REPORTS_DIR,
    YEARS,
    classify_drug,
    load_excluded_generic_patterns,
    load_mapping,
    write_json,
)


def profile_year(year: int) -> dict[str, object]:
    path = RAW_DIR / "cms_filtered" / f"cms_partd_provider_drug_diabetes_{year}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run scripts/download_data.py first")
    nulls = Counter()
    unique_drugs: set[tuple[str, str]] = set()
    duplicate_keys = 0
    seen: set[tuple[str, str, str]] = set()
    rows = 0
    numeric_min = {name: float("inf") for name in ["Tot_Clms", "Tot_30day_Fills", "Tot_Day_Suply", "Tot_Drug_Cst"]}
    numeric_max = {name: float("-inf") for name in numeric_min}
    observed_parts = []
    for chunk in pd.read_csv(path, dtype=str, chunksize=200_000, keep_default_na=False):
        if list(chunk.columns) != EXPECTED_COLUMNS:
            raise AssertionError(f"{year} schema mismatch")
        rows += len(chunk)
        for column in chunk.columns:
            nulls[column] += int(chunk[column].eq("").sum())
        pairs = chunk[["Brnd_Name", "Gnrc_Name"]].drop_duplicates()
        unique_drugs.update(map(tuple, pairs.itertuples(index=False, name=None)))
        keys = list(zip(chunk["Prscrbr_NPI"], chunk["Brnd_Name"], chunk["Gnrc_Name"]))
        for key in keys:
            if key in seen:
                duplicate_keys += 1
            seen.add(key)
        for column in numeric_min:
            values = pd.to_numeric(chunk[column], errors="coerce")
            numeric_min[column] = min(numeric_min[column], float(values.min()))
            numeric_max[column] = max(numeric_max[column], float(values.max()))
    observed = pd.DataFrame(sorted(unique_drugs), columns=["brand_name", "generic_name"])
    observed["year"] = year
    observed_parts.append(observed)
    return {
        "year": year,
        "row_count": rows,
        "column_count": len(EXPECTED_COLUMNS),
        "duplicate_provider_drug_keys": duplicate_keys,
        "distinct_brand_generic_pairs": len(unique_drugs),
        "null_counts": dict(nulls),
        "numeric_min": numeric_min,
        "numeric_max": numeric_max,
        "observed_drugs": observed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, default=list(YEARS))
    args = parser.parse_args()
    profiles = [profile_year(year) for year in args.years]
    observed = pd.concat([item.pop("observed_drugs") for item in profiles], ignore_index=True).drop_duplicates()
    observed.to_csv(REPORTS_DIR / "observed_drug_names.csv", index=False)
    mapping = load_mapping()
    exclusions = load_excluded_generic_patterns()
    decisions = [classify_drug(brand, generic, mapping, exclusions) for brand, generic in zip(observed["brand_name"], observed["generic_name"])]
    audit = observed.copy()
    audit["drug_class"] = [item["drug_class"] for item in decisions]
    audit["matched_terms"] = [item["matched_terms"] for item in decisions]
    audit["marketed_name_type"] = [item["marketed_name_type"] for item in decisions]
    audit["scope_status"] = [item["scope_status"] for item in decisions]
    audit.sort_values(["scope_status", "drug_class", "generic_name", "brand_name", "year"]).to_csv(
        REPORTS_DIR / "drug_scope_audit.csv", index=False
    )
    write_json(REPORTS_DIR / "data_profile.json", profiles)
    lines = ["# Data quality profile", "", "Generated from the exact filtered CMS source extracts.", ""]
    for item in profiles:
        bene_missing = item["null_counts"]["Tot_Benes"]
        lines += [
            f"## {item['year']}", "",
            f"- Rows: {item['row_count']:,}; columns: {item['column_count']}.",
            f"- Distinct brand/generic pairs: {item['distinct_brand_generic_pairs']:,}.",
            f"- Duplicate provider–brand–generic keys: {item['duplicate_provider_drug_keys']:,}.",
            f"- Suppressed/blank beneficiary counts: {bene_missing:,} ({bene_missing / max(item['row_count'], 1):.1%} of rows).",
            f"- Total claims range: {item['numeric_min']['Tot_Clms']:,.0f} to {item['numeric_max']['Tot_Clms']:,.0f}.", "",
        ]
    lines += [
        "## Drug-scope audit", "",
        f"The version-controlled map classified {int(audit['scope_status'].eq('included').sum()):,} observed year/product combinations as included and "
        f"{int(audit['scope_status'].eq('excluded_non_drug').sum()):,} as non-drug devices or supplies. "
        "See `reports/drug_scope_audit.csv` for every observed brand/generic/year decision.", "",
        "## Interpretation", "",
        "CMS omits provider–drug cells with fewer than 11 claims and blanks beneficiary counts below 11. "
        "Accordingly, the extract is left-censored and beneficiary-based rates are incomplete. No suppressed value is imputed.", "",
    ]
    (REPORTS_DIR / "data_quality_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
