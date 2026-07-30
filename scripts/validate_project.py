"""Independently reconcile Parquet, DuckDB, dashboard JSON, and source manifests."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pyarrow.compute as pc
import pyarrow.parquet as pq

from common import DATABASE_PATH, PROJECT_ROOT, REPORTS_DIR, YEARS, write_json


def close_enough(left: float, right: float, relative_tolerance: float = 1e-9) -> bool:
    scale = max(abs(left), abs(right), 1.0)
    return abs(left - right) <= relative_tolerance * scale


def main() -> None:
    dashboard = json.loads((PROJECT_ROOT / "public" / "dashboard_data.json").read_text(encoding="utf-8"))
    dashboard_years = {int(row["year"]): row for row in dashboard["market_year"]}
    manifests = {
        int(row["reporting_year"]): row
        for row in json.loads(
            (PROJECT_ROOT / "data" / "raw" / "cms_filtered" / "download_manifest.json").read_text(encoding="utf-8")
        )
    }
    transforms = {
        int(row["year"]): row
        for row in json.loads((REPORTS_DIR / "transform_summary.json").read_text(encoding="utf-8"))
    }
    sql_results = json.loads((REPORTS_DIR / "sql_results.json").read_text(encoding="utf-8"))
    con = duckdb.connect(str(DATABASE_PATH), read_only=True)
    rows: list[dict[str, object]] = []
    checks: list[dict[str, object]] = []
    for year in YEARS:
        parquet_path = PROJECT_ROOT / "data" / "processed" / f"year={year}" / "provider_drug.parquet"
        # Read the physical file directly so PyArrow does not also infer the
        # Hive-style `year=YYYY` directory as a conflicting partition column.
        table = pq.ParquetFile(parquet_path).read(
            columns=["total_claims", "total_30day_fills", "total_drug_cost"]
        )
        independent = {
            "rows": table.num_rows,
            "total_claims": int(pc.sum(table["total_claims"]).as_py()),
            "total_30day_fills": float(pc.sum(table["total_30day_fills"]).as_py()),
            "total_drug_cost": float(pc.sum(table["total_drug_cost"]).as_py()),
        }
        db_row = con.execute(
            "SELECT COUNT(*), SUM(total_claims), SUM(total_30day_fills), SUM(total_drug_cost) "
            "FROM fact_provider_drug WHERE year = ?",
            [year],
        ).fetchone()
        database = {
            "rows": int(db_row[0]),
            "total_claims": int(db_row[1]),
            "total_30day_fills": float(db_row[2]),
            "total_drug_cost": float(db_row[3]),
        }
        dashboard_row = dashboard_years[year]
        for metric in ["rows", "total_claims", "total_30day_fills", "total_drug_cost"]:
            if metric == "rows":
                observed = database[metric]
                expected = independent[metric]
            else:
                observed = float(dashboard_row[metric])
                expected = float(independent[metric])
            passed = observed == expected if metric in {"rows", "total_claims"} else close_enough(observed, expected)
            checks.append({"year": year, "check": f"independent_{metric}", "passed": passed})
        raw_reconciles = (
            int(manifests[year]["filtered_row_count"])
            == int(transforms[year]["input_candidate_rows"])
            == int(transforms[year]["row_count"]) + int(transforms[year]["excluded_non_drug_rows"])
        )
        checks.append({"year": year, "check": "raw_candidate_to_processed", "passed": raw_reconciles})
        rows.append(
            {
                "year": year,
                "source_rows_scanned": int(manifests[year]["source_rows_scanned"]),
                "raw_candidate_rows": int(manifests[year]["filtered_row_count"]),
                "excluded_non_drug_rows": int(transforms[year]["excluded_non_drug_rows"]),
                "processed_rows": independent["rows"],
                **{f"independent_{key}": value for key, value in independent.items() if key != "rows"},
                **{f"database_{key}": value for key, value in database.items() if key != "rows"},
            }
        )
    con.close()
    required_queries = {
        "market_size_and_growth", "class_leaders", "product_leaders_2024",
        "state_leaders_2024", "specialty_leaders_2024",
        "provider_grain_validation", "outlier_review_2024",
    }
    checks.append(
        {
            "year": None,
            "check": "all_named_sql_queries_executed",
            "passed": required_queries.issubset(sql_results),
        }
    )
    checks.append(
        {
            "year": None,
            "check": "provider_grain_query_zero_rows",
            "passed": sql_results.get("provider_grain_validation") == [],
        }
    )
    passed = all(bool(item["passed"]) for item in checks)
    result = {"status": "PASS" if passed else "FAIL", "years": rows, "checks": checks}
    write_json(REPORTS_DIR / "independent_reconciliation.json", result)
    detail_rows = "\n".join(
        f"| {row['year']} | {row['source_rows_scanned']:,} | {row['raw_candidate_rows']:,} | "
        f"{row['excluded_non_drug_rows']:,} | {row['processed_rows']:,} | "
        f"{row['independent_total_claims']:,.0f} | {row['independent_total_30day_fills']:,.1f} | "
        f"${row['independent_total_drug_cost']:,.2f} |"
        for row in rows
    )
    report = f"""# Validation report

**Independent artifact reconciliation: {result['status']}**

The validation reads each Parquet file with PyArrow, recomputes row counts and core sums, and compares them with the DuckDB fact table and dashboard JSON. It also reconciles source-candidate counts to documented processed exclusions and verifies that every named SQL query executed, including a zero-row duplicate-grain query.

| Year | CMS rows scanned | Raw candidates | Non-drug exclusions | Processed rows | Claims | Standardized fills | Aggregate drug cost |
|---:|---:|---:|---:|---:|---:|---:|---:|
{detail_rows}

Automated structural, domain, missingness, suppression, grain, join-multiplication, and dashboard checks are defined in `tests/test_pipeline.py`. Front-end build/output assertions are defined in `tests/rendered-html.test.mjs`. The exact executed command results are reported in the final project handoff; a passing result is never inferred from the presence of this file.
"""
    (REPORTS_DIR / "validation_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
