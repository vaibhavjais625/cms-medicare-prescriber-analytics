"""Build DuckDB, analytical views, and execute all named business queries."""

from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
import pandas as pd

from common import DATABASE_PATH, PROCESSED_DIR, PROJECT_ROOT, REPORTS_DIR, write_json


def parse_named_queries(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^-- name:\s*([a-zA-Z0-9_]+)\s*$", text)
    return [(parts[index], parts[index + 1].strip()) for index in range(1, len(parts), 2)]


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows returned."
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
    header = "| " + " | ".join(cell(column) for column in frame.columns) + " |"
    separator = "|" + "|".join("---" for _ in frame.columns) + "|"
    body = ["| " + " | ".join(cell(value) for value in row) + " |" for row in frame.itertuples(index=False, name=None)]
    return "\n".join([header, separator, *body])


def build_database() -> dict[str, object]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.unlink(missing_ok=True)
    con = duckdb.connect(str(DATABASE_PATH))
    parquet_glob = str(PROCESSED_DIR / "year=*" / "provider_drug.parquet").replace("\\", "/")
    con.execute("PRAGMA threads=4")
    con.execute(f"CREATE TABLE fact_provider_drug AS SELECT * FROM read_parquet('{parquet_glob}', hive_partitioning=false)")
    con.execute((PROJECT_ROOT / "sql" / "analytical_views.sql").read_text(encoding="utf-8"))
    con.execute("CREATE INDEX idx_fact_year_npi ON fact_provider_drug(year, provider_npi)")
    con.execute("CREATE INDEX idx_fact_year_class ON fact_provider_drug(year, drug_class)")
    row_count = con.execute("SELECT COUNT(*) FROM fact_provider_drug").fetchone()[0]
    results: dict[str, object] = {}
    output_lines = ["# Executed SQL analysis", "", "Every query below was executed against `database/rxmarketiq.duckdb`.", ""]
    queries = parse_named_queries((PROJECT_ROOT / "sql" / "analysis_queries.sql").read_text(encoding="utf-8"))
    for name, sql in queries:
        frame = con.execute(sql).fetchdf()
        results[name] = json.loads(frame.to_json(orient="records", date_format="iso"))
        output_lines += [f"## {name.replace('_', ' ').title()}", "", markdown_table(frame), ""]
    con.close()
    write_json(REPORTS_DIR / "sql_results.json", results)
    (REPORTS_DIR / "sql_analysis_results.md").write_text("\n".join(output_lines), encoding="utf-8")
    summary = {"database": str(DATABASE_PATH), "fact_row_count": row_count, "named_queries_executed": len(queries), "query_names": [name for name, _ in queries]}
    write_json(REPORTS_DIR / "database_build_summary.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(build_database(), indent=2))
