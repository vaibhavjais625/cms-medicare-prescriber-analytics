"""End-to-end integrity tests against executed project artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "rxmarketiq.duckdb"


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect(str(DB), read_only=True)
    yield connection
    connection.close()


def scalar(con, sql: str):
    return con.execute(sql).fetchone()[0]


def test_required_artifacts_exist():
    required = [
        DB, ROOT / "public" / "dashboard_data.json", ROOT / "reports" / "sql_results.json",
        ROOT / "data" / "raw" / "cms_filtered" / "download_manifest.json",
    ]
    assert all(path.exists() and path.stat().st_size > 0 for path in required)


def test_cross_year_schema_is_identical(con):
    columns = con.execute("DESCRIBE fact_provider_drug").fetchdf()["column_name"].tolist()
    assert len(columns) >= 30
    assert scalar(con, "SELECT COUNT(DISTINCT year) FROM fact_provider_drug") == 3
    assert set(row[0] for row in con.execute("SELECT DISTINCT year FROM fact_provider_drug").fetchall()) == {2022, 2023, 2024}


def test_provider_drug_grain_unique(con):
    duplicates = scalar(con, """
        SELECT COUNT(*) FROM (
          SELECT year, provider_npi, brand_name, generic_name, COUNT(*) n
          FROM fact_provider_drug GROUP BY ALL HAVING COUNT(*) > 1
        )
    """)
    assert duplicates == 0


def test_required_fields_not_null(con):
    invalid = scalar(con, """
        SELECT COUNT(*) FROM fact_provider_drug
        WHERE provider_npi IS NULL OR LENGTH(provider_npi) <> 10
           OR brand_name IS NULL OR generic_name IS NULL OR drug_class IS NULL
           OR total_claims IS NULL OR total_30day_fills IS NULL OR total_drug_cost IS NULL
    """)
    assert invalid == 0


def test_numeric_domains(con):
    invalid = scalar(con, """
        SELECT COUNT(*) FROM fact_provider_drug
        WHERE total_claims < 11 OR total_30day_fills < 0 OR total_day_supply < 0 OR total_drug_cost < 0
           OR (total_beneficiaries IS NOT NULL AND total_beneficiaries < 11)
    """)
    assert invalid == 0


def test_mapping_is_complete(con):
    assert scalar(con, "SELECT COUNT(*) FROM fact_provider_drug WHERE drug_class='Unmapped'") == 0
    assert scalar(con, "SELECT COUNT(*) FROM fact_provider_drug WHERE scope_status <> 'included'") == 0
    assert scalar(con, "SELECT COUNT(*) FROM fact_provider_drug WHERE lower(generic_name) LIKE '%pump%' OR lower(generic_name) LIKE '%syringe%' OR lower(generic_name) LIKE '%insulin device%' OR lower(generic_name) LIKE '%pen,reusable%'") == 0
    assert scalar(con, "SELECT COUNT(*) FROM fact_provider_drug WHERE lower(brand_name) IN ('wegovy','saxenda','zepbound')") == 0


def test_raw_processed_row_reconciliation(con):
    manifests = json.loads((ROOT / "data" / "raw" / "cms_filtered" / "download_manifest.json").read_text(encoding="utf-8"))
    transforms = {item["year"]: item for item in json.loads((ROOT / "reports" / "transform_summary.json").read_text(encoding="utf-8"))}
    for item in manifests:
        observed = scalar(con, f"SELECT COUNT(*) FROM fact_provider_drug WHERE year={int(item['reporting_year'])}")
        transform = transforms[item["reporting_year"]]
        assert item["filtered_row_count"] == transform["input_candidate_rows"]
        assert observed + transform["excluded_non_drug_rows"] == item["filtered_row_count"]


def test_class_aggregation_reconciles(con):
    fact = con.execute("SELECT year, SUM(total_claims), SUM(total_30day_fills), SUM(total_drug_cost) FROM fact_provider_drug GROUP BY year ORDER BY year").fetchall()
    view = con.execute("SELECT year, SUM(total_claims), SUM(total_30day_fills), SUM(total_drug_cost) FROM v_class_year GROUP BY year ORDER BY year").fetchall()
    for left, right in zip(fact, view):
        assert left[0] == right[0]
        for actual, expected in zip(left[1:], right[1:]):
            assert actual == pytest.approx(expected, rel=1e-10)


def test_dashboard_join_does_not_multiply_rows(con):
    fact = con.execute("SELECT SUM(total_claims), SUM(total_30day_fills), SUM(total_drug_cost) FROM fact_provider_drug").fetchone()
    cube = con.execute("SELECT SUM(total_claims), SUM(total_30day_fills), SUM(total_drug_cost) FROM v_dashboard_cube").fetchone()
    for actual, expected in zip(cube, fact):
        assert actual == pytest.approx(expected, rel=1e-10)


def test_suppression_and_missingness_are_preserved(con):
    suppressed = scalar(con, "SELECT COUNT(*) FROM fact_provider_drug WHERE beneficiary_count_suppressed")
    null_benes = scalar(con, "SELECT COUNT(*) FROM fact_provider_drug WHERE total_beneficiaries IS NULL")
    assert suppressed == null_benes
    assert suppressed > 0


def test_dashboard_payload_reconciles(con):
    payload = json.loads((ROOT / "public" / "dashboard_data.json").read_text(encoding="utf-8"))
    latest = next(row for row in payload["market_year"] if row["year"] == 2024)
    source = con.execute("SELECT total_claims, total_30day_fills, total_drug_cost FROM v_market_year WHERE year=2024").fetchone()
    assert latest["total_claims"] == pytest.approx(source[0])
    assert latest["total_30day_fills"] == pytest.approx(source[1])
    assert latest["total_drug_cost"] == pytest.approx(source[2])
    assert all(0 <= row["score_primary"] <= 100 for row in payload["state_opportunity"])


def test_named_sql_queries_executed():
    results = json.loads((ROOT / "reports" / "sql_results.json").read_text(encoding="utf-8"))
    expected = {"market_size_and_growth", "class_leaders", "product_leaders_2024", "state_leaders_2024", "specialty_leaders_2024", "provider_grain_validation", "outlier_review_2024"}
    assert expected.issubset(results)
    assert results["provider_grain_validation"] == []
