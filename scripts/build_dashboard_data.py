"""Create dashboard-ready aggregates, concentration metrics, and opportunity rankings."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from common import DATABASE_PATH, PROJECT_ROOT, REPORTS_DIR, US_STATES, gini, write_json


def records(frame: pd.DataFrame) -> list[dict[str, object]]:
    clean = frame.replace({np.nan: None, np.inf: None, -np.inf: None})
    return json.loads(clean.to_json(orient="records"))


def compact_cube(frame: pd.DataFrame) -> tuple[dict[str, list[object]], list[list[object]]]:
    """Dictionary-encode repeated labels to keep the browser payload practical."""
    dimensions: dict[str, list[object]] = {}
    coded = frame.copy()
    for column in ["provider_state", "provider_specialty", "drug_class", "marketed_name_type"]:
        labels = sorted(coded[column].astype(str).unique().tolist())
        dimensions[column] = labels
        lookup = {label: index for index, label in enumerate(labels)}
        coded[column] = coded[column].map(lookup).astype(int)
    coded["total_claims"] = coded["total_claims"].round().astype(int)
    coded["total_30day_fills"] = coded["total_30day_fills"].round(1)
    coded["total_drug_cost"] = coded["total_drug_cost"].round(2)
    coded["prescribers"] = coded["prescribers"].round().astype(int)
    coded["selected_class_fills"] = coded["selected_class_fills"].round(1)
    columns = [
        "year", "provider_state", "provider_specialty", "drug_class", "marketed_name_type",
        "volume_decile", "total_claims", "total_30day_fills", "total_drug_cost", "prescribers",
        "selected_class_fills",
    ]
    matrix = json.loads(coded[columns].to_json(orient="values"))
    return dimensions, matrix


def percentile(series: pd.Series) -> pd.Series:
    return series.rank(method="average", pct=True).fillna(0.5)


def winsorized(series: pd.Series) -> pd.Series:
    valid = series.replace([np.inf, -np.inf], np.nan)
    if valid.notna().sum() < 4:
        return valid.fillna(0)
    return valid.clip(valid.quantile(0.05), valid.quantile(0.95)).fillna(valid.median())


def opportunity_table(frame: pd.DataFrame, dimension: str, weights: dict[str, dict[str, float]]) -> pd.DataFrame:
    pivot = frame.pivot(index=dimension, columns="year", values="total_30day_fills")
    current = frame[frame.year == 2024].set_index(dimension).copy()
    current["growth_2022_2024_cagr"] = ((pivot.get(2024) / pivot.get(2022).replace(0, np.nan)) ** 0.5 - 1).reindex(current.index)
    current["selected_class_share"] = current["selected_class_fills"] / current["total_30day_fills"].replace(0, np.nan)
    national_share = current["selected_class_fills"].sum() / current["total_30day_fills"].sum()
    current["peer_gap_pp"] = (national_share - current["selected_class_share"]).clip(lower=0) * 100
    current["scale_component"] = percentile(np.log1p(current["total_30day_fills"]))
    current["growth_component"] = percentile(winsorized(current["growth_2022_2024_cagr"]))
    current["class_gap_component"] = percentile(current["peer_gap_pp"])
    current["completeness_component"] = percentile(current["beneficiary_completeness"])
    components = ["scale", "growth", "class_gap", "completeness"]
    for scenario, scenario_weights in weights.items():
        current[f"score_{scenario}"] = 100 * sum(current[f"{name}_component"] * scenario_weights[name] for name in components)
        current[f"rank_{scenario}"] = current[f"score_{scenario}"].rank(method="min", ascending=False).astype(int)
    current["rank_range"] = current[[f"rank_{name}" for name in weights]].max(axis=1) - current[[f"rank_{name}" for name in weights]].min(axis=1)
    current["observed_interpretation"] = np.where(
        current["peer_gap_pp"] > 0,
        "Observed scale with selected-class share below the national benchmark",
        "Observed scale/growth signal without a positive selected-class gap",
    )
    return current.reset_index().sort_values("score_primary", ascending=False)


def concentration(con: duckdb.DuckDBPyConnection) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    summaries = []
    lorenz = []
    for year in [2022, 2023, 2024]:
        values = con.execute("SELECT total_30day_fills FROM v_provider_year WHERE year=? ORDER BY total_30day_fills", [year]).fetchnumpy()["total_30day_fills"].astype(float)
        total = values.sum()
        descending = np.sort(values)[::-1]
        n = len(values)
        item = {"year": year, "prescribers": n, "gini": gini(values), "hhi": float(np.square(values / total).sum()) if total else 0}
        for pct in [1, 5, 10, 20]:
            count = max(1, math.ceil(n * pct / 100))
            item[f"top_{pct}_share"] = float(descending[:count].sum() / total) if total else 0
        summaries.append(item)
        cumulative = np.insert(np.cumsum(np.sort(values)) / total, 0, 0) if total else np.zeros(n + 1)
        for pct in range(0, 101, 2):
            idx = min(n, round(n * pct / 100))
            lorenz.append({"year": year, "provider_pct": pct, "fill_pct": float(cumulative[idx] * 100)})
    return summaries, lorenz


def main() -> None:
    con = duckdb.connect(str(DATABASE_PATH), read_only=True)
    weights = json.loads((PROJECT_ROOT / "config" / "opportunity_weights.json").read_text(encoding="utf-8"))
    market = con.execute("SELECT * FROM v_market_year ORDER BY year").fetchdf()
    market["yoy_fill_growth"] = market.total_30day_fills.pct_change()
    classes = con.execute("SELECT * FROM v_class_year ORDER BY year, total_30day_fills DESC").fetchdf()
    products = con.execute("SELECT * FROM v_product_year ORDER BY year, total_30day_fills DESC").fetchdf()
    states = con.execute("SELECT * FROM v_state_year ORDER BY year, total_30day_fills DESC").fetchdf()
    specialties = con.execute("SELECT * FROM v_specialty_year ORDER BY year, total_30day_fills DESC").fetchdf()
    cities = con.execute("SELECT * FROM v_city_year QUALIFY ROW_NUMBER() OVER (PARTITION BY year ORDER BY total_30day_fills DESC) <= 100 ORDER BY year, total_30day_fills DESC").fetchdf()
    cube = con.execute("SELECT * FROM v_dashboard_cube").fetchdf()
    # Keep complete geography aggregates, but rank only identifiable U.S. locations.
    # CMS uses ZZ for unknown/foreign locations and AA/AE/AP for military mail; these
    # are valid source values but are not actionable state-market comparisons.
    ranked_states = states[states.provider_state.isin(US_STATES - {"ZZ", "AA", "AE", "AP"})].copy()
    state_opp = opportunity_table(ranked_states, "provider_state", weights)
    specialty_opp = opportunity_table(specialties, "provider_specialty", weights)
    concentration_summary, lorenz = concentration(con)
    scatter = products[products.year == 2024].nlargest(80, "total_30day_fills").copy()
    scatter["cost_per_fill"] = scatter.total_drug_cost / scatter.total_30day_fills.replace(0, np.nan)
    top_specialties = set(specialties.groupby("provider_specialty")["total_30day_fills"].sum().nlargest(40).index)
    cube.loc[~cube.provider_specialty.isin(top_specialties), "provider_specialty"] = "Other specialties"
    cube = cube.groupby(["year", "provider_state", "provider_specialty", "drug_class", "marketed_name_type", "volume_decile"], as_index=False).agg(
        total_claims=("total_claims", "sum"), total_30day_fills=("total_30day_fills", "sum"), total_drug_cost=("total_drug_cost", "sum"),
        prescribers=("prescribers", "sum"), selected_class_fills=("selected_class_fills", "sum")
    )
    cube_dimensions, cube_rows = compact_cube(cube)
    payload = {
        "meta": {
            "title": "RxMarketIQ: Medicare Part D Prescriber & Pharmaceutical Market Analytics",
            "source": "CMS Medicare Part D Prescribers — by Provider and Drug",
            "years": [2022, 2023, 2024], "latest_year": 2024,
            "source_last_modified": "2026-05-21", "dashboard_built_utc": pd.Timestamp.now("UTC").isoformat(),
            "selected_class": "GLP-1 receptor agonists (including fixed-ratio insulin/GLP-1)",
            "scope_note": "Observed Medicare Part D provider–drug cells in the documented diabetes ingredient map; weight-management brands Wegovy, Saxenda and Zepbound excluded.",
        },
        "market_year": records(market), "class_year": records(classes),
        "product_year": records(products.groupby("year", group_keys=False).head(60)),
        "state_year": records(states), "specialty_year": records(specialties), "city_year": records(cities),
        "cube_dimensions": cube_dimensions, "cube": cube_rows,
        "state_opportunity": records(state_opp), "specialty_opportunity": records(specialty_opp.head(60)),
        "concentration": concentration_summary, "lorenz": lorenz, "product_scatter": records(scatter),
        "opportunity_weights": weights,
        "limitations": [
            "CMS omits provider–drug cells with fewer than 11 claims; low-volume activity is undercounted.",
            "Beneficiary counts below 11 are blank and are never imputed.",
            "Claims are prescription fills including refills, not unique patients.",
            "Total drug cost includes plan, beneficiary, subsidies and other third-party amounts; it is not CMS payment and excludes rebates.",
            "Part D records do not represent a provider's complete practice and volume is not a quality measure.",
            "Opportunity scores are descriptive prioritization scenarios, not causal estimates or targeting instructions.",
            "Provider-by-drug files do not contain a rural/urban field; no location proxy was inferred.",
        ],
    }
    con.close()
    dashboard_path = PROJECT_ROOT / "dashboard" / "dashboard_data.json"
    public_path = PROJECT_ROOT / "public" / "dashboard_data.json"
    write_json(dashboard_path, payload)
    shutil.copy2(dashboard_path, public_path)
    latest = market[market.year == 2024].iloc[0].to_dict()
    prior = market[market.year == 2023].iloc[0].to_dict()
    headline = {
        "latest": {key: float(value) if isinstance(value, (np.floating, float)) else int(value) if isinstance(value, (np.integer,)) else value for key, value in latest.items()},
        "yoy_fill_growth": float(latest["total_30day_fills"] / prior["total_30day_fills"] - 1),
        "top_class": records(classes[classes.year == 2024].nlargest(1, "total_30day_fills"))[0],
        "top_product": records(products[products.year == 2024].nlargest(1, "total_30day_fills"))[0],
        "top_state": records(states[states.year == 2024].nlargest(1, "total_30day_fills"))[0],
        "top_specialty": records(specialties[specialties.year == 2024].nlargest(1, "total_30day_fills"))[0],
        "concentration_2024": [row for row in concentration_summary if row["year"] == 2024][0],
        "top_opportunities": records(state_opp.head(10)),
    }
    write_json(REPORTS_DIR / "headline_metrics.json", headline)
    print(f"Wrote dashboard payload: {dashboard_path} ({dashboard_path.stat().st_size / 1_000_000:.1f} MB)")


if __name__ == "__main__":
    main()
