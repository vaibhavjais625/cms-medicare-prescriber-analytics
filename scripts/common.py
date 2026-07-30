"""Shared project configuration and deterministic metric helpers."""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATABASE_PATH = PROJECT_ROOT / "database" / "rxmarketiq.duckdb"

YEARS = (2022, 2023, 2024)

DATASETS = {
    2022: {
        "uuid": "b101b457-ffa4-49bb-8fd9-27c1266086e2",
        "file_name": "MUP_DPR_RY24_P04_V10_DY22_NPIBN.csv",
        "url": "https://data.cms.gov/sites/default/files/2024-05/18f82097-61a6-4889-9941-9a0b6ad7523c/MUP_DPR_RY24_P04_V10_DY22_NPIBN.csv",
        "modified": "2024-06-04",
    },
    2023: {
        "uuid": "e54db557-cd82-4e91-a0fe-61aad5865d69",
        "file_name": "MUP_DPR_RY25_P04_V10_DY23_NPIBN.csv",
        "url": "https://data.cms.gov/sites/default/files/2025-04/0d5915ce-002c-4d87-bde8-24ffb08bb6cc/MUP_DPR_RY25_P04_V10_DY23_NPIBN.csv",
        "modified": "2025-09-09",
    },
    2024: {
        "uuid": "d5aa71a8-dcc0-4570-8bcf-bd39deac69fe",
        "file_name": "MUP_DPR_RY26_P04_V10_DY24_NPIBN.csv",
        "url": "https://data.cms.gov/sites/default/files/2026-05/0ae165f4-eb44-495d-8cac-67f4571b6b83/MUP_DPR_RY26_P04_V10_DY24_NPIBN.csv",
        "modified": "2026-05-21",
    },
}

EXPECTED_COLUMNS = [
    "Prscrbr_NPI", "Prscrbr_Last_Org_Name", "Prscrbr_First_Name", "Prscrbr_City",
    "Prscrbr_State_Abrvtn", "Prscrbr_State_FIPS", "Prscrbr_Type", "Prscrbr_Type_Src",
    "Brnd_Name", "Gnrc_Name", "Tot_Clms", "Tot_30day_Fills", "Tot_Day_Suply",
    "Tot_Drug_Cst", "Tot_Benes", "GE65_Sprsn_Flag", "GE65_Tot_Clms",
    "GE65_Tot_30day_Fills", "GE65_Tot_Drug_Cst", "GE65_Tot_Day_Suply",
    "GE65_Bene_Sprsn_Flag", "GE65_Tot_Benes",
]

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN",
    "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY", "PR", "VI", "GU", "AS", "MP", "AA", "AE", "AP", "ZZ",
}


def normalize_text(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def load_mapping() -> list[dict[str, object]]:
    with (PROJECT_ROOT / "config" / "drug_mapping.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["priority"] = int(row["priority"])
    return sorted(rows, key=lambda row: int(row["priority"]))


def load_excluded_brands() -> set[str]:
    lines = (PROJECT_ROOT / "config" / "excluded_brands.txt").read_text(encoding="utf-8").splitlines()
    return {normalize_text(line) for line in lines if line.strip() and not line.lstrip().startswith("#")}


def load_excluded_generic_patterns() -> set[str]:
    lines = (PROJECT_ROOT / "config" / "excluded_generic_patterns.txt").read_text(encoding="utf-8").splitlines()
    return {normalize_text(line) for line in lines if line.strip() and not line.lstrip().startswith("#")}


def classify_drug(
    brand: object,
    generic: object,
    mapping: list[dict[str, object]] | None = None,
    excluded_generic_patterns: set[str] | None = None,
) -> dict[str, object]:
    mapping = mapping or load_mapping()
    excluded_generic_patterns = excluded_generic_patterns or load_excluded_generic_patterns()
    generic_norm = normalize_text(generic)
    brand_norm = normalize_text(brand)
    if any(pattern in generic_norm for pattern in excluded_generic_patterns):
        return {
            "drug_class": "Excluded non-drug device/supply",
            "matched_terms": "insulin",
            "is_selected_class": False,
            "marketed_name_type": "not applicable",
            "scope_status": "excluded_non_drug",
        }
    hits = [row for row in mapping if str(row["match_term"]) in generic_norm]
    components = {str(row["component_class"]) for row in hits}
    if "Insulin" in components and "GLP-1 receptor agonists" in components:
        drug_class = "Fixed-ratio insulin/GLP-1"
    elif "SGLT2 inhibitors" in components and "DPP-4 inhibitors" in components:
        drug_class = "SGLT2/DPP-4 combination"
    elif hits:
        drug_class = str(hits[0]["component_class"])
    else:
        drug_class = "Unmapped"
    selected = drug_class in {"GLP-1 receptor agonists", "Fixed-ratio insulin/GLP-1"}
    marketed_name_type = "generic-name listed" if brand_norm == generic_norm else "brand-identifiable"
    return {
        "drug_class": drug_class,
        "matched_terms": "|".join(sorted({str(row["match_term"]) for row in hits})),
        "is_selected_class": selected,
        "marketed_name_type": marketed_name_type,
        "scope_status": "included",
    }


def safe_divide(numerator: float, denominator: float) -> float | None:
    return None if denominator in (0, None) or not math.isfinite(float(denominator)) else numerator / denominator


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def gini(values: Iterable[float]) -> float:
    ordered = sorted(float(value) for value in values if value is not None and float(value) >= 0)
    if not ordered or sum(ordered) == 0:
        return 0.0
    n = len(ordered)
    weighted = sum((idx + 1) * value for idx, value in enumerate(ordered))
    return (2 * weighted) / (n * sum(ordered)) - (n + 1) / n
